"""
Minimal UN Comtrade API client.

This module is a hand-rolled replacement for the official
``comtradeapicall`` package, built so it has zero required dependencies
beyond ``requests``.  It is intentionally small and easy to read so you
can adapt it to your project.  All public methods return either:

* a :class:`ComtradeResponse` (raw JSON + metadata), or
* a :class:`pandas.DataFrame` (when pandas is installed, otherwise
  fall back to ``list[dict]``).

The UN Comtrade API is the official trade statistics service of the
United Nations Statistics Division.  Trade data comes in two flavours:

* **Final data** — official aggregates reported by countries
* **Tariffline data** — granular line-level records (more detail,
  same idea, more rows per shipment)

Both are available on the same query language; the only difference is
the URL path.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode

import requests


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_ROOT = "https://comtradeapi.un.org"
DATA_BASE = f"{API_ROOT}/data/v1"
TOOLS_BASE = f"{API_ROOT}/tools/v1"
PREVIEW_BASE = f"{API_ROOT}/public/v1"
REF_BASE = f"{API_ROOT}/files/v1/app/reference"

# Documented per-call cap.  We add a small client-side guard so you don't
# silently truncate the response if you forget to set maxRecords.
PREVIEW_RECORD_CAP = 500
AUTH_RECORD_CAP = 250_000

DEFAULT_TIMEOUT = 60
DEFAULT_RETRIES = 3
RETRY_BACKOFF = 5  # seconds; multiplied by attempt number


# ---------------------------------------------------------------------------
# Response wrapper
# ---------------------------------------------------------------------------

@dataclass
class ComtradeResponse:
    """Holds the raw JSON from UN Comtrade plus a few handy helpers."""

    elapsed_seconds: float
    count: int
    data: list[dict[str, Any]]
    error: str = ""
    url: str = ""
    status_code: int = 200

    # --- conversion helpers ------------------------------------------------

    def to_dataframe(self):
        """Return a :class:`pandas.DataFrame` if pandas is available,
        else a plain ``list[dict]``."""
        try:
            import pandas as pd  # type: ignore
        except ImportError:
            return self.data
        return pd.DataFrame(self.data)

    def to_json(self, path: str | os.PathLike, indent: int = 2) -> Path:
        """Save the response payload to ``path`` as pretty-printed JSON."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "url": self.url,
            "status_code": self.status_code,
            "elapsed_seconds": self.elapsed_seconds,
            "count": self.count,
            "error": self.error,
            "data": self.data,
        }
        p.write_text(json.dumps(payload, indent=indent, ensure_ascii=False), encoding="utf-8")
        return p

    # --- convenience -------------------------------------------------------

    def __len__(self) -> int:  # noqa: D401
        return self.count

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"ComtradeResponse(count={self.count}, error={self.error!r})"


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class ComtradeClient:
    """Thin wrapper around the UN Comtrade HTTP API.

    Parameters
    ----------
    subscription_key:
        Free API key from https://comtradedeveloper.un.org/profile .
        When ``None`` the client uses the public preview endpoint, which
        is limited to 500 records per call.  When set, calls go to the
        authenticated endpoint and can return up to 250K records.
    timeout:
        HTTP timeout in seconds.
    retries:
        Number of times to retry on 429 (rate-limited) or 5xx responses.
    proxy_url:
        Optional proxy, e.g. ``http://user:pass@host:8080``.
    """

    def __init__(
        self,
        subscription_key: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        proxy_url: str | None = None,
    ) -> None:
        self.subscription_key = subscription_key
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        if proxy_url:
            self.session.proxies = {"http": proxy_url, "https": proxy_url}
        # Some endpoints are sensitive to a UA header
        self.session.headers.update(
            {
                "User-Agent": "comtrade-python-client/1.0 (+https://uncomtrade.org)",
                "Accept": "application/json",
            }
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def is_authenticated(self) -> bool:
        return bool(self.subscription_key)

    def get_reference(self, category: str) -> list[dict[str, Any]]:
        """Fetch a reference list, e.g. ``"Reporters"``, ``"HS"``,
        ``"partnerAreas"`` (case-insensitive).

        Reference endpoints are public — no subscription key required.
        """
        path = self._resolve_reference_path(category)
        url = f"{REF_BASE}/{path}"
        resp = self._raw_get(url, params={})
        return resp.get("results", resp.get("data", []))

    def list_references(self) -> list[dict[str, Any]]:
        """Return the catalogue of every available reference table."""
        url = f"{REF_BASE}/ListofReferences.json"
        resp = self._raw_get(url, params={})
        return resp.get("results", [])

    # ------------------------------------------------------------------
    # Trade data
    # ------------------------------------------------------------------

    def preview_final(
        self,
        typeCode: str = "C",
        freqCode: str = "A",
        clCode: str = "HS",
        period: str | int | Iterable[str | int] = "2022",
        reporterCode: int | str | None = None,
        cmdCode: int | str | None = None,
        flowCode: str | None = None,
        partnerCode: int | str | None = None,
        partner2Code: int | str | None = None,
        customsCode: str | None = None,
        motCode: int | str | None = None,
        maxRecords: int | None = None,
        aggregateBy: str | None = None,
        breakdownMode: str = "classic",
        includeDesc: bool = True,
    ) -> ComtradeResponse:
        """Public preview — final trade data, no key, ≤500 records."""
        return self._call(
            base=f"{PREVIEW_BASE}/preview",
            typeCode=typeCode, freqCode=freqCode, clCode=clCode, period=period,
            reporterCode=reporterCode, cmdCode=cmdCode, flowCode=flowCode,
            partnerCode=partnerCode, partner2Code=partner2Code,
            customsCode=customsCode, motCode=motCode,
            maxRecords=maxRecords, aggregateBy=aggregateBy,
            breakdownMode=breakdownMode, includeDesc=includeDesc,
            auth=False, countOnly=False,
        )

    def preview_tariffline(
        self,
        typeCode: str = "C",
        freqCode: str = "A",
        clCode: str = "HS",
        period: str | int | Iterable[str | int] = "2022",
        reporterCode: int | str | None = None,
        cmdCode: int | str | None = None,
        flowCode: str | None = None,
        partnerCode: int | str | None = None,
        partner2Code: int | str | None = None,
        customsCode: str | None = None,
        motCode: int | str | None = None,
        maxRecords: int | None = None,
        includeDesc: bool = True,
    ) -> ComtradeResponse:
        """Public preview — tariffline data, no key, ≤500 records."""
        return self._call(
            base=f"{PREVIEW_BASE}/previewTariffline",
            typeCode=typeCode, freqCode=freqCode, clCode=clCode, period=period,
            reporterCode=reporterCode, cmdCode=cmdCode, flowCode=flowCode,
            partnerCode=partnerCode, partner2Code=partner2Code,
            customsCode=customsCode, motCode=motCode,
            maxRecords=maxRecords, aggregateBy=None,
            breakdownMode=None, includeDesc=includeDesc,
            auth=False, countOnly=False,
        )

    def get_final(
        self,
        typeCode: str = "C",
        freqCode: str = "A",
        clCode: str = "HS",
        period: str | int | Iterable[str | int] = "2022",
        reporterCode: int | str | None = None,
        cmdCode: int | str | None = None,
        flowCode: str | None = None,
        partnerCode: int | str | None = None,
        partner2Code: int | str | None = None,
        customsCode: str | None = None,
        motCode: int | str | None = None,
        maxRecords: int | None = None,
        aggregateBy: str | None = None,
        breakdownMode: str = "classic",
        includeDesc: bool = True,
    ) -> ComtradeResponse:
        """Authenticated — final trade data, ≤250K records per call."""
        if not self.is_authenticated:
            raise RuntimeError(
                "get_final requires a subscription_key — pass one to "
                "ComtradeClient(subscription_key=...). See "
                "https://comtradedeveloper.un.org/profile"
            )
        return self._call(
            base=f"{DATA_BASE}/get",
            typeCode=typeCode, freqCode=freqCode, clCode=clCode, period=period,
            reporterCode=reporterCode, cmdCode=cmdCode, flowCode=flowCode,
            partnerCode=partnerCode, partner2Code=partner2Code,
            customsCode=customsCode, motCode=motCode,
            maxRecords=maxRecords, aggregateBy=aggregateBy,
            breakdownMode=breakdownMode, includeDesc=includeDesc,
            auth=True, countOnly=False,
        )

    def get_tariffline(
        self,
        typeCode: str = "C",
        freqCode: str = "A",
        clCode: str = "HS",
        period: str | int | Iterable[str | int] = "2022",
        reporterCode: int | str | None = None,
        cmdCode: int | str | None = None,
        flowCode: str | None = None,
        partnerCode: int | str | None = None,
        partner2Code: int | str | None = None,
        customsCode: str | None = None,
        motCode: int | str | None = None,
        maxRecords: int | None = None,
        includeDesc: bool = True,
    ) -> ComtradeResponse:
        """Authenticated — tariffline data, ≤250K records per call."""
        if not self.is_authenticated:
            raise RuntimeError("get_tariffline requires a subscription_key.")
        return self._call(
            base=f"{DATA_BASE}/getTariffline",
            typeCode=typeCode, freqCode=freqCode, clCode=clCode, period=period,
            reporterCode=reporterCode, cmdCode=cmdCode, flowCode=flowCode,
            partnerCode=partnerCode, partner2Code=partner2Code,
            customsCode=customsCode, motCode=motCode,
            maxRecords=maxRecords, aggregateBy=None,
            breakdownMode=None, includeDesc=includeDesc,
            auth=True, countOnly=False,
        )

    def get_trade_balance(
        self,
        typeCode: str = "C",
        freqCode: str = "A",
        clCode: str = "HS",
        period: str | int | Iterable[str | int] = "2022",
        reporterCode: int | str | None = None,
        cmdCode: int | str | None = None,
        partnerCode: int | str | None = None,
        partner2Code: int | str | None = None,
        customsCode: str | None = None,
        motCode: int | str | None = None,
        maxRecords: int | None = None,
        breakdownMode: str = "classic",
        includeDesc: bool = True,
    ) -> ComtradeResponse:
        """Exports and imports laid out side-by-side (authenticated)."""
        if not self.is_authenticated:
            raise RuntimeError("get_trade_balance requires a subscription_key.")
        return self._call(
            base=f"{TOOLS_BASE}/getTradeBalance",
            typeCode=typeCode, freqCode=freqCode, clCode=clCode, period=period,
            reporterCode=reporterCode, cmdCode=cmdCode, flowCode=None,
            partnerCode=partnerCode, partner2Code=partner2Code,
            customsCode=customsCode, motCode=motCode,
            maxRecords=maxRecords, aggregateBy=None,
            breakdownMode=breakdownMode, includeDesc=includeDesc,
            auth=True, countOnly=False,
        )

    # ------------------------------------------------------------------
    # Internal — actually issue the HTTP call
    # ------------------------------------------------------------------

    def _call(
        self,
        *,
        base: str,
        typeCode: str,
        freqCode: str,
        clCode: str,
        period: str | int | Iterable[str | int],
        reporterCode: int | str | None,
        cmdCode: int | str | None,
        flowCode: str | None,
        partnerCode: int | str | None,
        partner2Code: int | str | None,
        customsCode: str | None,
        motCode: int | str | None,
        maxRecords: int | None,
        aggregateBy: str | None,
        breakdownMode: str | None,
        includeDesc: bool | None,
        auth: bool,
        countOnly: bool,
    ) -> ComtradeResponse:
        url = f"{base}/{typeCode}/{freqCode}/{clCode}"

        params: dict[str, Any] = {
            # NOTE: the preview endpoint is case-sensitive and uses
            # ``reportercode`` (all lowercase) for the reporter.
            "reportercode": reporterCode,
            "flowCode": flowCode,
            "period": _flatten(period),
            "cmdCode": cmdCode,
            "partnerCode": partnerCode,
            "partner2Code": partner2Code,
            "customsCode": customsCode,
            "motCode": motCode,
            "maxRecords": maxRecords,
            "format": "JSON",
            "aggregateBy": aggregateBy,
            "breakdownMode": breakdownMode,
            "countOnly": countOnly,
            "includeDesc": includeDesc,
        }

        if auth:
            params["subscription-key"] = self.subscription_key
            cap = AUTH_RECORD_CAP
        else:
            cap = PREVIEW_RECORD_CAP

        # Drop None values, but respect the documented maxRecords ceiling.
        params = {k: v for k, v in params.items() if v is not None}
        if "maxRecords" in params and params["maxRecords"] > cap:
            params["maxRecords"] = cap

        # Retry loop — Comtrade loves a 429 now and then.
        last_err = ""
        for attempt in range(1, self.retries + 1):
            try:
                t0 = time.time()
                r = self.session.get(url, params=params, timeout=self.timeout)
                elapsed = time.time() - t0
                if r.status_code == 429 or r.status_code >= 500:
                    last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                    time.sleep(RETRY_BACKOFF * attempt)
                    continue
                r.raise_for_status()
                body = r.json()
                return ComtradeResponse(
                    elapsed_seconds=elapsed,
                    count=body.get("count", 0),
                    data=body.get("data", []),
                    error=body.get("error", ""),
                    url=r.url,
                    status_code=r.status_code,
                )
            except requests.RequestException as exc:
                last_err = str(exc)
                time.sleep(RETRY_BACKOFF * attempt)

        return ComtradeResponse(
            elapsed_seconds=0.0, count=0, data=[],
            error=last_err or "request failed", url=url, status_code=0,
        )

    def _raw_get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(1, self.retries + 1):
            try:
                r = self.session.get(url, params=params, timeout=self.timeout)
                if r.status_code == 429 or r.status_code >= 500:
                    time.sleep(RETRY_BACKOFF * attempt)
                    continue
                r.raise_for_status()
                return r.json()
            except requests.RequestException:
                time.sleep(RETRY_BACKOFF * attempt)
        raise RuntimeError(f"Failed to fetch {url} after {self.retries} attempts")

    # ------------------------------------------------------------------
    # Path resolution for reference endpoints
    # ------------------------------------------------------------------

    # Public reference category aliases → file path fragment
    _REF_PATHS = {
        "reporters": "Reporters.json",
        "reporter": "Reporters.json",
        "partners": "partnerAreas.json",
        "partner": "partnerAreas.json",
        "partnerareas": "partnerAreas.json",
        "hs": "HS.json",
        "h0": "H0.json", "h1": "H1.json", "h2": "H2.json", "h3": "H3.json",
        "h4": "H4.json", "h5": "H5.json", "h6": "H6.json",
        "s1": "S1.json", "s2": "S2.json", "s3": "S3.json", "s4": "S4.json",
        "ss": "SS.json",
        "b4": "B4.json", "b5": "B5.json",
        "eb02": "EB02.json", "eb10": "EB10.json", "eb10s": "EB10S.json",
        "eb": "EB.json",
        "freq": "Frequency.json",
        "frequency": "Frequency.json",
        "flow": "tradeRegimes.json",
        "tradeflows": "tradeRegimes.json",
        "traderegimes": "tradeRegimes.json",
        "customs": "CustomsCodes.json",
        "customscodes": "CustomsCodes.json",
        "mot": "ModeOfTransportCodes.json",
        "modeoftransport": "ModeOfTransportCodes.json",
        "modeoftransportcodes": "ModeOfTransportCodes.json",
        "mos": "ModeOfSupply.json",
        "modeofsupply": "ModeOfSupply.json",
        "qty": "QuantityUnits.json",
        "quantityunits": "QuantityUnits.json",
        "dataitems": "TradeDataItems.json",
        "tradedataitems": "TradeDataItems.json",
    }

    def _resolve_reference_path(self, category: str) -> str:
        key = category.strip().lower().replace(" ", "").replace("-", "")
        if key in self._REF_PATHS:
            return self._REF_PATHS[key]
        # Allow direct file names like "Reporters.json"
        if category.lower().endswith(".json"):
            return category
        raise ValueError(
            f"Unknown reference category {category!r}. "
            f"Use one of: {sorted(self._REF_PATHS)} or a filename ending in .json"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _flatten(value: str | int | Iterable[str | int] | None) -> str | None:
    """Convert a list of periods (or single value) to a comma-separated string.

    Comtrade accepts comma-separated periods: ``"2020,2021,2022"`` for annual
    data or ``"202201,202202"`` for monthly.
    """
    if value is None:
        return None
    if isinstance(value, (str, int)):
        return str(value)
    return ",".join(str(v) for v in value)
