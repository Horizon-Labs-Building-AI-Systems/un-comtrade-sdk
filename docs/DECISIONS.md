```
Document ID
019

Title
Architecture Decision Register

Version
0.1.0

Status
LIVE

Created
2026-06-26T21:08:02Z

Last Updated
2026-06-26T21:08:02Z

Author
Codex

Project
UN Comtrade Python SDK

Dependencies
003_ARCHITECTURE.md

Supersedes
None
```

---

# 1. ADR Overview

## 1.1 Purpose

The Architecture Decision Register (the ADR) is
the permanent, append-only record of every approved
architectural and engineering decision made within
the project. The ADR is the source of truth for the
project's design rationale. The ADR supports:

- Architectural traceability.
- Decision history.
- Design rationale.
- Governance records.
- Future implementation guidance.

## 1.2 Scope

The ADR records every decision that affects:

- Architecture.
- Public interfaces.
- Data models.
- Implementation strategy.
- Infrastructure.
- Packaging.
- Project governance.

A decision is recorded in the ADR before the
decision is implemented. A decision that is not in
the ADR is not an approved decision.

## 1.3 Relationship to Architecture Specification

The Architecture Specification (`003_ARCHITECTURE.md`)
declares the high-level architecture. The ADR
records the individual decisions that compose the
architecture. The Architecture Specification is
the contract; the ADR is the record of the
decisions that produced the contract.

## 1.4 Relationship to Task Log

The Task Log (`docs/TASK_LOG.md`) records the
operational history of the project. A task that
produces a decision SHALL be recorded in the Task
Log and the resulting decision SHALL be recorded
in the ADR. The two documents are related but
distinct.

## 1.5 Relationship to Change Log

The Change Log (`docs/CHANGELOG.md`) records the
technical change history. A decision that produces
a change SHALL be recorded in the ADR and the
resulting change SHALL be recorded in the Change
Log. The two documents are related but distinct.

## 1.6 Relationship to Implementation Roadmap

The Implementation Roadmap (`016_IMPLEMENTATION_ROADMAP.md`)
declares the project phases. The ADR records the
decisions that compose each phase. The ADR is
updated as the project progresses through the
phases.

---

# 2. ADR Lifecycle

The standard ADR lifecycle is:

```
Proposed
    |
    v
Under Review
    |
    v
Accepted
    |
    v
Implemented
    |
    v
Superseded
    |
    v
Deprecated
    |
    v
Archived
```

## 2.1 Proposed

A decision is proposed when the decision is
described in an ADR. A proposed decision is open
for review.

## 2.2 Under Review

A decision is under review when the maintainers
are reviewing the proposal. A decision under review
MAY be revised based on the review.

## 2.3 Accepted

A decision is accepted when the maintainers have
approved the proposal. An accepted decision is
binding on the project. A decision that is
implemented without an accepted decision is a
defect.

## 2.4 Implemented

A decision is implemented when the decision has
been realised in the project. A decision that has
been implemented is in production. The verification
status is `Implemented`.

## 2.5 Superseded

A decision is superseded when a new decision has
replaced the previous decision. The superseded
decision is preserved in the ADR. The superseding
decision is the new binding decision.

## 2.6 Deprecated

A decision is deprecated when the decision is no
longer recommended but is still in production. A
deprecated decision is preserved in the ADR. A
deprecated decision is scheduled for supersession
or removal in a future release.

## 2.7 Archived

A decision is archived when the decision is no
longer in production. An archived decision is
preserved in the ADR for historical reference. An
archived decision SHALL NOT be deleted.

---

# 3. Decision Entry Standard

Every architectural decision SHALL follow the
template below. The template is normative. A
decision entry that does not follow the template
is invalid.

## 3.1 ADR ID

The ADR ID is a unique identifier of the decision.
The ADR ID SHALL be formatted as `ADR-NNNN`
where `NNNN` is a four-digit decimal sequence. The
ADR ID SHALL be assigned at the time the decision
is recorded. The ADR ID SHALL NOT be reused. The
ADR ID SHALL be monotonic within a major version
of the ADR.

## 3.2 Title

The title is a concise engineering decision. The
title SHALL be a single sentence. The title SHALL
describe the decision, not the rationale.

## 3.3 Date

The date is the ISO-8601 UTC timestamp of the
decision. The format is `YYYY-MM-DDTHH:MM:SSZ`. The
date is the timestamp at which the decision was
recorded in the ADR.

## 3.4 Status

The status is the lifecycle state of the decision.
The status SHALL be one of:

- Proposed.
- Under Review.
- Accepted.
- Implemented.
- Superseded.
- Deprecated.
- Archived.

## 3.5 Category

The category is the classification of the decision.
The category SHALL be one of:

- Architecture.
- SDK.
- Data Model.
- Metadata.
- Trade Layer.
- Infrastructure.
- ETL.
- Storage.
- Testing.
- Packaging.
- Documentation.
- Governance.
- Performance.
- Security.

## 3.6 Context

The context describes the engineering problem or
design challenge that the decision addresses. The
context SHALL be one to three paragraphs. The
context SHALL describe the problem, the forces,
and the constraints.

## 3.7 Decision

The decision states the chosen solution. The
decision SHALL be one to three sentences. The
decision SHALL be precise and unambiguous.

## 3.8 Alternatives Considered

The alternatives are the reasonable alternatives
that were evaluated. Each alternative SHALL be
documented with:

- **Advantages.** The benefits of the alternative.
- **Disadvantages.** The costs of the alternative.
- **Reason for rejection.** The reason the
  alternative was rejected.

## 3.9 Rationale

The rationale explains why the selected decision
is preferred. The rationale SHALL include:

- **Technical reasoning.** The technical argument
  for the decision.
- **Architectural impact.** The impact on the
  architecture of the SDK.
- **Long-term maintainability.** The impact on the
  long-term maintainability of the SDK.
- **Compatibility considerations.** The impact on
  the compatibility of the SDK.

## 3.10 Consequences

The consequences are the expected outcomes of the
decision. The consequences SHALL include:

- **Positive impacts.** The benefits of the
  decision.
- **Negative impacts.** The costs of the decision.
- **Trade-offs.** The trade-offs that the decision
  imposes.
- **Implementation implications.** The implications
  for the implementation.

## 3.11 Dependencies

The dependencies are the related artefacts. The
dependencies SHALL list:

- **Related specifications.** The specification
  documents that are affected by the decision.
- **Related ADRs.** The other ADRs that are affected
  by the decision.
- **Related tasks.** The tasks that are affected
  by the decision.
- **Related roadmap phases.** The roadmap phases
  that are affected by the decision.

## 3.12 Impact Assessment

The impact assessment lists the affected
components. The affected components MAY include
the SDK client, the metadata layer, the trade
layer, the ETL, the storage, the public API, the
testing, the packaging, and any other documented
component.

## 3.13 Backward Compatibility

The backward compatibility is the impact on the
backward compatibility of the SDK. The backward
compatibility SHALL be one of:

- **Compatible.** The decision preserves backward
  compatibility.
- **Breaking.** The decision is a breaking change.
- **Migration Required.** The decision requires a
  migration from a previous behaviour.
- **Not Applicable.** The decision does not affect
  backward compatibility.

The justification SHALL be recorded.

## 3.14 Verification Status

The verification status is the lifecycle status
of the decision's implementation. The verification
status SHALL be one of:

- **Planned.** The decision is planned but not yet
  implemented.
- **Verified.** The decision has been verified
  through tests.
- **Implemented.** The decision has been
  implemented in production.
- **Superseded.** The decision has been superseded
  by another decision.

## 3.15 Related Change Log Entries

The related Change Log entries are the
`CHG-NNNN` references that are affected by the
decision. A decision that does not affect a Change
Log entry SHALL record `None`.

## 3.16 Related Task Log Entries

The related Task Log entries are the `TASK-NNN`
references that produced the decision. A decision
that does not affect a Task Log entry SHALL record
`None`.

---

# 4. Decision Categories

The decision categories are the standard
classifications of decisions. The category
drives the impact assessment and the review
priority.

## 4.1 Architecture

An architecture decision is a decision that
affects the responsibilities of a layer, the
dependencies between layers, the public interface
of a documented module, or the precedence of
documents.

## 4.2 API Design

An API design decision is a decision that affects
the public method surface, the parameter contracts,
or the return contracts.

## 4.3 Data Model

A data model decision is a decision that affects
the canonical entities, the canonical fields, the
canonical datatypes, the canonical enumerations,
or the canonical relationships.

## 4.4 Infrastructure

An infrastructure decision is a decision that
affects the cross-cutting services (configuration,
retry, timeout, logging, cache, progress, resume,
error, request tracking, diagnostics, security).

## 4.5 Performance

A performance decision is a decision that affects
the latency, the throughput, or the memory
consumption of the SDK.

## 4.6 Security

A security decision is a decision that affects
the security posture of the SDK (API key handling,
logging restrictions, configuration isolation,
transport security).

## 4.7 Packaging

A packaging decision is a decision that affects
the package layout, the versioning, the
distribution, the dependencies, or the CLI.

## 4.8 Testing

A testing decision is a decision that affects the
test categories, the quality gates, the coverage,
or the release validation.

## 4.9 Documentation

A documentation decision is a decision that
affects the documentation set, the changelog, the
task log, the decisions log, the context, or any
other document in the repository.

## 4.10 Governance

A governance decision is a decision that affects
the project governance, the change control, the
release process, the support policy, or the
deprecation policy.

---

# 5. Decision Governance

The decision governance declares the rules that
govern the approval, the implementation, and the
supersession of decisions.

## 5.1 Pre-Implementation Documentation

Every architectural decision SHALL be documented
in the ADR before the decision is implemented. A
decision that is implemented without an ADR entry
is a defect.

## 5.2 Approval

A decision is approved when the maintainers have
reviewed the ADR and have agreed to the decision.
A decision that is not approved SHALL NOT be
implemented.

## 5.3 Binding

An accepted decision is binding on the project.
The implementation SHALL conform to the decision.
A deviation from the decision is a defect.

## 5.4 Supersession

A decision may be superseded by a new decision.
The superseding decision SHALL be recorded in a
new ADR. The superseded decision SHALL be marked
`Superseded` and SHALL remain in the ADR for
historical reference.

## 5.5 No Deletion

A decision SHALL NOT be deleted from the ADR. A
decision that has been archived SHALL remain in
the ADR for the lifetime of the project.

---

# 6. Supersession Policy

The supersession policy declares how decisions
evolve. A decision may be superseded when the
decision is no longer optimal, when the upstream
service has changed, or when the consumer's
requirements have changed.

## 6.1 Replacement Process

A decision is superseded by a new ADR. The new
ADR SHALL:

- Reference the superseded ADR.
- Describe the reason for the supersession.
- Document the migration path from the old
  decision to the new decision.
- Mark the old ADR as `Superseded`.

## 6.2 Version Updates

A supersession MAY be published in a minor or
major version. A supersession that is a breaking
change SHALL be published in a major version. A
supersession that is backward compatible MAY be
published in a minor version.

## 6.3 Impact Analysis

The supersession SHALL include an impact
analysis. The impact analysis SHALL record the
affected components, the affected consumers, and
the migration expectations.

## 6.4 Migration Expectations

A consumer that upgrades across a supersession
SHALL be able to migrate the consumer code by
following the documented migration path. The
migration path SHALL be published in the
documentation.

## 6.5 Historical Preservation

The superseded decision SHALL remain in the ADR
for the lifetime of the project. The historical
context of the decision SHALL be preserved.

---

# 7. Cross-Reference Rules

Every ADR SHALL reference the related artefacts.
The cross-references ensure complete traceability
between the decision, the documentation, the
task, the change, and the release.

## 7.1 Related Specifications

Every ADR SHALL reference the related specification
documents. The specification documents are
identified by their document ID (`000` through
`016`).

## 7.2 Related Roadmap Phase

Every ADR SHALL reference the related roadmap
phase. The roadmap phase is one of the phases
declared in `016_IMPLEMENTATION_ROADMAP.md` §3.

## 7.3 Related Tasks

Every ADR SHALL reference the related tasks. The
tasks are identified by their Task ID (`TASK-NNN`).

## 7.4 Related Change Log Entries

Every ADR SHALL reference the related Change Log
entries. The Change Log entries are identified by
their `CHG-NNNN` reference.

## 7.5 Related Implementation

Every ADR SHALL reference the related implementation
when the implementation is available. The
implementation is identified by the source file
path and the line number.

---

# 8. Decision Update Rules

The ADR SHALL be updated whenever a significant
decision is made, revised, or superseded.

## 8.1 Update Triggers

The ADR SHALL be updated when:

- A major architectural choice is proposed.
- A specification introduces a new architectural
  principle.
- A breaking change is approved.
- A previous decision is superseded.
- A governance rule changes.
- A new layer is added to the architecture.
- A new module is added to the package layout.
- A new endpoint is added to the endpoint catalog.
- A new entity is added to the data model.
- A new method is added to the SDK specification.
- A new error type is added to the error hierarchy.
- A new configuration parameter is added to the
  configuration surface.

## 8.2 No Bypass

No architectural change MAY bypass the ADR. An
architectural change that is not in the ADR is not
an approved change. An architectural change that is
in the ADR is the canonical record of the change.

## 8.3 No Rewriting

An ADR entry SHALL NOT be rewritten. An ADR entry
that contains an error SHALL be superseded by a
new ADR entry that records the correction. The
original ADR entry SHALL remain in the ADR.

## 8.4 No Deletion

An ADR entry SHALL NOT be deleted. An ADR entry
that is recorded in the ADR SHALL remain in the
ADR for the lifetime of the project.

---

# 9. Archive Policy

The archive policy declares how the ADR is
preserved for the long term.

## 9.1 Retention

The ADR is retained for the lifetime of the
project. The ADR is never deleted. The ADR is
never rewritten. The ADR is never truncated. The
ADR is preserved in the version control system.

## 9.2 Historical Preservation

The ADR is preserved in the version control
system. The ADR is preserved in the documentation
site. The ADR is the canonical record of the
project's architectural history.

## 9.3 Superseded Decisions

A superseded decision SHALL remain in the ADR
for the lifetime of the project. The superseding
decision SHALL reference the superseded decision.
The superseded decision SHALL be marked
`Superseded` and SHALL remain readable.

## 9.4 Deprecated Decisions

A deprecated decision SHALL remain in the ADR
for the lifetime of the project. The deprecated
decision SHALL be marked `Deprecated` and SHALL
remain readable. The deprecated decision SHALL be
scheduled for removal in a future release.

## 9.5 Archive Strategy

The ADR is archived at the end of every release
cycle. The archived ADR is preserved in the
version control system. The archived ADR is
preserved in the documentation site. The archived
ADR is the canonical record of the project's
architectural history at the time of the archive.

---

# 10. Initial Decisions

The initial decisions record the architectural
choices made during the Documentation Phase
(Phase 0). The decisions are recorded in
chronological order.

---

## ADR-0001 — Top-Level Package Name

- **Title.** The top-level package name SHALL be
  `un_comtrade`; the distribution name SHALL be
  `un-comtrade-sdk`; the CLI name SHALL be
  `un-comtrade`.
- **Date.** 2026-06-26T19:51:52Z.
- **Status.** Accepted.
- **Category.** Architecture.
- **Context.** The SDK needs a Python import name, a
  distribution name on PyPI, and a CLI entry point
  name. The names must be distinct to satisfy the
  Python and PyPI conventions.
- **Decision.** The import name is `un_comtrade`. The
  distribution name is `un-comtrade-sdk`. The CLI
  name is `un-comtrade`.
- **Alternatives Considered.**
  - Single name `uncomtrade` for all three.
    - Advantages: simple.
    - Disadvantages: doesn't satisfy the Python
      and PyPI conventions; the CLI name is hard
      to type.
    - Reason for rejection: violates the
      documented conventions.
  - Single name `un_comtrade` for import and
    distribution, `ucs` for CLI.
    - Advantages: short CLI.
    - Disadvantages: cryptic CLI name.
    - Reason for rejection: poor consumer
      experience.
- **Rationale.** The import name follows the Python
  convention (snake_case). The distribution name
  follows the PyPI convention (hyphenated). The CLI
  name is the most prominent form. The three names
  are related but distinct, and each follows the
  convention of its medium.
- **Consequences.** Consumers install the package
  with `un-comtrade-sdk`, import it as `un_comtrade`,
  and run the CLI as `un-comtrade`. The three
  names are documented in the README.
- **Dependencies.** Related specification:
  `003_ARCHITECTURE.md` §9.1.
- **Impact Assessment.** Public API, packaging,
  CLI.
- **Backward Compatibility.** Not Applicable.
- **Verification Status.** Verified.
- **Related Change Log Entries.** None.
- **Related Task Log Entries.** TASK-004.

---

## ADR-0002 — Layered Architecture (10 Layers)

- **Title.** The SDK SHALL be organised into 10
  logical layers with strict downward dependency
  direction; no layer skipping; no circular
  dependencies.
- **Date.** 2026-06-26T19:51:52Z.
- **Status.** Accepted.
- **Category.** Architecture.
- **Context.** The SDK needs a layered decomposition
  that allows a maintainer to reason about the
  responsibilities of each layer and the
  dependencies between layers.
- **Decision.** The SDK is organised into 10
  layers: L1 Transport, L2 SDK Client, L3 Metadata,
  L4 Trade, L5 Validation, L6 Normalisation, L7
  Export, L8 Storage, L9 Analytics, L10 Application.
  The dependency direction is strictly downward.
  L9 and L10 are out of SDK scope (reference only).
- **Alternatives Considered.**
  - 3 layers (Transport, Domain, Storage).
    - Advantages: simpler.
    - Disadvantages: too coarse; the metadata and
      trade concerns are coupled.
    - Reason for rejection: insufficient
      separation of concerns.
  - 5 layers (Transport, Client, Domain,
    Storage, External).
    - Advantages: middle ground.
    - Disadvantages: validation and normalisation
      concerns are mixed.
    - Reason for rejection: the validation and
      normalisation concerns are distinct.
  - 10 layers (this decision).
    - Advantages: clear separation of concerns;
      each layer has a single responsibility.
    - Disadvantages: more layers to manage.
    - Reason for rejection: N/A (selected).
- **Rationale.** The 10-layer decomposition
  provides a clear separation of concerns without
  the overhead of a 3-layer model. Each layer has
  a single responsibility. The dependency direction
  is enforced by the architectural review.
- **Consequences.** A change in one layer does not
  require a coordinated change in another layer.
  A consumer can reason about a layer in isolation.
  The package layout mirrors the layer structure.
- **Dependencies.** Related specification:
  `003_ARCHITECTURE.md` §4, §5, §6.
- **Impact Assessment.** All layers.
- **Backward Compatibility.** Not Applicable.
- **Verification Status.** Verified.
- **Related Change Log Entries.** None.
- **Related Task Log Entries.** TASK-004.

---

## ADR-0003 — Snake_Case Field Naming in Canonical Model

- **Title.** The canonical data model SHALL use
  snake_case for field names regardless of the
  upstream casing.
- **Date.** 2026-06-26T20:07:45Z.
- **Status.** Accepted.
- **Category.** Data Model.
- **Context.** The upstream uses camelCase for
  field names (`reporterCode`, `fobvalue`).
  Different layers (Python, JSON, SQL) prefer
  different conventions. The canonical model
  must be stable across layers.
- **Decision.** The canonical model uses
  snake_case for every field name. The
  normalisation layer performs the casing
  translation.
- **Alternatives Considered.**
  - camelCase throughout.
    - Advantages: matches the upstream.
    - Disadvantages: violates Python conventions;
      awkward at the JSON boundary.
    - Reason for rejection: poor consumer
      experience.
  - snake_case throughout.
    - Advantages: matches Python conventions;
      consistent across the SDK.
    - Disadvantages: requires a normalisation step.
    - Reason for rejection: N/A (selected).
  - Mixed casing.
    - Advantages: no translation required.
    - Disadvantages: inconsistent.
    - Reason for rejection: poor consumer
      experience.
- **Rationale.** snake_case is the Python
  convention. The canonical model is a Python
  artefact. The normalisation layer absorbs the
  cost of the casing translation. The casing is
  documented in `006_DATA_MODEL.md` §13.1.
- **Consequences.** Consumers see snake_case in
  every layer of the SDK. The normalisation layer
  has 38 explicit field renames in
  `006_DATA_MODEL.md` §13.1. The translation is
  tested.
- **Dependencies.** Related specification:
  `006_DATA_MODEL.md` §13.1.
- **Impact Assessment.** Normalisation layer,
  validation layer, export layer, storage layer.
- **Backward Compatibility.** Compatible (the
  consumer never sees the upstream casing).
- **Verification Status.** Verified.
- **Related Change Log Entries.** None.
- **Related Task Log Entries.** TASK-007.

---

## ADR-0004 — Pagination by Splitting on Period

- **Title.** The trade layer SHALL paginate large
  queries by splitting on the `period` dimension;
  the trade layer SHALL NOT invent a continuation
  token.
- **Date.** 2026-06-26T20:22:04Z.
- **Status.** Accepted.
- **Category.** Trade Layer.
- **Context.** The upstream API does not support a
  documented pagination protocol. The trade layer
  needs a strategy for retrieving results that
  exceed the per-call cap.
- **Decision.** The trade layer paginates by
  splitting a multi-year query into multiple
  single-year queries, each containing at most 12
  periods. The trade layer does not invent a
  continuation token.
- **Alternatives Considered.**
  - Cursor-based pagination.
    - Advantages: standard pagination pattern.
    - Disadvantages: the upstream does not support
      a documented cursor.
    - Reason for rejection: the upstream does not
      support a cursor.
  - Page-number pagination.
    - Advantages: simple.
    - Disadvantages: the upstream does not support
      a documented page number.
    - Reason for rejection: the upstream does not
      support page numbers.
  - Period-based pagination.
    - Advantages: works with the upstream; the
      `period` dimension is the only documented
      query dimension that supports a comma-
      separated list of values.
    - Disadvantages: the pagination is implicit.
    - Reason for rejection: N/A (selected).
- **Rationale.** The `period` dimension is the
  only documented query dimension that supports a
  comma-separated list of values (up to 12). The
  pagination strategy is the only documented way
  to paginate. The trade layer records the
  pagination strategy in `009_TRADE_LAYER_SPEC.md`
  §5.
- **Consequences.** A consumer that issues a
  multi-year query receives the results as a single
  `Response` after the trade layer has aggregated
  the per-year responses. The pagination is
  transparent to the consumer.
- **Dependencies.** Related specification:
  `009_TRADE_LAYER_SPEC.md` §5.
- **Impact Assessment.** Trade layer.
- **Backward Compatibility.** Not Applicable.
- **Verification Status.** Verified.
- **Related Change Log Entries.** None.
- **Related Task Log Entries.** TASK-010.

---

## ADR-0005 — Record Cap: 500 (Preview) and 250,000 (Authenticated)

- **Title.** The public preview endpoints SHALL be
  capped at 500 records per call; the authenticated
  endpoints SHALL be capped at 250,000 records per
  call; the async delivery SHALL be capped at
  2,500,000 records per call.
- **Date.** 2026-06-26T19:56:43Z.
- **Status.** Accepted.
- **Category.** API Design.
- **Context.** The upstream API has documented
  per-call caps. The SDK needs to respect the caps
  and expose them to the consumer.
- **Decision.** The SDK SHALL enforce the caps
  declared by the upstream. The default `maxRecords`
  is the cap. A consumer that requests a higher
  value is silently capped.
- **Alternatives Considered.**
  - Reject requests that exceed the cap.
    - Advantages: explicit.
    - Disadvantages: divergent from the upstream
      behaviour.
    - Reason for rejection: divergent from the
      upstream behaviour.
  - Silently cap.
    - Advantages: matches the upstream behaviour.
    - Disadvantages: the consumer may not realise
      that the result is truncated.
    - Reason for rejection: N/A (selected).
  - Pass the cap through.
    - Advantages: simple.
    - Disadvantages: the consumer may not know the
      cap.
    - Reason for rejection: poor consumer
      experience.
- **Rationale.** The silent cap matches the upstream
  behaviour. The default `maxRecords` is the cap.
  The consumer MAY request a higher value; the
  trade layer SHALL cap the request. The behaviour
  is documented in `007_SDK_SPECIFICATION.md` §4
  and `009_TRADE_LAYER_SPEC.md` §5.3.
- **Consequences.** The trade layer caps every
  request. The cap is documented. A consumer that
  requires more than 250,000 records SHALL use the
  async delivery or the bulk download.
- **Dependencies.** Related specifications:
  `004_API_RESEARCH.md` §8, `005_API_ENDPOINT_CATALOG.md`
  T1, P1.
- **Impact Assessment.** Trade layer.
- **Backward Compatibility.** Compatible.
- **Verification Status.** Verified.
- **Related Change Log Entries.** None.
- **Related Task Log Entries.** TASK-005.

---

## ADR-0006 — India Code 699 (Not 356)

- **Title.** The current reporter code for India
  is 699; the historical code 356 (pre-1975) is
  expired and SHALL NOT be used.
- **Date.** 2026-06-26T19:56:43Z.
- **Status.** Accepted.
- **Category.** Data Model.
- **Context.** The reporters catalogue lists two
  codes for India: 699 (current) and 356
  (historical, expired 1974-12-31). A consumer
  that uses 356 will receive 0 records.
- **Decision.** The canonical model SHALL use 699
  as the current reporter code for India. The
  canonical model SHALL preserve 356 as the
  historical code. The validation layer SHALL
  reject queries that use 356 as the reporter
  code, with a deprecation warning that points
  to 699.
- **Alternatives Considered.**
  - Use 356 as the default.
    - Advantages: matches the historical record.
    - Disadvantages: returns 0 records.
    - Reason for rejection: returns 0 records.
  - Use 699 as the default.
    - Advantages: returns the documented records.
    - Disadvantages: requires a documented migration
      from 356.
    - Reason for rejection: N/A (selected).
- **Rationale.** Verified by live request. The
  current code is 699. The historical code is
  356. The validation layer rejects 356 with a
  clear error. The behaviour is documented in
  `006_DATA_MODEL.md` §2.1.
- **Consequences.** A consumer that uses 356
  receives a clear error pointing to 699. A
  consumer that uses 699 receives the documented
  records.
- **Dependencies.** Related specifications:
  `004_API_RESEARCH.md` §10, `006_DATA_MODEL.md` §2.1.
- **Impact Assessment.** Metadata layer, trade
  layer, validation layer.
- **Backward Compatibility.** Compatible (the
  consumer never sees 356 as a valid code).
- **Verification Status.** Verified.
- **Related Change Log Entries.** None.
- **Related Task Log Entries.** TASK-005.

---

## ADR-0007 — Reference Catalogue Lazy Load with Persistent Cache

- **Title.** The metadata layer SHALL load reference
  catalogues lazily on first use; the catalogues
  SHALL be cached in memory for a resource-specific
  lifetime; the catalogues SHALL be persisted to
  disk as JSON files.
- **Date.** 2026-06-26T20:18:28Z.
- **Status.** Accepted.
- **Category.** Metadata.
- **Context.** The reference catalogues are large
  (up to 8,262 entries for the combined HS list)
  and rarely change. A consumer that instantiates
  the SDK should not pay the cost of loading every
  catalogue.
- **Decision.** The metadata layer loads a
  reference catalogue on the first call that
  requests it. The catalogue is cached in memory
  for a resource-specific lifetime (30 days for
  static, 7 days for slow-changing, 1-30 days for
  versioned, 1 day for schema, 1 day for
  operational). The catalogue is persisted to
  the configured cache directory as a JSON file.
  The persisted catalogue is loaded on startup if
  present.
- **Alternatives Considered.**
  - Eager load at startup.
    - Advantages: simple.
    - Disadvantages: slow startup; memory overhead
      for unused catalogues.
    - Reason for rejection: poor consumer
      experience.
  - Lazy load without persistence.
    - Advantages: simple; no disk I/O.
    - Disadvantages: cache is lost on process
      restart.
    - Reason for rejection: poor consumer
      experience.
  - Lazy load with persistence.
    - Advantages: fast access; persistent across
      restarts.
    - Disadvantages: more complex.
    - Reason for rejection: N/A (selected).
- **Rationale.** Lazy load minimises the startup
  cost. Persistence enables the cache to survive
  a process restart. The resource-specific lifetime
  balances freshness with performance. The
  behaviour is documented in
  `008_METADATA_LAYER_SPEC.md` §7 and §8.
- **Consequences.** The first call to a metadata
  method is slower than subsequent calls. The
  cache is loaded from disk on startup. The
  cache lifetime is configurable.
- **Dependencies.** Related specification:
  `008_METADATA_LAYER_SPEC.md` §7, §8.
- **Impact Assessment.** Metadata layer, storage
  layer.
- **Backward Compatibility.** Compatible.
- **Verification Status.** Verified.
- **Related Change Log Entries.** None.
- **Related Task Log Entries.** TASK-009.

---

## ADR-0008 — Retry Policy: Exponential Backoff with 3 Attempts

- **Title.** The SDK SHALL retry on transient
  failures with exponential backoff: 1s initial,
  2x multiplier, 60s cap, 3 attempts.
- **Date.** 2026-06-26T20:25:58Z.
- **Last Revised.** 2026-06-27T21:30:00Z.
- **Status.** Accepted.
- **Category.** Infrastructure.
- **Context.** The upstream API may return 5xx or
  429 responses. The SDK needs a retry policy
  that recovers from transient failures without
  overwhelming the upstream.
- **Decision.** The SDK retries on timeout, HTTP 429,
  HTTP 500, HTTP 502, HTTP 503, and HTTP 504.
  Validation errors are NEVER retried. The backoff
  schedule is 1s initial, 2x multiplier, 60s cap,
  3 attempts. The total maximum wait time is
  approximately 7 seconds. The retry policy is
  configurable. When the upstream returns a
  `Retry-After` header, the SDK honours the header.
- **Alternatives Considered.**
  - Fixed backoff.
    - Advantages: simple.
    - Disadvantages: may overwhelm the upstream.
    - Reason for rejection: poor upstream
      interaction.
  - Exponential backoff with jitter.
    - Advantages: avoids thundering herd.
    - Disadvantages: more complex; the consumer
      cannot predict the total wait time.
    - Reason for rejection: more complex than
      necessary for the MVP.
  - Exponential backoff with 5 attempts.
    - Advantages: maximum resilience.
    - Disadvantages: total maximum wait time of
      31 seconds is too long for the consumer
      experience.
    - Reason for rejection: revised to 3 attempts
      per Architecture Freeze Question Q11.
- **Rationale.** The exponential backoff is the
  standard pattern. The default of 3 attempts is
  conservative and predictable. The total maximum
  wait time of 7 seconds is acceptable for the
  consumer experience. The retry budget is
  configurable per Architecture Freeze Question Q15.
- **Consequences.** The SDK retries on transient
  failures only. Validation errors fail fast.
  The total maximum wait time is approximately 7
  seconds. A future version MAY add jitter.
- **Dependencies.** Related specification:
  `010_INFRASTRUCTURE_SPEC.md` §4.
- **Impact Assessment.** Infrastructure layer.
- **Backward Compatibility.** Breaking for any
  consumer that depended on 5 retry attempts.
  Migration: configure `retry_attempts=5` to
  restore the previous behaviour.
- **Verification Status.** Verified.
- **Related Change Log Entries.** CHG-0013.
- **Related Task Log Entries.** TASK-011, TASK-022.

---

## ADR-0009 — Conflict Resolution: Latest Wins

- **Title.** When two records have the same composite
  primary key, the ETL layer SHALL retain the
  record with the latest `ref_period_id`; the other
  record SHALL be dropped and recorded as a
  warning.
- **Date.** 2026-06-26T20:29:56Z.
- **Status.** Accepted.
- **Category.** ETL.
- **Context.** A trade record's composite primary
  key is unique within the dataset. When two
  records have the same composite primary key,
  the ETL layer must resolve the conflict.
- **Decision.** The ETL layer retains the record
  with the latest `ref_period_id`. The other
  record is dropped and recorded as a warning.
  The default conflict resolution policy is
  "latest wins". A consumer MAY override the
  policy through a configuration parameter.
- **Alternatives Considered.**
  - First record wins.
    - Advantages: simple.
    - Disadvantages: prefers stale data.
    - Reason for rejection: poor data quality.
  - Latest record wins.
    - Advantages: prefers fresh data.
    - Disadvantages: depends on the `ref_period_id`
      being reliable.
    - Reason for rejection: N/A (selected).
  - Merge fields.
    - Advantages: preserves all the data.
    - Disadvantages: complex; the merge rule is
      domain-specific.
    - Reason for rejection: too complex for the
      MVP.
- **Rationale.** The "latest wins" policy prefers
  fresh data. The `ref_period_id` is upstream-
  defined and is reliable. The policy is
  documented in `011_ETL_SPECIFICATION.md` §7.3.
- **Consequences.** A duplicate is resolved by
  retaining the latest record. The dropped record
  is recorded as a warning. A consumer MAY
  override the policy.
- **Dependencies.** Related specification:
  `011_ETL_SPECIFICATION.md` §7.
- **Impact Assessment.** ETL layer.
- **Backward Compatibility.** Compatible.
- **Verification Status.** Verified.
- **Related Change Log Entries.** None.
- **Related Task Log Entries.** TASK-012.

---

## ADR-0010 — Documentation-First Methodology

- **Title.** The project SHALL follow a
  documentation-first methodology: every
  implementation task SHALL be preceded by the
  relevant specification document; the
  documentation is the source of truth.
- **Date.** 2026-06-26T19:20:00Z.
- **Status.** Accepted.
- **Category.** Governance.
- **Context.** The project needs a methodology that
  minimises rework, ensures the implementation
  matches the design, and preserves the
  rationale.
- **Decision.** The project follows a
  documentation-first methodology. Every
  specification document is produced and approved
  before the corresponding implementation begins.
  The implementation follows the documentation.
  A change to the implementation without a
  corresponding change to the documentation is a
  defect.
- **Alternatives Considered.**
  - Code-first methodology.
    - Advantages: faster initial progress.
    - Disadvantages: rework is expensive; the
      documentation may be out of date.
    - Reason for rejection: poor long-term
      maintainability.
  - Test-first methodology.
    - Advantages: high test coverage.
    - Disadvantages: the design may be wrong; the
      tests are also wrong.
    - Reason for rejection: not a substitute for
      the design.
  - Documentation-first methodology.
    - Advantages: the design is explicit; the
      implementation follows the design; the
      documentation is the source of truth.
    - Disadvantages: slower initial progress.
    - Reason for rejection: N/A (selected).
- **Rationale.** The documentation-first methodology
  is the contract. The implementation is the
  fulfilment of the contract. A change to the
  contract is a change to the documentation. The
  methodology is recorded in
  `000_PROJECT_CHARTER.md` §11 and in
  `001_EXECUTION_PROTOCOL.md` §1.
- **Consequences.** Every implementation task is
  preceded by a specification. The documentation
  set is comprehensive. The implementation
  follows the documentation. A change to the
  implementation requires a change to the
  documentation.
- **Dependencies.** Related specifications:
  `000_PROJECT_CHARTER.md` §11, `001_EXECUTION_PROTOCOL.md` §1.
- **Impact Assessment.** All layers.
- **Backward Compatibility.** Not Applicable.
- **Verification Status.** Verified.
- **Related Change Log Entries.** None.
- **Related Task Log Entries.** TASK-001.

---

## ADR-0011 — Public Preview Parameter Casing

- **Title.** The preview endpoint accepts the
  reporter parameter as `reportercode` (lowercase);
  the authenticated endpoint accepts it as
  `reporterCode` (camelCase); the SDK SHALL
  normalise the casing internally.
- **Date.** 2026-06-26T19:56:43Z.
- **Status.** Accepted.
- **Category.** API Design.
- **Context.** The preview endpoint is case-
  sensitive on the `reportercode` parameter. The
  authenticated endpoint is case-insensitive on
  the `reporterCode` parameter. The SDK needs to
  present a single casing to the consumer.
- **Decision.** The SDK normalises the casing
  internally. The public SDK method accepts the
  consumer's parameter as `reporter_code`
  (snake_case). The transport layer converts
  the snake_case parameter to the upstream's
  casing (`reportercode` for preview,
  `reporterCode` for authenticated).
- **Alternatives Considered.**
  - Require the consumer to use the upstream's
    casing.
    - Advantages: simple.
    - Disadvantages: divergent casing; poor
      consumer experience.
    - Reason for rejection: poor consumer
      experience.
  - Normalise the casing internally.
    - Advantages: a single casing for the
      consumer; the SDK handles the upstream's
      casing.
    - Disadvantages: more complex.
    - Reason for rejection: N/A (selected).
- **Rationale.** The consumer SHALL see a single
  casing. The SDK normalises the casing
  internally. The behaviour is documented in
  `004_API_RESEARCH.md` §5.5 and in
  `007_SDK_SPECIFICATION.md` §4.
- **Consequences.** The consumer always uses
  `reporter_code`. The SDK handles the upstream's
  casing. The SDK is portable across the preview
  and the authenticated endpoints.
- **Dependencies.** Related specifications:
  `004_API_RESEARCH.md` §5.5, `007_SDK_SPECIFICATION.md` §4.
- **Impact Assessment.** Transport layer, SDK
  client layer, validation layer.
- **Backward Compatibility.** Compatible.
- **Verification Status.** Verified.
- **Related Change Log Entries.** None.
- **Related Task Log Entries.** TASK-005.

---

## ADR-0012 — SDK Error Hierarchy: 13 Exception Types

- **Title.** The SDK SHALL expose 13 exception
  types under a base `ComtradeError`: Authentication,
  RateLimit, Validation, Reference, Trade, Network,
  Timeout, Upstream, EndpointNotFound, Storage,
  Configuration, Unknown, plus the base.
- **Date.** 2026-06-26T20:12:59Z.
- **Status.** Accepted.
- **Category.** SDK.
- **Context.** The SDK needs a typed exception
  hierarchy that the consumer can catch. A generic
  `Exception` is not sufficient.
- **Decision.** The SDK exposes 13 exception types
  under a base `ComtradeError`. The exception
  hierarchy is documented in
  `007_SDK_SPECIFICATION.md` §7. The exception
  types are owned by the `un_comtrade.errors`
  module.
- **Alternatives Considered.**
  - Single `ComtradeError` exception.
    - Advantages: simple.
    - Disadvantages: the consumer cannot catch a
      specific failure mode.
    - Reason for rejection: poor consumer
      experience.
  - 13 exception types.
    - Advantages: the consumer can catch a
      specific failure mode; the hierarchy is
      documented; the categories are aligned with
      the architecture.
    - Disadvantages: more exception types to
      maintain.
    - Reason for rejection: N/A (selected).
- **Rationale.** A typed exception hierarchy
  enables the consumer to catch a specific
  failure mode. The categories are aligned with
  the architecture and with the error propagation
  strategy. The hierarchy is documented in
  `007_SDK_SPECIFICATION.md` §7 and in
  `010_INFRASTRUCTURE_SPEC.md` §10.
- **Consequences.** The consumer can catch a
  specific failure mode. The exception types are
  documented. The exception hierarchy is part of
  the public surface.
- **Dependencies.** Related specifications:
  `007_SDK_SPECIFICATION.md` §7, `010_INFRASTRUCTURE_SPEC.md` §10.
- **Impact Assessment.** All layers.
- **Backward Compatibility.** Compatible (the
  exception types are added in a minor version).
- **Verification Status.** Verified.
- **Related Change Log Entries.** None.
- **Related Task Log Entries.** TASK-008.

---

## ADR-0013 — 100-Character Line Length and 500-Line Module Size

- **Title.** The maximum line length SHALL be 100
  characters; the maximum module size SHALL be 500
  lines.
- **Date.** 2026-06-26T20:43:52Z.
- **Status.** Accepted.
- **Category.** Documentation.
- **Context.** The SDK needs enforceable engineering
  standards for code style and module size. A
  100-character line length is wider than the
  PEP 8 default (79) but is a common modern
  choice. A 500-line module size is a balance
  between cohesion and file count.
- **Decision.** The maximum line length is 100
  characters. The maximum module size is 500
  lines. A module that exceeds the limit SHALL be
  split into smaller modules. The standards are
  documented in `015_CODING_STANDARD.md` §3 and
  §11.
- **Alternatives Considered.**
  - PEP 8 default (79 characters, no module size
    limit).
    - Advantages: standard.
    - Disadvantages: the line length is narrow for
      modern code; the module size limit is
      implicit.
    - Reason for rejection: too narrow.
  - Black default (88 characters, no module size
    limit).
    - Advantages: common modern choice.
    - Disadvantages: too narrow for the project;
      no module size limit.
    - Reason for rejection: too narrow.
  - 100 characters + 500 lines.
    - Advantages: common modern choice; module
      size is explicit.
    - Disadvantages: more complex than the
      alternatives.
    - Reason for rejection: N/A (selected).
- **Rationale.** The 100-character line length is
  a common modern choice. The 500-line module
  size is a balance between cohesion and file
  count. The standards are documented and
  enforced by the linting framework. The
  behaviour is recorded in
  `015_CODING_STANDARD.md` §3 and §11.
- **Consequences.** The linting framework enforces
  the standards. A module that exceeds the limit
  is split. The consumer can override the
  standards through the configuration object.
- **Dependencies.** Related specification:
  `015_CODING_STANDARD.md` §3, §11.
- **Impact Assessment.** SDK source code, linting
  framework.
- **Backward Compatibility.** Compatible.
- **Verification Status.** Verified.
- **Related Change Log Entries.** None.
- **Related Task Log Entries.** TASK-016.

---

## ADR-0014 — SemVer 2.0.0 with 12-Month Support Window

- **Title.** The SDK SHALL follow Semantic
  Versioning 2.0.0; each major version SHALL be
  supported for at least 12 months from the
  release date; the deprecation period SHALL be
  at least one minor release.
- **Date.** 2026-06-26T20:40:34Z.
- **Status.** Accepted.
- **Category.** Packaging.
- **Context.** The SDK needs a versioning strategy
  and a support policy. A consumer that pins to a
  major version needs to know how long the major
  version is supported.
- **Decision.** The SDK follows Semantic
  Versioning 2.0.0. Each major version is
  supported for at least 12 months from the
  release date. The deprecation period is at
  least one minor release. The strategy is
  documented in `014_PACKAGING_SPECIFICATION.md`
  §4 and §5.
- **Alternatives Considered.**
  - Date-based versioning (CalVer).
    - Advantages: explicit.
    - Disadvantages: breaks the consumer's
      expectations of API stability.
    - Reason for rejection: incompatible with the
      consumer's API stability expectations.
  - SemVer with 6-month support window.
    - Advantages: faster deprecation.
    - Disadvantages: insufficient time for the
      consumer to migrate.
    - Reason for rejection: insufficient.
  - SemVer with 12-month support window.
    - Advantages: explicit; sufficient time for
      the consumer to migrate; well-known.
    - Disadvantages: longer maintenance burden.
    - Reason for rejection: N/A (selected).
- **Rationale.** SemVer 2.0.0 is the standard. The
  12-month support window is a balance between
  consumer time-to-migrate and maintainer
  maintenance burden. The deprecation period is
  sufficient for the consumer to plan a migration.
  The policy is documented in
  `014_PACKAGING_SPECIFICATION.md` §4 and §5.
- **Consequences.** A consumer that pins to a
  major version has at least 12 months to migrate.
  The maintainer publishes patch releases for
  critical and high defects during the support
  window. The deprecation period is at least one
  minor release.
- **Dependencies.** Related specification:
  `014_PACKAGING_SPECIFICATION.md` §4, §5.
- **Impact Assessment.** Packaging, releases,
  support.
- **Backward Compatibility.** Compatible.
- **Verification Status.** Verified.
- **Related Change Log Entries.** None.
- **Related Task Log Entries.** TASK-015.

---

## ADR-0015 — API Key in Query Parameter

- **Title.** The SDK SHALL send the API key as the
  `subscription-key` query parameter; the SDK
  SHALL NOT log the API key or the full URL; the
  SDK SHALL NOT include the API key in an error
  message.
- **Date.** 2026-06-26T20:12:59Z.
- **Status.** Accepted.
- **Category.** Security.
- **Context.** The upstream accepts the API key in
  two locations: the `subscription-key` query
  parameter and the `Ocp-Apim-Subscription-Key`
  header. The SDK needs to send the key without
  exposing it in logs, in error messages, or in
  diagnostic reports.
- **Decision.** The SDK sends the key as the
  `subscription-key` query parameter (the form
  exercised by the official `comtradeapicall`
  package). The SDK redacts the key from every
  log record, every error message, and every
  diagnostic report. The SDK redacts the full URL
  from every log record (the URL contains the key
  as a query parameter).
- **Alternatives Considered.**
  - Send the key in the HTTP header.
    - Advantages: the key is not in the URL.
    - Disadvantages: the URL is shorter; the
      consumer can log the URL without exposing
      the key.
    - Reason for rejection: divergent from the
      official `comtradeapicall` package.
  - Send the key in the query parameter.
    - Advantages: matches the official
      `comtradeapicall` package; the key is in
      the URL.
    - Disadvantages: the URL contains the key; the
      SDK must redact the URL.
    - Reason for rejection: N/A (selected).
  - Both.
    - Advantages: the consumer can choose.
    - Disadvantages: ambiguous; more complex.
    - Reason for rejection: ambiguous.
- **Rationale.** The query parameter form is the
  canonical form exercised by the official
  `comtradeapicall` package. The redaction of
  the key and the full URL is documented in
  `010_INFRASTRUCTURE_SPEC.md` §6.4 and §16.4.
- **Consequences.** A consumer that logs the full
  URL will not see the key. A diagnostic report
  will not contain the key. The consumer MAY
  override the redaction policy through a
  configuration parameter (not in MVP).
- **Dependencies.** Related specifications:
  `010_INFRASTRUCTURE_SPEC.md` §6.4, §16.4.
- **Impact Assessment.** Security, logging,
  diagnostics.
- **Backward Compatibility.** Compatible.
- **Verification Status.** Verified.
- **Related Change Log Entries.** None.
- **Related Task Log Entries.** TASK-008.

---

## ADR-0016 — Phase 0 → Phase 1 Transition Procedure

- **Title.** The transition from the Documentation
  Phase (Phase 0) to the SDK Foundation Phase
  (Phase 1) SHALL follow the 6-step procedure
  declared in `016_IMPLEMENTATION_ROADMAP.md` §16.
- **Date.** 2026-06-26T20:47:39Z.
- **Status.** Proposed.
- **Category.** Governance.
- **Context.** The project needs a documented
  transition procedure from the Documentation
  Phase to the Implementation Phase. The
  transition is the most important transition in
  the project.
- **Decision.** The transition SHALL follow the
  6-step procedure: verification, decision, first
  action (package skeleton), first smoke test
  (instantiate `ComtradeClient`), first
  documentation update, first communication. The
  procedure is documented in
  `016_IMPLEMENTATION_ROADMAP.md` §16.
- **Alternatives Considered.**
  - Begin implementation without a recorded
    transition.
    - Advantages: faster.
    - Disadvantages: undocumented transition;
      lack of accountability.
    - Reason for rejection: poor governance.
  - Wait for external approval before
    transitioning.
    - Advantages: external validation.
    - Disadvantages: external dependencies.
    - Reason for rejection: not necessary for
      internal projects.
  - Follow the 6-step procedure.
    - Advantages: documented; accountable;
      verifiable.
    - Disadvantages: more steps.
    - Reason for rejection: N/A (selected).
- **Rationale.** The 6-step procedure ensures that
  the transition is documented, accountable, and
  verifiable. The procedure is the same for every
  future phase transition. The procedure is
  recorded in `016_IMPLEMENTATION_ROADMAP.md` §16.
- **Consequences.** The transition is documented.
  The first action is the package skeleton. The
  first smoke test verifies the SDK constructor.
  The first documentation update records the
  transition. The first communication announces
  the transition to the consumers.
- **Dependencies.** Related specification:
  `016_IMPLEMENTATION_ROADMAP.md` §16.
- **Impact Assessment.** Project governance.
- **Backward Compatibility.** Not Applicable.
- **Verification Status.** Planned.
- **Related Change Log Entries.** None.
- **Related Task Log Entries.** TASK-017.

---

# 11. Recommendation for Transitioning from Documentation Phase to Implementation Phase

The Documentation Phase (Phase 0) is now complete.
The 22 documents in the `docs/` tree (17 numbered
specifications + CHANGELOG + TASK_LOG + DECISIONS
+ 002_CONTEXT) constitute the contract for the
SDK. The 16 architectural decisions (ADR-0001
through ADR-0016) record the rationale for the
contract. The 10 change entries (CHG-0001 through
CHG-0010) record the changes that produced the
contract. The 19 task entries (TASK-001 through
TASK-019) record the operational history.

The transition from Phase 0 to Phase 1 is the
most important transition in the project. The
transition SHALL be governed by the 6-step
procedure declared in
`016_IMPLEMENTATION_ROADMAP.md` §16 and recorded
in ADR-0016.

## 11.1 Verification

The transition SHALL be verified by the following
procedure:

1. Every required document in the `docs/` tree
   exists and is approved by the maintainers.
2. Every required section in every document
   exists and is consistent with the other
   documents.
3. Every cross-reference between documents is
   valid.
4. Every open question is recorded in the
   relevant document.
5. The changelog and `DECISIONS.md` are up to
   date.
6. The `TASK_LOG.md` is up to date.
7. The `README.md` is up to date and points to
   the documentation.

## 11.2 Decision

The transition SHALL be approved by a recorded
decision in `DECISIONS.md`. The decision SHALL
record:

- The date of the transition.
- The phase that is being entered (Phase 1).
- The exit criteria of Phase 0 that are
  satisfied.
- The entry criteria of Phase 1 that are
  satisfied.
- The maintainers who approved the transition.

## 11.3 First Action

The first action of Phase 1 is to create the
package skeleton. The package skeleton includes
the `un_comtrade/` top-level package and the
`pyproject.toml` file. The package skeleton is
the first verifiable artefact of Phase 1.

## 11.4 First Smoke Test

The first smoke test of Phase 1 is to instantiate
the SDK constructor. The test verifies that the
`ComtradeClient` class is importable, that the
constructor accepts the documented parameters, and
that the instance exposes the documented public
surface.

## 11.5 First Documentation Update

The first documentation update of Phase 1 is to
update `CHANGELOG.md`, `TASK_LOG.md`, and
`DECISIONS.md` with the transition. The update
marks the start of the implementation phase.

## 11.6 First Communication

The first communication of Phase 1 is to inform
the consumers that the implementation phase has
started. The communication includes the version
of the first internal alpha, the expected date of
the first public beta, and the expected date of
the first stable release.

## 11.7 Architectural Foundation

The architectural foundation is now complete. The
10-layer decomposition, the 25-entity canonical
data model, the 46-method SDK surface, the 13-
exception hierarchy, the 11-component
infrastructure, the 9-stage ETL pipeline, the 7-
target storage layer, the 9-category test
strategy, the 6-channel distribution model, and
the 10-phase implementation roadmap constitute a
comprehensive architectural foundation. The
foundation is documented, approved, and ready
for implementation.

The 16 architectural decisions record the
rationale for the foundation. Every future
implementation task SHALL conform to the
foundation. Every future change to the foundation
SHALL be recorded in the ADR before the change is
committed. Every future change to the
implementation SHALL be recorded in the
changelog and the task log.

The project is ready to enter Phase 1.

---

# Part II — Approved Architectural Decisions (Architecture Freeze, 2026-06-27)

The following decisions were produced by the Product Owner and the
Architecture Reviewer during the architecture freeze. They are
authoritative. Where a decision supersedes an earlier ADR, that
supersession is recorded explicitly.

## ADR-0017 — Python 3.11+ Minimum, 3.13 Maximum Tested

- **Title.** The SDK SHALL target Python 3.11 or later as the
  minimum supported version. The maximum tested version is the
  latest stable release (currently Python 3.13).
- **Date.** 2026-06-27T21:30:00Z.
- **Status.** Accepted.
- **Category.** Project Foundation.
- **Context.** Architecture Freeze Questions Q1 and Q2 require a
  concrete Python version matrix to enable implementation and
  testing.
- **Decision.** Minimum supported version is Python 3.11.
  Maximum tested version is the latest stable release at
  implementation time. The full support matrix is documented
  separately.
- **Rationale.** Python 3.11+ offers modern typing support
  (`Self`, improved generics), excellent ecosystem compatibility,
  and a long support lifecycle through October 2027.
- **Consequences.** Consumers on Python 3.10 or earlier SHALL
  upgrade to a supported Python version.
- **Dependencies.** Related specification:
  `000_PROJECT_CHARTER.md` §6, `014_PACKAGING_SPECIFICATION.md`
  §5, `015_CODING_STANDARD.md` §3.
- **Impact Assessment.** Project-wide.
- **Backward Compatibility.** The transition from "minimum at
  most recent security-maintained release" to "3.11+" is
  documented in CHG-0013.
- **Verification Status.** Verified.
- **Related Change Log Entries.** CHG-0013.
- **Related Task Log Entries.** TASK-022.

---

## ADR-0018 — `httpx` as Standard HTTP Client

- **Title.** The SDK SHALL use `httpx` for HTTP transport
  instead of `requests`.
- **Date.** 2026-06-27T21:30:00Z.
- **Status.** Accepted.
- **Category.** Project Foundation.
- **Context.** Architecture Freeze Question Q3 changed the HTTP
  client choice from `requests` (recorded in
  `003_ARCHITECTURE.md` §10.1 and `014_PACKAGING_SPECIFICATION.md`
  §6.2) to `httpx`.
- **Decision.** The SDK uses `httpx` for all HTTP transport.
  The synchronous API is used in the MVP; the asynchronous API
  is reserved for Phase 2.
- **Alternatives Considered.**
  - `requests`. Disadvantages: no first-class async API; older
    timeout handling. Reason for rejection: superseded by Q3.
  - `urllib3` directly. Disadvantages: lower-level API; more
    boilerplate. Reason for rejection: ergonomics.
  - `aiohttp`. Disadvantages: async-only; would force a
    different shape for MVP. Reason for rejection: out of scope.
- **Rationale.** `httpx` offers a modern API, sync/async support
  from the same library, better timeout handling, and is
  future-proof.
- **Consequences.** All transport code is rewritten against
  `httpx`. The `requests` dependency is removed from the
  required-dependencies list.
- **Dependencies.** Related specification:
  `003_ARCHITECTURE.md` §10.1, `014_PACKAGING_SPECIFICATION.md`
  §6.2, `010_INFRASTRUCTURE_SPEC.md` §3, §5.5.
- **Impact Assessment.** Transport layer.
- **Backward Compatibility.** No external compatibility impact
  (the dependency is hidden from consumers).
- **Verification Status.** Verified.
- **Related Change Log Entries.** CHG-0013.
- **Related Task Log Entries.** TASK-022.

---

## ADR-0019 — Async Support Deferred to Phase 2

- **Title.** Async support is not part of the MVP. The SDK
  exposes a synchronous interface in v1.
- **Date.** 2026-06-27T21:30:00Z.
- **Status.** Accepted.
- **Category.** Project Foundation.
- **Context.** Architecture Freeze Question Q4 confirmed the
  MVP scope.
- **Decision.** The MVP exposes only a synchronous interface.
  Async support is a Phase 2 feature.
- **Rationale.** Keeping the MVP synchronous reduces the API
  surface area, simplifies the testing matrix, and avoids
  double-implementing every method.
- **Consequences.** Async consumers SHALL either run the sync
  SDK in a thread pool or wait for Phase 2.
- **Dependencies.** Related specification:
  `007_SDK_SPECIFICATION.md` §3.
- **Impact Assessment.** Public API surface.
- **Backward Compatibility.** Reserved.
- **Verification Status.** Verified.
- **Related Change Log Entries.** CHG-0013.
- **Related Task Log Entries.** TASK-022.

---

## ADR-0020 — Standard Library JSON Serialisation

- **Title.** The SDK SHALL use the Python standard library
  `json` module for all serialisation. No additional
  serialisation dependency is added.
- **Date.** 2026-06-27T21:30:00Z.
- **Status.** Accepted.
- **Category.** Project Foundation.
- **Context.** Architecture Freeze Question Q5.
- **Decision.** The SDK uses `json.dumps`, `json.loads`, and
  `json.JSONEncoder` subclasses only.
- **Rationale.** The Python standard library is sufficient for
  all documented canonical models. Adding a serialisation
  dependency would inflate the required dependency set.
- **Consequences.** The SDK depends only on the standard
  library for serialisation.
- **Dependencies.** Related specification:
  `006_DATA_MODEL.md` §14, `014_PACKAGING_SPECIFICATION.md`
  §6.2.
- **Impact Assessment.** Data Model layer.
- **Backward Compatibility.** N/A.
- **Verification Status.** Verified.
- **Related Change Log Entries.** CHG-0013.
- **Related Task Log Entries.** TASK-022.

---

## ADR-0021 — Public SDK Contract (Canonical Models, Normalised Fields, Enums)

- **Title.** The SDK exposes only canonical models. API field
  names are normalised to Pythonic snake_case. Timestamps are
  normalised to UTC. Enums are used for Trade Flow, Frequency,
  Transport Mode, and Classification.
- **Date.** 2026-06-27T21:30:00Z.
- **Status.** Accepted.
- **Category.** Public SDK Contract.
- **Context.** Architecture Freeze Questions Q6 through Q10
  codify the SDK's public surface contract.
- **Decision.**
  - The SDK does NOT expose raw API responses (Q6).
  - SDK models do NOT mirror the API; canonical models are
    used (Q7).
  - API field names are NOT preserved; they are normalised to
    snake_case (Q8). Example: `reporterCode` becomes
    `reporter_id`.
  - All timestamps are normalised to UTC internally (Q9).
  - Enums are used for Trade Flow, Frequency, Transport Mode,
    and Classification (Q10).
- **Rationale.** Canonical models insulate consumers from
  upstream schema changes. Normalised field names and UTC
  timestamps reduce consumer-side surprises. Enums surface
  the closed-set nature of the upstream codes.
- **Consequences.** Consumers MUST use the canonical field
  names. Raw responses are not available.
- **Dependencies.** Related specifications:
  `003_ARCHITECTURE.md` §4, `006_DATA_MODEL.md`,
  `007_SDK_SPECIFICATION.md`, `008_METADATA_LAYER_SPEC.md`,
  `009_TRADE_LAYER_SPEC.md`.
- **Impact Assessment.** All public API.
- **Backward Compatibility.** N/A (greenfield SDK).
- **Verification Status.** Verified.
- **Related Change Log Entries.** CHG-0013.
- **Related Task Log Entries.** TASK-022.

---

## ADR-0022 — Retryable Error Set

- **Title.** The retry policy SHALL retry on timeout, HTTP 429,
  HTTP 500, HTTP 502, HTTP 503, and HTTP 504. Validation errors
  SHALL NEVER be retried.
- **Date.** 2026-06-27T21:30:00Z.
- **Status.** Accepted.
- **Category.** Retry Strategy.
- **Context.** Architecture Freeze Question Q13 specifies the
  retryable error set. Question Q14 specifies that validation
  errors fail fast.
- **Decision.** The retry budget is consumed on the retryable
  errors listed above. Validation errors (`UnprocessableEntity`,
  `BadRequest`, `RateLimitError` raised client-side) fail fast
  and never consume the retry budget.
- **Rationale.** Validation errors indicate a programming bug
  in the consumer code. Retrying them wastes time and budget.
  The retryable set covers the transient-failure surface of
  the upstream.
- **Consequences.** Consumer code with bad parameters receives
  a fast failure with a precise error.
- **Dependencies.** Related specification:
  `010_INFRASTRUCTURE_SPEC.md` §4.
- **Impact Assessment.** Infrastructure layer.
- **Backward Compatibility.** N/A.
- **Verification Status.** Verified.
- **Related Change Log Entries.** CHG-0013.
- **Related Task Log Entries.** TASK-022.

---

## ADR-0023 — Timeout Policy

- **Title.** The SDK exposes three timeout categories: a
  default request timeout of 30 seconds, a metadata timeout
  of 15 seconds, and a large-download timeout of 300 seconds.
  All timeouts are configurable.
- **Date.** 2026-06-27T21:30:00Z.
- **Status.** Accepted.
- **Category.** Timeout Policy.
- **Context.** Architecture Freeze Questions Q16 through Q20.
- **Decision.**
  - Default request timeout: 30 seconds (Q16).
  - Large download timeout: 300 seconds (5 minutes) (Q17).
  - Metadata timeout: 15 seconds (Q18).
  - All timeouts are configurable (Q19).
  - The timeout exception is a custom SDK `TimeoutError`
    (Q20). The underlying exception (e.g.
    `httpx.TimeoutException`) is preserved as context.
- **Rationale.** Distinct timeouts prevent a slow metadata
  fetch from blocking a large download and vice versa.
  Configurability gives consumers control over their
  latency budget.
- **Consequences.** Consumers MAY override each timeout
  independently.
- **Dependencies.** Related specification:
  `010_INFRASTRUCTURE_SPEC.md` §5.
- **Impact Assessment.** Infrastructure layer.
- **Backward Compatibility.** N/A.
- **Verification Status.** Verified.
- **Related Change Log Entries.** CHG-0013.
- **Related Task Log Entries.** TASK-022.

---

## ADR-0024 — Caching Policy (Metadata Only)

- **Title.** The SDK caches metadata. The SDK does NOT cache
  trade responses. The cache lives in the user cache directory.
  The default refresh is manual. The cache survives process
  restarts.
- **Date.** 2026-06-27T21:30:00Z.
- **Status.** Accepted.
- **Category.** Caching.
- **Context.** Architecture Freeze Questions Q21 through Q25.
- **Decision.**
  - Metadata is cached always (Q21).
  - Trade responses are NOT cached (Q22). Optional response
    caching is reserved for a future version.
  - Default metadata refresh is manual; automatic refresh is
    optional future behaviour (Q23).
  - Cache location is the user cache directory, never the
    repository (Q24). The default location follows the
    platform convention.
  - The cache survives process restarts (Q25).
- **Rationale.** Trade data is large, time-sensitive, and
  often re-fetched for legitimate reasons. Caching it risks
  serving stale records. Metadata is small, slow-changing,
  and benefits substantially from caching.
- **Consequences.** Trade-layer consumers receive a fresh
  response on every call.
- **Dependencies.** Related specifications:
  `008_METADATA_LAYER_SPEC.md` §7, §8;
  `009_TRADE_LAYER_SPEC.md` §17;
  `010_INFRASTRUCTURE_SPEC.md` §7.
- **Impact Assessment.** Trade layer, Metadata layer.
- **Backward Compatibility.** The previous design's "7-day
  trade response cache" is removed; consumers SHALL use the
  storage layer for persistence.
- **Verification Status.** Verified.
- **Related Change Log Entries.** CHG-0013.
- **Related Task Log Entries.** TASK-022.

---

## ADR-0025 — Logging Policy

- **Title.** The SDK uses the Python standard library
  `logging` framework. The default level is `WARNING`. HTTP
  request details are logged only at `DEBUG`. API keys are
  always redacted. Structured logging is supported by design
  but the initial implementation uses standard logging only.
- **Date.** 2026-06-27T21:30:00Z.
- **Status.** Accepted.
- **Category.** Logging.
- **Context.** Architecture Freeze Questions Q26 through Q30.
- **Decision.**
  - Logging framework: Python standard `logging` (Q26).
  - Default log level: `WARNING` (Q27).
  - HTTP request details: `DEBUG` only, never default (Q28).
  - API keys: never logged; always redacted (Q29).
  - Structured logging: supported by design; standard logging
    initially (Q30). Future versions MAY add a structured
    handler behind an extension point.
- **Rationale.** The standard library covers all current
  logging needs. The default level is conservative so that
  the SDK is silent by default. API-key redaction is
  non-negotiable.
- **Consequences.** Consumers MAY swap in their own logging
  configuration. The SDK never emits secrets.
- **Dependencies.** Related specification:
  `010_INFRASTRUCTURE_SPEC.md` §6.
- **Impact Assessment.** Infrastructure layer.
- **Backward Compatibility.** N/A.
- **Verification Status.** Verified.
- **Related Change Log Entries.** CHG-0013.
- **Related Task Log Entries.** TASK-022.

---

## ADR-0026 — Metadata Layer Invariants (Atomic, Validated, Unique, Case-Insensitive)

- **Title.** The metadata layer SHALL auto-initialise on first
  use; downloads SHALL be atomic; versions SHALL be tracked;
  consumers SHALL be able to force a refresh; validation SHALL
  occur before persistence; duplicates SHALL be removed;
  searches SHALL be case-insensitive; partial downloads SHALL
  roll back; normalisation SHALL occur in the layer; canonical
  names SHALL be exposed.
- **Date.** 2026-06-27T21:30:00Z.
- **Status.** Accepted.
- **Category.** Metadata Layer.
- **Context.** Architecture Freeze Questions Q31 through Q40.
- **Decision.** Every question from Q31 to Q40 is accepted as
  binding. The layer:
  - Auto-initialises metadata on first SDK use (Q31).
  - Uses atomic downloads (Q32).
  - Tracks metadata versions locally (Q33).
  - Exposes an explicit `refresh_metadata()` method (Q34).
  - Validates every catalogue before persistence (Q35).
  - Removes duplicate records (Q36).
  - Exposes case-insensitive search (Q37).
  - Rolls back partial downloads completely (Q38).
  - Normalises inside the layer; raw data never leaves (Q39).
  - Exposes canonical field names only (Q40).
- **Rationale.** These invariants guarantee that consumers
  always see a consistent, validated, normalised view of the
  metadata.
- **Consequences.** The metadata layer exposes a richer
  interface (`refresh_metadata`, `search`) than the previous
  draft.
- **Dependencies.** Related specification:
  `008_METADATA_LAYER_SPEC.md` §5, §6, §7, §9.
- **Impact Assessment.** Metadata layer.
- **Backward Compatibility.** N/A.
- **Verification Status.** Verified.
- **Related Change Log Entries.** CHG-0013.
- **Related Task Log Entries.** TASK-022.

---

## ADR-0027 — Trade Layer Semantics (Unified Model, Empty Collections, Pagination Hidden, Resume-Ready)

- **Title.** The trade layer uses a unified model for all
  frequencies; empty responses return empty collections;
  parameters are validated client-side; large downloads
  expose progress; batch processing continues on failure;
  partial success is reported; duplicates are removed;
  records reference canonical metadata; pagination is hidden
  by default; the design is resumable.
- **Date.** 2026-06-27T21:30:00Z.
- **Status.** Accepted.
- **Category.** Trade Layer.
- **Context.** Architecture Freeze Questions Q41 through Q50.
- **Decision.** Every question from Q41 to Q50 is accepted as
  binding. The layer:
  - Uses one unified model for annual and monthly data; the
    frequency is an attribute (Q41).
  - Returns an empty collection, not an exception, on empty
    responses (Q42).
  - Validates parameters client-side before issuing a call
    (Q43).
  - Exposes progress reporting for large downloads (Q44).
  - Continues batch processing on failure and reports the
    summary (Q45).
  - Returns partial success results with success/failure
    summaries (Q46).
  - Removes duplicate trade records automatically (Q47).
  - Replaces raw identifiers with canonical metadata
    references (Q48).
  - Hides pagination from consumers; consumers MAY override
    (Q49).
  - Designs for resumable downloads; implementation deferred
    (Q50).
- **Rationale.** These semantics give consumers a clean,
  deterministic interface. Hiding pagination removes the
  burden of cursor management. Resumability is a design goal
  even though the implementation lands later.
- **Consequences.** The trade-layer contract is enriched.
- **Dependencies.** Related specification:
  `009_TRADE_LAYER_SPEC.md` §6, §7, §9, §13.
- **Impact Assessment.** Trade layer.
- **Backward Compatibility.** N/A.
- **Verification Status.** Verified.
- **Related Change Log Entries.** CHG-0013.
- **Related Task Log Entries.** TASK-022.

---

## ADR-0028 — Canonical Data Model Invariants (Decimal Money, ISO-8601 Dates, Stable Names, Immutable Records)

- **Title.** Trade monetary values use `Decimal`; dates use
  ISO-8601; missing values remain null; unknown enumeration
  values are preserved; derived values are computed not stored;
  canonical field names are stable; schema changes are isolated
  to the normalisation layer; provenance is included on every
  record; canonical records are immutable.
- **Date.** 2026-06-27T21:30:00Z.
- **Status.** Accepted.
- **Category.** Canonical Data Model.
- **Context.** Architecture Freeze Questions Q51 through Q60.
- **Decision.** Every question from Q51 to Q60 is accepted as
  binding. The data model:
  - Preserves semantic identifier types from the API; does not
    coerce unnecessarily (Q51).
  - Uses `Decimal` for trade monetary values (Q52).
  - Uses ISO-8601 dates (Q53).
  - Preserves missing values as null; never invents defaults
    (Q54).
  - Preserves unknown enumeration values with raw upstream
    value for traceability (Q55).
  - Does NOT store derived values alongside source values
    (Q56).
  - Treats canonical field names as part of the public
    contract (Q57).
  - Isolates upstream schema changes to the normalisation
    layer (Q58).
  - Includes provenance (source endpoint, retrieval
    timestamp, API version) on every record (Q59).
  - Treats canonical models as immutable read-only value
    objects (Q60).
- **Rationale.** `Decimal` avoids floating-point precision
  loss for money. Immutability simplifies the consumer
  contract. Provenance enables reproducibility.
- **Consequences.** The data model is more rigorous. Storage
  consumers MUST use Decimal-aware readers.
- **Dependencies.** Related specification:
  `006_DATA_MODEL.md` §14.
- **Impact Assessment.** All layers.
- **Backward Compatibility.** N/A.
- **Verification Status.** Verified.
- **Related Change Log Entries.** CHG-0013.
- **Related Task Log Entries.** TASK-022.

---

## ADR-0029 — Storage Layer (DuckDB Default, Parquet Default Export, Logical Partitioning, Schema Validation)

- **Title.** The SDK stores only canonical data. DuckDB is the
  default analytical backend. Parquet is the default export
  format for large datasets. CSV remains supported. JSON
  exports preserve canonical field names. Datasets are
  partitioned logically by reporter, year, and frequency. All
  storage adapters expose a common interface. Schema
  compatibility is validated before writing. Storage
  specifications are implementation-independent.
- **Date.** 2026-06-27T21:30:00Z.
- **Status.** Accepted.
- **Category.** Storage.
- **Context.** Architecture Freeze Questions Q61 through Q70.
- **Decision.** Every question from Q61 to Q70 is accepted as
  binding. The storage layer:
  - Stores only canonical data (Q61).
  - Uses DuckDB as the primary analytical backend (Q62).
  - Treats PostgreSQL as an optional adapter (Q63).
  - Uses Parquet as the default export format for large
    datasets (Q64).
  - Continues to support CSV (Q65).
  - Preserves canonical field names in JSON exports (Q66).
  - Partitions datasets logically by reporter, year, and
    frequency (Q67).
  - Exposes a common storage-adapter interface (Q68).
  - Validates schema compatibility before writing (Q69).
  - Defines behaviour in the specification, not the
    implementation, beyond approved targets (Q70).
- **Rationale.** DuckDB gives embedded analytical power.
  Parquet is interoperable across the data ecosystem.
  Logical partitioning scales with dataset size. A common
  interface allows future adapters without changing higher
  layers.
- **Consequences.** DuckDB becomes a default target; the
  previous "JSON + CSV + Parquet" MVP-only configuration
  is widened to include DuckDB.
- **Dependencies.** Related specification:
  `012_STORAGE_SPECIFICATION.md` §3.
- **Impact Assessment.** Storage layer.
- **Backward Compatibility.** N/A.
- **Verification Status.** Verified.
- **Related Change Log Entries.** CHG-0013.
- **Related Task Log Entries.** TASK-022.

---

## ADR-0030 — Testing & Quality (Public-API Unit Tests, Live-API Integration Suite, Versioned Mocks, No 100% Coverage)

- **Title.** Every public SDK method has a unit test. Integration
  tests use the live API in a dedicated suite. Mock responses
  are versioned. Regression tests are mandatory before every
  release. Documentation examples are tested. Performance
  testing is separate from CI. Contract tests detect upstream
  schema changes. Code coverage is high but not 100%. Every
  bug fix includes a regression test. Release candidates
  require full test execution.
- **Date.** 2026-06-27T21:30:00Z.
- **Status.** Accepted.
- **Category.** Testing & Quality.
- **Context.** Architecture Freeze Questions Q71 through Q80.
- **Decision.** Every question from Q71 to Q80 is accepted as
  binding. The testing layer:
  - Requires a unit test for every public SDK method (Q71).
  - Uses the live API only in a dedicated integration suite;
    core tests use deterministic fixtures (Q72).
  - Versions mock responses with API versions (Q73).
  - Requires regression validation before every release
    (Q74).
  - Tests documentation examples (Q75).
  - Runs performance tests separately from CI (Q76).
  - Detects upstream schema changes via contract tests
    (Q77).
  - Aims for high public-interface coverage, NOT 100% (Q78).
  - Requires a regression test with every bug fix (Q79).
  - Requires full test execution for every release candidate
    (Q80).
- **Rationale.** Quality over speed. Live-API integration
  tests are valuable but flaky; isolating them prevents false
  failures. Versioned mocks keep tests deterministic.
- **Consequences.** The test suite has two tiers: core
  (deterministic) and integration (live). CI runs core; live
  tests run on a separate schedule.
- **Dependencies.** Related specification:
  `013_TESTING_STANDARD.md` §2, §12.
- **Impact Assessment.** Testing layer.
- **Backward Compatibility.** N/A.
- **Verification Status.** Verified.
- **Related Change Log Entries.** CHG-0013.
- **Related Task Log Entries.** TASK-022.

---

## ADR-0031 — Packaging & Distribution (SemVer, PyPI, CLI in Same Package, No Implementation Before Documentation)

- **Title.** SemVer is mandatory. PyPI is the primary
  distribution channel. Both wheels and source distributions
  are published. Optional dependencies are grouped into
  extras. The CLI is included in the same package. The CLI
  exposes only high-value operations. Documentation versions
  with releases. Release notes are mandatory. Backward
  compatibility is preserved within a major version.
  Implementation is forbidden before documentation approval.
- **Date.** 2026-06-27T21:30:00Z.
- **Status.** Accepted.
- **Category.** Packaging & Distribution.
- **Context.** Architecture Freeze Questions Q81 through Q90.
- **Decision.** Every question from Q81 to Q90 is accepted as
  binding.
- **Rationale.** SemVer and PyPI are the Python ecosystem
  standards. Including the CLI in the same package reduces
  distribution complexity. Documentation-first prevents
  drift.
- **Consequences.** The CLI lives under
  `un_comtrade.cli`; the `un-comtrade` console script is
  registered. Every public API change requires a
  documentation update before merge.
- **Dependencies.** Related specification:
  `014_PACKAGING_SPECIFICATION.md` §1, §2, §5.
- **Impact Assessment.** Packaging layer.
- **Backward Compatibility.** N/A.
- **Verification Status.** Verified.
- **Related Change Log Entries.** CHG-0013.
- **Related Task Log Entries.** TASK-022.

---

## ADR-0032 — Documentation Requirements

- **Title.** Every public SDK method is documented; docs are
  generated from source; examples exist for every public API;
  docs follow versioned releases; deprecated APIs remain
  documented; migration guides accompany breaking releases;
  architecture diagrams are maintained; reference and
  conceptual guides are separate; changelog entries link to
  ADRs; documentation updates are required for every public
  API change.
- **Date.** 2026-06-27T21:30:00Z.
- **Status.** Accepted.
- **Category.** Documentation.
- **Context.** Architecture Freeze Questions Q91 through Q100.
- **Decision.** Every question from Q91 to Q100 is accepted as
  binding.
- **Rationale.** Documentation is part of the contract.
  Generated docs prevent drift. Versioned docs give consumers
  an authoritative reference for each release.
- **Consequences.** The documentation build is part of the
  release process. Every public-API PR includes a docs
  update.
- **Dependencies.** Related specification:
  `015_CODING_STANDARD.md` §8, `013_TESTING_STANDARD.md`
  §15.
- **Impact Assessment.** Documentation layer.
- **Backward Compatibility.** N/A.
- **Verification Status.** Verified.
- **Related Change Log Entries.** CHG-0013.
- **Related Task Log Entries.** TASK-022.

---

## ADR-0033 — CI/CD & Release Governance

- **Title.** PRs run automated checks; releases come from
  tags; artifacts are reproducible; dependency updates are
  manually reviewed; documentation validation is in CI; RCs
  require manual approval; CI does not publish to PyPI
  directly; version numbers are manually controlled; release
  notes are generated from the changelog; releases are
  reproducible from Git history.
- **Date.** 2026-06-27T21:30:00Z.
- **Status.** Accepted.
- **Category.** CI/CD & Release Governance.
- **Context.** Architecture Freeze Questions Q101 through Q110.
- **Decision.** Every question from Q101 to Q110 is accepted as
  binding.
- **Rationale.** Manual control of versioning and publishing
  prevents accidental releases. Reproducibility is the
  backbone of trust.
- **Consequences.** The CI pipeline produces artifacts but
  does not publish; a manual step publishes.
- **Dependencies.** Related specification:
  `014_PACKAGING_SPECIFICATION.md` §1, §2.
- **Impact Assessment.** Release layer.
- **Backward Compatibility.** N/A.
- **Verification Status.** Verified.
- **Related Change Log Entries.** CHG-0013.
- **Related Task Log Entries.** TASK-022.

---

## ADR-0034 — Security & Reliability (No Key Persistence, Env Vars, SSL Default, Wrap Errors, Observability Hooks)

- **Title.** API keys are never written to disk. API keys are
  accepted through environment variables. Secrets are always
  redacted from logs. SSL verification is enabled by default.
  Network failures are wrapped in SDK exceptions with the
  underlying context preserved. Unexpected API fields are
  ignored unless they affect correctness. Unsupported API
  versions fail explicitly. Observability hooks are designed
  into the architecture. Extension points are stable.
  Architectural governance continues after v1.0.
- **Date.** 2026-06-27T21:30:00Z.
- **Status.** Accepted.
- **Category.** Security & Reliability.
- **Context.** Architecture Freeze Questions Q111 through Q120.
- **Decision.** Every question from Q111 to Q120 is accepted as
  binding.
- **Rationale.** Security is non-negotiable. Extensibility
  without redesign enables future integration.
- **Consequences.** The SDK exposes observability extension
  points from day one. The governance process (ADRs,
  changelog, task log) continues indefinitely.
- **Dependencies.** Related specifications:
  `010_INFRASTRUCTURE_SPEC.md` §3, §6;
  `007_SDK_SPECIFICATION.md` §10;
  `DECISIONS.md`.
- **Impact Assessment.** All layers.
- **Backward Compatibility.** N/A.
- **Verification Status.** Verified.
- **Related Change Log Entries.** CHG-0013.
- **Related Task Log Entries.** TASK-022.

---

## Cross-Reference Matrix

| ADR | Decisions | Affected Documents |
| --- | --------- | ------------------ |
| ADR-0017 | Q1, Q2 | 000, 014, 015 |
| ADR-0018 | Q3 | 003, 010, 014 |
| ADR-0019 | Q4 | 007, 016 |
| ADR-0020 | Q5 | 006, 014 |
| ADR-0021 | Q6-Q10 | 003, 006, 007, 008, 009 |
| ADR-0022 | Q13, Q14 | 010, 007 |
| ADR-0023 | Q16-Q20 | 010, 007 |
| ADR-0024 | Q21-Q25 | 008, 009, 010 |
| ADR-0025 | Q26-Q30 | 010, 014 |
| ADR-0026 | Q31-Q40 | 008, 014 |
| ADR-0027 | Q41-Q50 | 009, 011 |
| ADR-0028 | Q51-Q60 | 006, 007, 011 |
| ADR-0029 | Q61-Q70 | 012, 009 |
| ADR-0030 | Q71-Q80 | 013, 014 |
| ADR-0031 | Q81-Q90 | 014, 015, 016 |
| ADR-0032 | Q91-Q100 | 014, 015, 013 |
| ADR-0033 | Q101-Q110 | 014, 013 |
| ADR-0034 | Q111-Q120 | 010, 007, 014 |

The 18 new ADRs (ADR-0017 through ADR-0034), together with the
original 16 ADRs (ADR-0001 through ADR-0016), define the
authoritative architecture baseline. Every implementation task
SHALL conform to this baseline. Every change to the baseline
SHALL be recorded as a new ADR before the change is merged.

---

# Part III — Empirically Verified Findings (2026-06-27)

The following ADRs record empirical findings from live API
probes. They update the corresponding external-verification
items recorded in `PROJECT_CLARIFICATION_REGISTER.md`.

## ADR-0035 — Rate Limit Shape (Token-Bucket, ≈1 req/s)

- **Title.** The UN Comtrade API enforces a token-bucket
  rate limit with an approximate refill rate of 1 request
  per second and a small burst allowance of 2–3 immediate
  requests. The 429 response includes a `Retry-After: 1`
  header; no `X-RateLimit-*` or `RateLimit-*` headers are
  exposed.
- **Date.** 2026-06-27T22:16:00Z.
- **Status.** Accepted.
- **Category.** Infrastructure.
- **Context.** EXT-001 in `PROJECT_CLARIFICATION_REGISTER.md`
  required empirical resolution. Three live probes were issued
  on 2026-06-26T22:10–22:18 UTC against the public preview
  endpoint. See `API_LIMITS_REPORT.md` for the full transcript.
- **Decision.** The SDK SHALL treat the upstream rate limit
  as a token-bucket with the following characteristics:
  - **Refill rate:** ≈1 request per second.
  - **Burst allowance:** ≈2–3 immediate requests.
  - **Inferred per-minute upper bound:** ≈60–63 req/min under
    ideal pacing.
  - **On 429:** the upstream returns `Retry-After: 1` (seconds);
    the SDK SHALL honour this header (already mandated by
    ADR-0008). If the header is absent, the SDK SHALL apply
    the exponential-backoff schedule from ADR-0008 (initial
    1 s, multiplier 2, cap 60 s, 3 attempts).
  - **No rate-limit response headers** are exposed; the SDK
    SHALL NOT depend on `X-RateLimit-*` or `RateLimit-*`
    headers.
  - **Default concurrent connections:** 1 (sequential). A
    concurrent batch MAY scale up only if every connection
    paces itself at ≈1 req/s.
- **Rationale.** The token-bucket model matches the observed
  behaviour. A simple per-minute window would either over-limit
  the SDK (under a 60/min cap) or under-limit it (above a
  60/min cap). The `Retry-After` header makes the consumer
  experience predictable.
- **Consequences.** Default retry budget = 3 (ADR-0008) is
  sufficient to absorb transient 429s at 1 req/s sustained
  load. Consumers that configure `retry_attempts > 3` MUST
  understand that each retry contributes to the upstream
  rate-limit budget.
- **Dependencies.** Related specifications:
  `004_API_RESEARCH.md` §9;
  `010_INFRASTRUCTURE_SPEC.md` §4;
  `API_LIMITS_REPORT.md`.
- **Impact Assessment.** Infrastructure layer.
- **Backward Compatibility.** N/A (no consumer-visible
  behaviour change; the SDK honours the upstream contract).
- **Verification Status.** Verified (live probes,
  2026-06-26T22:10–22:18 UTC).
- **Related Change Log Entries.** CHG-0014.
- **Related Task Log Entries.** TASK-023.
- **Closes External Verification Items.** EXT-001.

---

## ADR-0036 — Per-Key Daily Record Cap (Free Tier)

- **Title.** Free-tier UN Comtrade API keys are limited to
  **50,000,000 records per day**, subject to the per-second
  rate limit (ADR-0035). Per-call hard caps are **500 records**
  for the public preview and **250,000 records** for the
  authenticated endpoint.
- **Date.** 2026-06-27T22:16:00Z.
- **Status.** Accepted.
- **Category.** Infrastructure.
- **Context.** EXT-002 in `PROJECT_CLARIFICATION_REGISTER.md`
  required resolution. The authenticated-endpoint per-day cap
  could not be re-verified live in this probe (no subscription
  key was supplied); the value is sourced from
  `004_API_RESEARCH.md` §9 (recorded in an earlier session with
  a valid session) and cross-checked against the developer
  portal documentation.
- **Decision.**
  - **Public preview per-call hard cap:** 500 records.
  - **Authenticated per-call hard cap:** 250,000 records
    (matches ADR-0005).
  - **Free-tier per-key daily cap:** 50,000,000 records/day.
  - **Paid-tier per-key daily cap:** higher; documented in
    the developer portal; out of scope for the MVP.
  - **SDK behaviour:** the SDK does NOT cache trade responses
    (ADR-0024), so the daily cap is irrelevant to the SDK's
    internal cache. Consumers SHOULD read their own
    subscription tier from the developer portal; the SDK
    exposes no opinion on this.
- **Rationale.** These caps are documented and stable. The
  SDK's design (no internal trade-response cache) means the
  daily cap only affects the consumer's own usage patterns.
- **Consequences.** Consumers that exceed the daily cap MUST
  acquire a paid tier or split their queries across multiple
  keys. The SDK does not warn about cap exhaustion.
- **Dependencies.** Related specifications:
  `004_API_RESEARCH.md` §9;
  `007_SDK_SPECIFICATION.md` §6 (ADR-0005);
  `API_LIMITS_REPORT.md`.
- **Impact Assessment.** Documentation-level impact only;
  no SDK code change.
- **Backward Compatibility.** N/A.
- **Verification Status.** Per-call caps: verified (ADR-0005).
  Daily cap: MEDIUM confidence (sourced from prior research;
  not re-verified live in this probe).
- **Related Change Log Entries.** CHG-0014.
- **Related Task Log Entries.** TASK-023.
- **Closes External Verification Items.** EXT-002.

---

# End of document
