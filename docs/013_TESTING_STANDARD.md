```
Document ID
013

Title
Quality Assurance & Testing Standard

Version
0.1.0

Status
DRAFT

Created
2026-06-26T20:37:16Z

Last Updated
2026-06-26T20:37:16Z

Author
Codex

Project
UN Comtrade Python SDK

Dependencies
012_STORAGE_SPECIFICATION.md

Supersedes
None
```

---

# 1. Quality Philosophy

## 1.1 Quality objectives

The quality objectives of the SDK are:

- **Correctness.** Every public method produces the
  documented result for every documented input.
- **Reliability.** The SDK recovers from transient
  failures and surfaces non-recoverable failures
  through the documented exception hierarchy.
- **Stability.** The public interface is stable
  within a major version.
- **Performance.** The SDK meets the documented
  latency expectations.
- **Security.** The API key is never exposed in a
  log, an error message, or a diagnostic report.
- **Documentation quality.** Every public method,
  every parameter, every return type, and every
  exception is documented.

## 1.2 Documentation-first validation

The documentation is the source of truth. A test
verifies that the implementation matches the
documentation, not the other way around. A
discrepancy between the implementation and the
documentation is treated as a defect in the
implementation.

## 1.3 Deterministic testing

A test is deterministic when its result is
reproducible across runs. The default test suite
is deterministic. A test that is not
deterministic is marked as a live test and is
excluded from the default suite.

## 1.4 Reproducibility

A test that passes locally SHALL pass in the
continuous integration pipeline. A test that
passes in the continuous integration pipeline
SHALL pass on every supported Python version and
every supported operating system. A test that is
not reproducible is treated as flaky and is
repaired or removed.

## 1.5 Reliability expectations

The SDK SHALL be reliable in the following sense:

- A network failure SHALL be retried with the
  documented backoff.
- An authentication failure SHALL raise a
  documented exception.
- A rate-limit failure SHALL be retried with the
  documented backoff.
- A timeout SHALL be raised as a documented
  exception.
- A validation failure SHALL be raised as a
  documented exception.
- An upstream error SHALL be raised as a documented
  exception.
- A configuration error SHALL be raised at
  construction.
- The SDK SHALL NOT silently swallow a failure.

## 1.6 Quality over speed

Quality is preferred over speed. A test SHALL NOT
be skipped to ship a release faster. A release
SHALL NOT be published without a passing test
suite.

---

# 2. Testing Strategy

The testing strategy is organised as a pyramid.
Each layer of the pyramid has a specific purpose
and a specific success criterion.

```
              E2E
            /     \
           /       \
          /  Live    \
         /___________\
        / Integration \
       /               \
      /    Contract    \
     /__________________\
    /       Unit         \
   /______________________\
```

## 2.1 Unit Testing

Unit testing verifies the behaviour of the smallest
testable unit of the SDK. A unit test is
deterministic and does not depend on the live
upstream API. A unit test uses a recorded sample
or a mock.

## 2.2 Integration Testing

Integration testing verifies the interaction
between two or more layers of the SDK. An
integration test is deterministic and uses a
recorded sample or a mock for the upstream API.

## 2.3 Contract Testing

Contract testing verifies that the SDK
implementation matches the documented contract of
the upstream API. A contract test compares the
SDK's request shape against the catalog and
compares the SDK's response normalisation against
the data model.

## 2.4 Mock API Testing

Mock API testing verifies the behaviour of the
SDK against a mock that simulates the upstream
API. A mock API test is deterministic and runs in
isolation from the live upstream.

## 2.5 Live API Testing

Live API testing verifies the behaviour of the
SDK against the live upstream API. A live API
test is part of a **dedicated integration suite**
that is run separately from the core test suite.
The core test suite relies on deterministic
fixtures and recorded mock responses (per
Architecture Freeze Question Q72). A live API
test requires a valid subscription key, is run
on a scheduled cadence (not on every commit), and
is the only place where the SDK is exercised
against the real upstream service.

## 2.6 Regression Testing

Regression testing verifies that a change to the
SDK does not break an existing behaviour. A
regression test is a recorded test that compares
the new behaviour against the previous behaviour.

## 2.7 Performance Testing

Performance testing verifies that the SDK meets
the documented latency expectations. A
performance test measures the latency of a
documented call and records the result as a
baseline. A regression in the latency is a defect.

## 2.8 End-to-End Validation

End-to-end validation verifies that the SDK
produces the documented result for a documented
end-to-end workflow. An end-to-end test is the
most expensive test category; it is run on a
scheduled cadence.

## 2.9 Release Validation

Release validation verifies that the SDK meets
the release criteria declared in section 14. A
release validation is a gated test that gates
the release.

## 2.10 Summary

| Test category        | Deterministic | Frequency        | Scope                  |
| -------------------- | ------------- | ---------------- | ---------------------- |
| Unit                 | Yes           | Every commit     | Smallest unit          |
| Integration          | Yes           | Every commit     | Two or more layers     |
| Contract             | Yes           | Every commit     | Upstream contract      |
| Mock API             | Yes           | Every commit     | Mocked upstream         |
| Live API             | No            | Scheduled        | Live upstream           |
| Regression           | Yes           | Every commit     | Existing behaviour     |
| Performance          | Yes           | Scheduled        | Latency baseline       |
| End-to-end           | Mixed         | Scheduled        | Full workflow          |
| Release validation   | Mixed         | Before release   | Release criteria       |

---

# 3. Unit Testing Standard

The unit testing standard declares the expectations
for every unit test of the SDK.

## 3.1 Public SDK Methods

Every public method of the SDK SHALL be covered by
at least one unit test. A unit test SHALL verify:

- The method returns the documented return type.
- The method raises the documented exception for
  every documented failure mode.
- The method does not perform I/O when the test
  uses a recorded sample.
- The method does not raise an undocumented
  exception.

## 3.2 Internal Utilities

Every internal utility of the SDK SHALL be covered
by at least one unit test. The internal utilities
are declared in the architecture document.

## 3.3 Data Models

Every entity of the canonical data model SHALL be
covered by at least one unit test. A unit test
SHALL verify:

- The entity can be constructed from a valid
  dictionary.
- The entity validates the documented fields.
- The entity preserves the documented relationships.

## 3.4 Validation Logic

Every validation rule of the canonical data model
SHALL be covered by at least one unit test. A unit
test SHALL verify:

- A valid input passes the validation.
- An invalid input fails the validation.
- The validation raises the documented exception
  on failure.

## 3.5 Error Handling

Every documented exception SHALL be covered by at
least one unit test. A unit test SHALL verify:

- The exception is raised at the documented
  condition.
- The exception carries the documented fields.
- The exception translates the originating error
  through the documented `__cause__` attribute.

## 3.6 Configuration

Every configuration parameter SHALL be covered by
at least one unit test. A unit test SHALL verify:

- The default value is the documented value.
- A valid override is accepted.
- An invalid override raises the documented
  exception.

---

# 4. Integration Testing Standard

The integration testing standard declares the
expectations for every integration test of the
SDK.

## 4.1 SDK Client ↔ API

An integration test of the SDK client against the
API SHALL verify:

- The client issues a request with the documented
  URL.
- The client issues a request with the documented
  parameters.
- The client receives the documented response
  shape.
- The client raises the documented exception on
  failure.

## 4.2 Metadata Layer ↔ Trade Layer

An integration test of the metadata layer against
the trade layer SHALL verify:

- The trade layer resolves every code through the
  metadata layer.
- The trade layer raises a `ReferenceError` when
  the metadata layer cannot resolve a code.
- The metadata layer is consulted on every code
  that appears in the request and the response.

## 4.3 ETL ↔ Storage

An integration test of the ETL layer against the
storage layer SHALL verify:

- The ETL layer hands off the canonical dataset
  to the storage layer.
- The storage layer validates the dataset before
  persistence.
- The storage layer persists the dataset in the
  documented format.
- The storage layer raises the documented
  exception on failure.

## 4.4 Infrastructure ↔ All Layers

An integration test of the infrastructure layer
against the other layers SHALL verify:

- Every layer invokes the documented
  infrastructure services.
- Every layer respects the documented
  configuration.
- Every layer logs at the documented level.
- Every layer reports progress through the
  documented callback.
- Every layer retries with the documented
  backoff.
- Every layer raises the documented exception on
  failure.

## 4.5 Success Criteria

An integration test is successful when:

- The test runs in isolation from every other
  test.
- The test runs in less than 5 seconds.
- The test produces a deterministic result.
- The test does not depend on the live upstream
  API.

---

# 5. Contract Testing

The contract testing standard declares the
expectations for verifying the compatibility
between the SDK and the upstream API.

## 5.1 Endpoint availability

A contract test SHALL verify that every endpoint
declared in the catalog is reachable. A test that
finds an endpoint to be unreachable SHALL record
the unreachable endpoint in the test result and
SHALL NOT raise an error.

## 5.2 Response schema compatibility

A contract test SHALL verify that the response
shape of every endpoint matches the documented
shape. A test that finds a deviation SHALL record
the deviation in the test result and SHALL NOT
raise an error. A deviation triggers a
re-verification of the data model.

## 5.3 Parameter compatibility

A contract test SHALL verify that every
parameter declared in the catalog is accepted by
the upstream. A test that finds a deviation SHALL
record the deviation in the test result.

## 5.4 Canonical model mapping

A contract test SHALL verify that the SDK
normalises the upstream response into the
canonical data model. A test that finds a
deviation SHALL record the deviation in the test
result.

## 5.5 Live contract tests

A live contract test is a contract test that
exercises the live upstream API. A live contract
test is run on a scheduled cadence, not on every
commit. A live contract test requires a valid
subscription key.

---

# 6. Mock API Strategy

The mock API strategy declares the strategy for
mocking the upstream API in tests.

## 6.1 Purpose

The purpose of the mock API is to enable
deterministic testing of the SDK without
depending on the live upstream API.

## 6.2 Mock datasets

A mock dataset is a recorded upstream response
that the mock serves in place of the live API.
The mock datasets are stored in the `data/`
directory and are versioned.

## 6.3 Failure simulation

The mock API supports failure simulation. A test
can configure the mock to return a 401 response,
a 429 response, a 500 response, a network
failure, or a timeout. The failure simulation
enables the test to verify the error handling of
the SDK.

## 6.4 Offline testing

The mock API enables offline testing. A test can
run without a network connection. The mock API
serves the recorded responses.

## 6.5 Deterministic responses

The mock API returns deterministic responses. A
test that issues the same request twice receives
the same response. A test that depends on a
non-deterministic response is treated as flaky
and is repaired or removed.

## 6.6 Schema evolution testing

The mock API supports schema evolution testing. A
test can configure the mock to return a response
with a new field, a removed field, or a changed
datatype. The schema evolution test verifies that
the SDK handles the change correctly.

## 6.7 Mock isolation

The mock API is isolated from the live upstream.
A test that uses the mock SHALL NOT issue a live
request. A test that uses the live upstream SHALL
NOT use the mock.

---

# 7. Regression Testing

The regression testing standard declares the
expectations for verifying that a change to the
SDK does not break an existing behaviour.

## 7.1 Public SDK behaviour

A regression test of the public SDK behaviour
SHALL verify that every documented behaviour of
the SDK continues to work after a change. A test
that finds a regression SHALL be repaired before
the change is merged.

## 7.2 Canonical data model

A regression test of the canonical data model
SHALL verify that every entity of the data model
continues to be persisted, validated, and
exposed after a change. A test that finds a
regression SHALL be repaired before the change is
merged.

## 7.3 API compatibility

A regression test of the API compatibility SHALL
verify that the SDK continues to issue the
documented requests to the upstream API. A test
that finds a regression SHALL be repaired before
the change is merged.

## 7.4 Storage compatibility

A regression test of the storage compatibility
SHALL verify that the persisted dataset continues
to be readable after a change. A test that finds
a regression SHALL be repaired before the change
is merged.

## 7.5 Backward compatibility

A regression test of the backward compatibility
SHALL verify that a consumer that pins to a
major version of the SDK continues to work after
a minor or patch version increment. A test that
finds a regression SHALL be repaired before the
change is merged.

## 7.6 Document protection

A regression test of the document protection
SHALL verify that the documentation continues to
match the implementation. A test that finds a
regression SHALL be repaired before the change is
merged.

## 7.7 Regression suite

The regression suite is the union of every
regression test. The regression suite SHALL be
run on every commit. The regression suite SHALL
be run on every pull request. A failure in the
regression suite blocks the merge.

---

# 8. Performance Testing

The performance testing standard declares the
expectations for verifying the latency of the
SDK.

## 8.1 Response latency

A performance test of the response latency SHALL
measure the elapsed time of a documented call.
The performance test records the elapsed time as
a baseline. A regression in the latency is a
defect.

## 8.2 Large dataset processing

A performance test of the large dataset processing
SHALL measure the throughput of a documented
batch. The performance test records the throughput
as a baseline. A regression in the throughput is
a defect.

## 8.3 Bulk downloads

A performance test of the bulk downloads SHALL
measure the download time of a documented bulk
file. The performance test records the download
time as a baseline. A regression in the download
time is a defect.

## 8.4 Memory behaviour

A performance test of the memory behaviour SHALL
measure the peak memory of a documented call. The
performance test records the peak memory as a
baseline. A regression in the peak memory is a
defect.

## 8.5 Batch operations

A performance test of the batch operations SHALL
measure the throughput of a documented batch. The
performance test records the throughput as a
baseline. A regression in the throughput is a
defect.

## 8.6 Scalability expectations

A performance test of the scalability SHALL
measure the throughput as a function of the
dataset size. The performance test records the
scaling factor as a baseline. A non-linear scaling
factor is a defect.

## 8.7 Performance baseline

The performance baseline is recorded in the test
result. The baseline is updated when a release
demonstrates an improvement. A regression from the
baseline is a defect.

---

# 9. Data Validation Testing

The data validation testing standard declares the
expectations for verifying the validity of the
canonical dataset.

## 9.1 Canonical models

A data validation test of the canonical models
SHALL verify that every entity of the data model
satisfies the documented validation rules. A test
that finds a deviation SHALL be repaired before
the change is merged.

## 9.2 Metadata

A data validation test of the metadata SHALL verify
that every reference catalogue is loaded, is
cached, and is consistent with the upstream. A
test that finds a deviation SHALL be repaired
before the change is merged.

## 9.3 Trade records

A data validation test of the trade records SHALL
verify that every record satisfies the documented
validation rules. A test that finds a deviation
SHALL be repaired before the change is merged.

## 9.4 ETL transformations

A data validation test of the ETL transformations
SHALL verify that the canonical dataset is
faithfully produced by the ETL layer. A test that
finds a deviation SHALL be repaired before the
change is merged.

## 9.5 Normalization

A data validation test of the normalisation SHALL
verify that the canonical dataset is normalised
correctly. A test that finds a deviation SHALL be
repaired before the change is merged.

## 9.6 Deduplication

A data validation test of the deduplication SHALL
verify that the canonical dataset is
deduplicated correctly. A test that finds a
deviation SHALL be repaired before the change is
merged.

## 9.7 Data integrity

A data validation test of the data integrity
SHALL verify that the canonical dataset preserves
the referential integrity, the schema
compatibility, and the version compatibility. A
test that finds a deviation SHALL be repaired
before the change is merged.

---

# 10. Error Handling Testing

The error handling testing standard declares the
expectations for verifying the error handling of
the SDK.

## 10.1 Authentication failures

An error handling test of the authentication
failures SHALL verify that the SDK raises
`AuthenticationError` on a 401 response. A test
that finds a deviation SHALL be repaired before
the change is merged.

## 10.2 Timeouts

An error handling test of the timeouts SHALL verify
that the SDK raises `TimeoutError` on a timeout.
A test that finds a deviation SHALL be repaired
before the change is merged.

## 10.3 Network failures

An error handling test of the network failures
SHALL verify that the SDK raises `NetworkError`
on a network failure. A test that finds a deviation
SHALL be repaired before the change is merged.

## 10.4 Invalid responses

An error handling test of the invalid responses
SHALL verify that the SDK raises a documented
exception on an invalid response. A test that
finds a deviation SHALL be repaired before the
change is merged.

## 10.5 Pagination failures

An error handling test of the pagination failures
SHALL verify that the SDK raises a documented
exception on a pagination failure. A test that
finds a deviation SHALL be repaired before the
change is merged.

## 10.6 Rate limiting

An error handling test of the rate limiting SHALL
verify that the SDK retries on a 429 response and
honours the `Retry-After` header. A test that finds
a deviation SHALL be repaired before the change
is merged.

## 10.7 Partial downloads

An error handling test of the partial downloads
SHALL verify that the SDK raises a documented
exception on a partial download and deletes the
partial file. A test that finds a deviation SHALL
be repaired before the change is merged.

## 10.8 Unexpected API changes

An error handling test of the unexpected API
changes SHALL verify that the SDK does not raise
an undocumented exception on an unexpected API
change. A test that finds a deviation SHALL be
repaired before the change is merged.

---

# 11. Test Data Strategy

The test data strategy declares the strategy for
managing the test data of the SDK.

## 11.1 Synthetic data

A synthetic dataset is a dataset that is
constructed for the test. A synthetic dataset is
deterministic and does not depend on the live
upstream.

## 11.2 Captured API responses

A captured API response is a response that was
recorded from the live upstream. A captured
response is stored in the `data/` directory and
is versioned.

## 11.3 Reference datasets

A reference dataset is a dataset that is used as
a baseline for a test. A reference dataset is
stored in the `data/` directory and is versioned.

## 11.4 Versioned datasets

A versioned dataset is a dataset that carries a
version identifier. A versioned dataset is
preserved across runs and is rotated when the
upstream changes.

## 11.5 Test isolation

A test SHALL be isolated from every other test. A
test SHALL NOT depend on a global state. A test
SHALL NOT depend on the order of execution. A test
SHALL NOT depend on a dataset that is not
declared in the test.

## 11.6 Reproducibility

A test that passes locally SHALL pass in the
continuous integration pipeline. A test that
fails in the continuous integration pipeline
SHALL be repaired or removed.

## 11.7 Test data lifecycle

The test data lifecycle is:

- **Create.** A test data is created for a new
  test.
- **Use.** A test data is used by a test.
- **Verify.** A test data is verified against the
  upstream on a scheduled cadence.
- **Refresh.** A test data is refreshed when the
  upstream changes.
- **Archive.** A test data is archived when it is
  no longer needed.
- **Delete.** A test data is deleted after the
  retention period.

---

# 12. Coverage Strategy

The coverage strategy declares the expectations
for the test coverage of the SDK.

## 12.1 Public API coverage

Every public method of the SDK SHALL be covered
by at least one test. A test that covers a public
method SHALL verify the documented return type,
the documented parameters, and the documented
exception behaviour.

## 12.2 Business logic coverage

Every business logic rule of the SDK SHALL be
covered by at least one test. A test that covers
a business logic rule SHALL verify the documented
behaviour.

## 12.3 Validation coverage

Every validation rule of the SDK SHALL be covered
by at least one test. A test that covers a
validation rule SHALL verify the documented
behaviour for a valid input and for an invalid
input.

## 12.4 Error path coverage

Every documented error path of every public method
of the SDK SHALL be covered by at least one test.
A test that covers an error path SHALL verify the
documented exception behaviour.

## 12.5 Integration coverage

Every documented integration point of the SDK
SHALL be covered by at least one integration test.
A test that covers an integration point SHALL
verify the documented behaviour of the
interaction.

## 12.6 Coverage threshold

The project SHALL NOT prescribe a percentage
threshold for test coverage. The project SHALL
prescribe a category coverage: every public
method, every business logic rule, every
validation rule, every error path, and every
integration point SHALL be covered. A category
coverage below 100% is a defect.

---

# 13. Quality Gates

The quality gates are the mandatory conditions for
module completion, feature completion, and SDK
release.

## 13.1 Module completion

A module is complete when:

- The module's source code is committed.
- The module's tests are committed.
- The module's documentation is committed.
- The module's tests pass.
- The module's coverage is at the documented
  threshold.
- The module's review is approved.

## 13.2 Feature completion

A feature is complete when:

- The feature's specification is committed.
- The feature's source code is committed.
- The feature's tests are committed.
- The feature's documentation is committed.
- The feature's tests pass.
- The feature's coverage is at the documented
  threshold.
- The feature's review is approved.
- The feature's documentation is published.

## 13.3 SDK release

An SDK release is complete when:

- Every module is complete.
- Every feature in the release is complete.
- The regression suite passes.
- The live API tests pass.
- The performance tests pass.
- The release notes are committed.
- The changelog is updated.
- The version is bumped.
- The documentation is published.
- The package is built.
- The package is signed.
- The package is published to the package index.

## 13.4 Blocking conditions

A change is blocked when:

- A test fails.
- A coverage threshold is not met.
- A review is not approved.
- A documentation is missing.
- A regression is detected.
- A performance regression is detected.
- A security defect is detected.
- A critical or high defect is open.

## 13.5 Acceptance criteria

A change is accepted when:

- Every quality gate is met.
- Every blocking condition is resolved.
- The change is reviewed and approved.
- The change is documented.
- The change is tested.

---

# 14. Release Validation

The release validation declares the release
readiness requirements.

## 14.1 Documentation complete

A release is documented when:

- Every public method is documented.
- Every parameter is documented.
- Every return type is documented.
- Every exception is documented.
- Every configuration parameter is documented.
- The README is up to date.
- The changelog is updated.
- The migration notes (if any) are written.

## 14.2 Public API validated

A release's public API is validated when:

- Every public method is covered by at least one
  test.
- Every public method passes the test.
- Every public method produces the documented
  result.
- Every public method raises the documented
  exception on failure.

## 14.3 Regression suite passing

A release's regression suite is passing when:

- Every regression test passes.
- Every integration test passes.
- Every contract test passes.
- Every mock API test passes.

## 14.4 Compatibility verified

A release's compatibility is verified when:

- The SDK continues to issue the documented
  requests to the upstream API.
- The SDK continues to normalise the documented
  responses.
- The SDK continues to persist the documented
  formats.
- The SDK continues to read the documented
  formats.

## 14.5 Known issues documented

A release's known issues are documented when:

- Every open defect is recorded in the changelog.
- Every deprecation is recorded in the changelog.
- Every migration note is recorded in the
  changelog.
- Every known limitation is recorded in the
  README.

## 14.6 Release readiness criteria

A release is ready when:

- The documentation is complete.
- The public API is validated.
- The regression suite is passing.
- The compatibility is verified.
- The known issues are documented.
- The release notes are published.
- The package is built and signed.

---

# 15. Defect Classification

The defects are classified into the categories
below. The category determines the handling.

## 15.1 Critical

A critical defect is a defect that:

- Causes a data loss.
- Causes a security breach.
- Causes a crash.
- Breaks a documented behaviour of the SDK.

A critical defect SHALL be repaired immediately.
A critical defect SHALL block the release. A
critical defect SHALL be reported to the
maintainers.

## 15.2 High

A high defect is a defect that:

- Causes a degraded behaviour of the SDK.
- Causes a regression in a documented behaviour.
- Breaks a documented edge case.

A high defect SHALL be repaired in the next
release. A high defect SHALL block the release
until it is repaired.

## 15.3 Medium

A medium defect is a defect that:

- Causes a minor inconvenience.
- Causes a degradation in a non-deterministic
  test.
- Causes a minor regression in a non-documented
  behaviour.

A medium defect SHALL be repaired in a future
release. A medium defect SHALL NOT block the
release.

## 15.4 Low

A low defect is a defect that:

- Causes a cosmetic issue.
- Causes a documentation typo.
- Causes a minor inconsistency.

A low defect SHALL be repaired when convenient. A
low defect SHALL NOT block the release.

## 15.5 Informational

An informational defect is a defect that:

- Is a question rather than a defect.
- Is a suggestion rather than a defect.
- Is a note rather than a defect.

An informational defect SHALL be recorded in the
issue tracker. An informational defect SHALL NOT
block the release.

---

# 16. Continuous Verification

The continuous verification section declares how
quality is maintained throughout the development.

## 16.1 Specification reviews

A specification SHALL be reviewed before it is
adopted. A specification review SHALL verify that
the specification is consistent with every
previously approved specification.

## 16.2 Architecture compliance

A change SHALL be reviewed for architecture
compliance. A change that violates the architecture
is rejected.

## 16.3 Regression validation

A change SHALL be validated against the regression
suite. A change that introduces a regression is
rejected.

## 16.4 Release verification

A release SHALL be verified against the release
validation criteria. A release that does not meet
the criteria is blocked.

## 16.5 Documentation synchronization

A change SHALL be accompanied by a documentation
update. A change that is not accompanied by a
documentation update is rejected.

## 16.6 Continuous integration

The continuous integration pipeline SHALL run:

- The unit test suite on every commit.
- The integration test suite on every commit.
- The contract test suite on every commit.
- The mock API test suite on every commit.
- The regression test suite on every commit.
- The performance test suite on a scheduled
  cadence.
- The live API test suite on a scheduled cadence.

The continuous integration pipeline SHALL block
the merge when a test fails.

## 16.7 Continuous deployment

The continuous deployment pipeline SHALL publish
the package to the package index on a successful
release. The continuous deployment pipeline SHALL
publish the documentation to the documentation
site on a successful release.

---

# 17. Assumptions

The assumptions below are recorded for
traceability. An assumption that turns out to be
false is recorded in `DECISIONS.md` as a
correction and is propagated to the relevant
specification documents.

## 17.1 Verified Assumptions

- The upstream is reachable from the public
  internet. Verified by live request.
- The reference endpoints are public and do not
  require a key. Verified.
- The preview endpoint is capped at 500 records.
  Verified.
- The authenticated endpoint is capped at 250,000
  records. Verified.
- The 401 response body is structured. Verified.

## 17.2 Inferred Assumptions

- The default test frequency is every commit for
  the deterministic tests and a scheduled cadence
  for the live tests. The default is inferred
  from common practice; the consumer can override
  the default.
- The default performance baseline is the result
  of the first successful test run. The default is
  inferred from common practice; the consumer can
  override the default.
- The default coverage threshold is 100% by
  category. The default is inferred from common
  practice; the consumer can override the default.
- The default defect category is "Medium". The
  default is inferred from common practice; the
  consumer can override the default.

## 17.3 Local Design Decisions

- The project does not prescribe a percentage
  threshold for test coverage. The project
  prescribes a category coverage: every public
  method, every business logic rule, every
  validation rule, every error path, and every
  integration point SHALL be covered.
- The project prescribes five defect categories:
  Critical, High, Medium, Low, and Informational.
  The categories are the responsibility of the
  maintainers.
- The project prescribes a documentation-first
  validation. The documentation is the source of
  truth; a test verifies that the implementation
  matches the documentation.

---

# 18. Open Questions

The questions below are recorded for future
resolution. Each question is described with the
impact and the suggested verification.

- **OQ-TS-001 (High).** What is the exact
  continuous integration pipeline to be used?
  **Impact.** The test frequency and the test
  environment depend on the pipeline.
  **Suggested verification.** Confirm with the
  packaging specification.

- **OQ-TS-002 (High).** What is the exact package
  index to be used? **Impact.** The release
  process depends on the package index.
  **Suggested verification.** Confirm with the
  packaging specification.

- **OQ-TS-003 (Medium).** What is the exact
  documentation site to be used? **Impact.** The
  release process depends on the documentation
  site. **Suggested verification.** Confirm with
  the packaging specification.

- **OQ-TS-004 (Medium).** Should the test suite
  support property-based testing for the
  normalisation layer? **Impact.** Property-based
  testing would catch more edge cases. **Suggested
  verification.** Confirm with the implementation
  ergonomics.

- **OQ-TS-005 (Medium).** Should the test suite
  support mutation testing for the validation
  layer? **Impact.** Mutation testing would
  catch more validation defects. **Suggested
  verification.** Confirm with the implementation
  ergonomics.

- **OQ-TS-006 (Medium).** Should the test suite
  support a chaos test that simulates upstream
  failures at random intervals? **Impact.** A
  chaos test would catch more resilience defects.
  **Suggested verification.** Confirm with the
  implementation ergonomics.

- **OQ-TS-007 (Medium).** Should the test suite
  support a load test that issues a sustained
  number of requests? **Impact.** A load test
  would catch more rate-limit defects. **Suggested
  verification.** Confirm with the implementation
  ergonomics.

- **OQ-TS-008 (Low).** Should the test suite
  support a snapshot test that compares the
  normalised record against a recorded snapshot?
  **Impact.** A snapshot test would catch more
  normalisation defects. **Suggested verification.**
  Confirm with the implementation ergonomics.

- **OQ-TS-009 (Low).** Should the test suite
  support a fuzz test that issues requests with
  random parameters? **Impact.** A fuzz test would
  catch more validation defects. **Suggested
  verification.** Confirm with the implementation
  ergonomics.

- **OQ-TS-010 (Low).** Should the test suite
  support a conformance test that verifies the
  SDK against the official test fixtures?
  **Impact.** A conformance test would catch
  more upstream-contract defects. **Suggested
  verification.** Confirm with the upstream
  conformance requirements.

---

# End of document
