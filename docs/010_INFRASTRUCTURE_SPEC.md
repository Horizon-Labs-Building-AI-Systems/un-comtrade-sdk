```
Document ID
010

Title
Infrastructure & Runtime Services Specification

Version
0.1.0

Status
DRAFT

Created
2026-06-26T20:25:58Z

Last Updated
2026-06-26T20:25:58Z

Author
Codex

Project
UN Comtrade Python SDK

Dependencies
009_TRADE_LAYER_SPEC.md

Supersedes
None
```

---

# 1. Infrastructure Overview

## 1.1 Purpose

The Infrastructure & Runtime Services layer (the
infrastructure layer) provides the cross-cutting
runtime services that every other layer of the SDK
consumes. The infrastructure layer is the seam
between the SDK and the runtime environment. It
encapsulates the cross-cutting concerns that are
not the responsibility of any single domain layer:
configuration, retry, timeout, logging, caching,
progress reporting, resume support, error
propagation, observability, and security.

The infrastructure layer is not a domain layer. The
infrastructure layer does not perform network I/O,
does not perform filesystem I/O, and does not own
domain entities. The infrastructure layer provides
the services that the domain layers use to perform
their work.

## 1.2 Responsibilities

The infrastructure layer is responsible for:

- Configuration management.
- Retry and backoff scheduling.
- Timeout enforcement.
- Logging at the documented levels.
- Caching of the metadata catalogue and the trade
  responses.
- Progress reporting through the documented callback.
- Resume support for interrupted downloads.
- Error propagation through the documented exception
  hierarchy.
- Observability through the documented diagnostic
  surface.
- Security of authentication material and sensitive
  configuration.
- Request tracking through the documented request
  identifier.

## 1.3 Position in architecture

The infrastructure layer is the cross-cutting seam
declared in `003_ARCHITECTURE.md` §5.1. The layer is
invoked by every domain layer of the SDK. The layer
depends on the Python standard library; the layer
does not depend on any other layer of the SDK.

The infrastructure layer is implemented as a set of
modules under the `un_comtrade` package. The modules
are:

- `un_comtrade.config` — configuration management.
- `un_comtrade.logging` — logging seam.
- `un_comtrade.retry` — retry and backoff.
- `un_comtrade.pagination` — pagination helpers.
- `un_comtrade.cache` — cache key construction.
- `un_comtrade.errors` — exception hierarchy.
- `un_comtrade.utils` — cross-cutting utilities.

## 1.4 Relationship to all other layers

The infrastructure layer is the lowest layer of the
SDK with respect to the domain layers. Every domain
layer MAY invoke the infrastructure layer; the
infrastructure layer SHALL NOT invoke any domain
layer.

The relationship is documented in detail in section
12 of this document.

---

# 2. Infrastructure Components

The infrastructure layer is composed of the
components below. Each component is documented with
its purpose and its scope.

## 2.1 Component I01 — Configuration

- **Purpose.** Manage the configuration of the SDK.
- **Scope.** Configuration object, configuration
  sources, configuration validation, configuration
  lifecycle.
- **Owned by.** `un_comtrade.config`.

## 2.2 Component I02 — Retry

- **Purpose.** Retry transient failures with
  exponential backoff.
- **Scope.** Retryable failure detection, backoff
  scheduling, retry budget.
- **Owned by.** `un_comtrade.retry`.

## 2.3 Component I03 — Timeout

- **Purpose.** Enforce timeouts on every call.
- **Scope.** Connection timeout, read timeout,
  download timeout, long-running operation timeout.
- **Owned by.** `un_comtrade.utils` (timeout helpers).

## 2.4 Component I04 — Logging

- **Purpose.** Emit structured log records at the
  documented levels.
- **Scope.** Log levels, log categories, log format,
  log destination, sensitive information handling.
- **Owned by.** `un_comtrade.logging`.

## 2.5 Component I05 — Cache

- **Purpose.** Cache metadata. The SDK does NOT cache
  trade responses (per Architecture Freeze Question Q22).
- **Scope.** Cache key construction, cache scope,
  cache lifetime, cache invalidation, cache refresh.
- **Owned by.** `un_comtrade.cache`.

## 2.6 Component I06 — Progress Reporting

- **Purpose.** Report progress to the consumer
  through a documented callback.
- **Scope.** Per-page callback, per-combination
  callback, cancellation, expected information.
- **Owned by.** `un_comtrade.utils` (callback
  helpers).

## 2.7 Component I07 — Resume Support

- **Purpose.** Support the resume of an interrupted
  download.
- **Scope.** Resume checkpoint, validation after
  resume, limitations.
- **Owned by.** `un_comtrade.utils` (resume helpers).

## 2.8 Component I08 — Error Handling

- **Purpose.** Translate low-level errors into the
  documented exception hierarchy.
- **Scope.** Error origin, error translation, error
  propagation, error termination, exception
  ownership.
- **Owned by.** `un_comtrade.errors`.

## 2.9 Component I09 — Request Tracking

- **Purpose.** Assign a unique identifier to every
  request.
- **Scope.** Request identifier generation, request
  identifier propagation, request identifier
  logging.
- **Owned by.** `un_comtrade.utils` (request tracking
  helpers).

## 2.10 Component I10 — Diagnostics

- **Purpose.** Provide diagnostic information about
  the SDK state.
- **Scope.** Health reporting, configuration
  reporting, cache reporting, retry reporting.
- **Owned by.** `un_comtrade.utils` (diagnostic
  helpers).

## 2.11 Component I11 — Security

- **Purpose.** Protect authentication material and
  sensitive configuration.
- **Scope.** API key handling, sensitive
  configuration, logging restrictions, configuration
  isolation.
- **Owned by.** `un_comtrade.config` (security
  policies).

## 2.12 Summary

| ID    | Component             | Module                        |
| ----- | --------------------- | ----------------------------- |
| I01   | Configuration         | `un_comtrade.config`          |
| I02   | Retry                 | `un_comtrade.retry`           |
| I03   | Timeout               | `un_comtrade.utils`           |
| I04   | Logging               | `un_comtrade.logging`         |
| I05   | Cache                 | `un_comtrade.cache`           |
| I06   | Progress Reporting    | `un_comtrade.utils`           |
| I07   | Resume Support        | `un_comtrade.utils`           |
| I08   | Error Handling        | `un_comtrade.errors`          |
| I09   | Request Tracking      | `un_comtrade.utils`           |
| I10   | Diagnostics           | `un_comtrade.utils`           |
| I11   | Security              | `un_comtrade.config`          |

---

# 3. Configuration Strategy

The configuration strategy declares how the SDK is
configured, how the configuration is loaded, and how
the configuration is validated.

## 3.1 Configuration ownership

The configuration is owned by the `un_comtrade.config`
module. The configuration object is created by the
SDK client constructor and is bound to the SDK
client. The configuration is immutable after
construction except through documented mutator
methods.

## 3.2 Configuration hierarchy

The configuration is loaded from the following
sources, in the order of precedence. The first source
that supplies a value wins.

- Explicit construction argument.
- Configuration object passed at construction.
- Environment variable.
- Configuration file.
- Default configuration.

The environment variables are:

- `UN_COMTRADE_KEY` — the subscription key.
- `UN_COMTRADE_TIMEOUT` — the request timeout.
- `UN_COMTRADE_CACHE_DIR` — the cache directory.
- `UN_COMTRADE_LOG_LEVEL` — the log level.
- `UN_COMTRADE_PROXY` — the proxy URL.

## 3.3 Default configuration

The default configuration is the configuration that
the SDK uses when no other source supplies a value.
The default values are declared in
`007_SDK_SPECIFICATION.md` §8. The default values
are also documented in the configuration object.

## 3.4 Override behaviour

A configuration value can be overridden at construction
through an explicit argument. The override is
recorded in the changelog when the override changes
the documented default.

## 3.5 Validation expectations

The configuration is validated at construction. An
invalid configuration raises a `ConfigurationError`
before the first call is issued. The validation
rules are declared in the configuration object.

## 3.6 Configuration lifecycle

The configuration lifecycle is:

- **Load.** The configuration is loaded from the
  documented sources.
- **Validate.** The configuration is validated
  against the documented rules.
- **Bind.** The configuration is bound to the SDK
  client.
- **Use.** The configuration is read by every call.
- **Mutate.** The configuration is mutated through
  documented mutator methods.
- **Dispose.** The configuration is disposed when
  the SDK client is closed.

The configuration is not disposed implicitly; the
consumer is responsible for closing the SDK
client.

## 3.7 Configuration immutability

A configuration value is not mutated after
construction except through documented mutator
methods. A mutation that violates the immutability
rule raises a `ConfigurationError`.

---

# 4. Retry Strategy

The retry strategy declares how the SDK retries on
transient failure. The strategy is shared across the
metadata layer, the trade layer, and the transport
layer.

## 4.1 Purpose

The purpose of the retry strategy is to recover from
transient upstream failures without the consumer
having to handle every retry.

## 4.2 Retryable failures

The retry strategy retries on the following
failures:

- HTTP 429 (rate limit).
- HTTP 500, 502, 503, 504 (server errors).
- Network failure (DNS, TLS, connection reset,
  connection refused).
- Request timeout.
- Connection timeout.

## 4.3 Non-retryable failures

The retry strategy does not retry on the following
failures:

- HTTP 400 (bad request).
- HTTP 401 (unauthenticated).
- HTTP 403 (forbidden).
- HTTP 404 (not found).
- HTTP 422 (unprocessable entity).
- Validation error.
- Configuration error.
- Programming error (an error in the consumer's
  code).

## 4.4 Retry ownership

The retry strategy is owned by the
`un_comtrade.retry` module. Every layer that issues
a call to the upstream invokes the retry strategy
through the documented interface.

## 4.5 Retry lifecycle

The retry lifecycle is:

- **Attempt.** The first attempt is the original
  call.
- **Detect.** The retry strategy detects that the
  failure is retryable.
- **Wait.** The retry strategy waits for the backoff
  duration.
- **Retry.** The retry strategy issues the call
  again.
- **Repeat.** The retry strategy repeats until the
  retry budget is exhausted or the call succeeds.
- **Exhaust.** When the retry budget is exhausted,
  the retry strategy raises the documented exception.

## 4.6 Backoff expectations

The backoff schedule is:

- Initial backoff: 1 second.
- Multiplier: 2.
- Cap: 60 seconds.
- Maximum attempts: 3 (configurable).

The backoff is applied to every retry. The first
retry is after 1 second, the second after 2 seconds,
and the third after 4 seconds.

The total maximum wait time across 3 retries is
approximately 7 seconds.

## 4.7 Maximum retry concepts

The maximum number of retries is configurable. The
default is 3. A retry budget of 0 disables retries.

## 4.8 Interaction with rate limits

When the upstream returns a `Retry-After` header, the
retry strategy honours the header. When the header
is absent, the retry strategy uses the documented
backoff schedule.

The retry strategy SHALL NOT retry more often than
the upstream's rate limit permits. The retry
strategy is rate-limited per the upstream policy.

## 4.9 Retry state

The retry state is recorded in the `Response`
envelope. The `Response` carries the number of
attempts, the elapsed time of each attempt, and the
final outcome.

## 4.10 Idempotency of retries

A retry is safe when the upstream call is idempotent.
The retry strategy assumes that the upstream is
idempotent for the documented GET endpoints. A
retry of a non-idempotent call is the consumer's
responsibility.

---

# 5. Timeout Strategy

The timeout strategy declares how the SDK enforces
timeouts on every call.

## 5.1 Connection timeout

The connection timeout is the maximum time the
transport layer waits for a connection to the
upstream. The default is 10 seconds. The connection
timeout is configurable.

## 5.2 Read timeout (default request timeout)

The read timeout is the maximum time the transport
layer waits for a response from the upstream. The
default is **30 seconds** for standard requests
(per Architecture Freeze Question Q16). The read
timeout is configurable.

## 5.3 Download timeout (large download timeout)

The download timeout is the maximum time the
transport layer waits for a bulk file download to
complete. The default is **300 seconds (5
minutes)** for large downloads (per Architecture
Freeze Question Q17). The download timeout is
configurable.

## 5.3a Metadata timeout

The metadata timeout is the maximum time the
transport layer waits for a metadata catalogue
fetch. The default is **15 seconds** (per
Architecture Freeze Question Q18). The metadata
timeout is configurable.

## 5.4 Long-running operations

A long-running operation is an async submit, an
async poll, or a bulk download. The timeout for a
long-running operation is the operation-specific
timeout. The default is the documented default for
the operation.

## 5.5 Cancellation expectations

A timeout is implemented as a cancellation. The
transport layer cancels the call when the timeout
is reached. The cancellation raises a custom
**`un_comtrade.TimeoutError`** SDK exception
(per Architecture Freeze Question Q20). The
underlying context (such as the wrapped
`httpx.TimeoutException`) is preserved for
diagnostics.

## 5.6 Timeout ownership

The timeout is enforced by the transport layer. The
transport layer reads the timeout from the
configuration.

## 5.7 Timeout configuration

The timeout is configurable through the
configuration object (per Architecture Freeze
Question Q19). The configuration exposes:

- `connection_timeout_seconds` (default 10).
- `read_timeout_seconds` (default 30; per Q16).
- `download_timeout_seconds` (default 300; per Q17).
- `metadata_timeout_seconds` (default 15; per Q18).
- `long_running_timeout_seconds` (default 600).

---

# 6. Logging Strategy

The logging strategy declares how the SDK emits log
records.

## 6.1 Logging objectives

The logging strategy aims to:

- Provide diagnostic information to the consumer.
- Provide operational information to the maintainer.
- Support troubleshooting without exposing sensitive
  information.
- Support change-data-capture workflows through the
  request identifier.

## 6.2 Log categories

The SDK emits log records in the following
categories:

- **Lifecycle.** A log record emitted at the start
  and at the end of a call.
- **Retry.** A log record emitted on every retry.
- **Cache.** A log record emitted on every cache hit
  and on every cache miss.
- **Validation.** A log record emitted on every
  validation failure.
- **Network.** A log record emitted on every network
  error.
- **Upstream.** A log record emitted on every
  upstream error.
- **Security.** A log record emitted on every
  authentication event.

## 6.3 Log levels

The SDK emits log records at the following levels:

- **DEBUG.** Cache hits, validation details, internal
  state transitions.
- **INFO.** Lifecycle events, refresh events.
- **WARNING.** Recoverable errors (retries, cache
  misses, validation failures).
- **ERROR.** Non-recoverable errors (upstream errors,
  authentication errors).
- **CRITICAL.** SDK integrity errors (corrupt cache,
  corrupt configuration).

## 6.4 Structured logging expectations

The SDK emits log records as structured records. A
log record contains:

- `timestamp` (ISO-8601 string).
- `level` (string).
- `category` (string).
- `request_id` (string).
- `message` (string).
- `context` (object).

The `context` object contains the operation-specific
fields. The `context` object SHALL NOT contain the
subscription key, the full URL, or any other
sensitive information.

## 6.5 Sensitive information handling

The SDK SHALL NOT log:

- The subscription key.
- The full URL (which contains the subscription key
  as a query parameter).
- The consumer's environment variables.
- The consumer's filesystem paths.
- The consumer's process arguments.

## 6.6 Correlation between operations

The request identifier correlates every log record
emitted during a single call. The consumer can use
the request identifier to correlate the log records
with the `Response` envelope.

## 6.7 Log destination

The log destination is the standard library's
default handler by default. The destination is
configurable through the configuration object.

---

# 7. Caching Strategy

The caching strategy declares how the SDK caches
metadata. **The SDK does NOT cache trade responses**
(per Architecture Freeze Question Q22). The
strategy is shared with the metadata layer only.
The trade layer queries the upstream directly on
every call.

## 7.1 Purpose

The purpose of the cache is to reduce the number of
upstream calls, to reduce the latency of metadata
resolution and trade retrieval, and to enable the
SDK to function when the upstream is temporarily
unavailable.

## 7.2 Cache ownership

The cache is owned by the metadata layer for
metadata entries. The trade layer does not cache
trade responses. The infrastructure layer provides
the cache key construction and the cache helpers.

## 7.3 Cache scope

The cache scope is per-process. Each `ComtradeClient`
instance has its own in-memory cache. The persisted
cache is shared across processes and is stored in
the **user cache directory**, never in the project
repository (per Architecture Freeze Question Q24).
The default location follows the platform
convention:

- Linux: `$XDG_CACHE_HOME/un_comtrade` or
  `~/.cache/un_comtrade`
- macOS: `~/Library/Caches/un_comtrade`
- Windows: `%LOCALAPPDATA%\un_comtrade\Cache`

The location is overridable through the
`UN_COMTRADE_CACHE_DIR` environment variable or
the `cache_dir` configuration option. The cache
survives process restarts (per Architecture
Freeze Question Q25).

## 7.4 Cache lifecycle

The cache lifecycle is:

- **Load.** The cache is loaded from the persisted
  files on startup.
- **Read.** The cache is read on every call.
- **Write.** The cache is written on every cache
  miss.
- **Invalidate.** The cache is invalidated on
  explicit request or on cache lifetime expiry.
- **Refresh.** The cache is refreshed by the
  metadata or trade layer.
- **Dispose.** The cache is disposed when the SDK
  client is closed.

## 7.5 Cache key construction

The cache key is constructed by the infrastructure
layer. The cache key is a deterministic hash of the
request descriptor and the endpoint family. The
hash function is documented in the cache module.

The cache key for a metadata entry is the resource
identifier. **Trade responses are NOT cached** (per
Architecture Freeze Question Q22), so no trade-response
cache key is defined.

## 7.6 Cache lifetime

The cache lifetime is resource-specific:

- Metadata static resources: 30 days.
- Metadata slow-changing resources: 7 days.
- Metadata versioned resources: 1-30 days.
- Trade responses: 7 days (configurable).
- Bulk files: until manually deleted.

The cache lifetime is configurable per resource
family.

## 7.7 Cache invalidation

The cache is invalidated on:

- Explicit consumer request.
- Cache lifetime expiry.
- Version mismatch.
- Corrupt cache file.

## 7.8 Refresh triggers

The cache is refreshed on:

- Cache miss.
- Explicit consumer request.
- Scheduled policy.

## 7.9 Offline behaviour

When the upstream is unavailable, the cache continues
to serve the consumer. The infrastructure layer does
not raise an error when the cache is fresh and the
upstream is unavailable. The infrastructure layer
raises a `ReferenceError` or a `TradeError` only when
the cache is empty or expired and the upstream is
unavailable.

## 7.10 Consistency expectations

A cached `Response` SHALL be invalidated when the
configuration declares that the cache lifetime has
expired. A cached `Response` SHALL NOT be returned
when the cache is invalid.

The infrastructure layer SHALL NOT mix records
from different upstream responses in a single
`Response`.

---

# 8. Progress Reporting

The progress reporting strategy declares how the
SDK reports progress to the consumer.

## 8.1 Single request

A single request is a single call. Progress is
reported as 0% before the call, 50% during the call,
and 100% after the call. The progress is reported
through the documented callback.

## 8.2 Batch request

A batch request reports progress after each page.
The progress is the ratio of pages processed to
pages in the batch. The progress is reported
through the documented callback.

## 8.3 Large download

A large download reports progress after each
combination of dimensions. The progress is the
ratio of combinations processed to combinations in
the download.

## 8.4 Metadata refresh

A metadata refresh reports progress after each
resource is loaded. The progress is the ratio of
resources loaded to resources in the catalogue.

## 8.5 Bulk operation

A bulk operation reports progress after each file
is downloaded. The progress is the ratio of files
downloaded to files in the bulk request.

## 8.6 Cancellation

A consumer can cancel a download through the
documented callback. The infrastructure layer
cancels the download at the next page boundary.

## 8.7 Expected information

The progress callback receives:

- `operation` (string). The type of operation.
- `current` (integer). The number of units processed.
- `total` (integer). The total number of units in
  the operation.
- `elapsed_seconds` (number). The elapsed time of
  the operation.
- `estimated_remaining_seconds` (number, nullable).
  The estimated remaining time.
- `request_id` (string). The request identifier.

The progress callback SHALL NOT block the operation.

---

# 9. Resume Support

The resume support strategy declares how the SDK
supports the resume of an interrupted download.

## 9.1 Interrupted downloads

A download is interrupted by a network failure, a
process crash, or a consumer cancellation. The
infrastructure layer records the state of the
download at the time of the interruption.

## 9.2 Partial completion

A partial completion is a download that has
processed some combinations and not others. The
infrastructure layer records the last successful
combination in the resume checkpoint.

## 9.3 Resume checkpoints

A resume checkpoint is recorded after each
successful combination. The checkpoint contains:

- The download identifier.
- The last successful combination.
- The total combinations.
- The timestamp of the last successful combination.

The checkpoint is recorded in the cache directory.

## 9.4 Validation after resume

A resumed download validates the checkpoint before
issuing the first new call. The validation verifies
that the checkpoint is consistent with the current
request.

A failed validation raises a `TradeError`. The
consumer SHALL start the download from the
beginning.

## 9.5 Resume limitations

A resume is supported for combination-based
downloads. A resume is not supported for a single
call, a batch request, or a bulk operation that has
not yet started.

A resume is not supported across SDK client
instances. A resume is supported only within the
same SDK client instance.

A resume is not supported across schema revisions.
A schema revision invalidates all in-flight
downloads.

## 9.6 Recovery expectations

The infrastructure layer does not guarantee that a
download can always be resumed. The consumer SHALL
treat a download interruption as a possible
recovery point, not as a guarantee.

---

# 10. Error Propagation

The error propagation strategy declares how errors
flow through the layers of the SDK.

## 10.1 Infrastructure errors

An infrastructure error is an error that originates
in the infrastructure layer. The infrastructure
errors are:

- `ConfigurationError` — an invalid configuration.
- `TimeoutError` — a timeout.
- `NetworkError` — a network failure.
- `RateLimitError` — a rate-limit response that
  exhausts the retry budget.
- `UpstreamError` — an upstream error that exhausts
  the retry budget.

## 10.2 Layer ownership

The exception hierarchy is owned by the
`un_comtrade.errors` module. Every layer raises the
documented exception type for the documented
condition. No layer invents a new exception type
without a recorded decision.

## 10.3 Propagation rules

Errors propagate upward through the layer chain. A
layer SHALL NOT swallow an error. A layer SHALL NOT
catch a documented exception and re-raise a less
informative exception unless the documentation
explicitly allows the re-mapping.

A layer that receives an error from a lower layer
SHALL translate the error into the documented
exception type of the receiving layer. The
translation records the originating error in a
documented `__cause__` or equivalent attribute, so
that the originating condition remains accessible
to the consumer.

## 10.4 Wrapping behaviour

When a lower-layer error is wrapped, the wrapping
exception records:

- The lower-layer exception.
- The lower-layer exception's message.
- The lower-layer exception's category.
- The context in which the lower-layer exception
  occurred.

The wrapping exception is an instance of a
documented exception type.

## 10.5 Termination behaviour

Errors terminate at the SDK client layer. The SDK
client layer raises the documented exception type
to the consumer. The consumer is responsible for
catching the exception and acting on it.

## 10.6 Relationship to SDK exceptions

The infrastructure errors map to the SDK exceptions
declared in `007_SDK_SPECIFICATION.md` §7. The
mapping is:

- `ConfigurationError` → `ConfigurationError`.
- `TimeoutError` → `TimeoutError`.
- `NetworkError` → `NetworkError`.
- `RateLimitError` → `RateLimitError`.
- `UpstreamError` → `UpstreamError`.

---

# 11. Observability

The observability strategy declares how the SDK
exposes operational and diagnostic information.

## 11.1 Operational visibility

The SDK exposes operational information through:

- The `Response` envelope, which carries the elapsed
  time, the count, and the error message.
- The configuration object, which carries the
  current configuration.
- The progress callback, which carries the per-step
  progress.
- The diagnostic helpers, which carry the SDK
  state.

## 11.2 Diagnostic information

The SDK exposes diagnostic information through:

- The `version` constant, which carries the SDK
  version.
- The `version` constant of the data model, which
  carries the data model version.
- The `version` constant of the metadata catalogue,
  which carries the catalogue version.
- The diagnostic helpers, which report the cache
  state, the configuration, and the recent log
  records.

## 11.3 Health reporting

The SDK exposes a health check through a documented
method. The health check reports:

- Whether the upstream is reachable.
- Whether the cache is fresh.
- Whether the configuration is valid.
- Whether the SDK is ready to serve requests.

## 11.4 Request tracing

The SDK assigns a unique request identifier to every
call. The request identifier is propagated through
every layer and is recorded in every log record. The
request identifier is also returned in the
`Response` envelope for traceability.

## 11.5 Execution context

The SDK exposes the execution context through a
documented object. The execution context contains:

- The request identifier.
- The endpoint family.
- The retry attempts.
- The elapsed time.
- The cache state.

The execution context is logged at the DEBUG level
on every call.

## 11.6 Debug support

The SDK exposes a debug mode through a documented
configuration parameter. When debug mode is enabled,
the SDK emits log records at the DEBUG level. The
default is `False`.

---

# 12. Dependency Rules

The dependency rules declare which layers may use
which infrastructure services.

## 12.1 Allowed dependencies

- The transport layer MAY use the retry, timeout,
  logging, error handling, request tracking, and
  diagnostics services.
- The validation layer MAY use the configuration,
  error handling, and logging services.
- The metadata layer MAY use the configuration,
  caching, error handling, logging, and request
  tracking services.
- The trade layer MAY use the configuration,
  caching, retry, timeout, logging, error handling,
  progress reporting, resume support, and request
  tracking services.
- The export layer MAY use the error handling and
  logging services.
- The storage layer MAY use the configuration,
  caching, error handling, and logging services.
- The analytics layer is out of scope of the SDK.

## 12.2 Forbidden dependencies

- The infrastructure layer SHALL NOT depend on any
  domain layer. The infrastructure layer is the
  lowest layer of the SDK.
- The application layer is out of scope of the SDK;
  the SDK SHALL NOT depend on the application layer.

## 12.3 Dependency direction

The dependency direction is strictly downward:
from the domain layers to the infrastructure layer.
The infrastructure layer depends only on the
Python standard library and on the documented
runtime dependencies.

## 12.4 No circular dependencies

A cycle in the dependency graph is a defect. The
infrastructure layer SHALL NOT introduce a cycle.
The verification of the cycle rule is the
responsibility of the testing standard
(`012_TESTING_STANDARD.md`).

## 12.5 No layer skipping

A domain layer that needs a capability that is
provided by the infrastructure layer SHALL invoke
the infrastructure layer directly. A domain layer
SHALL NOT reach across the infrastructure layer to
invoke a function of another domain layer.

---

# 13. Runtime Lifecycle

The runtime lifecycle describes the path that a
runtime operation follows from configuration to
cleanup.

```
Configuration
    |
    v
Request Created
    |
    v
Infrastructure Services Applied
    |
    v
Execution
    |
    v
Logging
    |
    v
Retry (if required)
    |
    v
Completion
    |
    v
Cleanup
```

## 13.1 Configuration

The configuration is loaded from the documented
sources and validated. The configuration is bound
to the SDK client.

## 13.2 Request Created

A request is created by the SDK client layer. The
request carries the consumer's parameters and the
configuration.

## 13.3 Infrastructure Services Applied

The infrastructure services are applied to the
request. The request identifier is generated. The
timeout is set. The retry policy is set. The
logging context is created.

## 13.4 Execution

The request is executed by the domain layer. The
domain layer invokes the transport layer to issue
the HTTP call. The transport layer applies the
retry policy and the timeout.

## 13.5 Logging

The logging service emits log records at the
documented levels. The log records carry the
request identifier and the documented context.

## 13.6 Retry (if required)

When a retry is required, the retry service
schedules the retry with the documented backoff.
The retry service logs the retry at the WARNING
level.

## 13.7 Completion

The completion is the end of the execution. The
domain layer returns a `Response` to the SDK
client layer. The SDK client layer returns the
`Response` to the consumer.

## 13.8 Cleanup

The cleanup is the disposal of the request
context. The cleanup releases the logging context,
the retry context, and the timeout context. The
cleanup is performed by the infrastructure layer
when the request is complete.

---

# 14. Failure Recovery

The failure recovery section declares the expected
behaviour of the infrastructure layer when a failure
occurs.

## 14.1 Network failures

A network failure is handled by the retry policy.
The infrastructure layer retries with the documented
backoff. When the retry budget is exhausted, the
infrastructure layer raises a `NetworkError`.

## 14.2 API failures

An API failure is handled by the layer that
encountered the failure. The infrastructure layer
retries on the documented retryable failures. The
infrastructure layer does not retry on the
documented non-retryable failures.

## 14.3 Timeouts

A timeout is handled by the retry policy. The
infrastructure layer retries with the documented
backoff. When the retry budget is exhausted, the
infrastructure layer raises a `TimeoutError`.

## 14.4 Interrupted downloads

An interrupted download is handled by the resume
support service. The infrastructure layer records
the last successful combination. The consumer can
resume the download from the last successful
combination.

## 14.5 Cache corruption

A cache corruption is handled by the cache
invalidation service. The infrastructure layer
deletes the corrupt file and treats the cache as
empty. The infrastructure layer re-downloads the
resource on the next call.

## 14.6 Configuration errors

A configuration error is handled by the configuration
validation service. The infrastructure layer raises
a `ConfigurationError` at construction. The
infrastructure layer does not perform network I/O
when the configuration is invalid.

## 14.7 Logging failures

A logging failure is handled by the logging
service. The infrastructure layer falls back to a
no-op logger when the logging service fails. The
infrastructure layer does not raise an error on a
logging failure.

## 14.8 Partial completion

A partial completion is handled by the resume
support service. The infrastructure layer records
the last successful combination. The consumer can
resume the download from the last successful
combination.

## 14.9 Recovery expectations

The infrastructure layer recovers from transient
failures through the retry policy. The
infrastructure layer recovers from configuration
errors only by re-construction of the SDK. The
infrastructure layer recovers from cache
corruption by cache invalidation. The
infrastructure layer recovers from logging
failures by falling back to a no-op logger.

---

# 15. Performance Considerations

The performance considerations section declares the
expected performance characteristics of the
infrastructure layer.

## 15.1 Resource utilization

The infrastructure layer is bounded by the per-call
cap. The infrastructure layer does not load the
entire result into memory before returning; the
infrastructure layer returns the result as the
pages are processed.

## 15.2 Memory considerations

The memory consumption of the infrastructure layer
is bounded by the configuration. The default
configuration bounds the cache to a few hundred
megabytes for the metadata catalogue and the
largest trade response.

## 15.3 Long-running operations

A long-running operation is an async submit, an
async poll, or a bulk download. The infrastructure
layer does not impose a maximum duration on a
long-running operation; the consumer is responsible
for cancelling the operation if needed.

## 15.4 Large datasets

A large dataset is a dataset that exceeds 250,000
records. The infrastructure layer processes a
large dataset through the batch processing strategy.
The total latency is the sum of the per-page
latencies plus the backoff time.

## 15.5 Scalability expectations

The infrastructure layer scales linearly with the
number of SDK client instances. The infrastructure
layer does not impose a process-level limit.

---

# 16. Security Considerations

The security considerations section declares the
expected security behaviour of the infrastructure
layer.

## 16.1 API key handling

The API key is held in memory only. The API key is
not written to disk except through the configuration
file, when the consumer explicitly configures a
configuration file.

The API key is redacted from every log record. The
API key is redacted from the `Response` envelope
when the envelope is logged.

## 16.2 Sensitive configuration

The sensitive configuration values are:

- The subscription key.
- The proxy credentials (if any).

The sensitive configuration values are redacted
from every log record and from the `Response`
envelope when the envelope is logged.

## 16.3 Credential exposure

The API key is never exposed to the consumer as a
return value. The API key is never included in an
error message. The API key is never included in a
diagnostic report.

## 16.4 Logging restrictions

The infrastructure layer SHALL NOT log:

- The API key.
- The full URL (which contains the API key as a
  query parameter).
- The consumer's environment variables.
- The consumer's filesystem paths.
- The consumer's process arguments.

## 16.5 Configuration isolation

The configuration is isolated to the SDK client
instance. The configuration is not shared across
SDK client instances. A consumer who wants to
share a configuration across instances SHALL
construct each instance with the same
configuration.

## 16.6 Transport security

The infrastructure layer uses TLS for every call to
the upstream. The infrastructure layer does not
support plain HTTP.

---

# 17. Future Extensibility

The future extensibility section declares how new
infrastructure services can be introduced without
affecting existing layers.

## 17.1 New infrastructure services

A new infrastructure service is added in a minor
version. The new service SHALL be documented in
section 2 of this document. The new service SHALL
NOT change the behaviour of an existing service.

## 17.2 New configuration parameters

A new configuration parameter is added in a minor
version. The new parameter SHALL be documented in
section 3 of this document. The new parameter
SHALL have a default value.

## 17.3 New retry policies

A new retry policy is added in a minor version. The
new policy SHALL be documented in section 4 of this
document. The new policy SHALL be a strict
superset of the existing policy.

## 17.4 New log categories

A new log category is added in a minor version. The
new category SHALL be documented in section 6 of
this document. The new category SHALL NOT change
the behaviour of an existing category.

## 17.5 Deprecation

A deprecated infrastructure service, parameter,
policy, or category is preserved in the SDK until
the deprecation period expires. The deprecation is
recorded in the changelog and the decisions log.

---

# 18. Assumptions

The assumptions below are recorded for
traceability. An assumption that turns out to be
false is recorded in `DECISIONS.md` as a
correction and is propagated to the relevant
specification documents.

## 18.1 Verified assumptions

- The upstream is reachable from the public
  internet. Verified by live request.
- The subscription key is a long opaque string.
  Verified.
- The preview endpoint is capped at 500 records.
  Verified.
- The authenticated endpoint is capped at 250,000
  records. Verified.
- The 401 response body is structured. Verified.
- The CORS headers are not set. Verified.
- The CORS limitation does not affect server-side
  use. Verified.

## 18.2 Inferred assumptions

- The per-minute request cap on the public preview
  surface is unverified. The default retry budget
  is configured to be conservative.
- The per-key daily record cap is unverified. The
  default cache lifetime is configured to be
  conservative.
- The `Retry-After` header is honoured when present.
  This is a documented upstream behaviour but is
  not verified by the research.

## 18.3 Local design decisions

- The infrastructure layer is composed of 11
  components. The components are organised by
  concern; the organisation is a local design
  decision.
- The default retry budget is 3 attempts. The
  default backoff is 1 second with a multiplier of
  2 and a cap of 60 seconds. The defaults are local
  design decisions that may be tuned.
- The default timeout is 30 seconds for standard
  requests, 300 seconds (5 minutes) for large
  downloads, and 15 seconds for metadata fetches.
  The defaults are local design decisions that may
  be tuned.
- The default log level is `WARNING`. The default
  log destination is the standard library's default
  handler. The defaults are local design decisions.
- The default cache lifetime is 30 days for static
  metadata. The trade layer does not maintain a
  cache by default. The defaults are local design
  decisions.
- The default progress callback is a no-op. The
  consumer is expected to override the default.
- The default configuration source is the explicit
  construction argument. The consumer is expected to
  override the default through the configuration
  object.
- The default request identifier is a UUID. The
  consumer is expected to override the default if
  the consumer has a higher-level correlation
  identifier.

---

# 19. Open Questions

The questions below are recorded for future
resolution. Each question is described with the
impact and the suggested verification.

- **OQ-IS-001 (High).** What is the exact per-
  minute request cap on the public preview surface?
  **Impact.** The default retry budget depends on
  the cap. **Suggested verification.** Run a
  monitoring experiment and observe the upstream
  cap.

- **OQ-IS-002 (High).** What is the exact per-key
  daily record cap? **Impact.** The default cache
  lifetime depends on the cap. **Suggested
  verification.** Read the developer portal
  subscription page.

- **OQ-IS-003 (Medium).** Should the SDK support a
  distributed cache backend (Redis, Memcached) for
  cross-process caching? **Impact.** A distributed
  cache backend would enable shared caching across
  processes. **Suggested verification.** Confirm
  with the consumer requirements.

- **OQ-IS-004 (Medium).** Should the SDK support a
  custom logger (e.g. structlog, loguru) through a
  documented extension point? **Impact.** A custom
  logger would enable richer log records.
  **Suggested verification.** Confirm with the
  consumer requirements.

- **OQ-IS-005 (Medium).** Should the SDK support
  OpenTelemetry tracing through a documented
  extension point? **Impact.** OpenTelemetry tracing
  would enable distributed tracing. **Suggested
  verification.** Confirm with the consumer
  requirements.

- **OQ-IS-006 (Medium).** Should the SDK support a
  custom retry policy through a documented
  extension point? **Impact.** A custom retry
  policy would enable consumer-specific retry
  strategies. **Suggested verification.** Confirm
  with the consumer requirements.

- **OQ-IS-007 (Medium).** Should the SDK expose
  the request identifier as a consumer-supplied
  header, so that the consumer can correlate the
  SDK calls with the consumer's own tracing?
  **Impact.** A consumer-supplied request
  identifier would enable end-to-end tracing.
  **Suggested verification.** Confirm with the
  consumer requirements.

- **OQ-IS-008 (Low).** Should the SDK support a
  custom cache key function through a documented
  extension point? **Impact.** A custom cache key
  function would enable consumer-specific cache
  strategies. **Suggested verification.** Confirm
  with the consumer requirements.

- **OQ-IS-009 (Low).** Should the SDK support a
  custom progress callback type? **Impact.** A
  custom progress callback type would enable
  richer progress reporting. **Suggested
  verification.** Confirm with the consumer
  requirements.

- **OQ-IS-010 (Low).** Should the SDK expose a
  `__version__` constant? **Impact.** A version
  constant would support runtime version checks.
  **Suggested verification.** Confirm with the
  packaging specification.

---

# End of document
