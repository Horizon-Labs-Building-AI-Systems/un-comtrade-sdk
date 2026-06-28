```
Document ID
016

Title
Implementation Roadmap & Execution Plan

Version
0.1.0

Status
DRAFT

Created
2026-06-26T20:47:39Z

Last Updated
2026-06-26T20:47:39Z

Author
Codex

Project
UN Comtrade Python SDK

Dependencies
015_CODING_STANDARD.md

Supersedes
None
```

---

# 1. Project Overview

## 1.1 Overall Implementation Strategy

The implementation strategy is **documentation-first,
phase-gated, layer-by-layer**. The project does not
begin implementation until the documentation set
is complete. The project does not begin a phase
until the previous phase's exit criteria are
satisfied. The project does not begin a layer
until the layer's specification is approved.

The implementation is organised into 10 phases. Each
phase produces a verifiable artefact. Each phase is
gated by entry and exit criteria. The phases are
sequenced to minimise the cost of rework: a change
in an early phase is propagated forward; a change
in a late phase is propagated backward.

## 1.2 Documentation-First Philosophy

The documentation is the source of truth. The
implementation is the realisation of the
documentation. A change to the implementation
without a corresponding change to the documentation
is a defect. A change to the documentation without
a corresponding change to the implementation is a
backlog item.

The documentation set produced in the Documentation
Phase is the contract. The contract is approved by
the maintainers. The implementation follows the
contract.

## 1.3 Incremental Delivery Approach

The implementation is delivered incrementally. Each
phase produces a release candidate. Each release
candidate is reviewed and approved by the
maintainers. Each release candidate is published
as a pre-release (alpha, beta, or release
candidate). The final release is published as a
stable release.

The incremental delivery approach minimises the
risk of a late discovery. A late discovery in a
late phase is more expensive than a late
discovery in an early phase. The incremental
delivery approach enables early discovery.

## 1.4 Phase-Gate Execution Model

The execution model is phase-gated. A phase begins
when the entry criteria are satisfied. A phase ends
when the exit criteria are satisfied. The exit
criteria are verified by the maintainers. The
verification is documented.

A phase that fails to satisfy the exit criteria is
rolled back to the previous phase. The rollback
is documented.

---

# 2. Roadmap Overview

The complete implementation sequence is organised
into 10 phases. The phases are sequenced to
minimise the cost of rework and to enable
incremental delivery.

```
Phase 0
Documentation
    |
    v
Phase 1
SDK Foundation
    |
    v
Phase 2
Metadata Layer
    |
    v
Phase 3
Trade Layer
    |
    v
Phase 4
Validation, Normalisation, Export
    |
    v
Phase 5
Infrastructure
    |
    v
Phase 6
Storage Layer
    |
    v
Phase 7
Testing & Validation
    |
    v
Phase 8
Packaging & Distribution
    |
    v
Phase 9
Production Release
    |
    v
Phase 10
Maintenance
```

The 10 phases are an elaboration of the 6 phases
declared in `000_PROJECT_CHARTER.md` §19. The
elaboration splits Phase 1 (SDK Foundation) and
Phase 2 (Reference Data) into a single Phase 1, and
splits Phase 2 (Trade Data) into Phases 3 and 4.

The phases are designed so that the implementation
of each layer is preceded by the documentation of
the layer, and the testing of each layer is
preceded by the implementation of the layer.

---

# 3. Phase Specifications

## 3.1 Phase 0 — Documentation

- **Objective.** Produce the complete
  documentation set.
- **Scope.** 17 specification documents.
- **Deliverables.** Every specification document
  in the `docs/` tree.
- **Dependencies.** None.
- **Estimated complexity.** 17 documents, ~1,500
  lines each, ~25,000 lines total.
- **Primary risks.** Scope creep, specification
  drift, undocumented assumptions.
- **Success criteria.** Every required document
  exists. Every required section exists. Every
  cross-reference is consistent. No
  implementation has been introduced.
- **Expected outputs.** 17 specification documents.
- **Exit criteria.** Every specification document
  is approved by the maintainers. The
  documentation set is internally consistent.
  The open questions are recorded in the relevant
  documents.

## 3.2 Phase 1 — SDK Foundation

- **Objective.** Implement the SDK's foundation:
  the SDK client constructor, the configuration
  object, the exception hierarchy, the logging
  seam, and the transport layer.
- **Scope.** The `un_comtrade.client`,
  `un_comtrade.config`, `un_comtrade.errors`,
  `un_comtrade.logging`, and `un_comtrade.transport`
  modules.
- **Deliverables.** A runnable SDK constructor that
  passes a smoke test. A `ComtradeError` base
  exception. A configuration object. A logging
  seam. A transport layer that issues a GET
  request.
- **Dependencies.** Phase 0 is complete.
- **Estimated complexity.** ~2,000 lines of code.
- **Primary risks.** Circular dependencies, hidden
  I/O at import time, side effects in the
  constructor.
- **Success criteria.** The SDK constructor is
  instantiable. The configuration is validatable.
  The exception hierarchy is raiseable. The
  logging seam is usable. The transport layer
  issues a documented GET.
- **Expected outputs.** A first internal alpha
  release.
- **Exit criteria.** The smoke test passes. The
  exception hierarchy is documented. The
  configuration is documented. The logging seam
  is documented. The transport layer is
  documented.

## 3.3 Phase 2 — Metadata Layer

- **Objective.** Implement the metadata layer.
- **Scope.** The `un_comtrade.metadata` module.
  The 15 reference catalogue endpoints. The
  catalogue cache. The search interface.
- **Deliverables.** The metadata layer exposes the
  15 reference catalogues through the public
  methods M01–M18. The metadata layer caches the
  catalogues. The metadata layer supports search.
- **Dependencies.** Phase 1 is complete.
- **Estimated complexity.** ~3,000 lines of code.
- **Primary risks.** Upstream schema drift, cache
  invalidation, reference resolution correctness.
- **Success criteria.** Every reference catalogue
  is loadable. Every reference code is resolvable.
  The cache is correct. The search interface
  returns the documented results.
- **Expected outputs.** A second internal alpha
  release.
- **Exit criteria.** Every reference catalogue is
  tested. The metadata layer is documented. The
  metadata layer is reviewed.

## 3.4 Phase 3 — Trade Layer

- **Objective.** Implement the trade layer.
- **Scope.** The `un_comtrade.trade` module. The
  13 trade datasets. The pagination strategy. The
  retry behaviour. The error handling.
- **Deliverables.** The trade layer exposes the
  13 datasets through the public methods T01–T11,
  F01–F02, P01–P04, C01–C03, A01–A05, U01–U03. The
  trade layer paginates large queries. The trade
  layer retries on transient failure. The trade
  layer raises the documented exceptions.
- **Dependencies.** Phase 2 is complete.
- **Estimated complexity.** ~4,000 lines of code.
- **Primary risks.** Upstream schema drift, query
  composition correctness, pagination correctness,
  download workflow correctness.
- **Success criteria.** Every dataset is queryable.
  Every dataset is normalised. Every error is
  raised at the documented condition. The
  pagination strategy is correct. The download
  workflow is correct.
- **Expected outputs.** A first public beta
  release.
- **Exit criteria.** Every dataset is tested. The
  trade layer is documented. The trade layer is
  reviewed.

## 3.5 Phase 4 — Validation, Normalisation, Export

- **Objective.** Implement the validation,
  normalisation, and export layers.
- **Scope.** The `un_comtrade.validation`,
  `un_comtrade.normalisation`, and `un_comtrade.export`
  modules.
- **Deliverables.** The validation layer validates
  every request. The normalisation layer
  converts the upstream response into the
  canonical model. The export layer packages the
  canonical model into a `Response`.
- **Dependencies.** Phase 3 is complete.
- **Estimated complexity.** ~2,000 lines of code.
- **Primary risks.** Validation rules drift,
  normalisation rules drift, export format drift.
- **Success criteria.** Every request is validated.
  Every response is normalised. Every export
  produces the documented format.
- **Expected outputs.** A second public beta
  release.
- **Exit criteria.** Every validation rule is
  tested. Every normalisation rule is tested. The
  export layer is documented. The export layer
  is reviewed.

## 3.6 Phase 5 — Infrastructure

- **Objective.** Implement the infrastructure
  layer.
- **Scope.** The `un_comtrade.retry`,
  `un_comtrade.pagination`, `un_comtrade.cache`,
  `un_comtrade.utils`, and `un_comtrade.config`
  modules.
- **Deliverables.** The retry policy. The
  pagination helpers. The cache key construction.
  The progress callback. The resume support. The
  request tracking. The diagnostics.
- **Dependencies.** Phase 4 is complete.
- **Estimated complexity.** ~2,000 lines of code.
- **Primary risks.** Retry policy drift, pagination
  strategy drift, cache invalidation drift.
- **Success criteria.** The retry policy is
  correct. The pagination strategy is correct.
  The cache key construction is correct. The
  progress callback is correct. The resume
  support is correct. The request tracking is
  correct.
- **Expected outputs.** A release candidate.
- **Exit criteria.** Every infrastructure service
  is tested. The infrastructure layer is
  documented. The infrastructure layer is
  reviewed.

## 3.7 Phase 6 — Storage Layer

- **Objective.** Implement the storage layer.
- **Scope.** The `un_comtrade.storage` module. The
  local files, JSON, CSV, and Parquet targets.
- **Deliverables.** The storage layer persists the
  canonical dataset in the documented format. The
  storage layer retrieves the persisted dataset.
  The storage layer versions the persisted
  dataset.
- **Dependencies.** Phase 5 is complete.
- **Estimated complexity.** ~2,000 lines of code.
- **Primary risks.** Persistence atomicity,
  versioning drift, integrity verification drift.
- **Success criteria.** The storage layer persists
  the canonical dataset atomically. The storage
  layer retrieves the persisted dataset. The
  storage layer versions the persisted dataset.
  The storage layer verifies the integrity of the
  persisted dataset.
- **Expected outputs.** A second release candidate.
- **Exit criteria.** Every storage target is
  tested. The storage layer is documented. The
  storage layer is reviewed.

## 3.8 Phase 7 — Testing & Validation

- **Objective.** Implement the test suite and
  validate the SDK end to end.
- **Scope.** The `tests/` directory. The unit
  tests, the integration tests, the contract
  tests, the mock API tests, the regression
  tests, the performance tests, the end-to-end
  tests.
- **Deliverables.** A passing test suite. A
  coverage report. A performance baseline. An
  end-to-end validation report.
- **Dependencies.** Phase 6 is complete.
- **Estimated complexity.** ~3,000 lines of test
  code.
- **Primary risks.** Flaky tests, missing test
  coverage, performance regression.
- **Success criteria.** The test suite passes on
  every supported Python version and every
  supported operating system. The coverage
  report shows 100% category coverage. The
  performance baseline is established. The
  end-to-end validation report is published.
- **Expected outputs.** A green CI pipeline. A
  coverage report. A performance baseline. An
  end-to-end validation report.
- **Exit criteria.** The test suite passes. The
  coverage report is published. The performance
  baseline is published. The end-to-end
  validation report is published.

## 3.9 Phase 8 — Packaging & Distribution

- **Objective.** Package and distribute the SDK.
- **Scope.** The package metadata. The build
  process. The signing process. The publishing
  process. The documentation publishing process.
  The CLI.
- **Deliverables.** A package that is installable
  with a single command. A wheel. A source
  distribution. A documentation site. A CLI.
- **Dependencies.** Phase 7 is complete.
- **Estimated complexity.** ~500 lines of build
  configuration.
- **Primary risks.** Build reproducibility, signing
  integrity, publishing automation.
- **Success criteria.** The package is
  installable. The package is reproducible. The
  package is signed. The package is published to
  the package index. The documentation is
  published to the documentation site. The CLI is
  installable.
- **Expected outputs.** A published package. A
  published documentation site. A published CLI.
- **Exit criteria.** The package is published. The
  documentation is published. The CLI is
  published. The release notes are published.

## 3.10 Phase 9 — Production Release

- **Objective.** Release the first stable version
  of the SDK.
- **Scope.** The first stable release. The
  release notes. The migration guide. The support
  window.
- **Deliverables.** A `1.0.0` release on the
  package index. A `1.0.0` documentation site. A
  `1.0.0` CLI.
- **Dependencies.** Phase 8 is complete.
- **Estimated complexity.** ~100 lines of release
  configuration.
- **Primary risks.** Release defects, consumer
  adoption, support burden.
- **Success criteria.** The first stable release is
  published. The release notes are published. The
  migration guide is published. The support
  window is documented.
- **Expected outputs.** A `1.0.0` release.
- **Exit criteria.** The first stable release is
  published. The release notes are published. The
  migration guide is published. The support
  window is documented.

## 3.11 Phase 10 — Maintenance

- **Objective.** Maintain the released SDK.
- **Scope.** The bug fixes. The new features. The
  documentation updates. The consumer support. The
  release cadence.
- **Deliverables.** Patch releases. Minor releases.
  Documentation updates. Consumer support responses.
- **Dependencies.** Phase 9 is complete.
- **Estimated complexity.** Continuous.
- **Primary risks.** API drift, support burden,
  contributor burnout.
- **Success criteria.** The release cadence is
  maintained. The consumer issues are responded to
  within the documented SLA. The documentation is
  kept up to date.
- **Expected outputs.** Patch releases. Minor
  releases. Documentation updates. Consumer
  support responses.
- **Exit criteria.** The maintenance phase
  continues until the project is archived.

---

# 4. Phase Gate Model

Every phase declares entry criteria and exit
criteria. The entry criteria SHALL be satisfied
before the phase begins. The exit criteria SHALL
be satisfied before the phase ends.

## 4.1 Entry Criteria

A phase's entry criteria are:

- Every required input is available.
- Every required completed document is approved.
- Every required completed implementation is
  merged.
- Every required validation is passed.
- Every required approval is granted.

## 4.2 Exit Criteria

A phase's exit criteria are:

- Every required deliverable is produced.
- Every required validation is passed.
- Every required documentation is updated.
- Every required approval is granted.
- The next phase's entry criteria are projected to
  be satisfiable.

## 4.3 Phase Gate Verification

The phase gate is verified by the maintainers. The
verification is documented. The verification is
recorded in the changelog and in `DECISIONS.md`.

A phase gate that fails is rolled back to the
previous phase. The rollback is documented.

## 4.4 Phase Gate Records

A phase gate record contains:

- The phase ID.
- The entry criteria.
- The exit criteria.
- The verification timestamp.
- The verification result.
- The verification authority.
- The next phase's projected entry criteria.

---

# 5. Milestone Definitions

The major milestones are recorded in this section.
Each milestone has measurable completion criteria.

## 5.1 Architecture Complete

- **Definition.** The architecture, the data model,
  the API research, the API endpoint catalog, the
  SDK specification, the metadata layer spec, the
  trade layer spec, the infrastructure spec, the
  ETL spec, the storage spec, the testing standard,
  the packaging spec, the coding standard, and the
  roadmap are approved.
- **Completion criteria.** Every required document
  exists. Every required section exists. Every
  cross-reference is consistent. The
  documentation set is internally consistent.

## 5.2 SDK Skeleton Complete

- **Definition.** The SDK constructor, the
  configuration, the exception hierarchy, the
  logging seam, and the transport layer are
  implemented.
- **Completion criteria.** The SDK constructor is
  instantiable. The configuration is validatable.
  The exception hierarchy is raiseable. The
  logging seam is usable. The transport layer
  issues a documented GET.

## 5.3 Metadata Complete

- **Definition.** The metadata layer is implemented.
- **Completion criteria.** Every reference
  catalogue is loadable. Every reference code is
  resolvable. The cache is correct. The search
  interface returns the documented results.

## 5.4 Trade Layer Complete

- **Definition.** The trade layer is implemented.
- **Completion criteria.** Every dataset is
  queryable. Every dataset is normalised. Every
  error is raised at the documented condition. The
  pagination strategy is correct. The download
  workflow is correct.

## 5.5 Infrastructure Complete

- **Definition.** The infrastructure layer is
  implemented.
- **Completion criteria.** The retry policy is
  correct. The pagination strategy is correct. The
  cache key construction is correct. The progress
  callback is correct. The resume support is
  correct. The request tracking is correct.

## 5.6 ETL Complete

- **Definition.** The ETL layer is implemented.
- **Completion criteria.** The extraction is
  correct. The validation is correct. The
  transformation is correct. The normalisation is
  correct. The deduplication is correct. The
  quality check is correct. The export is correct.

## 5.7 Storage Complete

- **Definition.** The storage layer is implemented.
- **Completion criteria.** The storage layer
  persists the canonical dataset atomically. The
  storage layer retrieves the persisted dataset.
  The storage layer versions the persisted
  dataset. The storage layer verifies the integrity
  of the persisted dataset.

## 5.8 Testing Complete

- **Definition.** The test suite is implemented
  and passing.
- **Completion criteria.** The test suite passes
  on every supported Python version and every
  supported operating system. The coverage report
  shows 100% category coverage. The performance
  baseline is established. The end-to-end
  validation report is published.

## 5.9 Release Candidate

- **Definition.** The package is built, signed, and
  published as a release candidate.
- **Completion criteria.** The package is
  installable. The package is reproducible. The
  package is signed. The package is published to
  the package index. The documentation is published
  to the documentation site. The CLI is
  installable.

## 5.10 Production Release

- **Definition.** The package is built, signed, and
  published as a stable release.
- **Completion criteria.** The first stable release
  is published. The release notes are published.
  The migration guide is published. The support
  window is documented.

---

# 6. Dependency Graph

The dependency graph declares the mandatory
dependencies, the optional dependencies, the
parallelisable work, the blocked phases, and the
critical path.

## 6.1 Mandatory Dependencies

The mandatory dependencies are:

- Phase 1 depends on Phase 0.
- Phase 2 depends on Phase 1.
- Phase 3 depends on Phase 2.
- Phase 4 depends on Phase 3.
- Phase 5 depends on Phase 4.
- Phase 6 depends on Phase 5.
- Phase 7 depends on Phase 6.
- Phase 8 depends on Phase 7.
- Phase 9 depends on Phase 8.
- Phase 10 depends on Phase 9.

A phase SHALL NOT begin before the previous phase
satisfies its exit criteria.

## 6.2 Optional Dependencies

The optional dependencies are:

- Phase 5 (Infrastructure) MAY begin in parallel
  with Phase 4 (Validation, Normalisation, Export).
- Phase 6 (Storage) MAY begin in parallel with
  Phase 5 (Infrastructure).

The optional dependencies are listed for
parallelisation opportunities. A phase that begins
in parallel SHALL NOT depend on the other phase's
exit criteria.

## 6.3 Parallelisable Work

The parallelisable work is:

- The CLI implementation MAY begin in parallel with
  Phase 7.
- The example scripts MAY begin in parallel with
  Phase 4.
- The Jupyter notebooks MAY begin in parallel with
  Phase 6.

The parallelisable work is listed for
parallelisation opportunities. A work item that
begins in parallel SHALL NOT depend on the other
work item's exit criteria.

## 6.4 Blocked Phases

A blocked phase is a phase that cannot begin
because the previous phase has not satisfied its
exit criteria. The blocked phases are:

- Phase 1 is blocked until Phase 0 is complete.
- Phase 2 is blocked until Phase 1 is complete.
- Phase 3 is blocked until Phase 2 is complete.
- Phase 4 is blocked until Phase 3 is complete.
- Phase 5 is blocked until Phase 4 is complete
  (or begins in parallel with Phase 4).
- Phase 6 is blocked until Phase 5 is complete
  (or begins in parallel with Phase 5).
- Phase 7 is blocked until Phase 6 is complete.
- Phase 8 is blocked until Phase 7 is complete.
- Phase 9 is blocked until Phase 8 is complete.
- Phase 10 is blocked until Phase 9 is complete.

## 6.5 Critical Path

The critical path is the sequence of phases whose
slippage would delay the production release. The
critical path is:

```
Phase 0 → Phase 1 → Phase 2 → Phase 3
        → Phase 4 → Phase 5 → Phase 6
        → Phase 7 → Phase 8 → Phase 9
```

A slippage in any phase on the critical path
delays the production release. A slippage in a
phase off the critical path MAY be absorbed by the
parallelisable work.

---

# 7. Deliverable Matrix

The deliverable matrix maps each phase to its
expected outputs. The deliverables are organised
by category.

| Phase | Docs | SDK Modules | Tests | Examples | CLI | Artifacts |
| ----- | ---- | ----------- | ----- | -------- | --- | --------- |
| 0     | 17   | 0           | 0     | 0        | 0   | 0         |
| 1     | 1    | 5           | 10    | 0        | 0   | 0         |
| 2     | 1    | 1           | 30    | 1        | 0   | 0         |
| 3     | 1    | 1           | 50    | 3        | 1   | 0         |
| 4     | 0    | 3           | 30    | 0        | 0   | 0         |
| 5     | 0    | 5           | 30    | 0        | 0   | 0         |
| 6     | 0    | 1           | 30    | 1        | 0   | 0         |
| 7     | 1    | 0           | 100   | 0        | 0   | 0         |
| 8     | 0    | 0           | 0     | 0        | 1   | 5         |
| 9     | 0    | 0           | 0     | 0        | 0   | 3         |

The deliverable counts are indicative; the
consumer can override the counts through the
project's velocity.

---

# 8. Risk Management

The risk management section identifies the
implementation risks and the mitigation strategies.

## 8.1 API changes

- **Impact.** The upstream API may change between
  documentation and implementation.
- **Likelihood.** Medium.
- **Mitigation.** The API research is verified by
  live request. The data model is updated when the
  upstream changes. The implementation follows the
  data model.
- **Monitoring.** The continuous integration
  pipeline runs the live API tests on a scheduled
  cadence. A failure in a live test is a signal that
  the upstream has changed.

## 8.2 Authentication changes

- **Impact.** The upstream may change the
  authentication model.
- **Likelihood.** Low.
- **Mitigation.** The authentication is isolated in
  the transport layer. A change in the authentication
  model produces a change in the transport layer.
- **Monitoring.** The continuous integration pipeline
  runs the live API tests on a scheduled cadence.

## 8.3 Large datasets

- **Impact.** A large dataset may exceed the
  documented limits.
- **Likelihood.** Medium.
- **Mitigation.** The pagination strategy is
  implemented. The async delivery is reserved. The
  bulk download is reserved.
- **Monitoring.** The performance tests record the
  throughput as a baseline. A regression in the
  throughput is a signal that the pagination
  strategy is not optimal.

## 8.4 Performance

- **Impact.** A performance regression may delay
  the production release.
- **Likelihood.** Medium.
- **Mitigation.** The performance tests are
  scheduled. The performance baseline is
  established. The performance regression is
  recorded as a defect.
- **Monitoring.** The performance tests run on a
  scheduled cadence. A regression in the latency
  is a signal that the implementation is not
  optimal.

## 8.5 Breaking changes

- **Impact.** A breaking change in a late phase is
  expensive.
- **Likelihood.** Low.
- **Mitigation.** The documentation is approved
  before the implementation. The implementation
  follows the documentation. A breaking change is
  recorded in `DECISIONS.md` and is approved by the
  maintainers.
- **Monitoring.** The review checklist verifies
  that the implementation does not introduce a
  breaking change.

## 8.6 Dependency updates

- **Impact.** A dependency update may introduce a
  breaking change.
- **Likelihood.** Medium.
- **Mitigation.** The dependency version pinning is
  documented. The dependency update policy is
  recorded. A breaking change in a dependency is
  published as a major release of the SDK.
- **Monitoring.** The dependency audit is scheduled.
  A breaking change in a dependency is a signal
  that the SDK SHALL publish a major release.

## 8.7 Contributor burnout

- **Impact.** A maintainer may become unavailable
  for a prolonged period.
- **Likelihood.** Medium.
- **Mitigation.** The documentation is
  comprehensive. The tests are deterministic. A new
  maintainer can be onboarded quickly. The
  succession plan is documented.
- **Monitoring.** The contributor activity is
  recorded in the changelog. A period of inactivity
  is a signal that the project SHALL recruit a
  new maintainer.

---

# 9. Success Metrics

The success metrics declare the measurable criteria
for the project's success.

## 9.1 Documentation Completed

The documentation is complete when every required
document exists, every required section exists, and
every cross-reference is consistent. The
documentation set is the contract.

## 9.2 SDK Public API Implemented

The SDK's public API is implemented when every
public method of the SDK specification is
implemented, every public method is tested, and
every public method is documented.

## 9.3 Metadata Support Completed

The metadata support is completed when every
reference catalogue is loadable, every reference
code is resolvable, and every metadata method of
the SDK specification is implemented.

## 9.4 Trade Retrieval Validated

The trade retrieval is validated when every
dataset is queryable, every dataset is normalised,
and every error is raised at the documented
condition.

## 9.5 Test Suite Passing

The test suite is passing when every unit test,
every integration test, every contract test, every
mock API test, every regression test, and every
end-to-end test passes on every supported Python
version and every supported operating system.

## 9.6 Release Artifacts Generated

The release artefacts are generated when the
package is built, signed, and published to the
package index. The documentation is published to
the documentation site. The CLI is published.

## 9.7 Production-Ready Package

The package is production-ready when the first
stable release is published, the release notes
are published, the migration guide is published,
and the support window is documented.

---

# 10. Change Management

The change management section declares how
roadmap changes are governed.

## 10.1 Versioning

The roadmap is versioned. The roadmap version is
incremented when a phase is added, removed, or
modified. The roadmap version is recorded in
`DECISIONS.md`.

## 10.2 Approval Requirements

A roadmap change requires the approval of the
maintainers. A roadmap change that affects the
critical path requires the approval of the
maintainers and the consumers. A roadmap change
that affects the deliverable matrix requires the
approval of the maintainers.

## 10.3 Impact Assessment

A roadmap change is accompanied by an impact
assessment. The impact assessment records the
affected phases, the affected milestones, the
affected deliverables, and the affected risks. The
impact assessment is recorded in `DECISIONS.md`.

## 10.4 Backward Compatibility

A roadmap change preserves backward compatibility
within a major version. A breaking change is
reserved for a major version increment.

## 10.5 Documentation Updates

A roadmap change is accompanied by a documentation
update. The documentation update records the
change in the changelog, in `DECISIONS.md`, and in
the affected specification documents.

---

# 11. Progress Tracking

The progress tracking section declares how
progress is measured.

## 11.1 Task Completion

A task is complete when the task's deliverables
are produced, the task's documentation is updated,
and the task's exit criteria are satisfied.

## 11.2 Phase Completion

A phase is complete when the phase's deliverables
are produced, the phase's validation is passed, the
phase's documentation is updated, and the phase's
exit criteria are satisfied.

## 11.3 Milestone Completion

A milestone is complete when the milestone's
completion criteria are satisfied. The
milestone's completion is recorded in the
changelog.

## 11.4 Documentation Completion

A documentation is complete when the documentation
is approved by the maintainers. The documentation
is recorded in the changelog.

## 11.5 Implementation Completion

An implementation is complete when the
implementation is merged, the implementation is
tested, and the implementation is documented. The
implementation is recorded in the changelog.

## 11.6 Release Readiness

A release is ready when the release's criteria
are satisfied. The release's readiness is recorded
in the changelog.

## 11.7 Logical Tracking

The progress is tracked at the logical level. A
Gantt chart is not produced. A burn-down chart is
not produced. A velocity chart is not produced. The
progress is recorded in the changelog and in
`DECISIONS.md`.

---

# 12. Release Readiness

The release readiness section declares the
requirements for the production release.

## 12.1 All Specifications Approved

Every specification document is approved by the
maintainers. Every cross-reference is consistent.
Every open question is resolved or deferred to a
documented milestone.

## 12.2 Implementation Complete

Every phase's deliverables are produced. Every
phase's exit criteria are satisfied. Every
deliverable is reviewed and approved.

## 12.3 Quality Gates Satisfied

The test suite passes on every supported Python
version and every supported operating system. The
coverage report shows 100% category coverage. The
performance baseline is established. The
end-to-end validation report is published.

## 12.4 Documentation Complete

The README is up to date. The getting started
guide is up to date. The API reference is up to
date. The migration guide is up to date. The
release notes are published. The changelog is
updated.

## 12.5 Regression Validation Complete

The regression suite passes. The live API tests
pass. The performance tests pass. The end-to-end
tests pass.

## 12.6 Packaging Complete

The package is built. The package is signed. The
package is published. The wheel is published. The
source distribution is published.

## 12.7 Release Notes Prepared

The release notes record the new features, the
bug fixes, the breaking changes, and the
deprecations. The release notes are published.

## 12.8 Support Window Documented

The support window is documented. The end-of-life
date is documented. The deprecation policy is
documented.

---

# 13. Future Roadmap

The future roadmap declares the post-v1
opportunities. The future roadmap is the source
of the post-v1 backlog. The future roadmap does
NOT include MVP deliverables.

## 13.1 Additional APIs

Additional APIs include the data availability
endpoint (OQ-API-003), the publication notes
endpoint (OQ-API-004), the trade balance endpoint
(T3), the bilateral endpoint (T4), the trade
matrix endpoint (T2), the standard unit value
endpoint (U1), the async delivery endpoints (D2),
and the bulk download endpoints (D3). These
endpoints are documented in the catalog and are
reserved for future implementation.

## 13.2 Additional Datasets

Additional datasets include the per-edition HS
classifications (H0–H6), the SITC classifications
(S1–S4), the BEC classifications (B4, B5), the
EBOPS classifications (EB02, EB10, EB), and the
service datasets. These datasets are documented
in the data model and are reserved for future
implementation.

## 13.3 Cloud Storage

Cloud object storage (T07) is a future target. The
target is documented in the storage specification
and is reserved for future implementation.

## 13.4 Streaming

Streaming is a future capability. The streaming
interface is documented in the SDK specification
and is reserved for future implementation.

## 13.5 Plugin Architecture

A plugin architecture is a future capability. The
plugin extension point is documented in the
infrastructure specification and is reserved for
future implementation.

## 13.6 Async Client

An async client class is a future capability. The
async client is documented in the SDK specification
and is reserved for future implementation.

## 13.7 DataFrame Output

A DataFrame output is a future capability. The
DataFrame output is documented in the SDK
specification and is reserved for future
implementation.

## 13.8 Distinct from MVP

The future roadmap items are distinct from the
MVP deliverables. The MVP deliverables are
declared in §3 and §5. The future roadmap items
are declared in this section. A future roadmap
item SHALL NOT be confused with an MVP deliverable.

---

# 14. Assumptions

The assumptions below are recorded for
traceability. An assumption that turns out to be
false is recorded in `DECISIONS.md` as a
correction and is propagated to the relevant
specification documents.

## 14.1 Verified Assumptions

- The documentation set produced in Phase 0 is
  the contract. Verified.
- The SDK is a pure-Python project. Verified.
- The dependency footprint is the minimum set
  required for the documented functionality.
  Verified by `014_PACKAGING_SPECIFICATION.md` §6.
- The top-level package is `un_comtrade`. Verified
  by the architecture document.

## 14.2 Inferred Assumptions

- The phase sequence is the most efficient
  sequence for the project. The sequence is
  inferred from the architecture; the consumer
  can override the sequence.
- The deliverable counts are indicative. The
  counts are inferred from common practice; the
  consumer can override the counts.
- The risk likelihoods are indicative. The
  likelihoods are inferred from common practice;
  the consumer can override the likelihoods.
- The success metrics are measurable. The metrics
  are inferred from common practice; the consumer
  can override the metrics.
- The release cadence is on-demand. The cadence
  is inferred from common practice; the consumer
  can override the cadence.

## 14.3 Local Design Decisions

- The implementation is organised into 10 phases.
  The phase count is a local design decision; the
  consumer can override the count.
- The phase sequence is the documented sequence.
  The sequence is a local design decision; the
  consumer can override the sequence.
- The phase gate is the entry and exit criteria
  declared in §4. The phase gate is a local
  design decision; the consumer can override the
  phase gate.
- The milestones are the documented milestones.
  The milestones are a local design decision; the
  consumer can override the milestones.

---

# 15. Open Questions

The questions below are recorded for future
resolution. Each question is described with the
impact and the suggested verification.

- **OQ-IM-001 (High).** When is Phase 0 complete?
  **Impact.** The Phase 0 completion gates Phase 1.
  **Suggested verification.** Confirm with the
  maintainers that every document is approved.

- **OQ-IM-002 (High).** When is Phase 9 complete?
  **Impact.** The Phase 9 completion marks the
  production release. **Suggested verification.**
  Confirm with the maintainers that the release
  criteria are satisfied.

- **OQ-IM-003 (High).** What is the exact cadence
  of Phase 10 (Maintenance)? **Impact.** The
  maintenance cadence affects the consumer's
  upgrade planning. **Suggested verification.**
  Confirm with the maintainers.

- **OQ-IM-004 (Medium).** What is the exact
  success criteria for each milestone? **Impact.**
  The success criteria are the gate of the
  milestone. **Suggested verification.** Confirm
  with the maintainers.

- **OQ-IM-005 (Medium).** What is the exact
  parallelisable work for each phase? **Impact.**
  The parallelisable work affects the project
  velocity. **Suggested verification.** Confirm
  with the maintainers.

- **OQ-IM-006 (Medium).** What is the exact impact
  assessment template for a roadmap change?
  **Impact.** The impact assessment template
  affects the change management. **Suggested
  verification.** Confirm with the maintainers.

- **OQ-IM-007 (Medium).** What is the exact
  escalation policy for a phase gate failure?
  **Impact.** The escalation policy affects the
  project velocity. **Suggested verification.**
  Confirm with the maintainers.

- **OQ-IM-008 (Low).** What is the exact
  celebration protocol for each milestone?
  **Impact.** The celebration protocol affects
  the contributor morale. **Suggested verification.**
  Confirm with the maintainers.

- **OQ-IM-009 (Low).** What is the exact
  communication channel for the project? **Impact.**
  The communication channel affects the consumer
  awareness. **Suggested verification.** Confirm
  with the maintainers.

- **OQ-IM-010 (Low).** What is the exact
  governance model for the project? **Impact.**
  The governance model affects the project
  decision-making. **Suggested verification.**
  Confirm with the maintainers.

---

# 16. Recommendation for Transitioning from Documentation Phase to Implementation Phase

The Documentation Phase (Phase 0) is the
prerequisite for every other phase. The transition
from Phase 0 to Phase 1 is the most important
transition in the project. The transition SHALL
be governed by the following procedure.

## 16.1 Verification

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

## 16.2 Decision

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

## 16.3 First Action

The first action of Phase 1 is to create the
package skeleton. The package skeleton includes:

- The `un_comtrade/` top-level package.
- The `un_comtrade/__init__.py` file.
- The `un_comtrade/client/` sub-package.
- The `un_comtrade/config/` sub-package.
- The `un_comtrade/errors/` sub-package.
- The `un_comtrade/logging/` sub-package.
- The `un_comtrade/transport/` sub-package.
- The `pyproject.toml` file.
- The `requirements.txt` file.
- The `tests/` directory.
- The `examples/` directory.

The package skeleton is the first verifiable
artefact of Phase 1. The package skeleton is the
seed of the SDK's source tree.

## 16.4 First Smoke Test

The first smoke test of Phase 1 is to instantiate
the SDK constructor. The test verifies:

- The `ComtradeClient` class is importable.
- The constructor accepts the documented
  parameters.
- The constructor returns an instance.
- The instance exposes the documented public
  surface (initially empty).

The smoke test is the first verifiable behaviour
of Phase 1. The smoke test is the seed of the
SDK's test suite.

## 16.5 First Documentation Update

The first documentation update of Phase 1 is to
update `CHANGELOG.md`, `TASK_LOG.md`, and
`DECISIONS.md`. The update records the
transition from Phase 0 to Phase 1.

The first documentation update of Phase 1 is also
to update the `README.md` to point to the
documentation. The update marks the start of
the implementation phase.

## 16.6 First Communication

The first communication of Phase 1 is to inform
the consumers that the implementation phase has
started. The communication includes:

- The version of the first internal alpha.
- The expected date of the first public beta.
- The expected date of the first release
  candidate.
- The expected date of the first stable release.

The first communication is the start of the
consumer's awareness of the project.

---

# End of document
