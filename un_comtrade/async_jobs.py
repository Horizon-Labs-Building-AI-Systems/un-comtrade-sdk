"""Authenticated asynchronous request support.

Per `005_API_ENDPOINT_CATALOG.md` §D2 and
`007_SDK_SPECIFICATION.md` §A01-A03, the upstream API
supports long-running data requests that exceed the
250,000-record cap of T1 via three endpoints:

- **Submit** — `POST /data/v1/bulk/{typeCode}/{freqCode}/{period}/{reporterCode}`
  (form body carries the query descriptor). Returns a
  handle (request id).
- **Status** — `GET /data/v1/bulk/{typeCode}/{freqCode}/{period}/{reporterCode}/{requestId}/status`.
  Returns the current status of the job.
- **Download** — `GET /data/v1/bulk/{typeCode}/{freqCode}/{period}/{reporterCode}/{requestId}/file`.
  Returns the result as a JSON file written to the
  consumer-specified directory.

**Verification status.** Per `005_API_ENDPOINT_CATALOG.md`
§D2: "Documented by `comtradeapicall`; not exercised in
this research." The exact URL paths are derived from the
`comtradeapicall` package documentation and are
**unverified** at SDK release time. The path constants
in this module are the documented-but-unverified
defaults; consumers that have access to the verified
paths can override them via the module constants.

Per the P3-004 task scope:

- **Reuse the existing transport.** No new HTTP /
  retry / timeout logic.
- **Implement only the 3 documented endpoints.**
  Polling logic (waiting for completion) is the
  consumer's responsibility.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

from .exceptions import ValidationError
from .logging import get_logger


if TYPE_CHECKING:
    from .transport import HttpTransport


__all__ = [
    "AsyncJobsService",
    "AsyncRequestHandle",
    "AsyncRequestStatus",
    "ASYNC_STATUS_COMPLETED",
    "ASYNC_STATUS_FAILED",
    "ASYNC_STATUS_PENDING",
    "ASYNC_STATUS_RUNNING",
    "ASYNC_STATUS_UNKNOWN",
    "DEFAULT_PATH_SUBMIT_ASYNC",
    "DEFAULT_PATH_CHECK_ASYNC",
    "DEFAULT_PATH_DOWNLOAD_ASYNC",
]


#: Default URL-path template for the async submit
#: endpoint (D2 §Submit). The path is `str.format`-able
#: with the documented placeholders.
#:
#: Verification status: documented by `comtradeapicall`;
#: not exercised at SDK release time. Consumers with
#: access to the verified path can override via the
#: `path_submit` constructor kwarg of `AsyncJobsService`.
DEFAULT_PATH_SUBMIT_ASYNC: str = (
    "/data/v1/bulk/{typeCode}/{freqCode}/{period}/{reporterCode}"
)

#: Default URL-path template for the async status endpoint.
DEFAULT_PATH_CHECK_ASYNC: str = (
    "/data/v1/bulk/{typeCode}/{freqCode}/{period}/{reporterCode}/{requestId}/status"
)

#: Default URL-path template for the async download endpoint.
DEFAULT_PATH_DOWNLOAD_ASYNC: str = (
    "/data/v1/bulk/{typeCode}/{freqCode}/{period}/{reporterCode}/{requestId}/file"
)


#: Async-request lifecycle statuses. The upstream's
#: status field is an opaque string; we surface these
#: canonical values for comparison via `AsyncRequestStatus.is_terminal`.
ASYNC_STATUS_PENDING: str = "Pending"
ASYNC_STATUS_RUNNING: str = "Running"
ASYNC_STATUS_COMPLETED: str = "Completed"
ASYNC_STATUS_FAILED: str = "Failed"
ASYNC_STATUS_UNKNOWN: str = "Unknown"


#: Set of terminal statuses (no further progress).
TERMINAL_STATUSES: frozenset[str] = frozenset(
    {ASYNC_STATUS_COMPLETED, ASYNC_STATUS_FAILED}
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AsyncRequestHandle:
    """E19 AsyncRequestHandle — handle returned by the submit endpoint.

    Carries the upstream `request_id` plus the metadata
    required to build the status / download URLs
    (`typeCode`, `frequencyCode`, `period`,
    `reporterCode`). The metadata is captured at submit
    time so the consumer does not need to remember it.
    """

    request_id: str
    type_code: str
    frequency_code: str
    period: str
    reporter_code: int
    upstream_url: str | None = None
    submitted_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise ValueError(
                "request_id must be a non-empty string"
            )
        if not isinstance(self.type_code, str) or not self.type_code.strip():
            raise ValueError(
                "type_code must be a non-empty string"
            )
        if not isinstance(self.frequency_code, str) or not self.frequency_code.strip():
            raise ValueError(
                "frequency_code must be a non-empty string"
            )
        if not isinstance(self.period, str) or not self.period.strip():
            raise ValueError(
                "period must be a non-empty string"
            )
        if isinstance(self.reporter_code, bool) or not isinstance(
            self.reporter_code, int
        ):
            raise TypeError(
                f"reporter_code must be an int; got "
                f"{type(self.reporter_code).__name__}"
            )
        if self.reporter_code < 0:
            raise ValueError(
                f"reporter_code must be non-negative; got "
                f"{self.reporter_code}"
            )
        if self.upstream_url is not None and not isinstance(
            self.upstream_url, str
        ):
            raise TypeError(
                f"upstream_url must be a str or None; got "
                f"{type(self.upstream_url).__name__}"
            )
        if self.submitted_at is not None and not isinstance(
            self.submitted_at, datetime
        ):
            raise TypeError(
                f"submitted_at must be a datetime or None; got "
                f"{type(self.submitted_at).__name__}"
            )


@dataclass(frozen=True)
class AsyncRequestStatus:
    """E20 AsyncRequestStatus — current status of an async job.

    The `status` field is the upstream's string. Common
    values (per the `comtradeapicall` documentation):
    `Pending`, `Running`, `Completed`, `Failed`. The SDK
    exposes `is_terminal` and `is_completed` helpers for
    common checks.

    `records_count` and `elapsed_seconds` are extracted
    from the upstream payload when present; they are
    `None` when the upstream omits them (e.g. while the
    job is still running).
    """

    request_id: str
    status: str
    records_count: int | None = None
    elapsed_seconds: float | None = None
    error: str | None = None
    raw: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise ValueError(
                "request_id must be a non-empty string"
            )
        if not isinstance(self.status, str):
            raise TypeError(
                f"status must be a str; got {type(self.status).__name__}"
            )
        if self.records_count is not None:
            if isinstance(self.records_count, bool) or not isinstance(
                self.records_count, int
            ):
                raise TypeError(
                    f"records_count must be an int or None; got "
                    f"{type(self.records_count).__name__}"
                )
            if self.records_count < 0:
                raise ValueError(
                    f"records_count must be non-negative; got "
                    f"{self.records_count}"
                )
        if self.elapsed_seconds is not None:
            if isinstance(self.elapsed_seconds, bool) or not isinstance(
                self.elapsed_seconds, (int, float)
            ):
                raise TypeError(
                    f"elapsed_seconds must be a number or None; got "
                    f"{type(self.elapsed_seconds).__name__}"
                )
            if self.elapsed_seconds < 0:
                raise ValueError(
                    f"elapsed_seconds must be non-negative; got "
                    f"{self.elapsed_seconds}"
                )
        if self.error is not None and not isinstance(self.error, str):
            raise TypeError(
                f"error must be a str or None; got "
                f"{type(self.error).__name__}"
            )

    @property
    def is_terminal(self) -> bool:
        """True if the status is `Completed` or `Failed`."""
        return self.status in TERMINAL_STATUSES

    @property
    def is_completed(self) -> bool:
        """True if the status is `Completed`."""
        return self.status == ASYNC_STATUS_COMPLETED

    @property
    def is_failed(self) -> bool:
        """True if the status is `Failed`."""
        return self.status == ASYNC_STATUS_FAILED


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


#: Field names that the upstream's submit response may
#: use to carry the request id. The exact field name is
#: unverified at SDK release time; consumers can
#: inspect `AsyncRequestHandle.upstream_url` and the
#: raw response body via the captured fields.
_REQUEST_ID_KEYS: tuple[str, ...] = (
    "requestId",
    "request_id",
    "id",
    "jobId",
    "job_id",
)


class AsyncJobsService:
    """Async job submit / status / download.

    Stateless: the service holds only the injected
    transport (and optional config). The handle returned
    by `submit_async_final_data` is the input to
    `check_async_request` and `download_async_request`.

    Per the task scope: reuses the existing
    `HttpTransport` (retry + timeout honoured). No new
    transport logic, no polling, no auto-wait.
    """

    def __init__(
        self,
        transport: "HttpTransport",
        *,
        path_submit: str = DEFAULT_PATH_SUBMIT_ASYNC,
        path_check: str = DEFAULT_PATH_CHECK_ASYNC,
        path_download: str = DEFAULT_PATH_DOWNLOAD_ASYNC,
        logger: logging.Logger | None = None,
    ) -> None:
        """Construct an async-jobs service.

        Parameters
        ----------
        transport
            The HTTP transport used for submit / status /
            download. The caller retains ownership.
        path_submit
            URL-path template for the submit endpoint.
            Default is `DEFAULT_PATH_SUBMIT_ASYNC`
            (documented-but-unverified). Consumers with
            access to the verified path can override.
        path_check
            URL-path template for the status endpoint.
        path_download
            URL-path template for the download endpoint.
        logger
            Optional logger. When `None`, the SDK's
            `metadata` logger is used.
        """
        self._transport: "HttpTransport" = transport
        self._path_submit: str = path_submit
        self._path_check: str = path_check
        self._path_download: str = path_download
        self._logger: logging.Logger = (
            logger if logger is not None else get_logger("metadata")
        )

    # ----- Properties ------------------------------------------------------

    @property
    def transport(self) -> "HttpTransport":
        """The HTTP transport this service uses."""
        return self._transport

    # ----- Public API ------------------------------------------------------

    def submit_async_final_data(
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
    ) -> AsyncRequestHandle:
        """Submit a long-running data request.

        Issues a POST to the async submit endpoint
        with the supplied query descriptor as the form
        body. Returns an `AsyncRequestHandle` carrying
        the upstream `requestId` plus the metadata
        needed for status / download.

        Parameters mirror `TradeService.get_trade` (T03):
        the upstream's async submit accepts the same
        query descriptor as the synchronous trade
        endpoint.
        """
        # Build path parameters from the metadata.
        type_code = "C"  # async MVP supports commodities
        # only; services (S) are documented but not
        # exercised.
        path_params = {
            "typeCode": type_code,
            "freqCode": _derive_freq_code(period),
            "period": period,
            "reporterCode": str(reporter_code),
        }
        path = self._path_submit.format(**path_params)

        # Form body — the upstream's submit endpoint
        # accepts the query descriptor as form fields.
        form: dict[str, str] = {
            "flowCode": flow_code,
            "cmdCode": commodity_code,
            "period": period,
            "reporterCode": str(reporter_code),
        }
        if partner_code is not None:
            form["partnerCode"] = str(partner_code)
        if classification is not None:
            form["classification"] = classification
        if edition is not None:
            form["edition"] = edition
        if breakdown_mode is not None:
            form["breakdownMode"] = breakdown_mode

        response = self._transport.post(
            path,
            params=form,
            kind="default",
        )
        upstream_url = response.url
        body = self._safe_parse_json(response)

        request_id = self._extract_request_id(body)
        if request_id is None:
            raise ValidationError(
                "async submit response did not contain a "
                "request id; raw body: "
                f"{getattr(body, '__repr__', lambda: body)() if body else '<empty>'}"
            )

        self._logger.info(
            "async submit ok reporter=%s period=%s flow=%s request_id=%s",
            reporter_code,
            period,
            flow_code,
            request_id,
        )

        return AsyncRequestHandle(
            request_id=request_id,
            type_code=type_code,
            frequency_code=path_params["freqCode"],
            period=period,
            reporter_code=reporter_code,
            upstream_url=upstream_url,
            submitted_at=datetime.now(timezone.utc),
        )

    def check_async_request(
        self, request_id: str | AsyncRequestHandle
    ) -> AsyncRequestStatus:
        """Poll the status of an async request.

        Accepts either a `request_id` string or a full
        `AsyncRequestHandle`. When given a string, the
        status path is built with placeholder metadata
        (the URL requires typeCode + freqCode + period
        + reporterCode); consumers SHOULD pass the
        full handle returned by `submit_async_final_data`
        so the URL is built with the correct metadata.
        """
        handle = self._resolve_handle(request_id)
        path = self._path_check.format(
            typeCode=handle.type_code,
            freqCode=handle.frequency_code,
            period=handle.period,
            reporterCode=handle.reporter_code,
            requestId=handle.request_id,
        )
        response = self._transport.get(path, kind="default")
        upstream_url = response.url
        body = self._safe_parse_json(response)

        status, records_count, elapsed_seconds, error, raw = self._extract_status(
            handle.request_id, body
        )
        return AsyncRequestStatus(
            request_id=handle.request_id,
            status=status,
            records_count=records_count,
            elapsed_seconds=elapsed_seconds,
            error=error,
            raw=raw,
        )

    def download_async_request(
        self,
        request_id: str | AsyncRequestHandle,
        directory: str | Path,
        *,
        filename: str | None = None,
    ) -> Path:
        """Download the result of an async request.

        Issues a GET to the async download endpoint and
        writes the response body to the supplied
        directory. Returns the path to the saved file.

        Parameters
        ----------
        request_id
            Either a `request_id` string or a full
            `AsyncRequestHandle`. The handle is
            preferred because it carries the metadata
            needed to build the URL.
        directory
            The destination directory. Must exist;
            `ValidationError` is raised otherwise.
        filename
            Optional filename override. When `None`,
            the SDK derives a default filename from the
            request id (e.g. `async_<request_id>.json`).
        """
        handle = self._resolve_handle(request_id)
        path = self._path_download.format(
            typeCode=handle.type_code,
            freqCode=handle.frequency_code,
            period=handle.period,
            reporterCode=handle.reporter_code,
            requestId=handle.request_id,
        )
        response = self._transport.get(path, kind="large_download")

        directory_path = Path(directory)
        if not directory_path.is_dir():
            raise ValidationError(
                f"download directory does not exist: {directory_path}"
            )
        if filename is None:
            filename = _default_filename(handle.request_id)
        destination = directory_path / filename
        destination.write_bytes(response.body)
        self._logger.info(
            "async download ok request_id=%s path=%s bytes=%d",
            handle.request_id,
            str(destination),
            len(response.body),
        )
        return destination

    # ----- Internal helpers ----------------------------------------------

    def _resolve_handle(
        self,
        request_id: str | AsyncRequestHandle,
    ) -> AsyncRequestHandle:
        """Coerce a string OR a handle to an `AsyncRequestHandle`.

        When the caller passes a string, we don't have
        the metadata required to build the status /
        download URL. We raise `ValidationError` rather
        than guess; the handle is the documented
        contract.
        """
        if isinstance(request_id, AsyncRequestHandle):
            return request_id
        raise ValidationError(
            "AsyncJobsService.check_async_request / "
            "download_async_request require an "
            "AsyncRequestHandle (the metadata is needed "
            "to build the URL); pass the handle returned "
            "by submit_async_final_data rather than the "
            "request id string alone."
        )

    def _safe_parse_json(self, response: Any) -> Any:
        """Parse the response body as JSON; return None on failure.

        Some endpoints may return a non-JSON body during
        failure modes; we treat that as "no body" rather
        than raising.
        """
        try:
            return response.json()
        except Exception:  # noqa: BLE001 - intentional catch-all
            try:
                return json.loads(response.text)
            except Exception:  # noqa: BLE001
                return None

    def _extract_request_id(self, body: Any) -> str | None:
        """Find the upstream's request id in the response body.

        The exact field name is unverified; we look in
        several documented-but-unverified locations and
        return the first non-empty string.
        """
        if not isinstance(body, Mapping):
            return None
        for key in _REQUEST_ID_KEYS:
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, int):
                return str(value)
        return None

    def _extract_status(
        self,
        request_id: str,
        body: Any,
    ) -> tuple[str, int | None, float | None, str | None, Mapping[str, Any] | None]:
        """Extract status, records_count, elapsed, error, raw from body.

        Returns a 5-tuple: `(status, records_count,
        elapsed_seconds, error, raw)`. The raw payload
        is preserved on `AsyncRequestStatus.raw` for
        consumers that want to inspect undocumented
        fields.
        """
        if not isinstance(body, Mapping):
            return (
                ASYNC_STATUS_UNKNOWN,
                None,
                None,
                "response body is not a JSON object",
                None,
            )
        # Status field — exact name is unverified;
        # search common candidates.
        status_value: str = ASYNC_STATUS_UNKNOWN
        for key in ("status", "state", "jobStatus", "job_status"):
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                status_value = value.strip()
                break
        # Records count.
        records_count: int | None = None
        for key in (
            "count",
            "recordsCount",
            "records_count",
            "recordCount",
            "n",
        ):
            value = body.get(key)
            if isinstance(value, bool):
                continue
            if isinstance(value, int):
                records_count = value
                break
            if isinstance(value, float) and value.is_integer():
                records_count = int(value)
                break
            if isinstance(value, str):
                try:
                    records_count = int(value)
                    break
                except ValueError:
                    continue
        # Elapsed seconds.
        elapsed_seconds: float | None = None
        for key in ("elapsedSeconds", "elapsed_seconds", "elapsed"):
            value = body.get(key)
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                elapsed_seconds = float(value)
                break
        # Error message.
        error: str | None = None
        for key in ("error", "message", "errorMessage", "error_message"):
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                error = value.strip()
                break
        return status_value, records_count, elapsed_seconds, error, dict(body)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


_PERIOD_PATTERN: re.Pattern[str] = re.compile(r"^(\d{4})(\d{2})?$")


def _derive_freq_code(period: str) -> str:
    """Derive the URL-path `freqCode` from the period token.

    Per `006_DATA_MODEL.md` §4.12, period tokens are
    either `YYYY` (annual) or `YYYYMM` (monthly).
    """
    if not isinstance(period, str) or not period.strip():
        raise ValidationError("period must be a non-empty string")
    match = _PERIOD_PATTERN.match(period.strip())
    if not match:
        raise ValidationError(
            f"period must be YYYY or YYYYMM; got {period!r}"
        )
    if match.group(2):
        return "M"
    return "A"


_SAFE_FILENAME_PATTERN: re.Pattern[str] = re.compile(r"[^A-Za-z0-9._-]")


def _default_filename(request_id: str) -> str:
    """Derive a safe default filename from a request id."""
    safe = _SAFE_FILENAME_PATTERN.sub("_", request_id).strip("._")
    if not safe:
        safe = "request"
    return f"async_{safe}.json"