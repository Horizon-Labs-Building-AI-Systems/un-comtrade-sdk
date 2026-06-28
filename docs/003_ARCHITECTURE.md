```
Document ID
003

Title
Software Architecture Specification

Version
0.1.0

Status
DRAFT

Created
2026-06-26T19:51:52Z

Last Updated
2026-06-26T19:51:52Z

Author
Codex

Project
UN Comtrade Python SDK

Dependencies
000_PROJECT_CHARTER.md
001_EXECUTION_PROTOCOL.md
002_CONTEXT.md

Supersedes
None
```

---

# 1. Architectural Overview

## 1.1 Overall purpose

The Software Architecture Specification defines the logical
architecture of the UN Comtrade Python SDK. The architecture
describes the layers, the responsibilities of each layer, the
dependencies between layers, the data flow across the layers,
and the boundaries at which future implementation tasks
shall be split.

The architecture is implementation-independent. It does not
name libraries, does not commit to specific class names,
does not include source code, and does not bind the project
to a particular runtime version. Where the architecture
requires a behaviour that is implementation-dependent, the
behaviour is expressed as a contract on a layer boundary
and is realised in the corresponding layer specification.

## 1.2 Primary responsibilities

The architecture has the following primary responsibilities.

- To describe the system context in which the SDK operates.
- To define the layered decomposition of the SDK.
- To declare the responsibilities, inputs, outputs, and
  boundaries of each layer.
- To record the dependency rules between layers and the
  prohibition of circular dependencies.
- To describe the data flow that connects the layers.
- To define the interface contracts at the layer
  boundaries.
- To declare the module skeleton that the SDK specification
  shall refine.
- To record the error-propagation strategy and the
  configuration architecture.
- To describe the extension strategy by which future
  functionality shall be added without breaking the
  architecture.

## 1.3 External dependencies

The architecture declares the following external
dependencies at the conceptual level. The concrete list
and the version constraints are recorded in
`000_PROJECT_CHARTER.md` section 6 and in the SDK
specification.

- The Python language as distributed by the Python Software
  Foundation.
- The Python standard library.
- The Python package ecosystem for runtime dependencies.
- The upstream UN Comtrade API, operated by the United
  Nations Statistics Division on an Azure API Management
  gateway.

## 1.4 Internal layers

The internal architecture is composed of ten logical layers
organised in a strict downward dependency chain. The
external upstream API is treated as the originating
source, and the application layer is the terminal
consumer. The layers are recorded in section 4.

---

# 2. System Context

The SDK operates between the upstream UN Comtrade API and
the consumers that embed it. The context in which the SDK
operates is described by the diagram below. Each box
outside the SDK represents a separate system with its own
responsibilities.

```
+----------------------------+
|  UN Comtrade API           |   source of truth for trade
|  (upstream HTTP service)   |   statistics and reference data
+----------------------------+
              |
              v
+----------------------------+
|  Python SDK                |   transport, validation,
|  (this project)            |   normalisation, caching
+----------------------------+
              |
              v
+----------------------------+
|  ETL Subsystem             |   scheduled extraction,
|  (consumer)                |   batching, watermarking
+----------------------------+
              |
              v
+----------------------------+
|  Storage Subsystem         |   data lake, warehouse,
|  (consumer)                |   or file-based persistence
+----------------------------+
              |
              v
+----------------------------+
|  Analytics Subsystem       |   transformations, indicators,
|  (consumer)                |   modelling
+----------------------------+
              |
              v
+----------------------------+
|  Application Subsystem     |   end-user products such as
|  (consumer)                |   notebooks, dashboards, APIs
+----------------------------+
```

The SDK is the only artefact that this project produces.
The ETL, storage, analytics, and application subsystems
are not part of the SDK. They are consumers of the SDK and
are referenced here only to describe the boundaries at
which the SDK's responsibilities end.

## 2.1 Interaction with the upstream API

The SDK interacts with the upstream API exclusively through
the transport layer. No other layer is permitted to issue
HTTP requests. The transport layer is the only layer that
understands the wire format of the upstream API.

## 2.2 Interaction with consumers

The SDK is consumed by other Python code through the public
interface declared in section 9. Consumers may be ETL
pipelines, notebooks, scripts, or services. The SDK does
not know which consumer is using it; the SDK's contract is
with the public interface, not with any specific consumer.

## 2.3 Interaction with the environment

The SDK reads configuration from the environment at
construction time, not at import time. The environment
sources are recorded in section 13. The SDK does not
mutate the environment; it does not write to global state
and does not register side effects at import time.

## 2.4 Interaction with the operating system

The SDK may read and write the local filesystem for the
purposes of caching and recorded-sample persistence. The
filesystem access is performed by the storage layer. No
other layer is permitted to perform filesystem I/O.

---

# 3. Architectural Principles

The architecture is governed by the principles below. Each
principle is binding for every future implementation task
unless a future revision of this document records an
explicit deviation. Deviations are recorded in
`DECISIONS.md`.

## 3.1 Layered architecture

The SDK is composed of a strict, ordered set of layers.
The layer order is declared in section 4. A layer may
depend on layers beneath it and shall not depend on
layers above it. Layer skipping is prohibited.

## 3.2 Separation of concerns

Each layer has a single, narrowly defined responsibility.
A change in one layer SHALL NOT require a coordinated
change in another layer except through the documented
interface contracts at the layer boundary.

## 3.3 Single responsibility

Each module within a layer has a single responsibility
that is captured by its name. A module whose name does
not communicate its responsibility is renamed.

## 3.4 Composition over inheritance

Layer relationships are expressed through composition
rather than inheritance. A layer that needs the
capabilities of another layer holds a reference to the
other layer and delegates to it.

## 3.5 Strong typing

Every public interface declares type hints. The type
signature of a function conveys the shape of its inputs
and outputs without requiring the consumer to read the
implementation. Types are precise; broad types such as
"any object" are not used at public boundaries.

## 3.6 Explicit error handling

The SDK raises a small, documented exception hierarchy.
Implicit errors, swallowed exceptions, and silent
fallbacks are prohibited. The error-propagation strategy
is recorded in section 12.

## 3.7 Deterministic behaviour

Given the same input and the same configuration, the SDK
produces the same output. Caching, retry, and rate-limit
logic do not introduce hidden non-determinism into
consumer code.

## 3.8 Documentation first

Every implementation task is preceded by the relevant
specification. The architecture is the source of truth
for layer boundaries; the layer specifications refine
the layer responsibilities; the SDK specification
refines the public interface.

## 3.9 Backward compatibility

The public interface declared in section 9 is stable
within a major version. Breaking changes are reserved
for major version increments and are recorded in
`DECISIONS.md` before they are committed.

## 3.10 Testability

Every layer is testable in isolation. The test standard
is recorded in `012_TESTING_STANDARD.md`. Layers that
cannot be tested in isolation are architectural defects
and are corrected through the change-governance process.

## 3.11 Minimal surface area

The public interface exposes the smallest set of
concepts required to model the upstream API. The SDK
does not invent capabilities that the upstream API does
not provide.

## 3.12 Explicit configuration

Configuration is explicit and is passed at construction
time. Configuration is not read from global state, is
not inferred from environment variables at import time,
and is not mutated after construction except through
documented mutator methods.

---

# 4. Layered Architecture

The SDK is composed of ten logical layers organised in a
strict downward dependency chain. The diagram below names
the layers in dependency order; each layer may depend on
the layers beneath it and shall not depend on the layers
above it.

```
+----------------------------------+
|  UN Comtrade API (external)      |  source of truth
+----------------------------------+
              |
              v
+----------------------------------+
|  L1  Transport Layer             |  HTTP, auth, retry
+----------------------------------+
              |
              v
+----------------------------------+
|  L2  SDK Client Layer            |  endpoint selection,
|                                  |  parameter validation
+----------------------------------+
              |
              v
+----------------------------------+
|  L3  Metadata Layer              |  reference catalogues
+----------------------------------+
              |
              v
+----------------------------------+
|  L4  Trade Layer                 |  trade data retrieval
+----------------------------------+
              |
              v
+----------------------------------+
|  L5  Validation Layer            |  parameter validation,
|                                  |  type coercion
+----------------------------------+
              |
              v
+----------------------------------+
|  L6  Normalisation Layer         |  stable data model,
|                                  |  schema versioning
+----------------------------------+
              |
              v
+----------------------------------+
|  L7  Export Layer                |  in-memory shapes for
|                                  |  consumer handoff
+----------------------------------+
              |
              v
+----------------------------------+
|  L8  Storage Layer               |  cache, recorded
|                                  |  samples, persistence
+----------------------------------+
              |
              v
+----------------------------------+
|  L9  Analytics Layer             |  consumer-side; outside
|                                  |  the SDK boundary
+----------------------------------+
              |
              v
+----------------------------------+
|  L10 Application Layer           |  consumer-side; outside
|                                  |  the SDK boundary
+----------------------------------+
```

The upstream API is the originating source. The analytics
and application layers are outside the SDK boundary; they
are referenced here only to describe the terminal
consumers of the data produced by the SDK.

## 4.1 Layer dependency direction

Dependency direction is strictly downward. A layer depends
on the layer immediately beneath it and on the layers
beneath that one, transitively, through the documented
interface contracts. A layer SHALL NOT depend on a layer
above it. A layer SHALL NOT skip a layer.

## 4.2 Layer skipping

Layer skipping is prohibited. A layer that needs the
capabilities of a non-adjacent layer SHALL route the call
through the intervening layers. The routing is recorded
in the interface contracts of section 8.

## 4.3 Circular dependencies

Circular dependencies are prohibited. The architecture is
verified against the cycle rule at every architectural
review. A change that introduces a cycle is rejected.

---

# 5. Layer Responsibilities

This section declares the responsibility of each layer.
The declaration is normative: a future implementation
task that adds behaviour to a layer SHALL conform to the
responsibility declared here.

## 5.1 L1 — Transport Layer

- **Purpose.** Isolate the SDK from the wire format and
  transport semantics of the upstream API.
- **Responsibilities.** Issue HTTP requests, manage
  authentication, apply retry and backoff, surface
  rate-limit responses, and translate HTTP responses into
  transport-level outcomes.
- **Inputs.** Request descriptors from the SDK client
  layer.
- **Outputs.** Transport-level outcomes to the SDK
  client layer.
- **Owned functionality.** Connection management, header
  construction, key rotation, proxy support, retry with
  exponential backoff, rate-limit detection.
- **Public interface.** None to the SDK consumer. Internal
  interface to the SDK client layer only.
- **Boundary conditions.** The transport layer is the
  boundary at which the SDK stops being agnostic about
  the network. The transport layer is the only layer
  permitted to perform network I/O.
- **Failure conditions.** Network failure, authentication
  failure, rate-limit failure, malformed response. Each
  failure is translated into a documented transport-level
  outcome.

## 5.2 L2 — SDK Client Layer

- **Purpose.** Provide the entry point for the SDK and
  select the appropriate endpoint and surface.
- **Responsibilities.** Validate high-level parameters,
  select the endpoint family, dispatch to the metadata
  layer or the trade layer, and orchestrate the request
  through the layers beneath.
- **Inputs.** Consumer-facing requests, configuration
  injected at construction.
- **Outputs.** Domain-level results returned to the
  consumer; lower-level results forwarded to the
  metadata and trade layers.
- **Owned functionality.** Endpoint selection, parameter
  composition, response correlation, lifecycle management
  of the lower layers.
- **Public interface.** The SDK client class. The exact
  name is recorded in section 9.
- **Boundary conditions.** The client layer is the
  boundary at which the consumer's request enters the
  SDK. Configuration is bound at construction and is not
  mutated after construction except through documented
  mutator methods.
- **Failure conditions.** Invalid configuration,
  invalid request shape, dispatcher failure. Each
  failure is translated into a documented SDK-level
  exception.

## 5.3 L3 — Metadata Layer

- **Purpose.** Expose the reference catalogues of the
  upstream API as a stable, queryable surface.
- **Responsibilities.** Load reference tables, cache
  reference data, expose query helpers for reporters,
  partners, classifications, flows, modes of transport,
  modes of supply, and quantity units.
- **Inputs.** Reference identifiers and query descriptors
  from the client layer.
- **Outputs.** Reference records and reference collections
  to the client layer.
- **Owned functionality.** Reference table loading,
  reference table caching, reference-data version
  tracking, reference-data freshness checks.
- **Public interface.** The metadata module. The exact
  name is recorded in section 9.
- **Boundary conditions.** The metadata layer is the
  boundary at which the SDK exposes a stable model of
  the upstream reference catalogues. The metadata layer
  SHALL NOT perform trade data retrieval.
- **Failure conditions.** Reference table unavailable,
  reference identifier unknown, reference table version
  mismatch.

## 5.4 L4 — Trade Layer

- **Purpose.** Expose trade data retrieval as a stable
  surface.
- **Responsibilities.** Compose trade queries, dispatch
  to the appropriate endpoint family, manage pagination
  and bulk download, and surface trade-level outcomes.
- **Inputs.** Trade query descriptors from the client
  layer.
- **Outputs.** Trade records and trade collections to
  the client layer; trade-level outcomes for the
  validation and normalisation layers.
- **Owned functionality.** Query composition, endpoint
  family selection, pagination, async dispatch, bulk
  download, data-availability checks.
- **Public interface.** The trade module. The exact name
  is recorded in section 9.
- **Boundary conditions.** The trade layer is the
  boundary at which the SDK begins to handle trade
  semantics. The trade layer SHALL NOT perform reference
  retrieval; reference lookups that the trade layer needs
  are delegated to the metadata layer.
- **Failure conditions.** Query rejected by the upstream
  API, partial response, query timeout, query that
  exceeds the documented record cap.

## 5.5 L5 — Validation Layer

- **Purpose.** Validate and coerce inputs before they
  reach the upstream API and the normalisation layer.
- **Responsibilities.** Validate parameter shapes, coerce
  string and integer parameters, enforce documented
  value sets, and reject invalid combinations.
- **Inputs.** Parameter descriptors from the client and
  trade layers.
- **Outputs.** Validated and coerced parameters to the
  client, trade, and normalisation layers.
- **Owned functionality.** Parameter validation, value-set
  enforcement, type coercion, range checks, format
  checks.
- **Public interface.** The validation module. The exact
  name is recorded in section 9.
- **Boundary conditions.** The validation layer is the
  boundary at which the SDK rejects inputs that the
  upstream API would also reject. The validation layer
  does not call the upstream API; it only prepares
  parameters for the transport layer.
- **Failure conditions.** Parameter of the wrong type,
  parameter outside the documented value set, parameter
  combination rejected by the documented rules.

## 5.6 L6 — Normalisation Layer

- **Purpose.** Convert upstream responses into the SDK's
  stable data model.
- **Responsibilities.** Coerce response fields, apply
  schema-versioning rules, attach documented defaults,
  normalise measurement units, and tag records with
  provenance metadata.
- **Inputs.** Raw response payloads from the transport
  layer.
- **Outputs.** Normalised records to the client, trade,
  and export layers.
- **Owned functionality.** Response coercion, schema
  version handling, default attachment, unit
  normalisation, provenance tagging.
- **Public interface.** The models module. The exact name
  is recorded in section 9.
- **Boundary conditions.** The normalisation layer is the
  boundary at which the SDK stops being aware of the
  upstream schema and becomes aware of the SDK's
  stable data model. The normalisation layer SHALL NOT
  perform network I/O.
- **Failure conditions.** Response field of the wrong
  type, response field missing, schema version
  unrecognised.

## 5.7 L7 — Export Layer

- **Purpose.** Provide a stable, in-memory shape that
  consumers can hand off to their own systems.
- **Responsibilities.** Package normalised records into
  consumer-facing collections, apply consumer-level
  defaults, and return the result through the public
  interface.
- **Inputs.** Normalised records from the normalisation
  layer.
- **Outputs.** Consumer-facing collections returned to
  the client layer for handoff.
- **Owned functionality.** Collection assembly, default
  application, handoff-shape management.
- **Public interface.** The export module. The exact name
  is recorded in section 9.
- **Boundary conditions.** The export layer is the
  boundary at which the SDK hands the result to the
  consumer. The export layer SHALL NOT perform network
  I/O, SHALL NOT perform filesystem I/O, and SHALL NOT
  depend on the storage layer.
- **Failure conditions.** Collection assembly failure,
  default application failure.

## 5.8 L8 — Storage Layer

- **Purpose.** Persist reference data, recorded samples,
  and optional cache entries for the metadata and trade
  layers.
- **Responsibilities.** Read and write the local cache,
  read and write recorded samples, manage cache
  invalidation, and respect the consumer's cache
  configuration.
- **Inputs.** Cacheable artefacts from the metadata and
  trade layers.
- **Outputs.** Cached artefacts returned to the metadata
  and trade layers.
- **Owned functionality.** Cache I/O, cache
  invalidation, sample persistence, cache-lifetime
  management.
- **Public interface.** The cache module. The exact name
  is recorded in section 9.
- **Boundary conditions.** The storage layer is the
  boundary at which the SDK performs filesystem I/O. The
  storage layer is the only layer permitted to perform
  filesystem I/O. The storage layer SHALL NOT perform
  network I/O.
- **Failure conditions.** Filesystem failure, cache
  corruption, permission failure, cache version
  mismatch.

## 5.9 L9 — Analytics Layer

- **Purpose.** Provide consumer-side analytics. The
  analytics layer is outside the SDK boundary; it is
  referenced here only to describe the terminal
  consumer of the data produced by the SDK.
- **Responsibilities.** None for the SDK. The analytics
  layer is the responsibility of the consumer.
- **Inputs.** Consumer-facing collections from the SDK.
- **Outputs.** Consumer-side indicators and reports.
- **Owned functionality.** None for the SDK.
- **Public interface.** None.
- **Boundary conditions.** The analytics layer is the
  boundary at which the SDK's responsibilities end.
- **Failure conditions.** None for the SDK.

## 5.10 L10 — Application Layer

- **Purpose.** Provide end-user products such as
  notebooks, dashboards, and APIs. The application layer
  is outside the SDK boundary; it is referenced here only
  to describe the terminal consumer of the data produced
  by the SDK.
- **Responsibilities.** None for the SDK.
- **Inputs.** Consumer-facing collections from the SDK.
- **Outputs.** End-user products.
- **Owned functionality.** None for the SDK.
- **Public interface.** None.
- **Boundary conditions.** The application layer is the
  boundary at which the consumer takes responsibility
  for the user-facing experience.
- **Failure conditions.** None for the SDK.

---

# 6. Layer Dependency Rules

The dependency rules below are normative. A change that
violates a rule is rejected by the architectural review.

## 6.1 Allowed dependencies

- A layer may depend on the layer immediately beneath it.
- A layer may depend on layers beneath that one, through
  the documented interface contracts.
- The client layer may depend on the metadata layer and
  on the trade layer.
- The trade layer may depend on the metadata layer for
  reference lookups.
- The metadata layer may depend on the validation layer
  for parameter coercion.
- The trade layer may depend on the validation layer for
  parameter coercion.
- The storage layer may be invoked by the metadata and
  trade layers through the documented interface.
- The transport layer is the only layer that depends on
  external network resources.

## 6.2 Forbidden dependencies

- A layer SHALL NOT depend on a layer above it.
- A layer SHALL NOT skip a layer; calls SHALL be routed
  through the intervening layers.
- The transport layer SHALL NOT depend on any other layer
  of the SDK; the transport layer is the lowest layer of
  the SDK and depends only on the external network.
- The normalisation layer SHALL NOT perform network I/O.
- The export layer SHALL NOT perform network I/O or
  filesystem I/O.
- The storage layer SHALL NOT perform network I/O.
- The validation layer SHALL NOT call the upstream API;
  the validation layer only prepares parameters for the
  transport layer.
- The metadata layer SHALL NOT perform trade data
  retrieval.
- The trade layer SHALL NOT perform reference catalogue
  loading; the trade layer delegates to the metadata
  layer.
- The application and analytics layers are outside the
  SDK boundary; the SDK SHALL NOT depend on them.

## 6.3 Dependency direction

The dependency direction is strictly downward: from L10
toward L1, and from L1 toward the external upstream API.
A module that imports another module that is not on a
lower-numbered layer is a defect.

## 6.4 No circular dependencies

A cycle in the dependency graph is a defect. The
architecture is verified against the cycle rule at every
architectural review. The verification records the
dependency graph in the architectural review notes.

## 6.5 No layer skipping

A layer that needs a capability that is provided by a
non-adjacent layer SHALL route the call through the
intervening layer. The intervening layer is responsible
for translating the call into a form that the target
layer accepts.

---

# 7. Data Flow

The data flow describes how a request from a consumer is
transformed into a response from the upstream API and back.
Each stage has a documented responsibility.

```
+------------------------------+
|  Consumer Request            |
+------------------------------+
              |
              v
+------------------------------+
|  L2 SDK Client Layer         |  accept request, bind config
+------------------------------+
              |
              v
+------------------------------+
|  L5 Validation Layer         |  validate parameters, coerce
+------------------------------+
              |
              v
+------------------------------+
|  L3 Metadata Layer or        |
|  L4 Trade Layer              |  compose query, select
|                              |  endpoint family
+------------------------------+
              |
              v
+------------------------------+
|  L1 Transport Layer          |  issue HTTP request,
|                              |  handle auth and retry
+------------------------------+
              |
              v
+------------------------------+
|  Upstream UN Comtrade API    |  return response
+------------------------------+
              |
              v
+------------------------------+
|  L1 Transport Layer          |  surface response
+------------------------------+
              |
              v
+------------------------------+
|  L6 Normalisation Layer      |  coerce response into
|                              |  stable data model
+------------------------------+
              |
              v
+------------------------------+
|  L7 Export Layer             |  package into
|                              |  consumer-facing collection
+------------------------------+
              |
              v
+------------------------------+
|  L8 Storage Layer            |  persist to cache if
|                              |  requested
+------------------------------+
              |
              v
+------------------------------+
|  Consumer Response           |
+------------------------------+
```

## 7.1 Stage responsibilities

- **Consumer Request.** The consumer invokes a public
  method of the SDK client. The request carries
  parameters, configuration, and identifiers.
- **L2 SDK Client Layer.** The client layer accepts the
  request, binds configuration, and routes the request
  to the metadata or trade layer based on the request
  shape.
- **L5 Validation Layer.** The validation layer validates
  the parameters and coerces them into the types
  expected by the upstream API.
- **L3 Metadata Layer or L4 Trade Layer.** The selected
  layer composes the query, selects the endpoint family,
  and dispatches the call to the transport layer.
- **L1 Transport Layer.** The transport layer issues the
  HTTP request, applies authentication, applies retry
  and backoff, and surfaces the response.
- **Upstream UN Comtrade API.** The upstream API returns
  the response.
- **L1 Transport Layer.** The transport layer returns
  the response to the calling layer.
- **L6 Normalisation Layer.** The normalisation layer
  coerces the response into the SDK's stable data
  model.
- **L7 Export Layer.** The export layer packages the
  normalised records into a consumer-facing collection.
- **L8 Storage Layer.** The storage layer persists the
  result to the cache if caching is requested.
- **Consumer Response.** The consumer receives the
  response through the public interface.

## 7.2 Caching data flow

The storage layer is invoked at two points: on the way
in, to populate the cache from a previous response, and
on the way out, to write a new response. The data flow
above is the outbound flow; the inbound flow is a
short-circuit in the metadata or trade layer that
satisfies the request from the cache without invoking
the transport layer.

## 7.3 Error data flow

Errors propagate upward through the layer chain. Each
layer is responsible for translating a lower-level error
into the documented exception type of the layer. The
error-propagation strategy is recorded in section 12.

---

# 8. Interface Contracts

This section declares the interface contracts at the
layer boundaries. The contracts are normative. The
implementation of each contract is the responsibility of
the layer specification for the layer that owns the
contract.

## 8.1 Client-to-Metadata contract

- **Purpose.** Allow the client layer to request
  reference data from the metadata layer.
- **Input.** A reference query descriptor identifying
  the reference table, the identifier, and the optional
  query parameters.
- **Output.** A reference record or reference collection
  in the SDK's stable data model.
- **Ownership.** Owned by the metadata layer.
- **Error propagation.** The metadata layer raises a
  documented metadata exception. The client layer does
  not catch the exception; the exception propagates to
  the consumer through the public interface.

## 8.2 Client-to-Trade contract

- **Purpose.** Allow the client layer to request trade
  data from the trade layer.
- **Input.** A trade query descriptor identifying the
  reporter, partner, period, classification, commodity,
  flow, and other trade-level parameters.
- **Output.** A trade record or trade collection in the
  SDK's stable data model.
- **Ownership.** Owned by the trade layer.
- **Error propagation.** The trade layer raises a
  documented trade exception. The client layer does not
  catch the exception; the exception propagates to the
  consumer through the public interface.

## 8.3 Trade-to-Metadata contract

- **Purpose.** Allow the trade layer to request
  reference data lookups from the metadata layer.
- **Input.** A reference identifier.
- **Output.** A reference record.
- **Ownership.** Owned by the metadata layer.
- **Error propagation.** The metadata layer raises a
  documented metadata exception.

## 8.4 Layer-to-Transport contract

- **Purpose.** Allow the metadata and trade layers to
  issue transport-level requests.
- **Input.** A request descriptor identifying the
  endpoint family, the URL template, the query
  parameters, and the authentication context.
- **Output.** A transport-level outcome containing the
  status code, the response payload, and the metadata
  required to interpret the response.
- **Ownership.** Owned by the transport layer.
- **Error propagation.** The transport layer raises a
  documented transport exception. The calling layer does
  not catch the exception; the exception propagates to
  the consumer.

## 8.5 Layer-to-Validation contract

- **Purpose.** Allow the metadata and trade layers to
  validate parameters before they are sent to the
  transport layer.
- **Input.** A parameter descriptor.
- **Output.** A validated and coerced parameter value.
- **Ownership.** Owned by the validation layer.
- **Error propagation.** The validation layer raises a
  documented validation exception.

## 8.6 Layer-to-Normalisation contract

- **Purpose.** Allow the metadata and trade layers to
  hand off a raw response for normalisation.
- **Input.** A raw response payload and the response
  context required to interpret it.
- **Output.** A normalised record in the SDK's stable
  data model.
- **Ownership.** Owned by the normalisation layer.
- **Error propagation.** The normalisation layer raises
  a documented normalisation exception.

## 8.7 Layer-to-Export contract

- **Purpose.** Allow the metadata and trade layers to
  package a result for the consumer.
- **Input.** A normalised record or collection.
- **Output.** A consumer-facing collection in the
  documented handoff shape.
- **Ownership.** Owned by the export layer.
- **Error propagation.** The export layer raises a
  documented export exception.

## 8.8 Layer-to-Storage contract

- **Purpose.** Allow the metadata and trade layers to
  read from and write to the cache.
- **Input.** A cache key, a cache entry, or a cache
  invalidation request.
- **Output.** A cache hit, a cache miss, or a cache
  acknowledgement.
- **Ownership.** Owned by the storage layer.
- **Error propagation.** The storage layer raises a
  documented storage exception.

---

# 9. Module Boundaries

This section declares the logical module skeleton of the
SDK. The skeleton is normative at the module level. The
detailed interface of each module is the responsibility of
the SDK specification. The module boundaries answer
open question CTX-001 by declaring the top-level
package layout at the architectural level.

## 9.1 Top-level package

The SDK SHALL be distributed as a single top-level Python
package. The package name is recorded in this section as
the architectural declaration; the SDK specification may
not change the name without amending this document.

- **Package name:** `un_comtrade`
- **Distribution name:** `un-comtrade-sdk`
- **Import name:** `un_comtrade`

## 9.2 Sub-packages

The top-level package is partitioned into the sub-packages
below. Each sub-package corresponds to a layer of the
architecture and SHALL NOT contain code that belongs to
a different layer.

- `un_comtrade.transport` — the transport layer (L1).
- `un_comtrade.client` — the SDK client layer (L2).
- `un_comtrade.metadata` — the metadata layer (L3).
- `un_comtrade.trade` — the trade layer (L4).
- `un_comtrade.validation` — the validation layer (L5).
- `un_comtrade.normalisation` — the normalisation layer
  (L6).
- `un_comtrade.export` — the export layer (L7).
- `un_comtrade.storage` — the storage layer (L8).
- `un_comtrade.models` — the stable data model shared
  across layers (resides at the package root because it
  is consumed by multiple layers; the module is
  read-only from the perspective of the consuming
  layers).
- `un_comtrade.errors` — the documented exception
  hierarchy.
- `un_comtrade.config` — the configuration objects.
- `un_comtrade.logging` — the logging seam.
- `un_comtrade.pagination` — the pagination helpers.
- `un_comtrade.retry` — the retry helpers.
- `un_comtrade.cache` — the storage-layer entry points
  that the metadata and trade layers invoke.
- `un_comtrade.utils` — the cross-cutting utilities that
  do not fit into any of the above.

## 9.3 Module-level responsibility summary

The responsibilities below are the architectural
declaration. The detailed interface is refined in the
SDK specification.

- **client.** The entry point of the SDK. Accepts
  consumer requests, binds configuration, dispatches
  to the metadata and trade layers.
- **metadata.** Reference catalogue access. Loads,
  caches, and queries the reference tables.
- **trade.** Trade data retrieval. Composes queries,
  dispatches to the upstream API, manages pagination.
- **transport.** Network I/O. Issues HTTP requests,
  applies authentication, applies retry, surfaces
  rate-limit responses.
- **validation.** Parameter validation and coercion.
  Rejects invalid inputs before they reach the upstream
  API.
- **normalisation.** Response coercion into the SDK's
  stable data model.
- **export.** Result packaging for the consumer.
- **storage.** Filesystem I/O for caching and recorded
  samples.
- **models.** The stable data model shared across
  layers. Read-only from the perspective of consuming
  layers.
- **errors.** The documented exception hierarchy.
- **config.** The configuration objects. Read at
  construction time.
- **logging.** The logging seam. The SDK emits
  structured log records at the documented levels.
- **pagination.** The pagination helpers used by the
  trade layer.
- **retry.** The retry helpers used by the transport
  layer.
- **cache.** The storage-layer entry points. Invoked by
  the metadata and trade layers.
- **utils.** Cross-cutting utilities. Limited to
  functions that do not belong to any other module.

## 9.4 Module dependency rules

The module dependency rules mirror the layer dependency
rules of section 6. A module may import from a module
that belongs to a lower-numbered layer and SHALL NOT
import from a module that belongs to a higher-numbered
layer.

## 9.5 Public versus private

A module is public if its name is listed in section 9.2
or 9.3. A module is private if its name is prefixed with
an underscore. Consumers SHALL NOT import a private
module; doing so is unsupported and may break at any
minor version.

---

# 10. External Dependencies

External dependencies are recorded at the conceptual
level. The concrete list of approved dependencies and
their version constraints is the responsibility of the
SDK specification and of the coding standard.

## 10.1 Current dependencies

- **Python language.** The supported versions are
  recorded in `000_PROJECT_CHARTER.md` section 6.
- **Python standard library.** Used for HTTP transport,
  data structures, type hints, abstract base classes,
  and cross-cutting utilities.
- **`httpx` library.** Approved for HTTP transport.
  The `httpx` library provides both a synchronous
  and asynchronous API; the SDK uses the
  synchronous API for the MVP (per Architecture
  Freeze Question Q3). The version constraint is
  recorded in the SDK specification.

## 10.2 Future dependencies

The following dependencies are anticipated for future
versions. They are not approved for the current version
and SHALL NOT be added without a recorded decision.

- A data-analysis library, for the optional DataFrame
  handoff shape.
- A caching library, for an optional high-performance
  cache backend.
- A structured-logging library, for richer log records.

## 10.3 Potential dependencies

The following dependencies are candidates but are not yet
approved. Each candidate is recorded for traceability
and SHALL be re-evaluated when the need arises.

- An HTTP/2 or HTTP/3 client, for performance.
- A serialization library, for binary handoff shapes.
- A retry library, for advanced retry policies.

## 10.4 Dependency approval

A new runtime dependency SHALL be approved by a recorded
decision in `DECISIONS.md` before it is added to
`pyproject.toml`. The decision SHALL record the
rationale, the alternatives considered, and the expected
lifecycle.

## 10.5 Dependency removal

A runtime dependency SHALL NOT be removed without a
major version increment. The removal is announced in
`CHANGELOG.md` and is recorded in `DECISIONS.md`.

---

# 11. Internal Dependencies

The internal dependency rules below are normative.

## 11.1 Ownership

Each module is owned by a single layer. The owner is
responsible for the module's interface, the module's
tests, and the module's documentation. A module is not
modified by a layer other than its owner except through
the documented interface contracts.

## 11.2 Communication rules

- A module communicates with the modules of the
  immediately lower layer through the documented
  interface contracts.
- A module SHALL NOT reach across layers to invoke a
  function of a non-adjacent layer.
- A module SHALL NOT invoke a function of a higher
  layer.

## 11.3 Cycle prevention

A cycle in the internal dependency graph is a defect.
The architecture is verified against the cycle rule at
every architectural review. The verification records
the dependency graph in the architectural review notes.

## 11.4 Cross-cutting concerns

Cross-cutting concerns such as logging, configuration,
and error handling are implemented as seams that the
layers invoke through narrow interfaces. The seams do
not introduce cycles. The logging, configuration, and
error seams are documented in section 13 and section
12 respectively.

---

# 12. Error Propagation Strategy

The error-propagation strategy is normative. Every
implementation task SHALL conform to the strategy.

## 12.1 Error origin

Errors originate in the layer that detected the
underlying condition. The transport layer is the
originator of network errors, authentication errors,
and rate-limit errors. The validation layer is the
originator of parameter errors. The metadata layer is
the originator of reference errors. The trade layer is
the originator of trade errors. The storage layer is
the originator of filesystem errors. The normalisation
layer is the originator of response-coercion errors.

## 12.2 Error translation

A layer that receives an error from a lower layer
SHALL translate the error into the documented exception
type of the receiving layer. The translation records
the originating error in a documented `__cause__` or
equivalent attribute, so that the originating condition
remains accessible to the consumer.

## 12.3 Error propagation

Errors propagate upward through the layer chain. A
layer SHALL NOT swallow an error. A layer SHALL NOT
catch a documented exception and re-raise a less
informative exception unless the documentation
explicitly allows the re-mapping.

## 12.4 Error termination

Errors terminate at the SDK client layer. The client
layer raises the documented exception type to the
consumer. The consumer is responsible for catching the
exception and acting on it.

## 12.5 Logging responsibilities

A layer that detects a recoverable error logs a warning
at the documented level. A layer that detects a
non-recoverable error logs an error at the documented
level. The log record includes the documented fields.

## 12.6 Exception ownership

The exception hierarchy is owned by the `un_comtrade.errors`
module. The hierarchy is documented in the SDK
specification. A new exception type is added through a
recorded decision.

---

# 13. Configuration Architecture

The configuration architecture declares the configuration
sources and the configuration surface. The concrete
configuration values are recorded in the SDK
specification.

## 13.1 Configuration sources

The SDK reads configuration from the following sources,
in the order of precedence. The first source that
supplies a value wins.

- Explicit construction arguments.
- A configuration object passed at construction.
- Environment variables read at construction time.
- The SDK's default configuration.

The SDK SHALL NOT read configuration at import time.
The SDK SHALL NOT read configuration from global state.

## 13.2 Configuration categories

The configuration surface is partitioned into the
categories below. Each category is owned by a single
module and is documented in the SDK specification.

- **Authentication.** Subscription key, key rotation
  policy.
- **Transport.** Timeout, retry count, backoff
  schedule, proxy.
- **Caching.** Cache location, cache lifetime, cache
  invalidation policy.
- **Logging.** Log level, log format, log destination.
- **Pagination.** Page size, page cap.
- **Rate limit.** Requests per window, window length.
- **Recorded samples.** Sample directory, sample
  retention.

## 13.3 Configuration immutability

Configuration is bound at construction. A configuration
value is not mutated after construction except through
documented mutator methods on the configuration object.
The mutator methods are themselves documented and
versioned.

## 13.4 Configuration validation

The configuration is validated at construction. An
invalid configuration is rejected with a documented
configuration exception.

---

# 14. Extension Strategy

The extension strategy describes how future functionality
may be added without breaking the architecture.

## 14.1 Additional API endpoints

A new upstream API endpoint is added by adding a new
method to the client layer and a new dispatch in the
metadata or trade layer. The new method SHALL conform
to the documented interface contracts. The new method
is added in a minor version.

## 14.2 Additional metadata tables

A new reference table is added by adding a new query
helper to the metadata layer. The new helper SHALL
conform to the documented metadata contract. The new
helper is added in a minor version.

## 14.3 Additional exporters

A new export shape is added by adding a new exporter
to the export layer. The new exporter SHALL conform
to the documented export contract. The new exporter
is added in a minor version.

## 14.4 Additional storage engines

A new storage backend is added by adding a new storage
engine to the storage layer. The new engine SHALL
conform to the documented storage contract. The new
engine is added in a minor version.

## 14.5 Additional analytics

Analytics is outside the SDK boundary. The SDK does
not add analytics features. A consumer that requires
analytics builds the analytics subsystem on top of the
SDK.

## 14.6 Additional classification systems

A new classification system is added by adding a new
module under the metadata layer for the new system and
by extending the trade layer to accept the new
classification as a query parameter. The new
classification is added in a minor version.

## 14.7 Additional transport mechanisms

A new transport mechanism is added by adding a new
transport engine to the transport layer. The new
engine SHALL conform to the documented transport
contract. The new engine is added in a minor version.

## 14.8 Backward compatibility

Every extension listed in this section preserves
backward compatibility within a major version. A
breaking change is reserved for a major version
increment and is recorded in `DECISIONS.md`.

---

# 15. Architecture Constraints

The constraints below are normative prohibitions. A
change that violates a constraint is rejected by the
architectural review.

## 15.1 No business logic in transport

The transport layer SHALL NOT contain business logic.
The transport layer is responsible for issuing HTTP
requests and surfacing responses. Domain logic
belongs to the higher layers.

## 15.2 No direct API calls outside the SDK

A consumer SHALL NOT issue a direct call to the
upstream UN Comtrade API outside the SDK. The SDK is
the only supported way to access the upstream API
from a consumer.

## 15.3 No circular dependencies

Circular dependencies are prohibited. The architecture
is verified against the cycle rule at every
architectural review.

## 15.4 No cross-layer shortcuts

A layer that needs the capabilities of a non-adjacent
layer SHALL route the call through the intervening
layers. Direct cross-layer calls are prohibited.

## 15.5 No hidden state

A module SHALL NOT maintain state that is not
documented. Hidden state is a defect and SHALL be
corrected.

## 15.6 No implicit configuration

Configuration SHALL NOT be inferred from global
state, environment variables at import time, or
side effects. Configuration is explicit and is
documented.

## 15.7 No I/O at import time

The SDK SHALL NOT perform I/O at import time. All
I/O is deferred to construction time or to explicit
method calls.

## 15.8 No silent schema changes

A change in the upstream schema is reflected in the
normalisation layer and is recorded in
`CHANGELOG.md`. Silent schema changes are prohibited.

## 15.9 No undocumented public surface

A public class, function, or method SHALL be
documented. Undocumented public surface is a defect.

## 15.10 No swallowed exceptions

An exception that is caught SHALL be either re-raised
or replaced with a documented exception type. Silent
swallowing is prohibited.

---

# 16. Non-Functional Architecture

The non-functional expectations below bind every future
implementation task.

## 16.1 Maintainability

The SDK is structured to be maintainable. The layer
boundaries, the module boundaries, and the interface
contracts are documented. A maintainer who is new to
the project SHALL be able to locate the code that
implements a given behaviour within a single layer.

## 16.2 Extensibility

The SDK is structured to be extensible. Adding a new
endpoint, a new reference table, a new exporter, or
a new storage engine does not require changes outside
the affected layer, except through the documented
interface contracts.

## 16.3 Testability

The SDK is structured to be testable. Each layer is
testable in isolation. The test standard is recorded
in `012_TESTING_STANDARD.md`. The tests are
deterministic and fast except for the documented live
tests.

## 16.4 Observability

The SDK is structured to be observable. The logging
seam records structured log records at the documented
levels. The error-propagation strategy preserves the
originating error for the consumer. The configuration
surface records the runtime configuration for
post-mortem analysis.

## 16.5 Performance

The SDK is structured to be performant. The transport
layer is the only layer that performs network I/O and
is the primary contributor to latency. Caching and
pagination are first-class concerns and are documented
in the storage and trade specifications.

## 16.6 Reliability

The SDK is structured to be reliable. Retry with
exponential backoff, rate-limit detection, and
documented failure modes are first-class concerns.
The SDK does not silently swallow failures and does
not silently produce partial results.

## 16.7 Security

The SDK is structured to be secure. Authentication
material is held by the transport layer and is not
exposed to the higher layers. The SDK does not log
authentication material. The configuration surface
documents the security-sensitive options.

## 16.8 Portability

The SDK is structured to be portable. The supported
Python versions are recorded in
`000_PROJECT_CHARTER.md` section 6. The supported
operating systems are recorded in the SDK
specification. The SDK does not depend on
platform-specific features except through the
standard library.

---

# 17. Assumptions

The assumptions below are recorded for traceability.
An assumption that turns out to be false is recorded
in `DECISIONS.md` as a correction and is propagated
to the relevant specification documents.

## 17.1 Architectural assumptions

- The upstream UN Comtrade API continues to be
  operated by the United Nations Statistics Division
  on an Azure API Management gateway.
- The URL structure of the upstream API is stable
  enough to be modelled by the transport layer
  without requiring a per-version client.
- The response format of the upstream API is JSON
  for every endpoint in scope.
- The reference catalogues are stable enough to be
  cached for the duration of a release cycle.
- The classification systems (HS, SITC, BEC, EBOPS)
  continue to be operated in the form documented in
  the upstream reference tables.

## 17.2 Consumer assumptions

- Consumers are professional Python developers who
  understand the request-response model of HTTP.
- Consumers are willing to install the SDK through
  the standard Python package index.
- Consumers are willing to handle their own
  authentication material and not to commit it to
  source control.

## 17.3 Project assumptions

- The project is implemented by volunteers and does
  not receive a continuous budget.
- The maintainers are willing to add new endpoints
  on request but will not implement features that
  are outside the scope of the project.
- The architecture is reviewed at every release
  boundary.

## 17.4 Environment assumptions

- The supported Python versions are the ones recorded
  in `000_PROJECT_CHARTER.md` section 6.
- The networking environment of the consumer allows
  direct egress to the upstream gateway or is
  configured with a proxy whose details are passed
  to the SDK at construction time.

## 17.5 Distinguished from verified facts

The assumptions in this section are not verified
facts. They are accepted as the basis for the
architecture but are subject to correction. Verified
facts are recorded in the upstream documentation of
the UN Comtrade service and are referenced from the
API research and the API endpoint catalogue.

---

# 18. Open Questions

The questions below are recorded for future resolution.
An open question is not an excuse to delay work; it is
a recorded decision to defer the answer until the
relevant task is in flight.

- **OQ-A-001.** Should the layer dependency graph be
  reflected exactly in the package hierarchy, or
  should the models module be split into per-layer
  sub-packages? Owner: SDK specification.
- **OQ-A-002.** Should the storage layer be split into
  a cache module and a recorded-samples module, with
  each owning its own interface? Owner: storage
  specification.
- **OQ-A-003.** Should the retry helpers be a
  sub-module of the transport layer or a top-level
  module? Owner: SDK specification.
- **OQ-A-004.** Should the logging seam be a wrapper
  around the standard library logging module or a
  dedicated structured-logging implementation? Owner:
  coding standard and SDK specification.
- **OQ-A-005.** Should the SDK ship a synchronous
  client and an asynchronous client as separate
  top-level classes, or should a single client
  expose both modes? Owner: SDK specification.
- **OQ-A-006.** Should the validation layer reject
  parameters that the upstream API would also reject,
  or should it forward every parameter to the
  upstream API and surface the upstream error? Owner:
  validation specification.
- **OQ-A-007.** Should the normalisation layer apply
  documented default values, or should it leave
  absent fields absent and let the consumer decide?
  Owner: normalisation specification.
- **OQ-A-008.** Should the storage layer expose a
  public cache-invalidation method, or should cache
  invalidation be internal? Owner: storage
  specification.
- **OQ-A-009.** Should the architecture pre-declare
  the public exception type names, or should the
  exception hierarchy be defined in the SDK
  specification? Owner: SDK specification.
- **OQ-A-010.** Should the public interface expose a
  DataFrame handoff shape, a row-dict handoff shape,
  or both? Owner: SDK specification, in coordination
  with the data-analysis library decision.

---

# 19. Future Architecture

The future architecture describes the anticipated
evolution of the SDK after the first stable release.
The description is high-level; the detailed evolution
is the responsibility of the roadmap document.

## 19.1 Multi-version support

The SDK MAY evolve to support multiple versions of
the upstream API simultaneously. The support is
expressed as a versioned client whose transport layer
selects the appropriate URL template based on the
declared version.

## 19.2 Streaming interface

The SDK MAY evolve to expose a streaming interface
for very large responses. The streaming interface is
built on top of the documented interface contracts
and does not change the layer boundaries.

## 19.3 Plugin model

The SDK MAY evolve to expose a plugin model for
storage engines, exporters, and transport engines.
The plugin model is implemented as a documented
extension point in the relevant layer.

## 19.4 Multi-language bindings

The SDK MAY evolve to expose bindings for additional
programming languages. The bindings are generated
from the documented interface contracts and are not
the responsibility of this Python project.

## 19.5 Server-side components

The SDK SHALL NOT evolve to include server-side
components. The SDK is a client library. Server-side
components are the responsibility of separate
projects.

---

# End of document
