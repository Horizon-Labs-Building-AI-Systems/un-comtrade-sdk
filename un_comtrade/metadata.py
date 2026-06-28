"""Metadata service for the UN Comtrade Python SDK.

This module implements the L3 Metadata Layer per
`003_ARCHITECTURE.md` §5.3 and `008_METADATA_LAYER_SPEC.md`.

Components:

- `MetadataDownloader` (P1-013) — owns endpoint routing
  and HTTP integration. Returns raw `HttpResponse`
  objects without parsing or persistence.
- `MetadataService` (P1-012) — the public surface that
  composes the downloader (and, when wired, the cache
  + parsing) and exposes the 18 reference-catalogue
  methods (M01-M18). In this build the service is a
  SKELETON: methods declare their documented signatures
  and raise `NotImplementedError`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Mapping

from .models import (
    Classification,
    Country,
    Frequency,
    HSCode,
    Partner,
    TradeFlow,
    TransportMode,
)


if TYPE_CHECKING:
    from .cache import MetadataCache
    from .parser import MetadataParser
    from .transport import HttpResponse, HttpTransport


__all__ = [
    "DEFAULT_REFERENCE_BASE_PATH",
    "ENDPOINT_FILENAMES",
    "MetadataDownloader",
    "MetadataService",
    "PARAMETERIZED_RESOURCES",
    "SUPPORTED_FETCHERS",
]


def _parse_iso_date(value: object) -> Any:
    """Parse an ISO-8601 date string into a `datetime.date`.

    Accepts `None`, `datetime.date` (returned as-is),
    or `str` (date-only or date+time). Returns `None`
    for any unparseable value.
    """
    if value is None or value == "":
        return None
    from datetime import date

    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    text = value.split("T", 1)[0].split(" ", 1)[0]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


#: Default base path for the reference catalogue endpoints
#: (per `005_API_ENDPOINT_CATALOG.md` M1-M15). The
#: service joins this with the configured base URL.
DEFAULT_REFERENCE_BASE_PATH: str = "/files/v1/app/reference"


#: Mapping of resource id (R01-R17) to upstream filename
#: under the reference base path. Filenames containing
#: ``{placeholders}`` are parameterised via ``str.format``.
#: Sources: `005_API_ENDPOINT_CATALOG.md` M1-M15.
ENDPOINT_FILENAMES: Mapping[str, str] = {
    "R01": "ListofReferences.json",            # M1
    "R02": "Reporters.json",                   # M2
    "R03": "partnerAreas.json",                # M3
    "R04": "HS.json",                          # M4
    "R05": "H{edition}.json",                  # M5 (HS per-edition)
    "R06": "S{edition}.json",                  # M6 (SITC)
    "R07": "B{edition}.json",                  # M7 (BEC)
    "R08": "EB{edition}.json",                 # M8 (EBOPS)
    "R09": "Frequency.json",                   # M9
    "R10": "tradeRegimes.json",                # M10
    "R11": "CustomsCodes.json",               # M11
    "R12": "ModeOfTransportCodes.json",       # M12
    "R13": "ModeOfSupply.json",               # M13
    "R14": "QuantityUnits.json",              # M14
    "R15": "TradeDataItems.json",             # M15
    # R16 (data availability) and R17 (publication notes)
    # endpoints are documented but unverified; placeholder
    # filenames are reserved for the future fetcher task.
    "R16": "dataAvailability.json",
    "R17": "PublicationNotes.json",
}

#: Resource ids whose filenames contain ``{placeholders}``.
#: Callers must pass the relevant keyword (typically
#: ``edition``) when downloading these resources.
PARAMETERIZED_RESOURCES: frozenset[str] = frozenset(
    {"R05", "R06", "R07", "R08"}
)


#: Resource ids whose catalogue fetchers are implemented
#: in this build. Other resources (R06/R07/R08 SITC/BEC/EBOPS,
#: R11 customs procedures, R13 modes of supply, R16 data
#: availability, R17 publication notes) require their own
#: canonical models before the fetchers can be wired.
SUPPORTED_FETCHERS: frozenset[str] = frozenset(
    {"R01", "R02", "R03", "R04", "R05", "R09", "R10", "R12", "R14", "R15"}
)


# ---------------------------------------------------------------------------
# MetadataDownloader
# ---------------------------------------------------------------------------


class MetadataDownloader:
    """L3 metadata download mechanism.

    Owns endpoint routing and HTTP integration for the
    reference catalogue. Returns raw `HttpResponse`
    objects without parsing or persistence — the
    catalogue fetcher task is responsible for those.

    The downloader is owned by `MetadataService`. It is
    duck-typed against `HttpTransport` for ease of
    testing with `httpx.MockTransport`.
    """

    #: Resource ids recognised by the downloader.
    RESOURCE_IDS: frozenset[str] = frozenset(ENDPOINT_FILENAMES.keys())

    def __init__(
        self,
        transport: "HttpTransport",
        *,
        base_path: str = DEFAULT_REFERENCE_BASE_PATH,
    ) -> None:
        """Construct a metadata downloader.

        Parameters
        ----------
        transport
            The HTTP transport used to issue upstream GETs.
        base_path
            The base path under the transport's configured
            base URL. Defaults to the documented UN Comtrade
            reference path. Tests may override.
        """
        self._transport: "HttpTransport" = transport
        self._base_path: str = base_path.rstrip("/")

    # ----- Properties -----------------------------------------------------

    @property
    def transport(self) -> "HttpTransport":
        """The HTTP transport used for upstream calls."""
        return self._transport

    @property
    def base_path(self) -> str:
        """The base path under the transport's base URL."""
        return self._base_path

    # ----- Endpoint routing ----------------------------------------------

    def path_for(self, resource_id: str, **params: object) -> str:
        """Return the upstream path for `resource_id`.

        For parameterised resources (R05-R08) callers
        must pass the relevant keyword (typically
        `edition`).
        """
        if resource_id not in ENDPOINT_FILENAMES:
            raise ValueError(
                f"Unknown metadata resource id: {resource_id!r}; "
                f"expected one of {sorted(ENDPOINT_FILENAMES)}"
            )
        filename_template = ENDPOINT_FILENAMES[resource_id]
        try:
            filename = filename_template.format(**params)
        except KeyError as exc:
            raise ValueError(
                f"Missing path parameter for {resource_id}: {exc!s}; "
                f"required placeholders: {filename_template}"
            ) from exc
        return f"{self._base_path}/{filename}"

    def resolve_path(self, relative_path: str) -> str:
        """Resolve a relative path under the metadata base path.

        Absolute URLs are returned unchanged. Otherwise
        the path is joined onto the base path.
        """
        if relative_path.startswith("http://") or relative_path.startswith("https://"):
            return relative_path
        return f"{self._base_path}/{relative_path.lstrip('/')}"

    # ----- Download orchestration ----------------------------------------

    def download(self, resource_id: str, **params: object) -> "HttpResponse":
        """Download the raw upstream payload for `resource_id`.

        Returns the `HttpResponse`. Callers parse and
        persist as they see fit.

        For parameterised resources (R05-R08) callers
        must pass the relevant keyword (typically
        `edition`); see `PARAMETERIZED_RESOURCES`.
        """
        path = self.path_for(resource_id, **params)
        return self._transport.get(path)

    def download_path(self, relative_path: str) -> "HttpResponse":
        """Download a specific filename under the base path.

        Useful for endpoints that are not covered by the
        R01-R17 routing table (e.g. `SS.json` from M6,
        SITC). The relative path is joined onto
        `base_path`.
        """
        path = self.resolve_path(relative_path)
        return self._transport.get(path)


# ---------------------------------------------------------------------------
# MetadataService
# ---------------------------------------------------------------------------


class MetadataService:
    """L3 Metadata Layer — reference catalogue service.

    The service owns the dependency graph for metadata
    fetches: a `HttpTransport` for the network calls,
    and (when the cache subsystem lands) a
    `MetadataCache` for persistence. In this task scope
    the service holds only the transport.

    The service is owned by `ComtradeClient`. Consumers
    should NOT instantiate it directly; use
    `client.metadata` instead.
    """

    def __init__(
        self,
        transport: "HttpTransport",
        *,
        cache: "MetadataCache | None" = None,
        parser: "MetadataParser | None" = None,
        base_path: str = DEFAULT_REFERENCE_BASE_PATH,
        downloader: "MetadataDownloader | None" = None,
    ) -> None:
        """Construct a metadata service.

        Parameters
        ----------
        transport
            The HTTP transport used to fetch reference
            catalogues from the upstream.
        cache
            Optional cache. When `None`, the service
            operates without persistence — every call hits
            the upstream.
        parser
            Optional parser. When `None`, the service
            constructs a default `MetadataParser` on first
            use (lazy).
        base_path
            The base URL path for reference catalogue
            endpoints. Defaults to the documented UN
            Comtrade path. Tests may override.
        downloader
            Optional pre-built `MetadataDownloader`. When
            `None`, the service constructs one lazily on
            first access via `service.downloader`.
        """
        self._transport: "HttpTransport" = transport
        self._cache: "MetadataCache | None" = cache
        self._parser: "MetadataParser | None" = parser
        self._base_path: str = base_path
        self._downloader: "MetadataDownloader | None" = downloader

    # ----- Properties -----------------------------------------------------

    @property
    def transport(self) -> "HttpTransport":
        """The HTTP transport used for upstream calls."""
        return self._transport

    @property
    def cache(self) -> "MetadataCache | None":
        """The cache, or `None` if caching is disabled."""
        return self._cache

    @property
    def base_path(self) -> str:
        """The base path for reference catalogue endpoints."""
        return self._base_path

    @property
    def downloader(self) -> "MetadataDownloader":
        """The download mechanism owned by this service.

        Constructed lazily on first access. The service
        retains ownership.
        """
        if self._downloader is None:
            self._downloader = MetadataDownloader(
                self._transport, base_path=self._base_path
            )
        return self._downloader

    @property
    def parser(self) -> "MetadataParser":
        """The parser owned by this service.

        Constructed lazily on first access. The service
        retains ownership.
        """
        if self._parser is None:
            # Local import to keep the module load path light.
            from .parser import MetadataParser

            self._parser = MetadataParser()
        return self._parser

    # ----- Reference: Countries (E01) --------------------------------------

    def get_countries(self) -> list[Country]:
        """M01 — Return the catalogue of reporter countries."""
        raise NotImplementedError("MetadataService.get_countries is not yet implemented")

    def get_country(self, country_code: int) -> Country:
        """M02 — Return a single country by its `country_code`."""
        raise NotImplementedError("MetadataService.get_country is not yet implemented")

    # ----- Reference: Partners (E01 partner role) -------------------------

    def get_partners(self) -> list[Partner]:
        """M03 — Return the catalogue of partner countries."""
        raise NotImplementedError("MetadataService.get_partners is not yet implemented")

    def get_partner(self, country_code: int) -> Partner:
        """M04 — Return a single partner by its `country_code`."""
        raise NotImplementedError("MetadataService.get_partner is not yet implemented")

    # ----- Reference: Classifications (E02) -------------------------------

    def get_classifications(self) -> list[Classification]:
        """M05 — Return the catalogue of classification systems."""
        raise NotImplementedError(
            "MetadataService.get_classifications is not yet implemented"
        )

    def get_classification(self, classification_code: str) -> Classification:
        """M06 — Return a single classification by its code."""
        raise NotImplementedError(
            "MetadataService.get_classification is not yet implemented"
        )

    # ----- Reference: Classification Editions (E03) ----------------------

    def get_classification_editions(self, classification_code: str) -> list[str]:
        """M07 — Return the editions of a classification."""
        raise NotImplementedError(
            "MetadataService.get_classification_editions is not yet implemented"
        )

    # ----- Reference: HS Codes (E04) -------------------------------------

    def get_hs_codes(self, edition: str) -> list[HSCode]:
        """M08 — Return the HS commodity codes for an edition."""
        raise NotImplementedError(
            "MetadataService.get_hs_codes is not yet implemented"
        )

    def get_hs_code(self, commodity_code: str, edition: str) -> HSCode:
        """M09 — Return a single HS code by its code and edition."""
        raise NotImplementedError(
            "MetadataService.get_hs_code is not yet implemented"
        )

    def search_hs(self, query: str, edition: str) -> list[HSCode]:
        """M10 — Search HS codes by a substring query."""
        raise NotImplementedError(
            "MetadataService.search_hs is not yet implemented"
        )

    # ----- Reference: Trade Flows (E05) -----------------------------------

    def get_trade_flows(self) -> list[TradeFlow]:
        """M11 — Return the catalogue of trade flow codes."""
        raise NotImplementedError(
            "MetadataService.get_trade_flows is not yet implemented"
        )

    # ----- Reference: Transport Modes (E06) -------------------------------

    def get_transport_modes(self) -> list[TransportMode]:
        """M12 — Return the catalogue of transport mode codes."""
        raise NotImplementedError(
            "MetadataService.get_transport_modes is not yet implemented"
        )

    # ----- Reference: Customs Procedures (E07) ----------------------------

    def get_customs_procedures(self) -> list[object]:
        """M13 — Return the catalogue of customs procedure codes.

        Returns a list of `CustomsProcedure` records. The
        model class is defined in a subsequent task; the
        signature uses `list[object]` here until the
        canonical model lands.
        """
        raise NotImplementedError(
            "MetadataService.get_customs_procedures is not yet implemented"
        )

    # ----- Reference: Quantity Units (E08) --------------------------------

    def get_quantity_units(self) -> list[object]:
        """M14 — Return the catalogue of quantity unit codes.

        Returns a list of `QuantityUnit` records. The model
        class is defined in a subsequent task; the signature
        uses `list[object]` here until the canonical model
        lands.
        """
        raise NotImplementedError(
            "MetadataService.get_quantity_units is not yet implemented"
        )

    # ----- Reference: Modes of Supply (E11) -------------------------------

    def get_modes_of_supply(self) -> list[object]:
        """M15 — Return the catalogue of mode-of-supply codes.

        Returns a list of `ModeOfSupply` records. The model
        class is defined in a subsequent task; the signature
        uses `list[object]` here until the canonical model
        lands.
        """
        raise NotImplementedError(
            "MetadataService.get_modes_of_supply is not yet implemented"
        )

    # ----- Reference: Frequencies (E09) -----------------------------------

    def get_frequencies(self) -> list[Frequency]:
        """M16 — Return the catalogue of frequency codes."""
        raise NotImplementedError(
            "MetadataService.get_frequencies is not yet implemented"
        )

    # ----- Reference: Data Items (auxiliary) ------------------------------

    def get_data_items(self) -> list[object]:
        """M17 — Return the catalogue of data-item (column) codes.

        Returns a list of `DataItem` records. The model class
        is defined in a subsequent task; the signature uses
        `list[object]` here until the canonical model lands.
        """
        raise NotImplementedError(
            "MetadataService.get_data_items is not yet implemented"
        )

    # ----- Reference: Generic metadata ------------------------------------

    def get_metadata(self, table_name: str) -> object:
        """M18 — Return a generic metadata collection by table name.

        Returns a `MetadataCollection` (E24). The result type
        is `object` until the envelope model lands.
        """
        return self._fetch_cached(self._resource_for_table(table_name))

    # ----- Catalogue fetchers (P2-001) ------------------------------------

    def _fetch_cached(self, resource_id: str, **params: object) -> list[Any]:
        """Cache-then-fetch-then-parse pipeline for a resource.

        1. Cache hit? Return the deserialised canonical list.
        2. Cache miss? Download the raw payload via the
           downloader, parse it via the parser, write the
           result back to the cache (serialised as a list
           of dicts), and return the canonical list.

        Raises
        ------
        ValueError
            When `resource_id` is not in `SUPPORTED_FETCHERS`.
        """
        if resource_id not in SUPPORTED_FETCHERS:
            raise ValueError(
                f"No fetcher implemented for resource {resource_id!r}; "
                f"supported: {sorted(SUPPORTED_FETCHERS)}"
            )

        # 1. Cache hit?
        if self._cache is not None:
            cached = self._cache.get(resource_id)
            if cached is not None and isinstance(cached, list):
                return self._reconstruct(resource_id, cached, **params)

        # 2. Cache miss — download.
        response = self.downloader.download(resource_id, **params)
        payload = response.json()

        # 3. Parse. R05 needs the `edition` kwarg, so call the
        # specific parser method directly rather than going
        # through the generic dispatch table.
        result = self._parse_for_resource(resource_id, payload, params)

        # 4. Cache (serialise as a list of dicts for JSON-friendly storage).
        if self._cache is not None:
            serialised = [m.to_dict() for m in result.records]
            self._cache.set(resource_id, serialised)

        # 5. Return.
        return list(result.records)

    def _parse_for_resource(self, resource_id: str, payload: Any, params: dict):
        """Dispatch parse calls that need path parameters.

        Mirrors `parser.parse(...)` for the supported
        resources but accepts extra kwargs for parameterised
        endpoints (R05 today).

        Returns a `ParseResult`-like duck type so the
        `_fetch_cached` caller can treat all resources
        uniformly.
        """
        records_list = self.parser._extract_data(payload)
        if resource_id == "R05":
            edition = str(params.get("edition", ""))
            records = self.parser.parse_r05_hs_edition(records_list, edition=edition)
            # Wrap the list in a ParseResult-shaped object so
            # `_fetch_cached` can read `.records` and `.skipped`.
            from .parser import ParseResult
            return ParseResult(records=list(records), skipped=0)
        return self.parser.parse(resource_id, payload)

    def _resource_for_table(self, table_name: str) -> str:
        """Map a user-facing table name to a resource id.

        Supports the common aliases used by the SDK spec
        ("Reporters", "Partners", etc.) plus the canonical
        resource ids.
        """
        aliases = {
            "Reporters": "R02",
            "Partners": "R03",
            "HSCombined": "R04",
            "HSEdition": "R05",
            "Frequency": "R09",
            "TradeFlows": "R10",
            "TransportModes": "R12",
            "QuantityUnits": "R14",
            "DataItems": "R15",
            "References": "R01",
        }
        if table_name in aliases:
            return aliases[table_name]
        if table_name in SUPPORTED_FETCHERS:
            return table_name
        raise ValueError(
            f"Unknown metadata table name: {table_name!r}; "
            f"supported: {sorted(aliases)}"
        )

    def _reconstruct(
        self, resource_id: str, items: list[dict], **params: object
    ) -> list[Any]:
        """Reconstruct canonical model instances from a cached list of dicts."""
        if resource_id == "R01":
            return [ReferenceEntry(**i) for i in items]
        if resource_id == "R02":
            return [Country(**self._country_kwargs(i)) for i in items]
        if resource_id == "R03":
            return [Partner(**self._country_kwargs(i)) for i in items]
        if resource_id == "R04":
            return [self._hs_code_kwargs(i, edition="combined") for i in items]
        if resource_id == "R05":
            edition = str(params.get("edition", ""))
            return [self._hs_code_kwargs(i, edition=edition) for i in items]
        if resource_id == "R09":
            return [Frequency(**i) for i in items]
        if resource_id == "R10":
            return [TradeFlow(**i) for i in items]
        if resource_id == "R12":
            return [TransportMode(**i) for i in items]
        if resource_id == "R14":
            return [QuantityUnit(**i) for i in items]
        if resource_id == "R15":
            return [DataItem(**i) for i in items]
        raise ValueError(f"No reconstructor for {resource_id}")

    @staticmethod
    def _country_kwargs(item: dict) -> dict:
        """Build kwargs for `Country` / `Partner` from a cached dict."""
        return dict(
            country_code=item["country_code"],
            iso_alpha2=item.get("iso_alpha2"),
            iso_alpha3=item.get("iso_alpha3"),
            display_name=item["display_name"],
            entry_effective_date=_parse_iso_date(item.get("entry_effective_date")),
            entry_expired_date=_parse_iso_date(item.get("entry_expired_date")),
        )

    @staticmethod
    def _hs_code_kwargs(item: dict, *, edition: str) -> dict:
        """Build kwargs for `HSCode` from a cached dict."""
        return dict(
            commodity_code=item["commodity_code"],
            classification_code="HS",
            edition=edition,
            display_name=item.get("display_name"),
        )

    # ----- Reference: Countries (E01) --------------------------------------

    def get_countries(self) -> list[Country]:
        """M01 — Return the catalogue of reporter countries."""
        return self._fetch_cached("R02")

    def get_country(self, country_code: int) -> Country | None:
        """M02 — Return a single country by its `country_code`."""
        for country in self.get_countries():
            if country.country_code == country_code:
                return country
        return None

    # ----- Reference: Partners (E01 partner role) -------------------------

    def get_partners(self) -> list[Partner]:
        """M03 — Return the catalogue of partner countries."""
        return self._fetch_cached("R03")

    def get_partner(self, country_code: int) -> Partner | None:
        """M04 — Return a single partner by its `country_code`."""
        for partner in self.get_partners():
            if partner.country_code == country_code:
                return partner
        return None

    # ----- Reference: Classifications (E02) -------------------------------

    def get_classifications(self) -> list[Classification]:
        """M05 — Return the catalogue of classification systems.

        Classifications are a small hard-coded set
        (HS, SITC, BEC, EBOPS) per the data model — there
        is no upstream endpoint. The cache is bypassed
        because the list is constant for the SDK's lifetime.
        """
        return [
            Classification(classification_code="HS", display_name="Harmonized System"),
            Classification(
                classification_code="SITC",
                display_name="Standard International Trade Classification",
            ),
            Classification(
                classification_code="BEC",
                display_name="Broad Economic Categories",
            ),
            Classification(
                classification_code="EBOPS",
                display_name="Extended Balance of Payments Services",
            ),
        ]

    def get_classification(self, classification_code: str) -> Classification | None:
        """M06 — Return a single classification by its code."""
        for c in self.get_classifications():
            if c.classification_code == classification_code:
                return c
        return None

    # ----- Reference: Classification Editions (E03) ----------------------

    def get_classification_editions(self, classification_code: str) -> list[str]:
        """M07 — Return the editions of a classification.

        Returns the documented HS editions (2022, 2017,
        2012, 2007, 2002, 1996, 1992) for `classification_code="HS"`.
        Other classifications return an empty list — their
        editions are documented in the spec but not yet
        exposed.
        """
        if classification_code == "HS":
            return ["HS2022", "HS2017", "HS2012", "HS2007", "HS2002", "HS1996", "HS1992"]
        return []

    # ----- Reference: HS Codes (E04) -------------------------------------

    def get_hs_codes(self, edition: str) -> list[HSCode]:
        """M08 — Return the HS commodity codes for an edition."""
        return self._fetch_cached("R05", edition=edition)

    def get_hs_code(self, commodity_code: str, edition: str) -> HSCode | None:
        """M09 — Return a single HS code by its code and edition."""
        for h in self.get_hs_codes(edition):
            if h.commodity_code == commodity_code:
                return h
        return None

    def search_hs(self, query: str, edition: str) -> list[HSCode]:
        """M10 — Search HS codes by a substring query (case-insensitive)."""
        codes = self.get_hs_codes(edition)
        q = query.lower()
        return [c for c in codes if c.display_name and q in c.display_name.lower()]

    # ----- Reference: Trade Flows (E05) -----------------------------------

    def get_trade_flows(self) -> list[TradeFlow]:
        """M11 — Return the catalogue of trade flow codes."""
        return self._fetch_cached("R10")

    # ----- Reference: Transport Modes (E06) -------------------------------

    def get_transport_modes(self) -> list[TransportMode]:
        """M12 — Return the catalogue of transport mode codes."""
        return self._fetch_cached("R12")

    # ----- Reference: Customs Procedures (E07) ----------------------------

    def get_customs_procedures(self) -> list[object]:
        """M13 — Return the catalogue of customs procedure codes.

        Not yet implemented — the `CustomsProcedure` model
        and the upstream parser land in a follow-up task.
        """
        raise NotImplementedError(
            "MetadataService.get_customs_procedures is not yet implemented"
        )

    # ----- Reference: Quantity Units (E08) --------------------------------

    def get_quantity_units(self) -> list[QuantityUnit]:
        """M14 — Return the catalogue of quantity unit codes."""
        return self._fetch_cached("R14")

    # ----- Reference: Modes of Supply (E11) -------------------------------

    def get_modes_of_supply(self) -> list[object]:
        """M15 — Return the catalogue of mode-of-supply codes.

        Not yet implemented — the `ModeOfSupply` model and
        the upstream parser land in a follow-up task.
        """
        raise NotImplementedError(
            "MetadataService.get_modes_of_supply is not yet implemented"
        )

    # ----- Reference: Frequencies (E09) -----------------------------------

    def get_frequencies(self) -> list[Frequency]:
        """M16 — Return the catalogue of frequency codes."""
        return self._fetch_cached("R09")

    # ----- Reference: Data Items (auxiliary) ------------------------------

    def get_data_items(self) -> list[DataItem]:
        """M17 — Return the catalogue of data-item (column) codes."""
        return self._fetch_cached("R15")

    # ----- Lifecycle ------------------------------------------------------

    def close(self) -> None:
        """Release the transport's underlying resources.

        Closes the transport only when the service created
        it. When the caller injected a transport, the
        caller retains ownership.
        """
        if self._downloader is not None:
            # The downloader is the only path that holds a
            # transport reference built by this service; the
            # caller-supplied transport case is covered by
            # `ComtradeClient.close` which owns its own
            # transport lifecycle.
            # No-op today (the downloader does not own the
            # transport); placeholder for future expansion.
            return
        # When the service was built with a caller-supplied
        # transport, do nothing — ComtradeClient owns the
        # lifecycle in that path.