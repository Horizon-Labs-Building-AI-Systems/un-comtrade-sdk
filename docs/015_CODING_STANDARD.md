```
Document ID
015

Title
Engineering Coding & Quality Standard

Version
0.1.0

Status
DRAFT

Created
2026-06-26T20:43:52Z

Last Updated
2026-06-26T20:43:52Z

Author
Codex

Project
UN Comtrade Python SDK

Dependencies
014_PACKAGING_SPECIFICATION.md

Supersedes
None
```

---

# 1. Engineering Philosophy

## 1.1 Readability over cleverness

The code is written to be read. The maintainers
optimise for the reader, not for the writer.
Cleverness is avoided in favour of clarity. A
clever one-liner is rewritten as a clear
multi-line statement when the rewrite improves
readability.

## 1.2 Explicit over implicit

The code is explicit. The dependencies are explicit.
The configuration is explicit. The error handling
is explicit. The lifecycle is explicit. A reader
who reads the code SHALL be able to understand
the behaviour without reading the implementation
of a callee.

## 1.3 Deterministic implementation

The code is deterministic. Given the same input
and the same configuration, the code produces the
same output. Caching, retry, and rate-limit logic
do not introduce hidden non-determinism into
consumer code.

## 1.4 Maintainability first

The code is maintainable. The maintainers
optimise for the next maintainer, not for the
current author. A code change that is hard to
maintain is rejected even if it is faster or
shorter.

## 1.5 Simplicity over unnecessary abstraction

The code is simple. An abstraction is added when
it reduces complexity, not when it adds
complexity. A premature abstraction is a defect.

## 1.6 Documentation-driven development

The code follows the documentation. The
documentation is the source of truth. A change
to the code without a corresponding change to
the documentation is rejected.

## 1.7 Type safety

The code is type-safe. Every public interface
declares type hints. The type hints are precise.
The type hints are part of the documented
interface.

## 1.8 Testability

The code is testable. Every public interface is
testable in isolation. The code that is not
testable is a defect.

## 1.9 Backward compatibility

The code preserves backward compatibility within
a major version. A breaking change is reserved for
a major version increment and is recorded in
`DECISIONS.md`.

## 1.10 Layer separation

The code respects the layer boundaries. A lower
layer SHALL NOT invoke a higher layer. A layer
that needs a capability of a non-adjacent layer
SHALL route the call through the intervening
layers.

---

# 2. Python Version Standards

## 2.1 Supported Python Versions

The supported Python versions are the ones recorded
in `000_PROJECT_CHARTER.md` §6. The minimum supported
version is the most recent Python release that is
still receiving security fixes. The recommended
version is the latest stable release.

## 2.2 Permitted Language Features

The following language features are permitted:

- Type hints, including `typing.Optional`,
  `typing.Union`, `typing.List`, `typing.Dict`,
  `typing.Any`, `typing.Callable`, `typing.Iterator`,
  `typing.Iterable`, `typing.Mapping`,
  `typing.Sequence`, `typing.Set`, `typing.Tuple`,
  `typing.Type`, `typing.Generic`.
- f-strings.
- Context managers.
- Decorators.
- Iterators and generators.
- Comprehensions.
- Destructuring assignments.
- Dataclasses (in the standard library).
- Context variables (where appropriate).
- Structural pattern matching (where appropriate,
  when supported by the minimum Python version).
- Type aliases.
- `match` statement (where appropriate, when
  supported by the minimum Python version).

## 2.3 Prohibited Language Features

The following language features are prohibited:

- Wildcard imports.
- Relative imports across module boundaries.
- Direct mutation of imported modules.
- Global variables.
- Mutable default arguments.
- `eval`, `exec`, `compile`.
- `__import__` dynamic imports.
- `pickle`, `cPickle` for untrusted data.
- `subprocess` with `shell=True` and untrusted
  input.
- `os.system` with untrusted input.
- `assert` for production logic (assertions may be
  disabled with `python -O`).
- Print statements for production logging.

## 2.4 Dependency Footprint

The dependency footprint of the SDK is the
smallest set of dependencies that allows the
documented functionality. A new runtime
dependency SHALL be approved by a recorded
decision. A runtime dependency SHALL be removed
only through a major version increment.

---

# 3. Code Style

## 3.1 PEP 8 Compliance

The code complies with PEP 8. The linting
framework enforces the compliance. The compliance
SHALL be verified on every commit.

## 3.2 Maximum Line Length

The maximum line length is 100 characters. A
docstring line MAY exceed the limit when the
exceeded line is a URL. The compliance SHALL be
verified on every commit.

## 3.3 File Organization

A file is organised in the following order:

1. Module docstring.
2. Imports (standard library, then third-party,
   then project, then relative).
3. Module-level constants.
4. Module-level type aliases.
5. Module-level functions.
6. Module-level classes.
7. The module's `__all__` declaration (if any).

## 3.4 Whitespace

The whitespace policy is:

- 4 spaces per indentation level.
- No tabs.
- 2 blank lines between top-level definitions.
- 1 blank line between method definitions.
- No trailing whitespace.
- Single newline at the end of the file.

## 3.5 Import Ordering

The imports are organised in three groups,
separated by a single blank line:

1. Standard library imports.
2. Third-party imports.
3. Project imports.

Within each group, the imports are sorted
alphabetically by module name. The linting
framework enforces the ordering.

## 3.6 Consistent Formatting

The formatting is consistent across the codebase.
The formatting framework enforces the consistency.
The compliance SHALL be verified on every commit.
The format SHALL NOT be edited manually; the
formatting framework SHALL be the source of truth.

---

# 4. Type Hinting Standard

## 4.1 Function Signatures

Every public function declares a type hint for
every parameter and for the return value. The
type hints are precise. The type hints are part
of the documented interface.

## 4.2 Method Signatures

Every public method declares a type hint for every
parameter and for the return value. The type
hints are precise. The type hints are part of the
documented interface. The type hints include the
`self` parameter only when the method overrides a
parent class.

## 4.3 Class Attributes

Every public class attribute declares a type hint.
The type hint is part of the documented interface.

## 4.4 Return Types

Every function and method declares a return type.
A function that does not return a value declares
`-> None`. A function that returns a value
declares the precise type. A function that may
return `None` declares `-> Optional[Type]`.

## 4.5 Optional Values

An optional value is declared as `Optional[Type]`.
The `Optional` type is imported from `typing`.
The optional value is documented in the function
or method's docstring.

## 4.6 Generic Types

A generic type is declared as `Type[T]`. The
generic type is imported from `typing`. The
generic type is documented in the function or
method's docstring.

## 4.7 Where Typing is Mandatory

The type hint is mandatory on:

- Every public function.
- Every public method.
- Every public class.
- Every public attribute.
- Every internal function whose signature is
  non-trivial.
- Every internal method whose signature is
  non-trivial.

The type hint is not mandatory on:

- Test code that is local to a test.
- Script code that is local to a script.
- A variable that is assigned a literal value
  and is used immediately.

---

# 5. Documentation Standard

## 5.1 Module Docstrings

Every module declares a module docstring. The
module docstring describes the purpose of the
module, the public surface of the module, and
any module-level constants.

## 5.2 Class Docstrings

Every public class declares a class docstring. The
class docstring describes the purpose of the
class, the public surface of the class, the
constructor parameters, and the instance
attributes.

## 5.3 Public Method Docstrings

Every public method declares a method docstring.
The method docstring describes the purpose of
the method, the parameters, the return value, the
exceptions, and the side effects.

## 5.4 Parameter Documentation

Every parameter is documented in the function or
method's docstring. The parameter documentation
includes the parameter name, the type, the
purpose, the default value, and the allowed
values.

## 5.5 Return Documentation

The return value is documented in the function
or method's docstring. The return documentation
includes the type, the meaning, and the
conditions under which the return value is
produced.

## 5.6 Exception Documentation

Every exception that the function or method
raises is documented in the function or method's
docstring. The exception documentation includes
the exception type, the cause, and the recovery
strategy.

## 5.7 Usage Notes

The function or method's docstring MAY include
usage notes. The usage notes describe the
intended use cases, the intended audience, and
any caveats.

## 5.8 Documentation Style

The documentation style is the standard declared
in `007_SDK_SPECIFICATION.md` §4. Every public
method follows the template of the SDK
specification. The style is consistent across the
codebase.

---

# 6. Import Standards

## 6.1 Standard Library Imports

The standard library imports are imported from the
top-level module. The standard library imports
are listed first.

## 6.2 Third-Party Imports

The third-party imports are imported from the
top-level module. The third-party imports are
listed second. The third-party imports SHALL be
the minimum set required for the documented
functionality.

## 6.3 Project Imports

The project imports are imported from the project
package. The project imports are listed third. The
project imports SHALL NOT be relative.

## 6.4 Relative vs. Absolute Imports

The project imports SHALL be absolute. The
relative imports are prohibited.

## 6.5 Import Grouping

The imports are grouped as described in §3.5. The
groups are separated by a single blank line. The
imports within a group are sorted alphabetically.

## 6.6 Circular Dependency Avoidance

A circular dependency is prohibited. A module
that imports another module SHALL NOT be imported
by that module. The linting framework SHALL
detect circular dependencies. A circular
dependency is a defect.

## 6.7 Import Hygiene

A module SHALL import only the symbols that it
uses. A wildcard import is prohibited. A
re-export SHALL be declared in `__all__`.

---

# 7. Exception Handling Standard

## 7.1 Custom Exception Hierarchy

The custom exception hierarchy is declared in
`007_SDK_SPECIFICATION.md` §7. The base class is
`ComtradeError`. The hierarchy is owned by the
`un_comtrade.errors` module. The hierarchy is
documented in the SDK specification.

## 7.2 Exception Naming

The exception class names are PascalCase. The
exception class names end with `Error`. The
exception class names are descriptive: a
`ReferenceError` is raised when a reference code
is unknown, a `ValidationError` is raised when a
parameter is invalid.

## 7.3 Error Propagation

An error propagates upward through the layer
chain. A layer SHALL NOT swallow an error. A
layer SHALL NOT catch a documented exception and
re-raise a less informative exception unless
the documentation explicitly allows the re-
mapping.

## 7.4 Error Wrapping

When a lower-layer error is wrapped, the wrapping
exception records:

- The lower-layer exception (via `__cause__`).
- The lower-layer exception's message.
- The lower-layer exception's category.
- The context in which the lower-layer exception
  occurred.

The wrapping exception is an instance of a
documented exception type.

## 7.5 User-Facing vs. Internal Exceptions

A user-facing exception is an exception that the
consumer is expected to catch. A user-facing
exception is documented in the SDK specification.
An internal exception is an exception that the
consumer is not expected to catch. An internal
exception SHALL NOT leak to the consumer.

## 7.6 Exception Principles

The exception principles are:

- Exceptions are exceptional. A control flow that
  uses exceptions is a defect.
- Exceptions are documented. An undocumented
  exception is a defect.
- Exceptions are typed. A `raise Exception` is
  prohibited.
- Exceptions are translated. A lower-layer
  exception is translated into the documented
  exception type of the receiving layer.

---

# 8. Logging Standard

## 8.1 Logging Objectives

The logging objectives are:

- Provide diagnostic information to the consumer.
- Provide operational information to the maintainer.
- Support troubleshooting without exposing sensitive
  information.
- Support change-data-capture workflows through
  the request identifier.

## 8.2 Log Severity Levels

The log severity levels are:

- **DEBUG.** Cache hits, validation details,
  internal state transitions.
- **INFO.** Lifecycle events, refresh events.
- **WARNING.** Recoverable errors (retries, cache
  misses, validation failures).
- **ERROR.** Non-recoverable errors (upstream
  errors, authentication errors).
- **CRITICAL.** SDK integrity errors (corrupt
  cache, corrupt configuration).

## 8.3 Structured Logging Expectations

The log records are structured. A log record
contains:

- `timestamp` (ISO-8601 string).
- `level` (string).
- `category` (string).
- `request_id` (string).
- `message` (string).
- `context` (object).

## 8.4 Sensitive Data Handling

The SDK SHALL NOT log:

- The API key.
- The full URL (which contains the API key as a
  query parameter).
- The consumer's environment variables.
- The consumer's filesystem paths.
- The consumer's process arguments.

## 8.5 Correlation Identifiers

The request identifier correlates every log
record emitted during a single call. The request
identifier is propagated through every layer.

## 8.6 Debug vs. Production Logging

The default log level is `WARNING`. The default
log destination is the standard library's default
handler. The consumer can override the default
log level and the default log destination through
the configuration object.

---

# 9. Naming Conventions

## 9.1 Modules

Module names use snake_case. Module names are
singular. Module names are descriptive: a module
that handles the trade layer is named `trade.py`,
not `trades.py`.

## 9.2 Packages

Package names use snake_case. Package names are
singular. Package names are descriptive: a
package that handles the trade layer is named
`un_comtrade/trade/`, not `un_comtrade/trades/`.

## 9.3 Classes

Class names use PascalCase. Class names are
singular. Class names are descriptive: a class
that represents a trade record is named
`TradeRecord`, not `TradeRecords`.

## 9.4 Functions

Function names use snake_case. Function names
are verbs: a function that returns a list of
countries is named `get_countries`, not
`countries()`.

## 9.5 Methods

Method names use snake_case. Method names are
verbs: a method that returns a list of countries
is named `get_countries`, not `countries()`.

## 9.6 Variables

Variable names use snake_case. Variable names
are descriptive: a variable that holds a list of
countries is named `countries`, not `c` or `cl`.

## 9.7 Constants

Constant names use UPPER_SNAKE_CASE. Constant
names are descriptive: a constant that holds the
World partner code is named `PARTNER_WORLD`.

## 9.8 Enums

Enum names use PascalCase. Enum member names use
UPPER_SNAKE_CASE. Enum members are documented.

## 9.9 Exceptions

Exception class names use PascalCase. Exception
class names end with `Error`. Exception class
names are descriptive.

## 9.10 Files

File names use snake_case. File names are
descriptive. File names SHALL NOT contain spaces
or special characters.

## 9.11 Directories

Directory names use snake_case. Directory names
are descriptive. Directory names SHALL NOT contain
spaces or special characters.

## 9.12 Consistency with the Data Model

The naming conventions are consistent with the
canonical data model. The entity names, the field
names, and the enumeration values are reused in
the code. A name that is documented in the data
model SHALL NOT be redefined in the code.

---

# 10. Folder Organization

The folder organization is declared in
`014_PACKAGING_SPECIFICATION.md` §13. The
high-level summary is:

- `docs/` — documentation source tree.
- `sdk/` — SDK source tree.
- `tests/` — test suite.
- `examples/` — example scripts.
- `notebooks/` — Jupyter notebooks.
- `scripts/` — maintainer scripts.
- `data/` — example datasets.

## 10.1 `docs/`

- **Purpose.** Documentation source tree.
- **Ownership.** Documentation maintainers.
- **Responsibilities.** Source of truth for the
  architecture, the data model, the SDK
  specification, the layer specifications, the
  ETL specification, the storage specification,
  the testing standard, the packaging
  specification, the coding standard, and the
  roadmap.
- **Allowed contents.** Markdown files, image
  files, schema files.
- **Prohibited contents.** Source code, build
  artefacts, generated documentation.

## 10.2 `sdk/`

- **Purpose.** SDK source tree.
- **Ownership.** SDK maintainers.
- **Responsibilities.** Source of truth for the
  SDK implementation.
- **Allowed contents.** Python modules, Python
  packages, test fixtures, type stubs.
- **Prohibited contents.** Documentation, build
  artefacts, generated code.

## 10.3 `tests/`

- **Purpose.** Test suite.
- **Ownership.** SDK maintainers.
- **Responsibilities.** Source of truth for the
  test coverage of the SDK.
- **Allowed contents.** Test modules, test
  fixtures, recorded samples, mock data.
- **Prohibited contents.** Source code, build
  artefacts.

## 10.4 `examples/`

- **Purpose.** Example scripts.
- **Ownership.** SDK maintainers.
- **Responsibilities.** Source of truth for the
  example usage of the SDK.
- **Allowed contents.** Python scripts, recorded
  samples.
- **Prohibited contents.** Source code, build
  artefacts.

## 10.5 `notebooks/`

- **Purpose.** Jupyter notebooks.
- **Ownership.** SDK maintainers.
- **Responsibilities.** Source of truth for the
  notebook usage of the SDK.
- **Allowed contents.** Jupyter notebooks, recorded
  samples.
- **Prohibited contents.** Source code, build
  artefacts.

## 10.6 `scripts/`

- **Purpose.** Maintainer scripts.
- **Ownership.** SDK maintainers.
- **Responsibilities.** Source of truth for the
  maintainer workflow.
- **Allowed contents.** Python scripts, shell
  scripts, configuration templates.
- **Prohibited contents.** Source code, build
  artefacts.

## 10.7 `data/`

- **Purpose.** Example datasets.
- **Ownership.** SDK maintainers.
- **Responsibilities.** Source of truth for the
  recorded upstream responses.
- **Allowed contents.** JSON files, CSV files,
  Parquet files, image files.
- **Prohibited contents.** Source code, build
  artefacts, secrets.

---

# 11. Module Design

## 11.1 Module Size

A module is small. A module SHALL NOT exceed 500
lines of code. A module that exceeds the limit
SHALL be split into smaller modules. A module that
is too small SHALL be merged with a related
module.

## 11.2 Single Responsibility

A module has a single responsibility. A module
that handles multiple responsibilities SHALL be
split into smaller modules. The responsibility of
a module is recorded in the module's docstring.

## 11.3 Public vs. Internal Modules

A module is public if its name is listed in
`014_PACKAGING_SPECIFICATION.md` §2.2. A module
is internal if its name is prefixed with an
underscore. A consumer SHALL NOT import an
internal module.

## 11.4 Dependency Direction

A module depends only on lower-layer modules. A
module SHALL NOT depend on a higher-layer module.
A module that needs a capability of a non-adjacent
module SHALL route the call through the
intervening modules.

## 11.5 Interface Boundaries

A module's public interface is the set of classes,
functions, and constants that are exported by the
module. A module's public interface is documented
in the module's docstring. A module's private
implementation is the set of classes, functions,
and constants that are not exported. A module's
private implementation SHALL NOT be accessed from
outside the module.

---

# 12. Code Quality Rules

## 12.1 No Duplicated Business Logic

A business logic rule is defined once. A business
logic rule that is duplicated is a defect. A
business logic rule that is similar to another
business logic rule SHALL be refactored into a
shared module.

## 12.2 No Hidden Side Effects

A function or method SHALL NOT perform a side
effect that is not documented in the docstring.
A side effect is a network call, a filesystem
write, a global state mutation, or a log record
that is not a normal log record.

## 12.3 No Circular Dependencies

A circular dependency is a defect. The linting
framework SHALL detect circular dependencies. A
circular dependency SHALL be resolved by
introducing an interface module.

## 12.4 Explicit Dependencies

A module's dependencies are explicit. A module
that uses a global state is a defect. A module
that uses an implicit configuration is a defect.
A module that uses a side effect to acquire a
dependency is a defect.

## 12.5 Predictable Behaviour

A function or method's behaviour is predictable.
Given the same input, the function or method
produces the same output. A function or method
that produces a different output for the same
input is a defect.

## 12.6 Consistent Error Handling

A function or method's error handling is
consistent. Every documented error is raised at
the documented condition. Every undocumented
error is a defect.

## 12.7 No Dead Code

A module SHALL NOT contain dead code. Dead code
is a function, a method, a class, or a constant
that is not used. Dead code SHALL be removed.

## 12.8 No Commented-Out Code

A module SHALL NOT contain commented-out code.
Commented-out code SHALL be removed. The history
is preserved in the version control system.

---

# 13. Public API Standards

## 13.1 Public Methods

A public method follows the template of
`007_SDK_SPECIFICATION.md` §4. The method is
documented. The method is tested. The method
preserves backward compatibility.

## 13.2 Internal Methods

An internal method is prefixed with an underscore.
An internal method is not documented. An internal
method MAY change at any time.

## 13.3 Stable Interfaces

A stable interface is a public interface that is
documented and tested. A stable interface
preserves backward compatibility within a major
version. A stable interface MAY be deprecated
through the deprecation process.

## 13.4 Deprecation Process

A public interface MAY be marked deprecated by:

1. Adding a deprecation note to the documentation.
2. Adding a deprecation warning to the runtime.
3. Adding a changelog entry.

The deprecation period SHALL last at least one
minor release before the interface is removed in
the next major release. The deprecation note
SHALL explain the migration path.

## 13.5 Backward Compatibility

A public interface preserves backward
compatibility within a major version. A breaking
change is reserved for a major version
increment. A breaking change is recorded in
`DECISIONS.md`.

---

# 14. Review Checklist

Every change SHALL be reviewed against the checklist
below. The checklist is the minimum; a change MAY
be reviewed against additional criteria.

- [ ] The coding standards are followed.
- [ ] The documentation is updated.
- [ ] The type hints are complete.
- [ ] The naming conventions are followed.
- [ ] The logging is appropriate.
- [ ] The exceptions are documented.
- [ ] The architecture is respected.
- [ ] The layer boundaries are respected.
- [ ] The tests are planned or updated.
- [ ] The public API is unchanged or documented.
- [ ] The cross-references are updated.
- [ ] The out-of-scope findings are recorded.
- [ ] The completion summary is delivered.

## 14.1 Reviewer Responsibility

The reviewer SHALL verify the checklist
independently and SHALL NOT rely on the author's
self-report. A reviewer who is unable to verify
an item SHALL mark the item as `Unverified` and
SHALL request a clarification from the author.

---

# 15. Technical Debt Policy

## 15.1 Identification

A technical debt is identified by a reviewer, a
maintainer, or a consumer. The technical debt is
recorded in `DECISIONS.md` with a description, an
impact, a priority, and a proposed resolution.

## 15.2 Documentation

A technical debt is documented in `DECISIONS.md`
with:

- A description of the debt.
- The location of the debt.
- The impact of the debt.
- The priority of the debt.
- The proposed resolution of the debt.
- The estimated effort to resolve the debt.
- The owner of the debt.

## 15.3 Prioritization

A technical debt is prioritised as one of:

- **Critical.** The debt blocks a release.
- **High.** The debt SHALL be resolved in the next
  release.
- **Medium.** The debt SHALL be resolved in a
  future release.
- **Low.** The debt MAY be resolved when
  convenient.

## 15.4 Approval

A technical debt that requires a major version
increment SHALL be approved by a recorded
decision. A technical debt that is a workaround
SHALL be approved by a recorded decision.

## 15.5 Resolution

A technical debt is resolved by a recorded
change. The change SHALL update `DECISIONS.md` to
record the resolution. The change SHALL update
the changelog to record the resolution.

## 15.6 Temporary Workarounds

A temporary workaround is a code change that is
intended to be replaced by a permanent solution.
A temporary workaround SHALL be explicitly
recorded in `DECISIONS.md` with:

- The reason for the workaround.
- The expected lifetime of the workaround.
- The planned replacement.
- The risk of leaving the workaround in place.

A temporary workaround that is not replaced at
the end of its expected lifetime is escalated to
a permanent solution or to a permanent debt.

---

# 16. Future Extensibility

## 16.1 New Modules

A new module is added in a minor version. The new
module is documented in the SDK specification.
The new module is added to the package layout.
The new module SHALL be tested. The new module
SHALL be documented in the README.

## 16.2 New Features

A new feature is added in a minor version. The new
feature is documented in the SDK specification.
The new feature is added to the public surface.
The new feature SHALL be tested.

## 16.3 New Python Versions

A new Python version is added in a minor version.
The new Python version SHALL be supported for the
duration of the major version.

## 16.4 New Operating Systems

A new operating system is added in a minor
version. The new operating system SHALL be
supported for the duration of the major version.

## 16.5 New Dependencies

A new runtime dependency is added in a minor
version. The new dependency SHALL be approved by
a recorded decision.

## 16.6 Backward Compatibility

Every extension listed in this section preserves
backward compatibility within a major version.
A breaking change is reserved for a major
version increment and is recorded in
`DECISIONS.md`.

---

# 17. Assumptions

The assumptions below are recorded for
traceability. An assumption that turns out to be
false is recorded in `DECISIONS.md` as a
correction and is propagated to the relevant
specification documents.

## 17.1 Verified Assumptions

- The supported Python versions are the ones
  recorded in `000_PROJECT_CHARTER.md` §6.
  Verified.
- The top-level package is `un_comtrade`. Verified
  by the architecture document.
- The dependency footprint of the SDK is the
  minimum set required for the documented
  functionality. Verified by the architecture
  document.

## 17.2 Inferred Assumptions

- The linting framework is a standard Python
  linter. The default is inferred from common
  practice; the consumer can override the default.
- The formatting framework is a standard Python
  formatter. The default is inferred from common
  practice; the consumer can override the default.
- The type-checking framework is a standard
  Python type checker. The default is inferred from
  common practice; the consumer can override the
  default.
- The documentation framework is a standard
  Python documentation framework. The default is
  inferred from common practice; the consumer can
  override the default.
- The testing framework is a standard Python
  testing framework. The default is inferred from
  common practice; the consumer can override the
  default.

## 17.3 Local Design Decisions

- The maximum line length is 100 characters. The
  limit is a local design decision; the consumer
  can override the limit through the linting
  framework.
- The maximum module size is 500 lines of code.
  The limit is a local design decision; the
  consumer can override the limit through the
  module splitting policy.
- The default log level is `WARNING`. The default
  is a local design decision; the consumer can
  override the default through the configuration
  object.
- The default dependency version pinning is a
  minimum compatible version and a maximum tested
  version. The pinning is a local design decision;
  the consumer can override the default through
  the package metadata.

---

# 18. Open Questions

The questions below are recorded for future
resolution. Each question is described with the
impact and the suggested verification.

- **OQ-CS-001 (High).** What is the exact linting
  framework to be used? **Impact.** The linting
  rules depend on the framework. **Suggested
  verification.** Confirm with the maintainers.

- **OQ-CS-002 (High).** What is the exact formatting
  framework to be used? **Impact.** The formatting
  rules depend on the framework. **Suggested
  verification.** Confirm with the maintainers.

- **OQ-CS-003 (High).** What is the exact
  type-checking framework to be used? **Impact.**
  The type-checking rules depend on the framework.
  **Suggested verification.** Confirm with the
  maintainers.

- **OQ-CS-004 (High).** What is the exact
  documentation framework to be used? **Impact.**
  The documentation build depends on the framework.
  **Suggested verification.** Confirm with the
  packaging specification.

- **OQ-CS-005 (High).** What is the exact testing
  framework to be used? **Impact.** The test
  suite depends on the framework. **Suggested
  verification.** Confirm with the testing
  standard.

- **OQ-CS-006 (Medium).** What is the exact commit
  message format? **Impact.** The commit history
  depends on the format. **Suggested verification.**
  Confirm with the maintainers.

- **OQ-CS-007 (Medium).** What is the exact branch
  strategy (trunk-based, GitFlow, etc.)? **Impact.**
  The release process depends on the branch
  strategy. **Suggested verification.** Confirm
  with the maintainers.

- **OQ-CS-008 (Medium).** What is the exact pull
  request template? **Impact.** The review process
  depends on the template. **Suggested verification.**
  Confirm with the maintainers.

- **OQ-CS-009 (Medium).** What is the exact issue
  template? **Impact.** The issue tracking depends
  on the template. **Suggested verification.**
  Confirm with the maintainers.

- **OQ-CS-010 (Low).** What is the exact
  pre-commit hook configuration? **Impact.** The
  pre-commit checks depend on the configuration.
  **Suggested verification.** Confirm with the
  maintainers.

---

# End of document
