"""Unit tests for the async jobs service (`un_comtrade.async_jobs`).

Per the P3-004 task scope, only three endpoints are
implemented:

- `submit_async_final_data` (POST)
- `check_async_request` (GET)
- `download_async_request` (GET)

The transport's retry + timeout policies are reused;
no new HTTP / retry / timeout logic is introduced.
The exact URL paths are documented-but-unverified
per `005_API_ENDPOINT_CATALOG.md` §D2; the module
constants `DEFAULT_PATH_SUBMIT_ASYNC`,
`DEFAULT_PATH_CHECK_ASYNC`, and
`DEFAULT_PATH_DOWNLOAD_ASYNC` capture the documented
defaults.

Coverage:

- AsyncRequestHandle: validation, immutability
- AsyncRequestStatus: validation, terminal-state
  helpers (`is_terminal`, `is_completed`, `is_failed`)
- AsyncJobsService:
  - Constructor (default + custom path templates)
  - Submit: URL path construction, form body,
    request-id extraction (multiple field names),
    POST method
  - Status: URL path with handle metadata, parsed
    status fields (status, count, elapsed, error)
  - Download: URL path, file write, default
    filename, custom filename, directory
    validation
  - Resolving handle from string vs `AsyncRequestHandle`
  - Edge cases: missing request id, malformed JSON,
    non-object body, missing directory
- Module constants + defaults
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import httpx
import pytest

from un_comtrade.async_jobs import (
    ASYNC_STATUS_COMPLETED,
    ASYNC_STATUS_FAILED,
    ASYNC_STATUS_PENDING,
    ASYNC_STATUS_RUNNING,
    ASYNC_STATUS_UNKNOWN,
    AsyncJobsService,
    AsyncRequestHandle,
    AsyncRequestStatus,
    DEFAULT_PATH_CHECK_ASYNC,
    DEFAULT_PATH_DOWNLOAD_ASYNC,
    DEFAULT_PATH_SUBMIT_ASYNC,
)
from un_comtrade.exceptions import ValidationError
from un_comtrade.transport import HttpTransport


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_transport(
    handler: Callable[[httpx.Request], httpx.Response],
) -> HttpTransport:
    """Build an `HttpTransport` backed by a mock handler."""
    return HttpTransport(
        base_url="https://example.invalid",
        user_agent="test/1.0",
        api_key="test-key-123",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


class _RequestCapture:
    """Capture requests observed by the mock handler."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, json={})


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_default_paths(self):
        assert DEFAULT_PATH_SUBMIT_ASYNC == (
            "/data/v1/bulk/{typeCode}/{freqCode}/{period}/{reporterCode}"
        )
        assert DEFAULT_PATH_CHECK_ASYNC == (
            "/data/v1/bulk/{typeCode}/{freqCode}/{period}/{reporterCode}/{requestId}/status"
        )
        assert DEFAULT_PATH_DOWNLOAD_ASYNC == (
            "/data/v1/bulk/{typeCode}/{freqCode}/{period}/{reporterCode}/{requestId}/file"
        )

    def test_status_constants(self):
        assert ASYNC_STATUS_PENDING == "Pending"
        assert ASYNC_STATUS_RUNNING == "Running"
        assert ASYNC_STATUS_COMPLETED == "Completed"
        assert ASYNC_STATUS_FAILED == "Failed"
        assert ASYNC_STATUS_UNKNOWN == "Unknown"


# ---------------------------------------------------------------------------
# AsyncRequestHandle
# ---------------------------------------------------------------------------


class TestAsyncRequestHandle:
    def test_minimal(self):
        h = AsyncRequestHandle(
            request_id="abc-123",
            type_code="C",
            frequency_code="A",
            period="2022",
            reporter_code=699,
        )
        assert h.request_id == "abc-123"
        assert h.type_code == "C"
        assert h.frequency_code == "A"
        assert h.period == "2022"
        assert h.reporter_code == 699
        assert h.upstream_url is None
        assert h.submitted_at is None

    def test_with_metadata(self):
        h = AsyncRequestHandle(
            request_id="abc-123",
            type_code="C",
            frequency_code="A",
            period="2022",
            reporter_code=699,
            upstream_url="https://example/",
            submitted_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        assert h.upstream_url == "https://example/"
        assert h.submitted_at == datetime(2024, 1, 1, tzinfo=timezone.utc)

    def test_empty_request_id_rejected(self):
        with pytest.raises(ValueError, match="request_id"):
            AsyncRequestHandle(
                request_id="",
                type_code="C",
                frequency_code="A",
                period="2022",
                reporter_code=699,
            )

    def test_whitespace_request_id_rejected(self):
        with pytest.raises(ValueError, match="request_id"):
            AsyncRequestHandle(
                request_id="   ",
                type_code="C",
                frequency_code="A",
                period="2022",
                reporter_code=699,
            )

    def test_negative_reporter_rejected(self):
        with pytest.raises(ValueError, match="reporter_code"):
            AsyncRequestHandle(
                request_id="abc",
                type_code="C",
                frequency_code="A",
                period="2022",
                reporter_code=-1,
            )

    def test_bool_reporter_rejected(self):
        with pytest.raises(TypeError, match="reporter_code"):
            AsyncRequestHandle(
                request_id="abc",
                type_code="C",
                frequency_code="A",
                period="2022",
                reporter_code=True,  # type: ignore[arg-type]
            )

    def test_immutable(self):
        import dataclasses
        h = AsyncRequestHandle(
            request_id="abc", type_code="C",
            frequency_code="A", period="2022", reporter_code=699,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            h.request_id = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AsyncRequestStatus
# ---------------------------------------------------------------------------


class TestAsyncRequestStatus:
    def test_minimal(self):
        s = AsyncRequestStatus(
            request_id="abc", status="Completed"
        )
        assert s.records_count is None
        assert s.elapsed_seconds is None
        assert s.error is None
        assert s.raw is None

    def test_full(self):
        s = AsyncRequestStatus(
            request_id="abc",
            status="Completed",
            records_count=1000,
            elapsed_seconds=2.5,
            error=None,
            raw={"status": "Completed", "count": 1000},
        )
        assert s.records_count == 1000
        assert s.elapsed_seconds == 2.5

    def test_is_terminal_completed(self):
        s = AsyncRequestStatus(request_id="abc", status="Completed")
        assert s.is_terminal is True
        assert s.is_completed is True
        assert s.is_failed is False

    def test_is_terminal_failed(self):
        s = AsyncRequestStatus(request_id="abc", status="Failed")
        assert s.is_terminal is True
        assert s.is_completed is False
        assert s.is_failed is True

    def test_is_terminal_pending(self):
        s = AsyncRequestStatus(request_id="abc", status="Pending")
        assert s.is_terminal is False
        assert s.is_completed is False
        assert s.is_failed is False

    def test_is_terminal_running(self):
        s = AsyncRequestStatus(request_id="abc", status="Running")
        assert s.is_terminal is False

    def test_is_terminal_unknown(self):
        s = AsyncRequestStatus(request_id="abc", status="Unknown")
        assert s.is_terminal is False

    def test_negative_records_count_rejected(self):
        with pytest.raises(ValueError, match="records_count"):
            AsyncRequestStatus(
                request_id="abc", status="Completed", records_count=-1
            )

    def test_negative_elapsed_rejected(self):
        with pytest.raises(ValueError, match="elapsed_seconds"):
            AsyncRequestStatus(
                request_id="abc", status="Completed", elapsed_seconds=-1.0
            )

    def test_immutable(self):
        import dataclasses
        s = AsyncRequestStatus(request_id="abc", status="Completed")
        with pytest.raises(dataclasses.FrozenInstanceError):
            s.status = "Failed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AsyncJobsService constructor
# ---------------------------------------------------------------------------


class TestAsyncJobsServiceConstructor:
    def test_default_paths(self):
        svc = AsyncJobsService(_make_transport(_RequestCapture()))
        assert svc._path_submit == DEFAULT_PATH_SUBMIT_ASYNC
        assert svc._path_check == DEFAULT_PATH_CHECK_ASYNC
        assert svc._path_download == DEFAULT_PATH_DOWNLOAD_ASYNC

    def test_custom_paths(self):
        svc = AsyncJobsService(
            _make_transport(_RequestCapture()),
            path_submit="/custom/submit",
            path_check="/custom/{requestId}/status",
            path_download="/custom/{requestId}/file",
        )
        assert svc._path_submit == "/custom/submit"
        assert svc._path_check == "/custom/{requestId}/status"
        assert svc._path_download == "/custom/{requestId}/file"

    def test_transport_property(self):
        transport = _make_transport(_RequestCapture())
        svc = AsyncJobsService(transport)
        assert svc.transport is transport


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------


class TestSubmit:
    def test_returns_handle(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"requestId": "abc-123"})

        svc = AsyncJobsService(_make_transport(handler))
        handle = svc.submit_async_final_data(699, "X", "2022")
        assert isinstance(handle, AsyncRequestHandle)
        assert handle.request_id == "abc-123"

    def test_url_path(self):
        capture = _RequestCapture()

        def handler(request: httpx.Request) -> httpx.Response:
            capture.requests.append(request)
            return httpx.Response(200, json={"requestId": "abc-123"})

        svc = AsyncJobsService(_make_transport(handler))
        svc.submit_async_final_data(699, "X", "2022")
        assert (
            capture.requests[0].url.path
            == "/data/v1/bulk/C/A/2022/699"
        )

    def test_method_is_post(self):
        capture = _RequestCapture()

        def handler(request: httpx.Request) -> httpx.Response:
            capture.requests.append(request)
            return httpx.Response(200, json={"requestId": "abc-123"})

        svc = AsyncJobsService(_make_transport(handler))
        svc.submit_async_final_data(699, "X", "2022")
        assert capture.requests[0].method == "POST"

    def test_form_body(self):
        capture = _RequestCapture()

        def handler(request: httpx.Request) -> httpx.Response:
            capture.requests.append(request)
            return httpx.Response(200, json={"requestId": "abc-123"})

        svc = AsyncJobsService(_make_transport(handler))
        svc.submit_async_final_data(699, "X", "2022")
        params = dict(capture.requests[0].url.params)
        assert params["flowCode"] == "X"
        assert params["cmdCode"] == "TOTAL"
        assert params["period"] == "2022"
        assert params["reporterCode"] == "699"

    def test_form_body_with_optional_kwargs(self):
        capture = _RequestCapture()

        def handler(request: httpx.Request) -> httpx.Response:
            capture.requests.append(request)
            return httpx.Response(200, json={"requestId": "abc-123"})

        svc = AsyncJobsService(_make_transport(handler))
        svc.submit_async_final_data(
            699, "X", "2022",
            partner_code=842,
            commodity_code="0101",
            classification="HS",
            edition="H2022",
            breakdown_mode="plus",
        )
        params = dict(capture.requests[0].url.params)
        assert params["partnerCode"] == "842"
        assert params["cmdCode"] == "0101"
        assert params["classification"] == "HS"
        assert params["edition"] == "H2022"
        assert params["breakdownMode"] == "plus"

    def test_monthly_freq_code(self):
        capture = _RequestCapture()

        def handler(request: httpx.Request) -> httpx.Response:
            capture.requests.append(request)
            return httpx.Response(200, json={"requestId": "abc-123"})

        svc = AsyncJobsService(_make_transport(handler))
        svc.submit_async_final_data(699, "X", "202201")
        assert "/data/v1/bulk/C/M/202201/699" == capture.requests[0].url.path

    def test_handle_carries_metadata(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"requestId": "abc-123"})

        svc = AsyncJobsService(_make_transport(handler))
        handle = svc.submit_async_final_data(699, "X", "2022")
        assert handle.type_code == "C"
        assert handle.frequency_code == "A"
        assert handle.period == "2022"
        assert handle.reporter_code == 699

    def test_handle_submitted_at_is_set(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"requestId": "abc-123"})

        svc = AsyncJobsService(_make_transport(handler))
        before = datetime.now(timezone.utc)
        handle = svc.submit_async_final_data(699, "X", "2022")
        after = datetime.now(timezone.utc)
        assert before <= handle.submitted_at <= after

    def test_handle_upstream_url_set(self):
        capture = _RequestCapture()

        def handler(request: httpx.Request) -> httpx.Response:
            capture.requests.append(request)
            return httpx.Response(200, json={"requestId": "abc-123"})

        svc = AsyncJobsService(_make_transport(handler))
        handle = svc.submit_async_final_data(699, "X", "2022")
        assert handle.upstream_url is not None
        # URL contains the submit path + the request id
        # (per httpx's URL canonicalisation, paths and
        # query keys may be lowercased; values preserve
        # case).
        assert "/data/v1/bulk" in handle.upstream_url.lower()
        assert "699" in handle.upstream_url

    def test_extract_request_id_alternate_field_names(self):
        # The upstream's exact field name is unverified;
        # we accept several documented-but-unverified
        # alternatives.
        for field_name in ("requestId", "request_id", "id", "jobId", "job_id"):
            def handler(
                request: httpx.Request, _name=field_name
            ) -> httpx.Response:
                return httpx.Response(200, json={_name: "abc-123"})

            svc = AsyncJobsService(_make_transport(handler))
            handle = svc.submit_async_final_data(699, "X", "2022")
            assert handle.request_id == "abc-123"

    def test_request_id_missing_raises_validation_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"unrelated": "field"})

        svc = AsyncJobsService(_make_transport(handler))
        with pytest.raises(ValidationError, match="request id"):
            svc.submit_async_final_data(699, "X", "2022")

    def test_request_id_int_returned_as_string(self):
        # Some upstream payloads use integer ids; coerce.
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"requestId": 12345})

        svc = AsyncJobsService(_make_transport(handler))
        handle = svc.submit_async_final_data(699, "X", "2022")
        assert handle.request_id == "12345"

    def test_non_object_body_raises_validation_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"[1, 2, 3]")

        svc = AsyncJobsService(_make_transport(handler))
        with pytest.raises(ValidationError, match="request id"):
            svc.submit_async_final_data(699, "X", "2022")

    def test_malformed_json_body_raises_validation_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"not json {{{")

        svc = AsyncJobsService(_make_transport(handler))
        with pytest.raises(ValidationError, match="request id"):
            svc.submit_async_final_data(699, "X", "2022")


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


def _make_handle() -> AsyncRequestHandle:
    return AsyncRequestHandle(
        request_id="abc-123",
        type_code="C",
        frequency_code="A",
        period="2022",
        reporter_code=699,
    )


class TestCheckStatus:
    def test_returns_status(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "status": "Completed",
                    "count": 50000,
                    "elapsedSeconds": 1.5,
                },
            )

        svc = AsyncJobsService(_make_transport(handler))
        status = svc.check_async_request(_make_handle())
        assert isinstance(status, AsyncRequestStatus)
        assert status.status == "Completed"
        assert status.records_count == 50000
        assert status.elapsed_seconds == 1.5

    def test_url_path(self):
        capture = _RequestCapture()

        def handler(request: httpx.Request) -> httpx.Response:
            capture.requests.append(request)
            return httpx.Response(200, json={"status": "Completed"})

        svc = AsyncJobsService(_make_transport(handler))
        svc.check_async_request(_make_handle())
        assert (
            capture.requests[0].url.path
            == "/data/v1/bulk/C/A/2022/699/abc-123/status"
        )

    def test_method_is_get(self):
        capture = _RequestCapture()

        def handler(request: httpx.Request) -> httpx.Response:
            capture.requests.append(request)
            return httpx.Response(200, json={"status": "Pending"})

        svc = AsyncJobsService(_make_transport(handler))
        svc.check_async_request(_make_handle())
        assert capture.requests[0].method == "GET"

    def test_alternate_field_names_status(self):
        for field in ("status", "state", "jobStatus", "job_status"):
            def handler(
                request: httpx.Request, _f=field
            ) -> httpx.Response:
                return httpx.Response(200, json={_f: "Completed"})

            svc = AsyncJobsService(_make_transport(handler))
            status = svc.check_async_request(_make_handle())
            assert status.status == "Completed"

    def test_alternate_field_names_count(self):
        for field in (
            "count",
            "recordsCount",
            "records_count",
            "recordCount",
            "n",
        ):
            def handler(
                request: httpx.Request, _f=field
            ) -> httpx.Response:
                return httpx.Response(200, json={_f: 1000})

            svc = AsyncJobsService(_make_transport(handler))
            status = svc.check_async_request(_make_handle())
            assert status.records_count == 1000

    def test_string_count_parsed(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"count": "12345"})

        svc = AsyncJobsService(_make_transport(handler))
        status = svc.check_async_request(_make_handle())
        assert status.records_count == 12345

    def test_unparseable_count_ignored(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"count": "not a number"})

        svc = AsyncJobsService(_make_transport(handler))
        status = svc.check_async_request(_make_handle())
        assert status.records_count is None

    def test_unknown_status_returned_as_unknown(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"unrelated": "field"})

        svc = AsyncJobsService(_make_transport(handler))
        status = svc.check_async_request(_make_handle())
        assert status.status == "Unknown"

    def test_non_object_body_yields_unknown(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"[1, 2, 3]")

        svc = AsyncJobsService(_make_transport(handler))
        status = svc.check_async_request(_make_handle())
        assert status.status == "Unknown"
        assert status.error is not None

    def test_malformed_json_body_yields_unknown(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"not json")

        svc = AsyncJobsService(_make_transport(handler))
        status = svc.check_async_request(_make_handle())
        assert status.status == "Unknown"

    def test_error_message_extracted(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"status": "Failed", "error": "boom"}
            )

        svc = AsyncJobsService(_make_transport(handler))
        status = svc.check_async_request(_make_handle())
        assert status.is_failed
        assert status.error == "boom"

    def test_raw_payload_preserved(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "status": "Completed",
                    "count": 1000,
                    "extra": "field",
                },
            )

        svc = AsyncJobsService(_make_transport(handler))
        status = svc.check_async_request(_make_handle())
        assert status.raw == {
            "status": "Completed",
            "count": 1000,
            "extra": "field",
        }

    def test_string_only_request_id_rejected(self):
        # The status / download methods require a full
        # handle so the URL can be built with metadata.
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"status": "Completed"})

        svc = AsyncJobsService(_make_transport(handler))
        with pytest.raises(ValidationError, match="AsyncRequestHandle"):
            svc.check_async_request("abc-123")  # type: ignore[arg-type]

    def test_string_only_request_id_for_download_rejected(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"{}")

        svc = AsyncJobsService(_make_transport(handler))
        with tempfile.TemporaryDirectory() as tmp:
            with pytest.raises(ValidationError, match="AsyncRequestHandle"):
                svc.download_async_request(
                    "abc-123", tmp  # type: ignore[arg-type]
                )


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


class TestDownload:
    def test_returns_path(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, content=b'{"records": []}',
                headers={"content-type": "application/json"},
            )

        svc = AsyncJobsService(_make_transport(handler))
        with tempfile.TemporaryDirectory() as tmp:
            path = svc.download_async_request(_make_handle(), tmp)
            assert isinstance(path, Path)
            assert path.exists()

    def test_url_path(self):
        capture = _RequestCapture()

        def handler(request: httpx.Request) -> httpx.Response:
            capture.requests.append(request)
            return httpx.Response(200, content=b"{}")

        svc = AsyncJobsService(_make_transport(handler))
        with tempfile.TemporaryDirectory() as tmp:
            svc.download_async_request(_make_handle(), tmp)
            assert (
                capture.requests[0].url.path
                == "/data/v1/bulk/C/A/2022/699/abc-123/file"
            )

    def test_default_filename(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"{}")

        svc = AsyncJobsService(_make_transport(handler))
        with tempfile.TemporaryDirectory() as tmp:
            path = svc.download_async_request(_make_handle(), tmp)
            assert path.name.startswith("async_")
            assert path.suffix == ".json"

    def test_custom_filename(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"{}")

        svc = AsyncJobsService(_make_transport(handler))
        with tempfile.TemporaryDirectory() as tmp:
            path = svc.download_async_request(
                _make_handle(), tmp, filename="my_data.json"
            )
            assert path.name == "my_data.json"

    def test_content_written_to_file(self):
        body = b'{"records": [{"id": 1}]}'

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=body)

        svc = AsyncJobsService(_make_transport(handler))
        with tempfile.TemporaryDirectory() as tmp:
            path = svc.download_async_request(_make_handle(), tmp)
            assert path.read_bytes() == body

    def test_nonexistent_directory_raises_validation_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"{}")

        svc = AsyncJobsService(_make_transport(handler))
        with pytest.raises(ValidationError, match="directory"):
            svc.download_async_request(
                _make_handle(),
                "/path/that/does/not/exist/at/all",
            )

    def test_directory_path_accepts_string(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"{}")

        svc = AsyncJobsService(_make_transport(handler))
        with tempfile.TemporaryDirectory() as tmp:
            path = svc.download_async_request(_make_handle(), tmp)
            assert path.parent == Path(tmp)

    def test_directory_path_accepts_path(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"{}")

        svc = AsyncJobsService(_make_transport(handler))
        with tempfile.TemporaryDirectory() as tmp:
            path = svc.download_async_request(
                _make_handle(), Path(tmp)
            )
            assert path.parent == Path(tmp)

    def test_path_supports_unsafe_chars(self):
        # Request IDs may contain unsafe filename chars;
        # the default filename sanitises them.
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"{}")

        handle = AsyncRequestHandle(
            request_id="abc/123:def",
            type_code="C",
            frequency_code="A",
            period="2022",
            reporter_code=699,
        )
        svc = AsyncJobsService(_make_transport(handler))
        with tempfile.TemporaryDirectory() as tmp:
            path = svc.download_async_request(handle, tmp)
            # Unsafe chars sanitised; the file is still
            # created.
            assert path.exists()
            assert "/" not in path.name
            assert ":" not in path.name


# ---------------------------------------------------------------------------
# End-to-end: submit → check → download
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_full_workflow(self):
        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if request.method == "POST":
                return httpx.Response(200, json={"requestId": "abc-123"})
            if path.endswith("/status"):
                # First call: pending; second call: completed.
                handler.counter += 1
                if handler.counter == 1:
                    return httpx.Response(
                        200, json={"status": "Running"}
                    )
                return httpx.Response(
                    200,
                    json={"status": "Completed", "count": 1000},
                )
            if path.endswith("/file"):
                return httpx.Response(
                    200,
                    content=b'{"records": []}',
                    headers={"content-type": "application/json"},
                )
            return httpx.Response(404)

        handler.counter = 0  # type: ignore[attr-defined]
        svc = AsyncJobsService(_make_transport(handler))

        # Submit
        handle = svc.submit_async_final_data(699, "X", "2022")
        assert handle.request_id == "abc-123"

        # Check status (first poll: running)
        s1 = svc.check_async_request(handle)
        assert s1.status == "Running"
        assert s1.is_terminal is False

        # Check status (second poll: completed)
        s2 = svc.check_async_request(handle)
        assert s2.status == "Completed"
        assert s2.is_completed is True

        # Download
        with tempfile.TemporaryDirectory() as tmp:
            path = svc.download_async_request(handle, tmp)
            assert path.exists()
            assert path.read_bytes() == b'{"records": []}'


# ---------------------------------------------------------------------------
# Transport integration (regression coverage)
# ---------------------------------------------------------------------------


class TestTransportIntegration:
    def test_auth_header_injected_on_submit(self):
        capture = _RequestCapture()

        def handler(request: httpx.Request) -> httpx.Response:
            capture.requests.append(request)
            return httpx.Response(200, json={"requestId": "abc-123"})

        svc = AsyncJobsService(_make_transport(handler))
        svc.submit_async_final_data(699, "X", "2022")
        assert (
            capture.requests[0].headers.get("ocp-apim-subscription-key")
            == "test-key-123"
        )

    def test_user_agent_injected(self):
        capture = _RequestCapture()

        def handler(request: httpx.Request) -> httpx.Response:
            capture.requests.append(request)
            return httpx.Response(200, json={"status": "Completed"})

        svc = AsyncJobsService(_make_transport(handler))
        svc.check_async_request(_make_handle())
        assert (
            capture.requests[0].headers.get("user-agent") == "test/1.0"
        )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_handle_immutable(self):
        import dataclasses

        handle = _make_handle()
        with pytest.raises(dataclasses.FrozenInstanceError):
            handle.request_id = "other"  # type: ignore[misc]

    def test_custom_path_template_used(self):
        capture = _RequestCapture()

        def handler(request: httpx.Request) -> httpx.Response:
            capture.requests.append(request)
            return httpx.Response(200, json={"status": "Completed"})

        svc = AsyncJobsService(
            _make_transport(handler),
            path_check="/custom/check/{requestId}",
        )
        svc.check_async_request(_make_handle())
        assert capture.requests[0].url.path == "/custom/check/abc-123"

    def test_handle_with_submitted_at(self):
        ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
        handle = AsyncRequestHandle(
            request_id="abc",
            type_code="C",
            frequency_code="A",
            period="2022",
            reporter_code=699,
            submitted_at=ts,
        )
        assert handle.submitted_at == ts