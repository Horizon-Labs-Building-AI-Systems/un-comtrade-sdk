"""L4 Trade Layer (T01-T11 implemented in P2-005) per `003_ARCHITECTURE.md` §5.4.

This module implements the trade-service surface
per `007_SDK_SPECIFICATION.md` §3.2 (T01-T08 annual
trade retrieval), §3.3 (T09-T11 monthly trade
retrieval), §3.4 (F01-F02 tariffline retrieval).
Preview (P01-P04), counting (C01-C03), async / bulk
(A01-A05), and utility (U01-U03) methods are declared
but not yet implemented; they land in later tasks.

In this build (P2-005 + P3-001 + P3-006) the service
implements:

- T01 `get_exports` — annual exports (`flow_code="X"`).
- T02 `get_imports` — annual imports (`flow_code="M"`).
- T03 `get_trade` — annual trade with explicit flow.
- T04 `get_trade_by_hs` — annual trade for a specific HS code.
- T05 `get_world_trade` — annual world trade (`partner_code=0`).
- T06 `get_trade_balance` — annual exports-vs-imports balance.
- T07 `get_bilateral` — annual reported + mirror data.
- T08 `get_trade_matrix` — annual world trade matrix.
- T09 `get_monthly_exports` — monthly exports.
- T10 `get_monthly_imports` — monthly imports.
- T11 `get_monthly_trade` — monthly trade with flow.
- F01 `get_tariffline` — annual line-level tariffline data.
- F02 `get_tariffline_by_hs` — annual line-level tariffline for an HS code.

Each method:

1. Builds a `TradeQuery` from the method kwargs.
2. Builds the upstream URL path
   `/{trade_type}/{freqCode}/{flowCode}/{classificationCode}`.
3. Issues an authenticated `GET` via the configured
   `HttpTransport` (retry + timeout honoured).
4. Validates the response envelope
   (status, JSON shape, top-level fields).
5. Returns a canonical `TradeResponse` (E22) wrapping
   the raw upstream records.

Per the P2-005 task scope:

- No pagination (single call, no chunking).
- No batch downloads.
- No record-level parsing (records are passed through
  as raw upstream dicts; conversion to `TradeRecord`
  is the responsibility of a future parser task).

A01-A05 (async + bulk) and U01-U03 (utility)
remain unimplemented in this task; they are
separate concerns that will land in later tasks
per `IMPLEMENTATION_ROADMAP.md`.
"""

from __future__ import annotations

import json
from types import TracebackType
from typing import TYPE_CHECKING, Any, Self


from .config import Configuration
from .exceptions import (
    APIError,
    SerializationError,
    ServerError,
    UnknownError,
)
from .models import TradeResponse
from .query import (
    BREAKDOWN_MODES,
    DEFAULT_BREAKDOWN_MODE,
    DEFAULT_CLASSIFICATION,
    FLOW_CODES,
    MAX_RECORDS_LIMIT,
    MIN_RECORDS,
    PARTNER_WORLD,
    TradeQuery,
)


from .parser import TradeParser
from .transport import HttpTransport


__all__ = ["TradeService"]


#: Annual frequency code (URL path segment + downstream use).
_FREQUENCY_ANNUAL: str = "A"

#: Monthly frequency code (URL path segment + downstream use).
_FREQUENCY_MONTHLY: str = "M"


#: URL-path templates for the supported trade endpoints.
#: Each template is a `str.format` template with the
#: documented placeholders. The default trade endpoint
#: (T01-T05, T09-T11) uses `_PATH_TRADE`. The alternative
#: endpoints (T06 balance, T07 bilateral, T08 matrix)
#: have different path shapes per
#: `005_API_ENDPOINT_CATALOG.md` §T2-T4.
_PATH_TRADE: str = "/{trade_type}/{freqCode}/{flowCode}/{classificationCode}"
_PATH_BALANCE: str = (
    "/tools/v1/getTradeBalance/{trade_type}/{freqCode}/{classificationCode}"
)
_PATH_BILATERAL: str = (
    "/tools/v1/getBilateralData/{trade_type}/{freqCode}/{classificationCode}"
)
_PATH_MATRIX: str = "/data/v1/getTradeMatrix/{trade_type}/{freqCode}/TM"
#: Tariffline endpoint (F1 in `005_API_ENDPOINT_CATALOG.md`).
#: `flowCode` is NOT a path parameter on this endpoint —
#: it travels as a query parameter alongside `cmdCode`,
#: `partnerCode`, etc. The template intentionally omits
#: `{flowCode}` so the trade service injects it via
#: `TradeQuery.to_query_params` instead.
_PATH_TARIFFLINE: str = (
    "/data/v1/getTariffline/{trade_type}/{freqCode}/{classificationCode}"
)


class TradeService:
    """L4 Trade Layer (skeleton).

    Composes the L4 trade-layer dependencies (HTTP
    transport, parser, configuration, defaults) and
    exposes the documented trade-retrieval methods.

    The service is **owned by the caller** (typically
    `ComtradeClient`). When the client owns the
    service, `close()` is a no-op in this skeleton;
    it will be implemented when the parser lands.

    Usage (future, when methods are implemented)::

        with ComtradeClient(cfg) as client:
            response = client.trade.get_exports(
                reporter_code=699, period="2022"
            )
            for record in response.records:
                print(record.partner.name, record.trade_value.primary_value)

    Construction (this task)::

        from un_comtrade.config import Configuration
        from un_comtrade.transport import HttpTransport
        from un_comtrade.trade import TradeService

        cfg = Configuration(api_key="...")
        transport = HttpTransport(base_url=cfg.base_url, ...)
        service = TradeService(transport, configuration=cfg)
    """

    def __init__(
        self,
        transport: "HttpTransport",
        *,
        parser: "TradeParser | None" = None,
        configuration: Configuration | None = None,
        default_classification: str = DEFAULT_CLASSIFICATION,
        default_breakdown_mode: str = DEFAULT_BREAKDOWN_MODE,
        default_max_records: int | None = None,
    ) -> None:
        """Construct a trade service.

        Parameters
        ----------
        transport
            Required `HttpTransport` instance. The
            service does NOT take ownership of the
            transport — closing the service does NOT
            close the transport (the client owns it).
        parser
            Optional `TradeParser` instance. Reserved
            for the parser that will land with P2-005.
            When `None`, the parser is expected to be
            injected later (no auto-construction in
            this skeleton).
        configuration
            Optional `Configuration` instance. When
            supplied, it is exposed via the
            `configuration` property. Defaults are
            used to populate method defaults.
        default_classification
            Default classification for methods that
            accept a `classification` parameter
            (default `"HS"`).
        default_breakdown_mode
            Default breakdown mode for methods that
            accept a `breakdown_mode` parameter
            (default `"classic"`).
        default_max_records
            Optional default for `max_records`. When
            `None`, callers must supply it explicitly
            (or accept the upstream's cap).
        """
        if default_classification != DEFAULT_CLASSIFICATION:
            # Allow override but document the default.
            pass
        if default_breakdown_mode not in BREAKDOWN_MODES:
            raise ValueError(
                f"default_breakdown_mode must be one of "
                f"{sorted(BREAKDOWN_MODES)}; got "
                f"{default_breakdown_mode!r}"
            )
        if default_max_records is not None and (
            default_max_records < MIN_RECORDS
            or default_max_records > MAX_RECORDS_LIMIT
        ):
            raise ValueError(
                f"default_max_records must be in "
                f"{MIN_RECORDS}..{MAX_RECORDS_LIMIT}; got "
                f"{default_max_records}"
            )

        self._transport: "HttpTransport" = transport
        self._parser: "TradeParser | None" = parser
        self._configuration: Configuration | None = configuration
        self._default_classification: str = default_classification
        self._default_breakdown_mode: str = default_breakdown_mode
        self._default_max_records: int | None = default_max_records

    # ----- Properties -----------------------------------------------------

    @property
    def transport(self) -> "HttpTransport":
        """The HTTP transport used by this service.

        Exposed for advanced consumers (e.g. diagnostics)
        and for the parser when it lands with P2-005.
        """
        return self._transport

    @property
    def parser(self) -> "TradeParser | None":
        """The trade parser used by this service.

        `None` in this skeleton; the parser lands with
        P2-005. When wired, the service will use the
        parser to transform upstream JSON payloads
        into `TradeRecord` instances.
        """
        return self._parser

    @property
    def configuration(self) -> Configuration | None:
        """The configuration this service was built from.

        `None` when the service was constructed without
        a configuration. Used by future methods to
        read defaults (timeout category, retry hints,
        etc.).
        """
        return self._configuration

    @property
    def default_classification(self) -> str:
        """Default classification for methods that accept one."""
        return self._default_classification

    @property
    def default_breakdown_mode(self) -> str:
        """Default breakdown mode for methods that accept one."""
        return self._default_breakdown_mode

    @property
    def default_max_records(self) -> int | None:
        """Optional default cap on `max_records`."""
        return self._default_max_records

    # ----- Internal helpers ----------------------------------------------

    def _build_query(
        self,
        *,
        reporter_code: int,
        flow_code: str | None,
        partner_code: int | None,
        period: str,
        commodity_code: str,
        classification: str | None,
        edition: str | None,
        breakdown_mode: str | None,
        max_records: int | None,
    ) -> TradeQuery:
        """Translate method kwargs into a `TradeQuery`.

        Used by the future method implementations. In
        this skeleton the helper is exposed for tests
        but no public method calls it.
        """
        return TradeQuery(
            reporter_code=reporter_code,
            partner_code=partner_code,
            period=period,
            cmd_code=commodity_code,
            flow_code=flow_code,
            classification_code=(
                classification
                if classification is not None
                else self._default_classification
            ),
            classification_edition=edition,
            breakdown_mode=(
                breakdown_mode
                if breakdown_mode is not None
                else self._default_breakdown_mode
            ),
            max_records=(
                max_records
                if max_records is not None
                else self._default_max_records
            ),
        )

    # ----- Internal helpers ----------------------------------------------

    def _build_query(
        self,
        *,
        reporter_code: int,
        flow_code: str | None,
        partner_code: int | None,
        period: str,
        commodity_code: str,
        classification: str | None,
        edition: str | None,
        breakdown_mode: str | None,
        max_records: int | None,
    ) -> TradeQuery:
        """Translate method kwargs into a `TradeQuery`.

        Used by the future method implementations. In
        this skeleton the helper is exposed for tests
        but no public method calls it.
        """
        return TradeQuery(
            reporter_code=reporter_code,
            partner_code=partner_code,
            period=period,
            cmd_code=commodity_code,
            flow_code=flow_code,
            classification_code=(
                classification
                if classification is not None
                else self._default_classification
            ),
            classification_edition=edition,
            breakdown_mode=(
                breakdown_mode
                if breakdown_mode is not None
                else self._default_breakdown_mode
            ),
            max_records=(
                max_records
                if max_records is not None
                else self._default_max_records
            ),
        )

    def _execute(
        self,
        query: TradeQuery,
        *,
        frequency: str,
        trade_type: str = "C",
        path_template: str = _PATH_TRADE,
    ) -> TradeResponse:
        """Execute a trade query and return the canonical envelope.

        Builds the upstream URL path from `path_template`,
        issues the GET, validates the response envelope,
        and returns a `TradeResponse`.

        `frequency` is one of `"A"` (annual) or `"M"`
        (monthly). `trade_type` is `"C"` (commodities,
        default) or `"S"` (services). `path_template`
        is a `str.format` template with named
        placeholders (`{trade_type}`, `{freqCode}`,
        `{flowCode}`, `{classificationCode}`). The
        default template is the standard trade endpoint
        used by T01-T05 + T09-T11. Alternative
        templates (balance / bilateral / matrix) are
        selected by the higher-level methods.

        Raises:
            AuthenticationError / AuthorizationError:
                raised by the transport on 401 / 403.
            APIError: 4xx upstream response.
            ServerError: 5xx that escaped the transport's
                retry loop (RetryError is raised instead
                when retries are exhausted).
            SerializationError: response body is not
                valid JSON or is not a JSON object.
        """
        if frequency not in (_FREQUENCY_ANNUAL, _FREQUENCY_MONTHLY):
            raise ValueError(
                f"frequency must be {_FREQUENCY_ANNUAL!r} (annual) or "
                f"{_FREQUENCY_MONTHLY!r} (monthly); got {frequency!r}"
            )
        if trade_type not in ("C", "S"):
            raise ValueError(
                f"trade_type must be 'C' (commodities) or "
                f"'S' (services); got {trade_type!r}"
            )

        path = path_template.format(
            trade_type=trade_type,
            freqCode=frequency,
            flowCode=query.flow_code or "",
            classificationCode=(
                query.classification_edition
                or query.classification_code
                or ""
            ),
        )
        params = query.to_query_params(trade_type=trade_type)

        response = self._transport.get(path, params=params, kind="default")

        # Transport already raises AuthenticationError on 401 and
        # AuthorizationError on 403; other non-2xx responses fall
        # through to here.
        if not response.is_success:
            if 400 <= response.status_code < 500:
                raise APIError(
                    f"Upstream {response.status_code} from {response.url}",
                    status_code=response.status_code,
                    response_body=response.text,
                )
            if 500 <= response.status_code < 600:
                raise ServerError(
                    f"Upstream {response.status_code} from {response.url}",
                    status_code=response.status_code,
                    response_body=response.text,
                )
            raise UnknownError(  # pragma: no cover
                f"Upstream {response.status_code} from {response.url}",
                status_code=response.status_code,
                response_body=response.text,
            )

        try:
            envelope = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise SerializationError(
                f"Trade response body is not valid JSON: {exc!s}"
            ) from exc

        if not isinstance(envelope, dict):
            raise SerializationError(
                f"Trade response is not a JSON object; got "
                f"{type(envelope).__name__}"
            )

        elapsed_seconds_raw = envelope.get("elapsed_seconds") or 0
        try:
            elapsed_seconds = float(elapsed_seconds_raw)
        except (TypeError, ValueError) as exc:
            raise SerializationError(
                f"elapsed_seconds is not a number; got "
                f"{elapsed_seconds_raw!r}"
            ) from exc

        count_raw = envelope.get("count") or 0
        try:
            count = int(count_raw)
        except (TypeError, ValueError) as exc:
            raise SerializationError(
                f"count is not an integer; got {count_raw!r}"
            ) from exc

        records_raw = envelope.get("data")
        if records_raw is None:
            records_raw_list: list[dict[str, Any]] = []
        elif isinstance(records_raw, list):
            records_raw_list = records_raw
        else:
            raise SerializationError(
                f"data is not a list; got {type(records_raw).__name__}"
            )

        error_raw = envelope.get("error") or ""
        if not isinstance(error_raw, str):
            error: str = str(error_raw)
        else:
            error = error_raw

        # Parse records into canonical TradeRecord instances.
        # When a parser is supplied to the constructor, it is
        # used to validate and dedupe the raw records.
        # When no parser is supplied, an empty list of
        # TradeRecord is returned (preserving the envelope's
        # metadata only) — callers that need canonical records
        # MUST inject a parser at construction time.
        skipped: int = 0
        records: list[Any] = []
        parser = self._parser
        if parser is not None:
            parse_result = parser.parse_records(records_raw_list)
            records = parse_result.records
            skipped = parse_result.skipped

        return TradeResponse(
            elapsed_seconds=elapsed_seconds,
            count=count,
            records=records,
            error=error,
            upstream_url=response.url,
            skipped=skipped,
        )

    # ----- Annual trade retrieval (T01-T03 implemented) -----------------
    #
    # T01-T03 land in P2-005. T04-T08 land in P3-001.
    # F01-F02 land in P3-006. P01-P04, C01-C03, A01-A05,
    # U01-U03 remain deferred to later tasks.

    def get_exports(
        self,
        reporter_code: int,
        period: str,
        *,
        partner_code: int | None = None,
        commodity_code: str = "TOTAL",
        classification: str | None = None,
        edition: str | None = None,
        breakdown_mode: str | None = None,
        max_records: int | None = None,
    ) -> TradeResponse:
        """T01 — return the annual exports of a reporter.

        Per `007_SDK_SPECIFICATION.md` §T01.
        Implies `flow_code="X"`. Default partner is all
        partners; default commodity is the `TOTAL`
        aggregate.
        """
        query = self._build_query(
            reporter_code=reporter_code,
            flow_code="X",
            partner_code=partner_code,
            period=period,
            commodity_code=commodity_code,
            classification=classification,
            edition=edition,
            breakdown_mode=breakdown_mode,
            max_records=max_records,
        )
        return self._execute(query, frequency=_FREQUENCY_ANNUAL)

    def get_imports(
        self,
        reporter_code: int,
        period: str,
        *,
        partner_code: int | None = None,
        commodity_code: str = "TOTAL",
        classification: str | None = None,
        edition: str | None = None,
        breakdown_mode: str | None = None,
        max_records: int | None = None,
    ) -> TradeResponse:
        """T02 — return the annual imports of a reporter.

        Per `007_SDK_SPECIFICATION.md` §T02.
        Implies `flow_code="M"`.
        """
        query = self._build_query(
            reporter_code=reporter_code,
            flow_code="M",
            partner_code=partner_code,
            period=period,
            commodity_code=commodity_code,
            classification=classification,
            edition=edition,
            breakdown_mode=breakdown_mode,
            max_records=max_records,
        )
        return self._execute(query, frequency=_FREQUENCY_ANNUAL)

    def get_trade(
        self,
        reporter_code: int,
        flow_code: str,
        period: str,
        *,
        partner_code: int | None = None,
        commodity_code: str = "TOTAL",
        classification: str | None = None,
        edition: str | None = None,
        breakdown_mode: str | None = None,
        max_records: int | None = None,
    ) -> TradeResponse:
        """T03 — return annual trade with an explicit flow.

        Per `007_SDK_SPECIFICATION.md` §T03.
        """
        query = self._build_query(
            reporter_code=reporter_code,
            flow_code=flow_code,
            partner_code=partner_code,
            period=period,
            commodity_code=commodity_code,
            classification=classification,
            edition=edition,
            breakdown_mode=breakdown_mode,
            max_records=max_records,
        )
        return self._execute(query, frequency=_FREQUENCY_ANNUAL)

    def get_trade_by_hs(
        self,
        commodity_code: str,
        reporter_code: int,
        flow_code: str,
        period: str,
        *,
        partner_code: int | None = None,
        classification: str | None = None,
        edition: str | None = None,
        breakdown_mode: str | None = None,
        max_records: int | None = None,
    ) -> TradeResponse:
        """T04 — return annual trade for a specific HS code.

        Per `007_SDK_SPECIFICATION.md` §T04.
        `commodity_code` is required and identifies the
        HS code; unlike T01-T03 it is NOT defaulted to
        `"TOTAL"`. Reuses the standard trade endpoint
        via `_build_query` + `_execute`.
        """
        query = self._build_query(
            reporter_code=reporter_code,
            flow_code=flow_code,
            partner_code=partner_code,
            period=period,
            commodity_code=commodity_code,
            classification=classification,
            edition=edition,
            breakdown_mode=breakdown_mode,
            max_records=max_records,
        )
        return self._execute(query, frequency=_FREQUENCY_ANNUAL)

    def get_world_trade(
        self,
        reporter_code: int,
        flow_code: str,
        period: str,
        *,
        commodity_code: str = "TOTAL",
        classification: str | None = None,
        edition: str | None = None,
        breakdown_mode: str | None = None,
        max_records: int | None = None,
    ) -> TradeResponse:
        """T05 — return annual world trade for a reporter.

        Per `007_SDK_SPECIFICATION.md` §T05.
        Implies `partner_code=0` (World aggregate).
        Reuses the standard trade endpoint.
        """
        query = self._build_query(
            reporter_code=reporter_code,
            flow_code=flow_code,
            partner_code=0,
            period=period,
            commodity_code=commodity_code,
            classification=classification,
            edition=edition,
            breakdown_mode=breakdown_mode,
            max_records=max_records,
        )
        return self._execute(query, frequency=_FREQUENCY_ANNUAL)

    def get_trade_balance(
        self,
        reporter_code: int,
        period: str,
        *,
        partner_code: int | None = None,
        commodity_code: str = "TOTAL",
        classification: str | None = None,
        edition: str | None = None,
        breakdown_mode: str | None = None,
        max_records: int | None = None,
    ) -> TradeResponse:
        """T06 — return the trade balance (exports - imports).

        Per `007_SDK_SPECIFICATION.md` §T06 and
        `005_API_ENDPOINT_CATALOG.md` §T3.
        Hits the dedicated balance endpoint
        (`/tools/v1/getTradeBalance/{type}/{freq}/{cl}`)
        which returns exports and imports side by side
        for the same query. `flow_code` is NOT a path
        parameter on this endpoint; the TradeQuery is
        built without one so the resulting query
        params omit `flowCode`.
        """
        query = self._build_query(
            reporter_code=reporter_code,
            flow_code=None,
            partner_code=partner_code,
            period=period,
            commodity_code=commodity_code,
            classification=classification,
            edition=edition,
            breakdown_mode=breakdown_mode,
            max_records=max_records,
        )
        return self._execute(
            query, frequency=_FREQUENCY_ANNUAL, path_template=_PATH_BALANCE
        )

    def get_bilateral(
        self,
        reporter_code: int,
        flow_code: str,
        period: str,
        *,
        partner_code: int | None = None,
        commodity_code: str = "TOTAL",
        classification: str | None = None,
        edition: str | None = None,
        breakdown_mode: str | None = None,
        max_records: int | None = None,
    ) -> TradeResponse:
        """T07 — return bilateral trade observations.

        Per `007_SDK_SPECIFICATION.md` §T07 and
        `005_API_ENDPOINT_CATALOG.md` §T4.
        Hits the dedicated bilateral endpoint
        (`/tools/v1/getBilateralData/{type}/{freq}/{cl}`)
        which returns reported data complemented by
        mirror partner data. `flow_code` is supplied
        as a query parameter (not in the URL path).
        """
        query = self._build_query(
            reporter_code=reporter_code,
            flow_code=flow_code,
            partner_code=partner_code,
            period=period,
            commodity_code=commodity_code,
            classification=classification,
            edition=edition,
            breakdown_mode=breakdown_mode,
            max_records=max_records,
        )
        return self._execute(
            query, frequency=_FREQUENCY_ANNUAL, path_template=_PATH_BILATERAL
        )

    def get_trade_matrix(
        self,
        period: str,
        flow_code: str,
        reporter_code: int,
        partner_code: int,
        commodity_code: str,
        *,
        classification: str | None = None,
        max_records: int | None = None,
    ) -> TradeResponse:
        """T08 — return a trade matrix for a fixed period.

        Per `007_SDK_SPECIFICATION.md` §T08 and
        `005_API_ENDPOINT_CATALOG.md` §T2.
        Hits the dedicated matrix endpoint
        (`/data/v1/getTradeMatrix/{type}/{freq}/TM`)
        which uses the fixed classification code
        `"TM"` in the URL path. The `classification`
        kwarg is accepted for API symmetry but does
        not affect the URL (the matrix endpoint
        doesn't take a `classification` query
        parameter — only `maxRecords`, `format`,
        `aggregateBy`, `countOnly`, `includeDesc`).
        """
        # The matrix endpoint uses `"TM"` as the
        # classification code (in the URL path). The
        # `_PATH_MATRIX` template hard-codes this.
        # We also pass `classification="TM"` so the
        # query params emit `classification=TM` for
        # consistency with the URL.
        query = self._build_query(
            reporter_code=reporter_code,
            flow_code=flow_code,
            partner_code=partner_code,
            period=period,
            commodity_code=commodity_code,
            classification="TM",
            edition=None,
            breakdown_mode=None,
            max_records=max_records,
        )
        return self._execute(
            query, frequency=_FREQUENCY_ANNUAL, path_template=_PATH_MATRIX
        )

    # ----- Monthly trade retrieval (T09-T11 implemented) -----------------

    def get_monthly_exports(
        self,
        reporter_code: int,
        period: str,
        *,
        partner_code: int | None = None,
        commodity_code: str = "TOTAL",
        classification: str | None = None,
        edition: str | None = None,
        max_records: int | None = None,
    ) -> TradeResponse:
        """T09 — return monthly exports.

        Per `007_SDK_SPECIFICATION.md` §T09.
        `period` SHALL be `YYYYMM` (one or comma-separated).
        """
        query = self._build_query(
            reporter_code=reporter_code,
            flow_code="X",
            partner_code=partner_code,
            period=period,
            commodity_code=commodity_code,
            classification=classification,
            edition=edition,
            breakdown_mode=None,  # monthly does not expose breakdown_mode
            max_records=max_records,
        )
        return self._execute(query, frequency=_FREQUENCY_MONTHLY)

    def get_monthly_imports(
        self,
        reporter_code: int,
        period: str,
        *,
        partner_code: int | None = None,
        commodity_code: str = "TOTAL",
        classification: str | None = None,
        edition: str | None = None,
        max_records: int | None = None,
    ) -> TradeResponse:
        """T10 — return monthly imports.

        Per `007_SDK_SPECIFICATION.md` §T10.
        """
        query = self._build_query(
            reporter_code=reporter_code,
            flow_code="M",
            partner_code=partner_code,
            period=period,
            commodity_code=commodity_code,
            classification=classification,
            edition=edition,
            breakdown_mode=None,
            max_records=max_records,
        )
        return self._execute(query, frequency=_FREQUENCY_MONTHLY)

    def get_monthly_trade(
        self,
        reporter_code: int,
        flow_code: str,
        period: str,
        *,
        partner_code: int | None = None,
        commodity_code: str = "TOTAL",
        classification: str | None = None,
        edition: str | None = None,
        max_records: int | None = None,
    ) -> TradeResponse:
        """T11 — return monthly trade with an explicit flow.

        Per `007_SDK_SPECIFICATION.md` §T11.
        """
        query = self._build_query(
            reporter_code=reporter_code,
            flow_code=flow_code,
            partner_code=partner_code,
            period=period,
            commodity_code=commodity_code,
            classification=classification,
            edition=edition,
            breakdown_mode=None,
            max_records=max_records,
        )
        return self._execute(query, frequency=_FREQUENCY_MONTHLY)

    # ----- Tariffline methods (F01-F02 implemented in P3-006) ----------

    def get_tariffline(
        self,
        reporter_code: int,
        flow_code: str,
        period: str,
        *,
        partner_code: int | None = None,
        commodity_code: str | None = None,
        classification: str | None = None,
        edition: str | None = None,
        max_records: int | None = None,
    ) -> TradeResponse:
        """F01 — return line-level tariffline data.

        Per `007_SDK_SPECIFICATION.md` §F01 and
        `005_API_ENDPOINT_CATALOG.md` §F1. As T03, but
        hits the dedicated tariffline endpoint
        (`/data/v1/getTariffline/{type}/{freq}/{cl}`)
        which returns line-level records (typically with
        8+ digit HS codes). `breakdown_mode` and
        `partner2_code` are not applicable to tariffline
        data per the SDK specification (F01-2) and are
        intentionally NOT exposed on this method.

        `commodity_code` is optional; when omitted the
        query defaults to `"TOTAL"` (all commodities)
        via the `_build_query` helper.

        Reuses the existing `_build_query` /
        `_execute` / `TradeParser.parse_records`
        pipeline; no new parser or transport logic.
        """
        query = self._build_query(
            reporter_code=reporter_code,
            flow_code=flow_code,
            partner_code=partner_code,
            period=period,
            commodity_code=(
                commodity_code if commodity_code is not None else "TOTAL"
            ),
            classification=classification,
            edition=edition,
            breakdown_mode=None,  # not applicable to tariffline data
            max_records=max_records,
        )
        return self._execute(
            query,
            frequency=_FREQUENCY_ANNUAL,
            path_template=_PATH_TARIFFLINE,
        )

    def get_tariffline_by_hs(
        self,
        commodity_code: str,
        reporter_code: int,
        flow_code: str,
        period: str,
        *,
        partner_code: int | None = None,
        classification: str | None = None,
        edition: str | None = None,
        max_records: int | None = None,
    ) -> TradeResponse:
        """F02 — return line-level tariffline data for an HS code.

        Per `007_SDK_SPECIFICATION.md` §F02. As T04, but
        hits the dedicated tariffline endpoint
        (`/data/v1/getTariffline/{type}/{freq}/{cl}`)
        which returns line-level records at the requested
        HS code granularity. `commodity_code` is REQUIRED
        and identifies the HS code (unlike F01 which
        defaults to `"TOTAL"`).

        `breakdown_mode` and `partner2_code` are not
        applicable to tariffline data per the SDK
        specification (F02-2) and are intentionally NOT
        exposed on this method.

        Reuses the existing `_build_query` /
        `_execute` / `TradeParser.parse_records`
        pipeline; no new parser or transport logic.
        """
        query = self._build_query(
            reporter_code=reporter_code,
            flow_code=flow_code,
            partner_code=partner_code,
            period=period,
            commodity_code=commodity_code,
            classification=classification,
            edition=edition,
            breakdown_mode=None,  # not applicable to tariffline data
            max_records=max_records,
        )
        return self._execute(
            query,
            frequency=_FREQUENCY_ANNUAL,
            path_template=_PATH_TARIFFLINE,
        )

    # ----- Preview methods (P01-P04) -------------------------------------

    def preview_exports(
        self,
        reporter_code: int,
        period: str,
        *,
        partner_code: int | None = None,
        commodity_code: str = "TOTAL",
        classification: str | None = None,
        edition: str | None = None,
        max_records: int | None = None,
    ) -> TradeResponse:
        """P01 — preview annual exports (no key required).

        Per `007_SDK_SPECIFICATION.md` §P01.
        Uses the public preview endpoint with
        `max_records` capped at 500.
        """
        raise NotImplementedError(
            "TradeService.preview_exports is not yet implemented."
        )

    def preview_imports(
        self,
        reporter_code: int,
        period: str,
        *,
        partner_code: int | None = None,
        commodity_code: str = "TOTAL",
        classification: str | None = None,
        edition: str | None = None,
        max_records: int | None = None,
    ) -> TradeResponse:
        """P02 — preview annual imports (no key required).

        Per `007_SDK_SPECIFICATION.md` §P02.
        """
        raise NotImplementedError(
            "TradeService.preview_imports is not yet implemented."
        )

    def preview_trade(
        self,
        reporter_code: int,
        flow_code: str,
        period: str,
        *,
        partner_code: int | None = None,
        commodity_code: str = "TOTAL",
        classification: str | None = None,
        edition: str | None = None,
        max_records: int | None = None,
    ) -> TradeResponse:
        """P03 — preview annual trade with an explicit flow.

        Per `007_SDK_SPECIFICATION.md` §P03.
        """
        raise NotImplementedError(
            "TradeService.preview_trade is not yet implemented."
        )

    def preview_tariffline(
        self,
        reporter_code: int,
        flow_code: str,
        period: str,
        *,
        partner_code: int | None = None,
        commodity_code: str | None = None,
        classification: str | None = None,
        edition: str | None = None,
        max_records: int | None = None,
    ) -> TradeResponse:
        """P04 — preview tariffline data (no key required).

        Per `007_SDK_SPECIFICATION.md` §P04.
        """
        raise NotImplementedError(
            "TradeService.preview_tariffline is not yet implemented."
        )

    # ----- Counting methods (C01-C03) ------------------------------------

    def count_exports(
        self,
        reporter_code: int,
        period: str,
        *,
        partner_code: int | None = None,
        commodity_code: str = "TOTAL",
        classification: str | None = None,
        edition: str | None = None,
        breakdown_mode: str | None = None,
    ) -> int:
        """C01 — count annual exports without fetching them.

        Per `007_SDK_SPECIFICATION.md` §C01.
        Uses `countOnly=true` on the upstream.
        """
        raise NotImplementedError(
            "TradeService.count_exports is not yet implemented."
        )

    def count_imports(
        self,
        reporter_code: int,
        period: str,
        *,
        partner_code: int | None = None,
        commodity_code: str = "TOTAL",
        classification: str | None = None,
        edition: str | None = None,
        breakdown_mode: str | None = None,
    ) -> int:
        """C02 — count annual imports without fetching them.

        Per `007_SDK_SPECIFICATION.md` §C02.
        """
        raise NotImplementedError(
            "TradeService.count_imports is not yet implemented."
        )

    def count_trade(
        self,
        reporter_code: int,
        flow_code: str,
        period: str,
        *,
        partner_code: int | None = None,
        commodity_code: str = "TOTAL",
        classification: str | None = None,
        edition: str | None = None,
        breakdown_mode: str | None = None,
    ) -> int:
        """C03 — count annual trade observations.

        Per `007_SDK_SPECIFICATION.md` §C03.
        """
        raise NotImplementedError(
            "TradeService.count_trade is not yet implemented."
        )

    # ----- Lifecycle -----------------------------------------------------

    def close(self) -> None:
        """Release any service-owned resources.

        In this skeleton the service owns no resources
        (the transport is caller-owned, the parser is
        optional and not yet implemented). The method
        is a no-op placeholder that will be implemented
        when the parser lands.
        """
        return None

    def __enter__(self) -> Self:
        """Enter the context manager; returns the service."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context manager; closes any owned resources."""
        self.close()


# ---------------------------------------------------------------------------
# Module-level convenience: documented method-method count
# ---------------------------------------------------------------------------


#: Number of public trade-retrieval methods declared on
#: the skeleton. Used by tests to confirm the surface
#: matches the SDK spec.
DECLARED_METHOD_COUNT: int = sum(
    1
    for name in dir(TradeService)
    if not name.startswith("_") and callable(getattr(TradeService, name, None))
)