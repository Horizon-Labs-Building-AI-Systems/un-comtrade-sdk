```
Document ID
000

Title
Project Charter

Version
0.1.0

Status
DRAFT

Created
2026-06-26T19:35:23Z

Last Updated
2026-06-26T19:35:23Z

Author
Codex

Project
UN Comtrade Python SDK

Dependencies
None

Supersedes
None
```

---

# 1. Purpose

## 1.1 Why this project exists

The United Nations Comtrade Database publishes the official
international merchandise trade statistics of more than two hundred
reporting economies. The dataset is exposed through an HTTP API
managed by the United Nations Statistics Division and operated on
top of an Azure API Management gateway. Accessing the data
programmatically requires a working knowledge of the API
endpoints, query parameters, reference catalogues, record caps,
authentication model, and classification nomenclature that the
service uses.

At present, consumers of the data who wish to use Python must
either hand-roll HTTP requests or depend on a community-maintained
package whose interface and stability characteristics are not
guaranteed. The result is a recurring cost paid by every analyst,
data engineer, and application developer who needs to integrate
the dataset into a reproducible workflow.

This project exists to remove that recurring cost by providing a
production-quality Python SDK that exposes the API through a
stable, type-hinted, well-documented, and testable interface.

## 1.2 What problem it solves

The SDK reduces the work required to obtain, normalise, and persist
Comtrade data to a small number of well-named Python calls. It
encapsulates:

- knowledge of the public preview endpoints and the
  subscription-backed data endpoints;
- the parameter validation rules of each endpoint;
- the reference catalogue structure and lookup semantics;
- retry, pagination, and rate-limit handling;
- a normalisation layer that exposes a consistent data model
  regardless of which endpoint produced the record;
- an extension surface that allows higher-level subsystems
  (ETL, storage, analytics) to consume the same primitive.

## 1.3 Intended audience

The intended audience is:

- Data engineers who need a reproducible source of Comtrade
  data inside ETL pipelines.
- Quantitative analysts and economists who work with trade
  statistics from Jupyter notebooks or batch jobs.
- Application developers who embed Comtrade data inside larger
  products.
- Researchers and academics who require stable, citable access
  to a normalised representation of the dataset.
- Internal platform teams who build ETL, data-lake, and
  warehouse solutions on top of Comtrade and need a
  maintainable, testable client layer.

The SDK is not intended for non-technical end users, for
visualisation front-ends, or for any consumer who does not need
programmatic access to the data.

## 1.4 Primary objectives

The primary objectives of the project are:

1. To expose every supported Comtrade endpoint through a
   stable, type-hinted Python interface.
2. To document every public class, function, and parameter of
   that interface.
3. To guarantee the correctness of the interface through an
   automated test suite.
4. To provide reference data, ETL, and analytics layers that
   build on top of the SDK.
5. To publish the SDK as a versioned package consumable via
   the standard Python package index.

---

# 2. Vision

The long-term vision of the project is a production-quality
Python SDK and accompanying data toolkit that becomes the
default way to access the United Nations Comtrade Database
from Python.

The SDK is intended to be:

- A production-quality software artefact suitable for
  inclusion in regulated and audited environments.
- A reusable architectural foundation that downstream
  projects can extend without forking.
- A stable public API that does not break existing consumer
  code without a major version increment.
- A foundation for ETL pipelines, lake-house architectures,
  and warehouse loads built on top of Comtrade data.
- A foundation for analytics, research, and policy-oriented
  workloads.
- A foundation for future applications, including scheduled
  extractors, change-data-capture systems, mirror-data
  reconciliation tools, and harmonisation services.

The vision is not to build a finished analytics product; it is
to build the substrate on which analytics products can be
reliably constructed.

---

# 3. Scope

The following items are explicitly included in the scope of
this project.

## 3.1 Software artefacts

- A Python package distributed as an importable library and
  installable through the standard Python package index.
- A reference implementation of the metadata layer, exposing
  reporters, partners, classifications, flows, and modes of
  transport.
- A reference implementation of the trade layer, exposing
  annual, monthly, tariffline, and trade-matrix data.
- An asynchronous interface for long-running data deliveries.

## 3.2 Functional capabilities

- Retrieval of metadata reference tables.
- Retrieval of trade data at annual and monthly frequencies.
- Retrieval of trade data at the final and tariffline
  granularity.
- Bulk data download support, where the upstream API supports
  it.
- Synchronous and asynchronous query execution.
- Pagination across the public preview and the
  subscription-backed data endpoints.
- Retry behaviour for transient errors, including
  rate-limit responses.
- Local caching of metadata and reference data.
- Optional disk-based caching of trade data, configured per
  call site.
- Type hints throughout the public interface.
- A documented exception hierarchy.

## 3.3 Non-functional capabilities

- Documentation for every public class, function, and
  parameter.
- A test suite that covers the public interface and the
  reference layer.
- Example scripts that demonstrate the supported workflows.
- A reference set of Jupyter notebooks that exercise the
  SDK against live and recorded data.

---

# 4. Non-Goals

The following items are explicitly excluded from the scope of
this project. Each is recorded here to prevent scope drift.

- A web dashboard, browser application, or graphical user
  interface of any kind.
- A built-in machine-learning or statistical model.
- A built-in data-visualisation layer or chart renderer.
- A built-in database or query engine.
- A built-in AI assistant, summariser, or natural-language
  interface.
- A built-in forecasting or nowcasting subsystem.
- A commercial analytics product, subscription service, or
  managed offering.
- A command-line interface beyond what is necessary to run
  the example scripts.
- A web service, REST gateway, or gRPC server.
- An ETL orchestrator. The SDK may be used as a library by
  orchestrators but shall not include one.
- A data-lake or warehouse reference architecture. The SDK
  may populate one but shall not include one.
- A pre-built catalogue of derived indicators, such as
  trade balance, revealed comparative advantage, or
  trade complementarity indices.
- A real-time streaming interface. The upstream API is
  request-response; the SDK shall not invent a streaming
  layer on top of it.
- Localised, translated, or region-specific forks of the
  documentation.
- Support for programming languages other than Python.
- A production deployment, hosting environment, or
  cloud-specific integration.

---

# 5. Supported APIs

This section lists every UN Comtrade API surface that the SDK
intends to support. Each entry identifies the purpose, the
intended support status, the implementation priority, and
whether the surface requires authentication. The list is
restricted to endpoints that the upstream service exposes
and that the project team has verified to be in operation
as of the date of this document.

## 5.1 Reference data endpoints

The reference data endpoints are public, do not require a
subscription key, and serve catalogue data used to interpret
trade records.

| Endpoint                                              | Purpose                                              | Status | Priority | Auth |
| ----------------------------------------------------- | ---------------------------------------------------- | ------ | -------- | ---- |
| List of reference tables                              | Enumerate the available reference tables             | Planned | High    | No   |
| Data items reference                                  | Enumerate the data item (column) catalogue           | Planned | High    | No   |
| Frequency reference                                   | Enumerate the frequency codes (annual, monthly)      | Planned | High    | No   |
| Trade flow reference                                  | Enumerate the trade flow codes                       | Planned | High    | No   |
| Customs procedure code reference                      | Enumerate the customs procedure codes                | Planned | Medium  | No   |
| Mode of transport reference                           | Enumerate the modes of transport                     | Planned | Medium  | No   |
| Mode of supply reference                              | Enumerate the modes of supply for services           | Planned | Low     | No   |
| Partner areas reference                               | Enumerate the partner country and area codes         | Planned | High    | No   |
| Reporter reference                                    | Enumerate the reporter country and area codes        | Planned | High    | No   |
| Quantity unit reference                               | Enumerate the quantity unit codes                    | Planned | Medium  | No   |
| HS combined classification                            | Enumerate the harmonised system codes                | Planned | High    | No   |
| HS 1992 through HS 2022 per-edition classifications   | Enumerate harmonised system codes by edition         | Planned | High    | No   |
| SITC Rev.1 through SITC Rev.4 classifications         | Enumerate SITC codes by revision                     | Planned | Medium  | No   |
| BEC Rev.4 and BEC Rev.5 classifications               | Enumerate broad economic category codes              | Planned | Low     | No   |
| EBOPS 2002, 2010, and combined EBOPS classifications  | Enumerate EBOPS codes for services                   | Planned | Low     | No   |

## 5.2 Trade data endpoints

The trade data endpoints are partitioned into a public preview
surface and a subscription-backed surface. The public preview
is rate-limited and capped at a small record count per call.
The subscription-backed surface is authenticated and accepts
larger queries.

| Endpoint family  | Purpose                                            | Status   | Priority | Auth |
| ---------------- | -------------------------------------------------- | -------- | -------- | ---- |
| Final data preview     | Public preview of final trade data             | Planned  | High     | No   |
| Final data full        | Authenticated final trade data                 | Planned  | High     | Yes  |
| Tariffline data preview| Public preview of tariffline trade data        | Planned  | Medium   | No   |
| Tariffline data full   | Authenticated tariffline trade data            | Planned  | Medium   | Yes  |
| Trade balance          | Exports and imports laid out side by side      | Planned  | Medium   | Yes  |
| Bilateral data         | Reported data complemented by mirror data      | Planned  | Low      | Yes  |
| Trade matrix           | Estimated world trade values                   | Planned  | Low      | Yes  |
| Standard unit values   | Reference unit value and range data            | Planned  | Low      | Yes  |
| Data availability      | Enumerate the data currently available          | Planned  | High     | Yes  |
| Bulk download          | Download large official data files             | Planned  | Medium   | Yes  |
| Async delivery         | Submit and check long-running data requests    | Planned  | Medium   | Yes  |
| Metadata               | Retrieve publication notes and metadata        | Planned  | Medium   | Yes  |

## 5.3 Excluded API surfaces

The following surfaces are not in the scope of this SDK and
shall not be implemented unless a future revision of this
charter extends the supported API list.

- Any endpoint not documented by the United Nations
  Statistics Division.
- Any endpoint whose presence on the gateway has not been
  independently verified.
- Internal Azure API Management surfaces.
- Surfaces reserved for institutional subscribers that
  require contractual access.

---

# 6. Supported Python Versions

The SDK targets the Python language as distributed by the
Python Software Foundation. The version policy is stated in
this section.

## 6.1 Minimum supported version

The minimum supported Python version is **Python
3.11 or later** (per Architecture Freeze Question
Q1). Choosing 3.11+ gives modern typing support
(`Self`, improved generics, better TypedDict),
excellent ecosystem compatibility, and a long
support lifecycle through October 2027.

## 6.2 Recommended version

The recommended Python version is the most recent
stable release at the date of the most recent SDK
release. This is the version used by the
maintainers during development and is the version
exercised by the continuous integration pipeline.

## 6.3 Maximum tested version

The maximum tested version is the highest Python
release at implementation time (currently Python
3.13, per Architecture Freeze Question Q2). The
support matrix is documented separately and
tracked in the test suite.
that the maintainers have executed the test suite against
prior to publishing a release. The value is recorded in
the release notes.

## 6.4 Reasoning

The version policy is intentionally narrow. Limiting the
support matrix reduces the combinatorial cost of testing
and dependency resolution, and it gives the maintainers a
clear contract with consumers. The narrow support matrix is
recorded in the coding standard and is enforced by the test
suite.

The SDK is implemented in pure Python; it does not require
a C extension, and therefore does not require additional
binary wheel support for each supported Python release.

The SDK depends on **`httpx`** for HTTP transport
(per Architecture Freeze Question Q3). The
`httpx` library provides both synchronous and
asynchronous APIs; the SDK uses the synchronous
API for the MVP. Async support is a Phase 2
feature (per Architecture Freeze Question Q4).
JSON serialisation uses the Python standard
library `json` module — no additional dependency
is required (per Architecture Freeze Question
Q5).

---

# 7. Design Philosophy

The SDK is governed by the following architectural principles.
Each principle is binding for any future implementation task
unless an explicit decision is recorded in
`docs/DECISIONS.md` to deviate from it.

## 7.1 Documentation first

Every implementation task shall be preceded by the relevant
specification document. No source file shall be created
without a corresponding specification entry that justifies
its existence.

## 7.2 Simplicity

The public interface shall expose the smallest possible
number of concepts required to model the underlying API.
Where the upstream API provides a parameter, the SDK shall
expose that parameter; where the upstream API does not
provide a capability, the SDK shall not invent one.

## 7.3 Reusability

Every class, function, and module shall be designed for
reuse. Internal helpers shall be defined at the lowest layer
that supports their intended use and shall be exposed to
higher layers through clear, narrow contracts.

## 7.4 Strong typing

The public interface shall be fully type-hinted. Types
shall be precise: the type signature of a function shall
convey the shape of its inputs and outputs without requiring
the consumer to read the implementation.

## 7.5 Deterministic behaviour

The SDK shall produce deterministic behaviour for any given
input. Caching, retry, and rate-limit logic shall not
introduce hidden non-determinism into consumer code.
Side-effects on the network or the local filesystem shall
be explicit and documented.

## 7.6 Layer separation

The SDK shall be partitioned into distinct layers with
well-defined responsibilities. The metadata layer shall not
contain trade-retrieval logic. The trade layer shall not
contain reference-retrieval logic. Higher layers shall not
reach across layer boundaries.

## 7.7 Low coupling

Modules shall not import across layer boundaries except
through explicitly declared interfaces. A change in one
layer shall not require a coordinated change in another
layer.

## 7.8 High cohesion

Each module shall group behaviour that changes together. A
module shall not contain functionality that evolves on
different release cadences.

## 7.9 Explicit errors

The SDK shall raise a small, documented exception hierarchy.
Implicit errors, swallowed exceptions, and silent fallbacks
are forbidden in the public interface.

## 7.10 Backward compatibility

The SDK shall preserve backward compatibility for any
public interface that is documented as stable. Breaking
changes shall require a major version increment and a
recorded decision in `docs/DECISIONS.md`.

## 7.11 Testability

Every public function shall be covered by a test. Tests
shall be deterministic, fast, and independent of the live
upstream service unless explicitly recorded as live tests.

## 7.12 Minimal dependencies

The SDK shall depend only on libraries that are required
to deliver the documented functionality. Each new runtime
dependency shall require a recorded decision.

## 7.13 Layered configuration

Configuration that affects behaviour (timeout, retry count,
proxy, cache location) shall be settable at construction
time and shall be inheritable through composition rather
than through global state.

## 7.14 No hidden I/O

The SDK shall not perform I/O at import time. All network
and filesystem operations shall occur inside explicit
methods.

---

# 8. Repository Structure

The repository is organised into the following top-level
directories. The list is normative; deviation from it
requires a recorded decision.

| Path          | Purpose                                                                                                  |
| ------------- | -------------------------------------------------------------------------------------------------------- |
| `docs/`       | Specification documents, charters, decisions, task logs, and changelog. Source of truth for design.     |
| `sdk/`        | The Python package source tree, containing the production code.                                          |
| `tests/`      | The automated test suite, including unit, integration, and live smoke tests.                            |
| `examples/`   | Reference scripts that demonstrate the supported workflows.                                             |
| `notebooks/`  | Jupyter notebooks that exercise the SDK against live and recorded data.                                  |
| `scripts/`    | Maintainer scripts for release engineering, metadata refresh, and repository maintenance.               |
| `data/`       | Recorded sample responses used for testing and for offline examples.                                     |
| `pyproject.toml` | The Python project descriptor; declares the package, dependencies, and tool configuration.            |
| `README.md`   | The top-level entry point for new consumers, pointing into the docs and the SDK.                         |
| `LICENSE`     | The license under which the project is distributed.                                                       |

Additional directories may be created later, but their
existence shall be recorded in the relevant specification
document before they appear in the repository.

---

# 9. High-Level Architecture

The system is partitioned into a chain of layers. Each
layer has a single responsibility and a single direction of
dependency.

```
UN Comtrade API
        |
        v
   +----------+
   |   SDK    |   (transport, retry, pagination, parameter validation)
   +----------+
        |
        v
   +----------------+
   | Normalisation  |   (stable data model, type coercion, schema versioning)
   +----------------+
        |
        v
   +----------+
   | Storage  |   (reference data, recorded samples, optional local cache)
   +----------+
        |
        v
   +----------+
   | Analytics|   (consumers; outside the SDK scope)
   +----------+
        |
        v
   +-----------+
   |Applications|  (consumers; outside the SDK scope)
   +-----------+
```

The responsibilities of each layer are as follows.

- The **SDK** layer owns transport, authentication, retry,
  pagination, parameter validation, and request shape
  definition.
- The **Normalisation** layer converts upstream records into
  the SDK's stable data model and applies documented
  coercion rules.
- The **Storage** layer is responsible for the persistence of
  reference data, the recording of sample data, and the
  optional caching of trade data. The storage layer does not
  perform analytics.
- The **Analytics** layer is out of scope for the SDK. The
  SDK exposes the data and the metadata; analytics
  consumers compose on top of it.
- The **Applications** layer is out of scope for the SDK.
  Applications may embed the SDK but the SDK does not embed
  any application.

The direction of dependency is strictly downward. Higher
layers may depend on lower layers; lower layers shall not
depend on higher layers.

---

# 10. Public SDK Philosophy

The public interface of the SDK is governed by the following
commitments.

## 10.1 Stable interfaces

Any class, function, or method that is documented as part
of the public interface is considered stable. Stability
means that the documented name, signature, semantic
behaviour, and exception behaviour shall not change without
a major version increment.

## 10.2 Semantic versioning

The project follows Semantic Versioning 2.0.0. The version
number encodes backward compatibility. A consumer that
pins to a major version may upgrade within that major
version without code changes for any documented public
behaviour.

## 10.3 Backward compatibility

Backward compatibility is preserved for documented
behaviour. Undocumented behaviour, internal helper
functions, and private modules may change without notice.
A consumer who relies on undocumented behaviour accepts
the risk of breakage.

## 10.4 Minimal breaking changes

Breaking changes are reserved for cases where backward
compatibility is technically impossible. Where a breaking
change is unavoidable, the change shall be announced in
`docs/CHANGELOG.md` and shall be accompanied by a migration
note that explains the consumer-side action required.

## 10.5 Deprecation policy

A documented public element may be marked deprecated by
adding a deprecation note to the documentation and a
deprecation warning to the runtime. The deprecation period
shall last at least one minor release before the element
is removed in the next major release.

## 10.6 Additive evolution

New functionality is added in additive fashion. New
optional parameters, new return values, and new public
classes are added without a major version increment. New
required parameters on a stable function are not added
without a major version increment.

---

# 11. Documentation Philosophy

Documentation is the primary artefact of the project. The
project is delivered under a documentation-first
methodology in which every implementation task is preceded
by the relevant specification document and every
architectural decision is recorded before it is implemented.

## 11.1 Precedence

For any design question, the relevant specification document
takes precedence over implementation, tests, and examples.
Where implementation, tests, or examples contradict a
specification document, the specification document is
correct and the implementation, tests, or examples are
wrong.

## 11.2 Reading order

Every future task shall begin by reading the documents in
the order they are numbered. The task implementer shall
confirm that the document is current and shall note any
discrepancy before proceeding.

## 11.3 Decision recording

Every architectural decision shall be recorded in
`docs/DECISIONS.md` with a date, a status, a context, a
decision, and the consequences of the decision. Decisions
are not deleted; they are superseded.

## 11.4 Change log

Every change to a specification document shall be recorded
in `docs/CHANGELOG.md` with the document identifier, the
version, the change, and the date.

## 11.5 Source of truth

The `docs/` tree is the source of truth for the project.
No source file may be committed that contradicts the
current revision of any document in the `docs/` tree.

---

# 12. Coding Philosophy

The coding standard for the project is recorded in
`docs/014_CODING_STANDARD.md`. The standard is summarised
here and is normative only by reference to that document.

## 12.1 Type hints

Every public function, method, and class shall declare
type hints for its parameters and return values. Type hints
are part of the documented interface; the type checker
output is part of the release artefact.

## 12.2 Docstrings

Every public function, method, and class shall carry a
docstring that describes its purpose, its parameters, its
return value, and any raised exceptions. The docstring
style is recorded in the coding standard.

## 12.3 Clean interfaces

Interfaces shall be minimal. A function shall accept the
parameters it requires and shall return the values it
produces. Optional behaviour shall be expressed through
keyword arguments and configuration objects, not through
side channels.

## 12.4 Explicit exceptions

The SDK shall not raise generic exceptions. The exception
hierarchy is documented in the SDK specification and shall
be used consistently. A consumer shall be able to catch the
documented exception types without depending on string
matching or attribute probing.

## 12.5 Readability

Source code shall be written to be read. The maintainers
optimise for the reader, not for the writer. Cleverness is
avoided in favour of clarity.

## 12.6 Minimal dependencies

The runtime dependency set is the smallest set that allows
the documented functionality. Every new runtime dependency
shall require a recorded decision and shall appear in
`pyproject.toml` with an explicit version constraint.

## 12.7 No side effects at import

The SDK shall not perform I/O, shall not mutate global
state, and shall not read configuration from the
environment at import time. All such activity is deferred
to construction time or to explicit method calls.

---

# 13. Release Strategy

The project follows a four-stage release strategy. Each
stage is described in terms of the contract with consumers
and the visibility of the release.

## 13.1 Alpha

Alpha releases are pre-feature releases. The interface is
subject to change without notice. Alpha releases are
versioned `0.y.z` where the first minor version is
odd-numbered, by convention. Alpha releases are not
published to the public package index.

## 13.2 Beta

Beta releases are feature-complete previews whose interface
is approaching stability. The interface is documented but
may still change. Beta releases are versioned `0.y.z` where
the first minor version is even-numbered, by convention.
Beta releases are not published to the public package
index unless an explicit decision records that they should
be.

## 13.3 Release candidate

A release candidate is a near-final release whose interface
is frozen. The release candidate is published to the public
package index under a release-candidate version. No further
features are accepted against a release candidate. Bug
fixes against a release candidate produce new release
candidates.

## 13.4 Stable

A stable release is a release whose interface is frozen
and that is intended for production use. Stable releases
are versioned as `1.0.0` and above and are published to
the public package index. A stable release is followed by a
period of patch releases for bug fixes; subsequent
features are released as the next minor version.

---

# 14. Versioning Strategy

The project follows Semantic Versioning 2.0.0.

## 14.1 Version number

A version number is of the form `MAJOR.MINOR.PATCH`.

- `MAJOR` is incremented when a backward-incompatible
  change is made to the documented public interface.
- `MINOR` is incremented when a backward-compatible feature
  is added.
- `PATCH` is incremented when a backward-compatible bug
  fix is made.

## 14.2 Pre-release labels

Pre-release versions use the Semantic Versioning
pre-release identifier syntax. A pre-release is identified
by a hyphen followed by a series of dot-separated
identifiers. Examples: `0.1.0a1`, `0.2.0b1`, `1.0.0rc1`.

## 14.3 Initial development

Versions prior to `1.0.0` are considered initial
development. The public interface may change between
minor releases within the initial development series.

## 14.4 First stable release

The first stable release is `1.0.0`. Reaching `1.0.0`
requires:

- a complete SDK specification;
- a complete reference data layer;
- a complete trade data layer for at least the public
  preview surface;
- a documented exception hierarchy;
- a complete test suite for the documented public
  interface;
- a complete set of example scripts;
- a complete set of reference notebooks;
- a public package index entry.

## 14.5 Breaking change rules

A breaking change is any change that requires a consumer to
modify code to continue using the documented behaviour.
The following are examples of breaking changes:

- removing a documented public function, method, or class;
- changing the name, the signature, or the semantic
  behaviour of a documented public function or method;
- changing the documented exception behaviour of a public
  function;
- changing the type of a documented public attribute;
- changing the documented return type of a documented
  public function;
- removing a documented attribute from a documented public
  class;
- changing the documented default value of a public
  parameter where the change is observable to consumers
  who relied on the previous default.

The following are not breaking changes:

- adding a new public function, method, or class;
- adding a new parameter with a default value to an
  existing public function;
- adding a new attribute to a documented public class;
- changing the implementation of a function whose
  documented behaviour is preserved;
- correcting a documentation error that previously described
  unintended behaviour.

## 14.6 Versioning of specification documents

Each specification document is versioned independently of
the SDK. The metadata block of every document records the
document version, the status, the creation timestamp, and
the last-update timestamp. The version of a specification
document is incremented when the document changes; the
version of the SDK is incremented when the SDK changes.

---

# 15. Success Criteria

The success of the project shall be measured against the
following criteria. A criterion is met when an independent
verifier can repeat the procedure and obtain the documented
result.

## 15.1 Stable SDK

The SDK publishes a `1.0.0` release whose public interface
remains stable across subsequent `1.x` releases.

## 15.2 Documented public API

Every public class, function, and parameter is documented
in the SDK specification and in the source-level
docstrings. The coverage of the documentation is one
hundred per cent of the public interface.

## 15.3 Automated testing

The continuous integration pipeline runs the test suite
against every supported Python version and every supported
operating system on every change to the `main` branch and
on every pull request.

## 15.4 Complete examples

The `examples/` directory contains at least one runnable
script per supported workflow. Each script is tested for
import-time and configuration-time correctness in the
continuous integration pipeline.

## 15.5 Production-ready package

The published package includes a wheel and a source
distribution, a valid `pyproject.toml`, a complete long
description, a complete classifier set, and a recorded
provenance.

## 15.6 Backward compatibility within a major version

A consumer who pins to a major version of the SDK shall be
able to upgrade to any later release within the same major
version without modifying consumer code, except where a
deprecation note has been carried over from a previous
release.

## 15.7 Specification discipline

Every implementation task is preceded by a reference to the
relevant specification document. The continuous integration
pipeline verifies that no source file is added that lacks a
recorded specification reference.

---

# 16. Risks

The following risks have been identified during planning.
Each risk is recorded with a brief description and a note
on the planned mitigation.

## 16.1 API changes

The upstream API is operated by the United Nations
Statistics Division and is subject to change. New
endpoints may be added, existing endpoints may be modified,
and the response schema may evolve.

Mitigation: the SDK isolates upstream shape changes inside
the normalisation layer. Changes to the upstream schema
produce changes to the internal representation but not to
the public data model unless the public data model is
itself affected.

## 16.2 Rate limits

The public preview surface is rate-limited. The
subscription-backed surface is rate-limited per key.
Uncontrolled consumption may cause the SDK to be blocked
by the upstream gateway.

Mitigation: the SDK implements a documented retry policy
with exponential backoff. The retry policy is configurable
per client. The documentation describes the rate-limit
behaviour and the recommended client-side pacing.

## 16.3 Deprecations

The upstream service may deprecate endpoints, parameters,
or reference tables. A deprecated endpoint may continue
to function for a period and may then be removed.

Mitigation: the SDK tracks the deprecation notices published
by the upstream service and raises a deprecation warning
when a deprecated endpoint is invoked. The deprecation is
recorded in `docs/CHANGELOG.md` and is communicated through
the release notes.

## 16.4 Authentication changes

The upstream service may change the authentication model,
the key issuance process, or the key format.

Mitigation: the SDK isolates authentication inside a small
authentication module. A change in the authentication
model produces a change in the authentication module but
not in the rest of the SDK.

## 16.5 Large dataset downloads

Bulk downloads of historical or country-wide data can be
very large. A consumer who does not configure pagination
and batching correctly may attempt to download a payload
that exceeds the available memory or the available disk.

Mitigation: the SDK exposes batching, streaming, and
async-delivery surfaces that allow the consumer to control
the download cadence. The documentation describes the
recommended approach for large downloads.

## 16.6 Classification drift

The harmonised system, SITC, and other classifications are
periodically revised. The reference tables are not stable
across years.

Mitigation: the SDK indexes reference data by the version
of the classification that the data was queried against.
The reference data layer exposes the edition explicitly so
that consumers can reason about classification drift.

## 16.7 Reference data staleness

The reference tables may be updated independently of the
trade data. A consumer who caches reference data may
encounter a mismatch between cached and live reference
data.

Mitigation: the SDK exposes a documented cache-invalidation
interface. The documentation describes the
recommended refresh cadence for reference data.

## 16.8 Single-maintainer risk

The project is, at the date of this document, maintained
by a single author. A prolonged absence of the maintainer
may delay the response to upstream changes and to consumer
issues.

Mitigation: the documentation, the test suite, and the
decision log reduce the cost of onboarding a new
maintainer. The project is structured to allow a
succession event without loss of context.

## 16.9 Schema documentation gaps

The upstream service publishes its schema in parts. Some
fields are described in the human-readable documentation,
some are documented only in the reference tables, and
some appear in the wire response without an explicit
description.

Mitigation: the SDK documents every field that it exposes
and records the source of each description in the SDK
specification. Where a field is undocumented, the SDK
records the gap in `docs/DECISIONS.md` rather than
guessing.

## 16.10 Test flakiness from live calls

Tests that exercise the live upstream service may become
flaky when the service is degraded, rate-limited, or
undergoing maintenance.

Mitigation: the test suite separates live tests from
deterministic tests. Live tests are tagged and are not
executed on every commit; deterministic tests are
executed on every commit.

---

# 17. Assumptions

The following assumptions have been made during planning.
Each assumption is recorded so that future tasks may
verify it and either confirm or correct it. An
assumption that turns out to be false is recorded in
`docs/DECISIONS.md` as a correction and is propagated
into the relevant specification document.

## 17.1 About the upstream service

- The United Nations Comtrade API is operated continuously
  and is reachable from the public internet.
- The public preview surface and the subscription-backed
  surface are both operated by the same upstream gateway.
- The subscription key issued by the developer portal is a
  long opaque string that is sent on every authenticated
  request.
- The upstream service is versioned and the URL structure
  encodes the version. Breaking changes in the URL
  structure require a new SDK major version.
- The upstream service responds with JSON only for the
  endpoints in scope; other content types are not
  expected.
- The reference tables are stable enough to be cached for
  the duration of a release cycle.

## 17.2 About the consumers

- Consumers are professional developers who understand the
  Python type system and the request-response model of
  HTTP.
- Consumers are expected to install the SDK through the
  standard Python package index.
- Consumers are expected to handle their own credentials
  and not to commit them to source control.
- Consumers are expected to be aware of the rate-limit
  policies of the upstream service and to configure the
  SDK accordingly.

## 17.3 About the project

- The project is maintained by volunteers and does not
  receive a continuous budget.
- The release cadence is set by the maintainers and is
  not bound to a fixed schedule.
- The maintainers are willing to add new endpoints on
  request but will not implement features that are not in
  the scope of the project.
- The project is delivered under a permissive open-source
  license whose exact terms are recorded in `LICENSE`.

## 17.4 About the environment

- The supported Python versions are the ones described in
  section 6.
- The supported operating systems are the ones tested in
  the continuous integration pipeline; the exact set is
  recorded in the SDK specification.
- The networking environment of the consumer allows direct
  egress to the upstream gateway or is configured with a
  proxy whose details are passed to the SDK at
  construction time.

---

# 18. Open Questions

The following questions remain open at the date of this
document. They are recorded here so that future tasks can
resolve them. An open question is not an excuse to delay
work; it is a recorded decision to defer the answer until
the relevant task is in flight.

- OQ-001. What is the exact list of reference tables that
  the SDK will load eagerly at construction time, and what
  is the list that the SDK will load lazily on first use?
- OQ-002. What is the default location of the on-disk
  cache for reference data and recorded sample data, and
  how is that location overridden by the consumer?
- OQ-003. What is the canonical name of the asynchronous
  client, and does it share the public interface with the
  synchronous client, or is it a separate public class?
- OQ-004. What is the documented behaviour of the SDK when
  the upstream service returns a partial response or a
  response that is missing a field that the SDK expects?
- OQ-005. How does the SDK represent a query that the
  upstream service does not support, and how is the
  consumer notified of the rejection?
- OQ-006. What is the policy for handling changes to the
  classification code of a commodity that the consumer has
  cached under the old code?
- OQ-007. What is the policy for handling the
  `includeDesc` parameter, given that the upstream service
  leaves the field empty when the parameter is set to
  false?
- OQ-008. How is the SDK version aligned with the
  upstream API version, and is there a documented mapping
  between SDK major versions and upstream API versions?
- OQ-009. What is the policy for the SDK when the consumer
  requests a period that the upstream service does not yet
  hold data for?
- OQ-010. What is the policy for the SDK when the consumer
  requests a commodity code that is not defined in the
  classification chosen for the query?
- OQ-011. What is the policy for the SDK when the consumer
  requests a reporter or partner that is not in the
  reference tables?
- OQ-012. What is the policy for the SDK when the
  subscription key is missing, malformed, or expired?
- OQ-013. What is the policy for the SDK when the consumer
  requests a synchronous call against an endpoint that is
  documented as asynchronous only?
- OQ-014. What is the policy for the SDK when the
  continuous integration pipeline cannot reach the
  upstream service for an extended period?
- OQ-015. What is the policy for the SDK when the
  documentation of the upstream service contradicts the
  observed behaviour of the upstream service?

---

# 19. Future Roadmap

The roadmap below describes the high-level phases of the
project. Each phase is associated with a milestone in
`docs/015_ROADMAP.md`, which is the source of truth for
delivery planning.

## 19.1 Phase 0 — Specification

The specification phase produces the documents numbered
`000` through `099`. No source code is written during this
phase. The output is a complete and consistent specification
tree that the implementation phase can read.

## 19.2 Phase 1 — Reference data layer

The reference data phase produces the metadata layer of the
SDK. The output is a stable interface for loading,
caching, and querying the reference tables.

## 19.3 Phase 2 — Trade data layer

The trade data phase produces the trade layer of the SDK
on top of the reference data layer. The output is a stable
interface for querying final data, tariffline data, and
trade balance data, against both the public preview and
the subscription-backed surfaces.

## 19.4 Phase 3 — Bulk and async surfaces

The bulk and async phase produces the bulk download and
asynchronous delivery surfaces on top of the trade data
layer. The output is a stable interface for handling large
volumes of data and long-running requests.

## 19.5 Phase 4 — Packaging and release

The packaging phase produces the first public release of
the SDK on the standard Python package index. The output
is a `1.0.0` release with a complete set of examples and
notebooks.

## 19.6 Phase 5 — Maintenance and evolution

The maintenance phase maintains the released SDK, addresses
consumer issues, and accepts contributions. New endpoints
and features are added in minor releases; breaking changes
are reserved for major releases.

The roadmap is a planning artefact. The deliverable for
each phase is a milestone that is recorded in
`docs/015_ROADMAP.md`; this charter is not the source of
truth for delivery dates.

---

# End of document
