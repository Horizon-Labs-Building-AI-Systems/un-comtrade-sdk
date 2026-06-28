```
Document ID
014

Title
SDK Packaging & Distribution Specification

Version
0.1.0

Status
DRAFT

Created
2026-06-26T20:40:34Z

Last Updated
2026-06-26T20:40:34Z

Author
Codex

Project
UN Comtrade Python SDK

Dependencies
013_TESTING_STANDARD.md

Supersedes
None
```

---

# 1. Packaging Philosophy

## 1.1 Why packaging matters

The packaging of the SDK is the contract between the
maintainers and the consumers. The package carries
the public interface, the documentation, the
dependencies, the metadata, the version, the
license, and the provenance. A well-designed
package is a faithful reproduction of the SDK
specification. A poorly-designed package forces
the consumer to learn the internals of the SDK to
install it.

The packaging of the SDK is also the boundary
between the source code and the published artefact.
The package is what the consumer installs. The
package is what the consumer upgrades. The package
is what the consumer pins to. The package is the
unit of compatibility.

## 1.2 Public distribution goals

The public distribution goals of the SDK are:

- **Discoverability.** The package is published to
  the standard Python package index with a
  documented name, a documented description, and
  documented keywords.
- **Installability.** The package is installable with
  a single command on every supported Python
  version and every supported operating system.
- **Reproducibility.** The package is reproducible:
  a given version of the package produces the same
  artefact on every build.
- **Verifiability.** The package is verifiable: a
  consumer can verify the integrity and the
  provenance of the package.
- **Maintainability.** The package is maintainable:
  a maintainer can publish a new version without
  breaking the existing consumers.

## 1.3 Ease of installation

The ease of installation is a first-class goal. A
consumer SHALL be able to install the SDK with a
single command. The default installation SHALL
include only the required dependencies. The
optional dependencies SHALL be installable through
a documented extras mechanism.

## 1.4 Long-term maintainability

The long-term maintainability of the SDK is a
first-class goal. The package SHALL be maintainable
by a single maintainer. The package SHALL NOT
depend on a build infrastructure that is not
documented. The package SHALL NOT depend on a
publication workflow that is not documented.

## 1.5 Backward compatibility

The backward compatibility of the SDK is preserved
within a major version. A consumer that pins to a
major version of the SDK SHALL be able to upgrade
to any later release within the same major version
without modifying consumer code.

---

# 2. Package Architecture

The package architecture is the logical layout of
the SDK source tree. The architecture is declarative;
the physical layout is the responsibility of the
concrete build system.

## 2.1 Top-Level Package

The top-level package is `un_comtrade`. The package
is the import name. The distribution name is
`un-comtrade-sdk`. The two names are related but
distinct; the import name follows the Python
convention, the distribution name follows the
PyPI convention.

## 2.2 Public Sub-Packages

The public sub-packages are:

- `un_comtrade.client` — the SDK client.
- `un_comtrade.metadata` — the metadata layer.
- `un_comtrade.trade` — the trade layer.
- `un_comtrade.transport` — the transport layer.
- `un_comtrade.validation` — the validation layer.
- `un_comtrade.normalisation` — the normalisation
  layer.
- `un_comtrade.export` — the export layer.
- `un_comtrade.storage` — the storage layer.
- `un_comtrade.config` — the configuration object.
- `un_comtrade.logging` — the logging seam.
- `un_comtrade.errors` — the exception hierarchy.
- `un_comtrade.pagination` — the pagination helpers.
- `un_comtrade.retry` — the retry helpers.
- `un_comtrade.cache` — the storage-layer entry
  points.
- `un_comtrade.models` — the stable data model.
- `un_comtrade.utils` — the cross-cutting utilities.

The public sub-packages are declared in
`003_ARCHITECTURE.md` §9.2. The list above is
normative; a future addition is allowed through a
documented decision.

## 2.3 Internal Sub-Packages

The internal sub-packages are prefixed with an
underscore and are not part of the public surface.
A consumer SHALL NOT import an internal sub-
package. The internal sub-packages are owned by the
maintainers and may change at any time.

## 2.4 Documentation

The documentation is distributed alongside the
package. The documentation is built from the
`docs/` source tree. The documentation is published
to the documentation site. The documentation is
versioned with the package.

## 2.5 Examples

The examples are distributed alongside the
package. The examples are runnable scripts that
demonstrate the public surface. The examples are
versioned with the package.

## 2.6 Tests

The tests are distributed alongside the package
as a development extra. A consumer that installs
the test extra SHALL be able to run the test
suite.

## 2.7 CLI

The CLI is distributed alongside the package. The
CLI is a thin wrapper over the SDK. The CLI is
versioned with the package.

## 2.8 Optional Extensions

The optional extensions are distributed as separate
packages. An optional extension is a documented
companion to the SDK that adds a new capability
without modifying the SDK.

## 2.8 Ownership

The ownership of the package is the maintainers.
The maintainers are responsible for:

- Publishing the package.
- Signing the package.
- Responding to consumer issues.
- Maintaining the package metadata.
- Maintaining the documentation.
- Maintaining the examples.
- Maintaining the tests.
- Maintaining the CLI.
- Maintaining the optional extensions.

---

# 3. Distribution Strategy

The distribution strategy declares the channels
through which the SDK is distributed.

## 3.1 PyPI

- **Purpose.** Public distribution of the package.
- **Audience.** Every Python developer.
- **Support status.** Primary distribution channel.
- **Lifecycle.** Every release is published to PyPI.

## 3.2 Source Distribution

- **Purpose.** Source-level distribution of the
  package.
- **Audience.** Consumers that need to build the
  package from source.
- **Support status.** Primary distribution channel.
- **Lifecycle.** Every release produces a source
  distribution.

## 3.3 Wheel Distribution

- **Purpose.** Binary distribution of the package.
- **Audience.** Every Python developer.
- **Support status.** Primary distribution channel.
- **Lifecycle.** Every release produces a wheel for
  every supported Python version and every
  supported operating system.

## 3.4 Local Installation

- **Purpose.** Installation from a local file.
- **Audience.** Consumers that have downloaded the
  package manually.
- **Support status.** Supported.
- **Lifecycle.** Every release produces a local
  installation artefact.

## 3.5 Editable/Development Installation

- **Purpose.** Installation from a local source
  tree.
- **Audience.** Maintainers and contributors.
- **Support status.** Supported.
- **Lifecycle.** Every commit of the source tree
  is installable as an editable package.

## 3.6 Future Enterprise Deployment

- **Purpose.** Installation from an enterprise
  package index.
- **Audience.** Enterprise consumers.
- **Support status.** Reserved for a future version.
- **Lifecycle.** TBD.

## 3.7 Summary

| Channel                    | Status   | Lifecycle     |
| -------------------------- | -------- | ------------- |
| PyPI                       | Primary  | Every release |
| Source distribution        | Primary  | Every release |
| Wheel distribution         | Primary  | Every release |
| Local installation         | Supported| Every release |
| Editable installation      | Supported| Every commit  |
| Enterprise deployment      | Future   | TBD           |

---

# 4. Versioning Strategy

The versioning strategy declares the project
versioning model. The model is Semantic Versioning
2.0.0, as refined by `000_PROJECT_CHARTER.md` §14.

## 4.1 Semantic Versioning

The version is encoded as `MAJOR.MINOR.PATCH`. A
pre-release version is encoded as
`MAJOR.MINOR.PATCH-IDENTIFIER`.

## 4.2 Major Releases

A major release increments `MAJOR`. A major release
is reserved for breaking changes to the documented
public interface. A major release is published when
a breaking change is unavoidable.

## 4.3 Minor Releases

A minor release increments `MINOR`. A minor release
is reserved for backward-compatible features. A
minor release is published when a new feature is
added.

## 4.4 Patch Releases

A patch release increments `PATCH`. A patch release
is reserved for backward-compatible corrections. A
patch release is published when a bug is fixed or a
documentation error is corrected.

## 4.5 Pre-Release Versions

A pre-release version is encoded with a hyphen and
a series of dot-separated identifiers. Examples:
`0.1.0a1`, `0.2.0b1`, `1.0.0rc1`.

## 4.6 Alpha

An alpha release is a pre-release version that is
intended for internal testing. The alpha release is
labelled with the `a` identifier (`0.1.0a1`,
`0.1.0a2`).

## 4.7 Beta

A beta release is a pre-release version that is
intended for external testing. The beta release is
labelled with the `b` identifier (`0.1.0b1`,
`0.1.0b2`).

## 4.8 Release Candidate

A release candidate is a pre-release version that
is intended for final validation. The release
candidate is labelled with the `rc` identifier
(`1.0.0rc1`, `1.0.0rc2`).

## 4.9 Stable

A stable release is a final release. The stable
release is the version that the consumer is
expected to install.

## 4.10 Permitted Changes Per Level

| Level    | Permitted changes                                                |
| -------- | --------------------------------------------------------------- |
| Major    | Removal, renaming, signature change of public interface.        |
| Minor    | New methods, new optional parameters, new entities, new values. |
| Patch    | Bug fixes, documentation corrections, internal refactors.        |
| Alpha    | Any change.                                                     |
| Beta     | Any change except breaking changes to the public interface.     |
| RC       | Bug fixes only.                                                 |
| Stable   | Bug fixes only (after release).                                 |

---

# 5. Compatibility Policy

The compatibility policy declares the rules that
govern the compatibility of the SDK across
versions.

## 5.1 Backward Compatibility

A change is backward compatible when a consumer
that upgrades within a major version can continue
to use the SDK without modifying consumer code.
The compatibility rules are declared in
`000_PROJECT_CHARTER.md` §10.1.

## 5.2 Forward Compatibility

The SDK is not forward compatible. A consumer that
installs a future version of the SDK may observe
new behaviour. The forward compatibility is
limited by the SemVer expectation that a consumer
will pin to a major version.

## 5.3 Deprecation Process

A documented public element may be marked
deprecated by:

1. Adding a deprecation note to the documentation.
2. Adding a deprecation warning to the runtime.
3. Adding a changelog entry.

The deprecation period SHALL last at least one
minor release before the element is removed in
the next major release. The deprecation note
SHALL explain the migration path.

## 5.4 Breaking Change Policy

A breaking change is a change that requires a
consumer to modify consumer code to continue
using the documented behaviour. A breaking change
SHALL be reserved for a major version increment.
A breaking change SHALL be recorded in
`DECISIONS.md` before the change is committed.

The breaking change rules are declared in
`000_PROJECT_CHARTER.md` §14.5.

## 5.5 Migration Expectations

A consumer that upgrades across a major version
SHALL be able to migrate the consumer code by
following the documented migration guide. The
migration guide SHALL be published in the
documentation. The migration guide SHALL be
discoverable through the README.

## 5.6 Support Window

A major version of the SDK is supported for a
documented period. The support window is the
period during which the maintainers SHALL:

- Publish patch releases for critical and high
  defects.
- Respond to consumer issues.
- Maintain the documentation.
- Maintain the examples.

The support window SHALL be at least 12 months
from the release of the major version. The support
window SHALL be documented in the README.

---

# 6. Dependency Management

The dependency management section declares the
dependency philosophy of the SDK.

## 6.1 Dependency Categories

The dependencies of the SDK are partitioned into
the categories below. The categories determine the
installation policy.

- **Required.** A dependency that is required for
  the SDK to function. A required dependency is
  installed by default.
- **Optional.** A dependency that is required for
  an optional feature. An optional dependency is
  installed through an extras mechanism.
- **Development.** A dependency that is required
  for development. A development dependency is
  installed through a development extra.
- **Documentation.** A dependency that is required
  for the documentation build. A documentation
  dependency is installed through a documentation
  extra.
- **Testing.** A dependency that is required for
  the test suite. A testing dependency is installed
  through a testing extra.

## 6.2 Required Dependencies

The required dependencies of the SDK are the
dependencies that are required for the SDK to
function. The required dependencies are:

- The Python standard library.
- The `httpx` library, for HTTP transport (sync and async).

The required dependencies are documented in the
SDK specification. The required dependencies
SHALL NOT include a library that is not required
for the documented functionality.

## 6.3 Optional Dependencies

The optional dependencies of the SDK are the
dependencies that are required for an optional
feature. The optional dependencies are:

- A data-analysis library, for the optional DataFrame
  handoff shape (OQ-SDK-006).
- A structured-logging library, for richer log
  records (OQ-IS-004).
- A caching library, for an optional high-
  performance cache backend (OQ-IS-003).

The optional dependencies are installed through
extras. The extras are documented in the README.

## 6.4 Development Dependencies

The development dependencies of the SDK are the
dependencies that are required for development.
The development dependencies include the testing
framework, the linting framework, the formatting
framework, the type-checking framework, and the
documentation framework.

## 6.5 Documentation Dependencies

The documentation dependencies of the SDK are the
dependencies that are required for the
documentation build. The documentation
dependencies include the documentation framework
(e.g. Sphinx, MkDocs) and the theme.

## 6.6 Testing Dependencies

The testing dependencies of the SDK are the
dependencies that are required for the test
suite. The testing dependencies include the test
runner, the mocking framework, the assertion
library, and the coverage tool.

## 6.7 Minimal Dependency Footprint

The dependency footprint of the SDK is the
smallest set of dependencies that allows the
documented functionality. A new runtime
dependency SHALL be approved by a recorded
decision in `DECISIONS.md`. A runtime dependency
SHALL be removed only through a major version
increment.

## 6.8 Version Pinning Strategy

The version of each dependency SHALL be pinned to a
minimum compatible version and a maximum tested
version. The pin is documented in the package
metadata. The pin SHALL be updated through a
recorded decision.

The minimum compatible version is the lowest
version of the dependency that supports the
documented functionality. The maximum tested
version is the highest version of the dependency
that has been tested by the maintainers.

## 6.9 Dependency Update Policy

A dependency update is published through a minor
or patch release. A dependency update SHALL be
recorded in the changelog. A dependency update
that introduces a breaking change in the
dependency SHALL be published through a major
release of the SDK.

## 6.10 Dependency Audit

The maintainers SHALL audit the dependencies on a
scheduled cadence. The audit records the current
version, the available updates, the security
advisories, and the recommended action. The
audit is published in the documentation.

---

# 7. Command-Line Interface (CLI)

The CLI is a thin wrapper over the SDK. The CLI
exposes a small subset of the public surface
through a command-line interface.

## 7.1 Purpose

The purpose of the CLI is to enable quick
exploration of the UN Comtrade data without
writing a Python script. The CLI is a complement
to the SDK, not a replacement.

## 7.2 Supported Operations

The CLI supports the operations below. Each
operation is a thin wrapper over a public SDK
method.

- `un-comtrade get-countries` — list the reporter
  countries.
- `un-comtrade get-partners` — list the partner
  countries.
- `un-comtrade get-hs-codes` — list the HS codes.
- `un-comtrade search-hs <query>` — search the HS
  codes.
- `un-comtrade get-exports <reporter> <period>`
  — list the exports of a reporter.
- `un-comtrade get-imports <reporter> <period>`
  — list the imports of a reporter.
- `un-comtrade get-trade <reporter> <flow>
  <period>` — list the trade of a reporter.
- `un-comtrade get-trade-balance <reporter>
  <period>` — list the trade balance of a
  reporter.
- `un-comtrade download-country-trade <reporter>
  <period> <directory>` — download a country's
  trade.
- `un-comtrade download-world-trade <reporter>
  <period> <directory>` — download a country's
  world trade.

## 7.3 Relationship to SDK

The CLI calls the SDK. The CLI does not implement
any logic that is not in the SDK. The CLI is a
thin wrapper; the SDK is the source of truth.

## 7.4 Relationship to Public API

The CLI exposes a small subset of the public API.
A consumer that wants the full surface uses the
SDK directly. The CLI is not a substitute for the
SDK.

## 7.5 Future Extensibility

The CLI is extended in a minor version. A new
command is added to the CLI when a new SDK method
is added. The new command SHALL be a thin wrapper
over the new SDK method.

---

# 8. Installation Strategy

The installation strategy declares the supported
installation scenarios.

## 8.1 Production

A production installation is the default
installation. A consumer installs the SDK with
the documented command. The default installation
includes only the required dependencies.

## 8.2 Development

A development installation is the installation
that includes the development dependencies. A
maintainer or a contributor installs the SDK with
the documented development command. The
development installation includes the testing
framework, the linting framework, the formatting
framework, the type-checking framework, and the
documentation framework.

## 8.3 Offline Installation

An offline installation is the installation from
a local package file. A consumer that does not
have a network connection installs the SDK from
a local file. The offline installation is
supported.

## 8.4 Local Source Installation

A local source installation is the installation
from a local source tree. A maintainer or a
contributor installs the SDK from a local source
tree. The local source installation is supported.

## 8.5 Future Enterprise Deployment

A future enterprise deployment is the
installation from an enterprise package index.
The enterprise deployment is reserved for a
future version.

---

# 9. Release Lifecycle

The release lifecycle describes the path that a
release follows from development to stable.

```
Development
    |
    v
Internal Validation
    |
    v
Alpha
    |
    v
Beta
    |
    v
Release Candidate
    |
    v
Stable Release
```

## 9.1 Development

The development stage is the active development
of the next release. The development is performed
on the `main` branch of the source repository. The
development is gated by the continuous integration
pipeline.

## 9.2 Internal Validation

The internal validation stage is the validation
of the next release by the maintainers. The
internal validation is performed on a dedicated
branch. The internal validation records the
results in the release notes.

## 9.3 Alpha

The alpha stage is the first public release of
the next version. The alpha release is published
as a pre-release. The alpha release is intended
for early adopters.

## 9.4 Beta

The beta stage is the second public release of
the next version. The beta release is published
as a pre-release. The beta release is intended
for broader testing.

## 9.5 Release Candidate

The release candidate stage is the third public
release of the next version. The release
candidate is published as a pre-release. The
release candidate is intended for final
validation.

## 9.6 Stable Release

The stable release is the final release of the
next version. The stable release is published
as a non-pre-release. The stable release is the
version that the consumer is expected to install.

---

# 10. Documentation Packaging

The documentation is distributed alongside the
package. The documentation is built from the
`docs/` source tree. The documentation is
versioned with the package.

## 10.1 API Reference

The API reference is the documentation of every
public class, function, method, parameter, return
type, and exception. The API reference is built
from the docstrings of the public surface. The API
reference is the authoritative documentation of
the public surface.

## 10.2 Getting Started

The getting started guide is the documentation of
the supported workflows. The getting started
guide is the first documentation that a consumer
reads. The getting started guide includes the
installation instructions, the configuration
instructions, and the first example.

## 10.3 Examples

The examples are runnable scripts that demonstrate
the public surface. The examples are distributed
in the `examples/` directory. The examples are
versioned with the package.

## 10.4 Migration Guides

A migration guide is the documentation of the
migration path from a previous major version to
the current major version. A migration guide is
published for every major version. The migration
guide is discoverable through the README.

## 10.5 Release Notes

The release notes are the documentation of the
changes in every release. The release notes
include the new features, the bug fixes, the
breaking changes, and the deprecations. The
release notes are discoverable through the
README.

## 10.6 Changelog

The changelog is the append-only record of every
change. The changelog is distributed with the
package. The changelog is the source of truth for
the release notes.

## 10.7 Architecture Documentation

The architecture documentation is the
documentation of the SDK architecture. The
architecture documentation is the
`003_ARCHITECTURE.md` and the related
specifications. The architecture documentation is
discoverable through the README.

---

# 11. Upgrade Strategy

The upgrade strategy declares the rules that govern
the upgrade of the SDK across versions.

## 11.1 Version Upgrades

A consumer upgrades the SDK by installing a new
version. A version upgrade is performed through
the documented install command. A version upgrade
SHOULD be performed through a requirements file
or a lock file.

## 11.2 Breaking Upgrades

A breaking upgrade is an upgrade across a major
version. A breaking upgrade is supported by the
migration guide. A consumer that performs a
breaking upgrade SHALL follow the migration guide
and SHALL update the consumer code accordingly.

## 11.3 Migration Documentation

A migration documentation is published for every
major version. The migration documentation
includes:

- The list of breaking changes.
- The migration path for each breaking change.
- The list of deprecations.
- The list of new features.
- The list of bug fixes.

## 11.4 Compatibility Checks

A compatibility check is a documented procedure
that a consumer can use to verify that the
consumer code is compatible with a new version
of the SDK. A compatibility check is published
in the migration documentation.

## 11.5 Rollback Expectations

A rollback is the act of reverting to a previous
version of the SDK. A rollback is supported by
the package index. A consumer that performs a
rollback SHALL pin the consumer code to the
previous version.

---

# 12. Distribution Artifacts

The distribution artefacts are the deliverables of
the build and the publication process.

## 12.1 Source Package

The source package is the tar.gz archive of the
SDK source tree. The source package is the
canonical artefact. The source package is
reproducible from the source repository.

## 12.2 Binary Wheel

The binary wheel is the platform-specific binary
distribution of the SDK. A wheel is produced for
every supported Python version and every
supported operating system. A wheel is
reproducible from the source repository.

## 12.3 Documentation

The documentation is the HTML site built from the
`docs/` source tree. The documentation is
published to the documentation site. The
documentation is versioned with the package.

## 12.4 CLI

The CLI is the entry point installed alongside the
package. The CLI is a thin wrapper over the SDK.
The CLI is the same binary as the package.

## 12.5 Example Datasets

The example datasets are recorded upstream
responses that demonstrate the public surface.
The example datasets are distributed in the
`data/` directory. The example datasets are
versioned with the package.

## 12.6 License

The license is the legal terms under which the
package is distributed. The license is the
`LICENSE` file. The license is the same for every
artefact.

## 12.7 Changelog

The changelog is the append-only record of every
change. The changelog is the `CHANGELOG.md` file.
The changelog is versioned with the package.

## 12.8 Summary

| Artefact             | Format            | Versioned? |
| -------------------- | ----------------- | ---------- |
| Source package       | tar.gz            | Yes        |
| Binary wheel         | .whl              | Yes        |
| Documentation        | HTML              | Yes        |
| CLI                  | entry point       | Yes        |
| Example datasets     | JSON              | Yes        |
| License              | plain text        | Yes        |
| Changelog            | markdown          | Yes        |

---

# 13. Repository Layout

The repository layout is the logical organisation
of the source tree. The layout is declarative; the
physical layout is the responsibility of the
version-control system.

## 13.1 Top-Level Directories

The top-level directories are:

- `docs/` — the documentation source tree.
- `sdk/` — the SDK source tree.
- `tests/` — the test suite.
- `examples/` — the example scripts.
- `notebooks/` — the Jupyter notebooks.
- `scripts/` — the maintainer scripts.
- `data/` — the example datasets.

## 13.2 Documentation

The `docs/` directory contains the documentation
source tree. The directory is the source of truth
for the documentation. The directory is the
authoritative reference for the architecture, the
data model, the SDK specification, the layer
specifications, the ETL specification, the storage
specification, the testing standard, the packaging
specification, the coding standard, and the
roadmap.

## 13.3 SDK

The `sdk/` directory contains the SDK source
tree. The directory contains the top-level
package `un_comtrade` and the public sub-packages.
The directory is the source of truth for the SDK
implementation.

## 13.4 Tests

The `tests/` directory contains the test suite.
The directory contains the unit tests, the
integration tests, the contract tests, the mock
API tests, the regression tests, the performance
tests, the end-to-end tests, and the release
validation tests.

## 13.5 Examples

The `examples/` directory contains the example
scripts. The directory contains the runnable
scripts that demonstrate the public surface. The
directory is the source of truth for the example
scripts.

## 13.6 Notebooks

The `notebooks/` directory contains the Jupyter
notebooks. The directory contains the notebooks
that exercise the SDK against live and recorded
data.

## 13.7 Scripts

The `scripts/` directory contains the maintainer
scripts. The directory contains the scripts for
release engineering, metadata refresh, and
repository maintenance.

## 13.8 Data

The `data/` directory contains the example
datasets. The directory contains the recorded
upstream responses that the example scripts and
the notebooks consume.

## 13.9 Build Artifacts

The build artefacts are produced by the build
process. The build artefacts are not committed to
the repository. The build artefacts are the
output of the build process.

---

# 14. Future Extensibility

The future extensibility section declares how new
plugins, extensions, optional modules, and
additional distribution targets can be introduced
without affecting existing consumers.

## 14.1 New Plugins

A new plugin is a documented companion to the
SDK that adds a new capability. A new plugin is
distributed as a separate package. A new plugin
SHALL conform to the documented extension point.

## 14.2 New Extensions

A new extension is a documented addition to the
SDK. A new extension is added in a minor version.
A new extension SHALL be backward compatible
within a major version.

## 14.3 New Optional Modules

A new optional module is a documented addition to
the SDK that is not required for the documented
functionality. A new optional module is
installed through an extras mechanism. A new
optional module SHALL NOT change the behaviour
of the existing modules.

## 14.4 New Distribution Targets

A new distribution target is a new channel
through which the SDK is distributed. A new
distribution target is added in a minor version.
A new distribution target SHALL be documented
in section 3 of this document.

## 14.5 New Python Versions

A new Python version is added in a minor version.
A new Python version SHALL be supported for the
duration of the major version.

## 14.6 New Operating Systems

A new operating system is added in a minor
version. A new operating system SHALL be supported
for the duration of the major version.

## 14.7 Backward Compatibility

Every extension listed in this section preserves
backward compatibility within a major version.
A breaking change is reserved for a major
version increment.

---

# 15. Assumptions

The assumptions below are recorded for
traceability. An assumption that turns out to be
false is recorded in `DECISIONS.md` as a
correction and is propagated to the relevant
specification documents.

## 15.1 Verified Assumptions

- The top-level package is `un_comtrade`. Verified
  by the architecture document.
- The distribution name is `un-comtrade-sdk`.
  Verified by the architecture document.
- The supported Python versions are the ones
  recorded in `000_PROJECT_CHARTER.md` §6.
  Verified.
- The default installation includes only the
  required dependencies. Verified by the package
  metadata.

## 15.2 Inferred Assumptions

- The support window for a major version is at
  least 12 months. The default is inferred from
  common practice; the consumer can override the
  default.
- The default version pinning is a minimum
  compatible version and a maximum tested version.
  The default is inferred from common practice;
  the consumer can override the default.
- The default distribution channel is PyPI. The
  default is inferred from common practice; the
  consumer can override the default.
- The default documentation site is the
  documentation site configured for the project.
  The default is inferred from common practice;
  the consumer can override the default.

## 15.3 Local Design Decisions

- The package uses the `un_comtrade` import name
  and the `un-comtrade-sdk` distribution name. The
  names are local design decisions.
- The CLI is named `un-comtrade`. The name is a
  local design decision.
- The support window is at least 12 months. The
  window is a local design decision.
- The default installation policy is to install
  only the required dependencies. The policy is a
  local design decision.
- The default version pinning is a minimum
  compatible version and a maximum tested version.
  The pinning is a local design decision.
- The default release schedule is on-demand. The
  schedule is a local design decision.

---

# 16. Open Questions

The questions below are recorded for future
resolution. Each question is described with the
impact and the suggested verification.

- **OQ-PS-001 (High).** What is the exact
  continuous integration pipeline to be used?
  **Impact.** The build process and the test
  process depend on the pipeline. **Suggested
  verification.** Confirm with the testing
  standard.

- **OQ-PS-002 (High).** What is the exact package
  index to be used? **Impact.** The publication
  process depends on the package index.
  **Suggested verification.** Confirm with the
  maintainers.

- **OQ-PS-003 (High).** What is the exact
  documentation site to be used? **Impact.** The
  documentation publication process depends on
  the documentation site. **Suggested verification.**
  Confirm with the maintainers.

- **OQ-PS-004 (Medium).** What is the exact
  signing key to be used for the package? **Impact.**
  The signature is part of the package's
  provenance. **Suggested verification.** Confirm
  with the maintainers.

- **OQ-PS-005 (Medium).** What is the exact release
  schedule (on-demand vs. scheduled)? **Impact.**
  The release cadence affects the consumer's
  upgrade planning. **Suggested verification.**
  Confirm with the maintainers.

- **OQ-PS-006 (Medium).** What is the exact
  Python version support policy? **Impact.** The
  Python version support affects the consumer's
  compatibility planning. **Suggested
  verification.** Confirm with the maintainers.

- **OQ-PS-007 (Medium).** What is the exact
  operating system support policy? **Impact.**
  The operating system support affects the
  consumer's compatibility planning. **Suggested
  verification.** Confirm with the maintainers.

- **OQ-PS-008 (Medium).** What is the exact
  changelog format? **Impact.** The changelog
  format affects the tooling. **Suggested
  verification.** Confirm with the maintainers.

- **OQ-PS-009 (Low).** Should the package support
  a `pip install un-comtrade-sdk[all]` mechanism
  that installs every optional dependency?
  **Impact.** The mechanism enables a "kitchen
  sink" installation. **Suggested verification.**
  Confirm with the consumer requirements.

- **OQ-PS-010 (Low).** Should the package support
  a Docker image as a distribution target?
  **Impact.** A Docker image would enable
  reproducible deployments. **Suggested
  verification.** Confirm with the consumer
  requirements.

---

# End of document
