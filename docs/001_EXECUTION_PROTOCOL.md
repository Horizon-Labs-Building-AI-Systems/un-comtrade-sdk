```
Document ID
001

Title
Execution Protocol

Version
0.1.0

Status
DRAFT

Created
2026-06-26T19:41:45Z

Last Updated
2026-06-26T19:41:45Z

Author
Codex

Project
UN Comtrade Python SDK

Dependencies
000_PROJECT_CHARTER.md

Supersedes
None
```

---

# 1. Execution Philosophy

The repository follows a Documentation-First Development
methodology in which no source code, test, notebook, example,
or integration is produced before the specification that
justifies it has been written, reviewed, and versioned.

The execution philosophy of the repository is governed by the
following principles.

## 1.1 Specification before implementation

Every implementation task is preceded by the relevant
specification document. The specification is the contract;
the implementation is the fulfilment of the contract. An
implementation that contradicts a specification is rejected;
a specification that cannot be implemented is revised through
the documented change-governance process.

## 1.2 Architecture before coding

Architectural decisions are recorded in
`docs/DECISIONS.md` before any source file is created that
depends on them. Architectural drift is treated as a
first-class defect and is corrected by updating the
specification, not by reverting the implementation in
isolation.

## 1.3 Deterministic execution

Given the same input state and the same task description, the
execution protocol produces the same set of artefacts. The
protocol does not depend on the order in which tasks are
issued, on the time of day at which the task is run, or on
any environmental variable that is not part of the input
state.

## 1.4 Small incremental tasks

Tasks are scoped to a single responsibility. A task that
delivers more than one deliverable is decomposed before
work begins. Decomposition is the responsibility of the
task requester; the executor SHALL NOT decompose a task
silently.

## 1.5 One responsibility per task

A task that modifies architecture, behaviour, and tests in a
single step is rejected. Tasks that cross layer boundaries
are split at the boundary; each sub-task addresses one
layer.

## 1.6 Documentation as the source of truth

For any design question, the relevant specification document
takes precedence over the implementation, the tests, the
examples, and the notebooks. Where the implementation,
tests, examples, or notebooks contradict a current
specification, the specification is correct.

## 1.7 Reversibility of work

Every change to the repository SHALL be reversible through
the version-control system. The protocol does not require
or rely on manual undo procedures; every modification is
expressed as a commit against a tracked file.

---

# 2. Documentation Hierarchy

The documentation tree is ordered by precedence. A document
at a higher level overrides a document at a lower level in
the event of a conflict. Conflicts are resolved by editing
the higher-level document and propagating the change to the
lower-level documents, never the reverse.

```
000_PROJECT_CHARTER.md
        |
        v
001_EXECUTION_PROTOCOL.md   (this document)
        |
        v
002_ARCHITECTURE.md
        |
        v
003_API_RESEARCH.md
004_API_ENDPOINT_CATALOG.md
005_DATA_MODEL.md
006_SDK_SPECIFICATION.md
007_METADATA_LAYER_SPEC.md
008_TRADE_LAYER_SPEC.md
009_INFRASTRUCTURE_SPEC.md
        |
        v
010_ETL_SPECIFICATION.md
011_STORAGE_SPECIFICATION.md
        |
        v
012_TESTING_STANDARD.md
013_PACKAGING_SPEC.md
014_CODING_STANDARD.md
        |
        v
015_ROADMAP.md
```

The remaining documents in the `docs/` tree — `CHANGELOG.md`,
`TASK_LOG.md`, and `DECISIONS.md` — are record-keeping
documents. They are not part of the precedence chain; they
are append-only and are never edited retroactively. A
correction to a record-keeping document is expressed as a
new entry that supersedes the earlier one.

## 2.1 Precedence rules

- Where `002_ARCHITECTURE.md` and a layer specification
  disagree, `002_ARCHITECTURE.md` is correct.
- Where a layer specification and the SDK specification
  disagree, the layer specification is correct for the
  layer it describes, and the SDK specification is correct
  for the cross-layer behaviour.
- Where a specification and `CHANGELOG.md` disagree, the
  specification is correct; the changelog is corrected by
  a new entry.
- Where `DECISIONS.md` records a decision that contradicts
  a current specification, the decision is honoured; the
  specification is updated to match the decision, and the
  change is logged in `CHANGELOG.md`.

## 2.2 Inherited rules

This document inherits the project-wide rules recorded in
`000_PROJECT_CHARTER.md`, including the design philosophy,
the public-SDK philosophy, the documentation philosophy, the
coding philosophy, the release strategy, the versioning
strategy, the success criteria, the risk register, and the
assumption list. The execution protocol is consistent with
those rules; it does not relax them.

---

# 3. Mandatory Reading Order

Before the execution of every task, the executor SHALL read
the following documents, in the order shown. The executor
SHALL NOT reread unrelated specifications, and SHALL NOT
skip a document in the order unless the document is
explicitly listed as a "depend on" annotation that is
satisfied by a more recent reading.

```
000_PROJECT_CHARTER.md
001_EXECUTION_PROTOCOL.md
CHANGELOG.md
TASK_LOG.md
Relevant specification documents only
```

## 3.1 Always-read documents

`000_PROJECT_CHARTER.md`, `001_EXECUTION_PROTOCOL.md`,
`CHANGELOG.md`, and `TASK_LOG.md` are read on every task.
The reading of `CHANGELOG.md` and `TASK_LOG.md` ensures
that the executor is aware of every recent change that
might affect the current task.

## 3.2 Relevant specifications

"Relevant specification documents only" means the documents
that the current task modifies, the documents that the
current task depends on, and the documents one level above
the modified documents in the precedence chain. Reading
further than that is discouraged because it dilutes the
focus of the task.

## 3.3 Skipping rules

The executor SHALL NOT skip a document in the reading
order. Where a document has been read recently and the
executor is confident that no change has been made since,
the executor may cite the reading in the task log without
re-reading the full document. The citation SHALL include
the document version, the last-update timestamp, and the
commit hash at which the document was last read.

## 3.4 Conflict resolution during reading

Where two documents disagree, the executor SHALL honour the
precedence chain recorded in section 2. The executor SHALL
NOT silently pick one of the documents. The disagreement
SHALL be recorded in the task log and SHALL be resolved
through the change-governance process before the task is
completed.

---

# 4. Task Lifecycle

Every task follows the lifecycle below. Each state
transition is recorded in `TASK_LOG.md` together with the
state-transition timestamp.

```
Planned
    |
    v
Ready
    |
    v
In Progress
    |
    v
Review
    |
    v
Completed
    |
    v
Archived
```

A task may also transition to `Blocked` or `Cancelled`
from any state. A `Blocked` task returns to its prior state
once the blocker is resolved. A `Cancelled` task is final
and is archived with the cancellation reason recorded.

## 4.1 Planned

The task has been described and the deliverable has been
defined. The task has not yet been started. The
`Definition of Ready` has not been evaluated.

## 4.2 Ready

The `Definition of Ready` has been satisfied. The executor
is free to begin work. A task that fails the `Definition of
Ready` SHALL NOT transition to `Ready` and SHALL remain in
`Planned` or move to `Blocked`.

## 4.3 In Progress

The executor is actively working on the task. The task log
records the start timestamp. Only one task per executor
session SHALL be in `In Progress` at a time.

## 4.4 Review

The deliverable has been produced and is awaiting
verification. The review is performed against the
`Definition of Done`. The executor SHALL NOT begin a new
task while a deliverable is in `Review`.

## 4.5 Completed

The deliverable has been verified. The completion summary
has been recorded. The state transition to `Completed` is
final within the lifecycle; further work on the deliverable
is a new task.

## 4.6 Archived

The task is closed. The deliverable is part of the
historical record. `TASK_LOG.md` is the canonical record of
archived tasks.

## 4.7 Blocked

The task cannot proceed. The blocker is recorded in
`TASK_LOG.md` and is referenced in the deliverable. A
blocked task SHALL NOT proceed by guessing. The protocol
for blocked tasks is described in section 10.

## 4.8 Cancelled

The task has been withdrawn by the requester. The
cancellation reason is recorded in `TASK_LOG.md`. A
cancelled task SHALL NOT be resumed; a replacement task is
created instead.

## 4.9 State transition record

Every state transition is recorded in `TASK_LOG.md` with
the following fields:

- Task ID
- Previous state
- New state
- Timestamp
- Reason for transition

---

# 5. Documentation Update Rules

Every completed task SHALL update the documentation. The
following updates are mandatory; no exception is permitted.

## 5.1 TASK_LOG.md

A new entry SHALL be appended to `TASK_LOG.md` describing
the task. The entry SHALL be appended; existing entries
SHALL NOT be edited. A correction to a previous entry is
expressed as a new entry that supersedes the earlier one
and is referenced by Task ID.

## 5.2 CHANGELOG.md

A new entry SHALL be appended to `CHANGELOG.md` describing
the change. The entry SHALL follow the changelog standard
recorded in section 14.

## 5.3 Document version

If a specification document has been modified, the document
version SHALL be incremented according to the versioning
rules in section 15. The version increment is recorded in
the changelog.

## 5.4 Last Updated timestamp

The `Last Updated` field in the metadata block of every
modified document SHALL be updated to the new modification
timestamp. The `Last Updated` value SHALL be a UTC
timestamp in ISO-8601 form.

## 5.5 Cross-references

Where a modification changes the meaning of a cross-reference,
the cross-reference SHALL be updated in every document in
which it appears. Broken cross-references are a defect and
SHALL be corrected in the same task that introduced them.

## 5.6 Suppression of updates

No update required by this section may be suppressed, even
if the executor judges the change to be trivial. The
protocol does not define a minimum size for a documented
change.

---

# 6. Architecture Protection

The architecture of the repository is recorded in
`002_ARCHITECTURE.md` and in the specification documents
that descend from it. The architecture is protected by the
following rules.

## 6.1 No silent architectural change

The executor SHALL NOT modify the architecture without
prior documentation. An architectural change is any change
that alters the responsibilities of a layer, the
dependencies between layers, the public interface of a
documented module, or the precedence of documents.

## 6.2 No silent renaming of public interfaces

The executor SHALL NOT rename a public interface without
updating the specification that defines the interface and
the changelog. A rename without documentation is treated
as a removal and an addition, and is governed by the
versioning rules in section 15.

## 6.3 No silent breaking change

A breaking change is described in section 14 of
`000_PROJECT_CHARTER.md`. The executor SHALL NOT introduce
a breaking change without a recorded decision in
`DECISIONS.md` and a major version increment.

## 6.4 No silent removal of documented functionality

The executor SHALL NOT remove a documented function, class,
method, parameter, or attribute. Removal is permitted only
through the deprecation process described in
`000_PROJECT_CHARTER.md` section 10.5.

## 6.5 No silent repository restructuring

The executor SHALL NOT rename a folder, move a file, or
change the top-level repository layout without updating
`002_ARCHITECTURE.md` and the relevant specification
documents. Restructuring is documented before it is
executed.

## 6.6 Pre-flight check

Before modifying any file, the executor SHALL verify that
the modification is consistent with the current
specification. Where the modification is not consistent,
the executor SHALL stop and request clarification as
described in section 16.

---

# 7. Scope Protection

The executor SHALL perform only the task that has been
requested. The executor SHALL NOT, without explicit
instruction, perform adjacent work.

## 7.1 Prohibited behaviours

The executor SHALL NOT:

- begin work on a future milestone that is not in the
  requested task;
- implement an adjacent feature that is not in the
  requested task;
- refactor a file that is not in the requested task;
- introduce a speculative improvement that is not in the
  requested task;
- bundle a related but separate change into the current
  commit;
- add commentary or examples beyond what the task
  explicitly requires;
- create a file that is not listed in the task
  deliverables.

## 7.2 Out-of-scope findings

Where the executor identifies a defect, an inconsistency, or
an improvement opportunity that is not in the scope of the
current task, the executor SHALL record the finding in
`TASK_LOG.md` under "Out-of-scope findings" and SHALL NOT
address the finding in the current task. The finding is
addressed by a follow-up task.

## 7.3 Over-scope detection

Where the executor judges that the requested change exceeds
the scope of a single task, the executor SHALL stop the
work, document the issue in the task log, and request
clarification as described in section 16. The executor
SHALL NOT silently decompose the task.

## 7.4 Bounded initiative

The executor may use judgement to choose the appropriate
wording, the appropriate example, or the appropriate
formatting within the boundaries of the requested task. The
executor SHALL NOT use judgement to change the substance of
the task, the deliverables, or the dependencies.

---

# 8. Definition of Ready

A task is `Ready` when every condition below is satisfied.
Where any condition fails, the task SHALL NOT begin.

## 8.1 Required documents exist

The documents listed in the task description, the
documents in the mandatory reading order, and any document
referenced by a "depend on" annotation SHALL exist in the
repository and SHALL be readable.

## 8.2 Dependencies are satisfied

Every dependency declared by the task SHALL be in a state
that allows the task to proceed. A dependency is satisfied
when the dependent task is `Completed` or when the
dependency is satisfied by a static artefact that already
exists in the repository.

## 8.3 Scope is defined

The task description SHALL define a single deliverable, a
single set of files to be modified, and a single acceptance
criterion. A task description that does not meet this
criterion SHALL be clarified before the task is begun.

## 8.4 Inputs are available

The information, references, and source material required
to perform the task SHALL be available to the executor. A
missing input is recorded as a blocker; the task SHALL NOT
begin by guessing.

## 8.5 Blockers are identified

Every known blocker, including missing documentation,
inconsistent requirements, unverifiable API behaviour, and
ambiguous wording, SHALL be listed in the task description
or recorded in `TASK_LOG.md` before the task begins. A
blocker that is discovered after the task has begun is
handled according to section 10.

## 8.6 Failure of the Definition of Ready

Where the `Definition of Ready` is not satisfied, the task
transitions to `Blocked`. The blocker is recorded in
`TASK_LOG.md` and the requester is notified.

---

# 9. Definition of Done

A task is `Done` only when every condition below is
satisfied. A task that does not satisfy every condition is
returned to `In Progress` and is completed by the same
executor; the task is not handed over to a new session
with the deliverable in an incomplete state.

## 9.1 Deliverables produced

Every deliverable listed in the task description SHALL be
present in the repository. The presence of a deliverable
is verified by file-system inspection, not by the
executor self-reporting.

## 9.2 Documentation updated

`TASK_LOG.md`, `CHANGELOG.md`, the modified document
versions, and the `Last Updated` timestamps SHALL be
updated. The cross-references introduced by the
modification SHALL be valid.

## 9.3 Formatting verified

The markdown formatting of every modified document SHALL be
consistent with the formatting of the existing documents.
The verification is performed by inspection of headers,
list styles, table styles, and code-fence discipline.

## 9.4 No unresolved TODOs

The task deliverable SHALL NOT contain a TODO, FIXME, XXX,
or equivalent marker. Where such a marker is required by
the task, it SHALL be replaced with an explicit
out-of-scope finding recorded in `TASK_LOG.md`.

## 9.5 No undocumented assumptions

Every assumption that the executor relied on during the
task SHALL be recorded either in the deliverable itself
(in the relevant section) or in `TASK_LOG.md` under
"Assumptions". An undocumented assumption is a defect.

## 9.6 No scope violations

The deliverable SHALL NOT contain changes that are not in
the scope of the task. A scope violation is a defect and
SHALL be corrected before the task is `Done`.

## 9.7 Completion summary

The task is closed with a completion summary that records
the sections completed, the governance decisions
established, the assumptions made, the open questions, and
the recommended next task. The format of the completion
summary is described in section 19.

---

# 10. Definition of Blocked

A task is `Blocked` when one or more of the following
conditions hold. A blocked task SHALL NOT proceed by
guessing; the executor SHALL stop and request
clarification.

## 10.1 Required documentation is missing

A specification document that the task depends on does not
exist or is not readable. The blocker is the missing
document and the file path at which the document is
expected.

## 10.2 Requirements conflict

The task description conflicts with a specification
document. The conflict is recorded in `TASK_LOG.md` and
the requester is asked to resolve the conflict by editing
the higher-precedence document and re-issuing the task.

## 10.3 API behaviour cannot be verified

The task requires the verification of an upstream API
behaviour that the executor cannot observe. The blocker is
the unverifiable behaviour and the verification step that
the executor attempted.

## 10.4 Dependencies are incomplete

A task that the current task depends on is not
`Completed`. The blocker is the dependent task and the
state of the dependent task.

## 10.5 Requested behaviour is ambiguous

The task description admits more than one interpretation
that would lead to materially different deliverables. The
executor SHALL NOT pick one of the interpretations. The
executor SHALL request a clarification that names the
ambiguity and the candidate interpretations.

## 10.6 Resolution of a block

A blocker is resolved by editing the relevant
specification document, by completing the dependent task,
or by clarifying the request. The resolution is recorded
in `TASK_LOG.md`; the blocked task is then re-evaluated
against the `Definition of Ready`.

---

# 11. Assumption Rules

An assumption is a statement that the executor accepts as
true without having verified it. Assumptions are not
evidence. An assumption SHALL NOT be treated as a verified
fact in the deliverable, in the documentation, or in
subsequent tasks.

## 11.1 Required fields

Every recorded assumption includes the following fields.

- **Statement.** The claim that is being assumed.
- **Reason.** The reason the assumption is being made.
- **Impact.** The impact of the assumption on the
  deliverable and on downstream tasks.
- **Verification status.** Whether the assumption has been
  verified, by whom, by what method, and at what
  timestamp. Until the verification status is set to
  `verified`, the assumption SHALL be considered unverified.

## 11.2 Location of record

Assumptions are recorded in the section of the deliverable
that the assumption affects. Cross-cutting assumptions are
recorded in `TASK_LOG.md` under "Assumptions" for the
task. Project-wide assumptions are recorded in
`000_PROJECT_CHARTER.md` section 17.

## 11.3 Correction of an assumption

Where an assumption is later found to be false, the
correction is recorded in `DECISIONS.md` with a reference
to the original assumption. The deliverable that relied
on the assumption is corrected by a follow-up task.

## 11.4 Prohibited uses

An unverified assumption SHALL NOT be:

- cited as evidence for a design decision;
- cited as a reason to skip a verification step;
- used to override a specification document;
- used to override a documented upstream API behaviour.

---

# 12. Change Governance

Every change to the repository is governed by the rules in
this section. The rules apply to specification documents,
to source code, to tests, to examples, to notebooks, to
scripts, and to data artefacts.

## 12.1 Required change record

Every change records the following fields.

- **Version.** The version of the changed artefact after
  the change.
- **Timestamp.** The UTC timestamp of the change.
- **Modified files.** The list of files that were modified
  by the change.
- **Reason.** The reason for the change.
- **Impact.** The impact of the change on existing
  artefacts, including the impact on consumers of the
  SDK.
- **Related task.** The Task ID of the task that produced
  the change.

## 12.2 Silent modifications

Silent modifications are prohibited. A modification that
does not record every field in section 12.1 is treated as
a defect and is corrected by a follow-up task.

## 12.3 Change-control window

A change that crosses a release boundary is governed by the
release strategy in `000_PROJECT_CHARTER.md` section 13.
The executor SHALL NOT make a change that requires a
release boundary to be crossed without the explicit
approval of the requester.

## 12.4 Atomic commits

A commit SHALL contain a single logical change. The
executor SHALL NOT bundle a documentation update, a
source change, and a test update into a single commit
where the change is logically separable. Where a
documentation update and a source change are conceptually
linked, the commit message records the linkage and the
changelog entry references the source change.

## 12.5 Change review

A change that introduces a breaking interface, removes
documented functionality, or alters the public-API
contract is reviewed against `000_PROJECT_CHARTER.md`
section 14.5 before the change is committed. The review
records the rationale in `DECISIONS.md`.

---

# 13. Task Logging Standard

`TASK_LOG.md` is the canonical record of every task. The
log is append-only. Each entry contains the fields below.

## 13.1 Required fields

- **Task ID.** A monotonic identifier, formatted
  `TASK-NNN` where `NNN` is a three-digit decimal
  sequence. The Task ID is assigned at task creation and
  is never reused.
- **Title.** A short, human-readable title.
- **Status.** One of `Planned`, `Ready`, `In Progress`,
  `Review`, `Completed`, `Blocked`, `Cancelled`,
  `Archived`.
- **Started.** The UTC timestamp at which the task
  transitioned to `In Progress`.
- **Completed.** The UTC timestamp at which the task
  transitioned to `Completed`. The field is empty for
  non-final states.
- **Deliverables.** The list of files produced by the
  task.
- **Files modified.** The list of files modified by the
  task, including the documentation updates required by
  section 5.
- **Dependencies.** The list of Task IDs that this task
  depends on, or `None`.
- **Notes.** Free-form notes, including out-of-scope
  findings, blockers, and clarifications.
- **Next recommended task.** The Task ID or document
  identifier of the next task in the workflow.

## 13.2 State transitions

Each state transition is recorded in `TASK_LOG.md` with
the Task ID, the previous state, the new state, the
timestamp, and the reason. The recording is appended; the
existing entry is not edited.

## 13.3 Cross-references

A task entry SHALL cross-reference the specifications it
modifies, the decisions it implements, and the changelog
entries it produces. A broken cross-reference is a defect
and SHALL be corrected in the same task that introduced
it.

## 13.4 Format

The format of a task entry is markdown. The headings used
within an entry are the field names in section 13.1. The
heading levels are consistent across entries.

---

# 14. Changelog Standard

`CHANGELOG.md` is the canonical record of every change
to the repository. The changelog is append-only. Each
entry contains the fields below.

## 14.1 Required fields

- **Version.** The version of the changed artefact after
  the change. For the repository as a whole, the version
  follows the release strategy in `000_PROJECT_CHARTER.md`
  section 13.
- **Date.** The UTC date of the change.
- **Summary.** A one-sentence summary of the change.
- **Added.** The list of new artefacts, new public
  interfaces, new tests, new examples, and new
  documentation.
- **Changed.** The list of modified artefacts and the
  nature of the modification.
- **Removed.** The list of removed artefacts and the
  reason for removal.
- **Fixed.** The list of defects that were corrected.

## 14.2 Order of entries

Entries are ordered by version, descending. The most
recent version is at the top. Within a version, entries
are ordered by date, descending. The order is not edited
retroactively.

## 14.3 Cross-references

A changelog entry SHALL cross-reference the Task ID that
produced the change, the affected specification documents,
and the decisions in `DECISIONS.md` that the change
implements.

## 14.4 Format

The format of a changelog entry is markdown. The headings
used within an entry are the field names in section 14.1.
The heading levels are consistent across entries.

---

# 15. Versioning Rules

The repository follows the Semantic Versioning 2.0.0
specification. The rules below are normative for the
documentation tree and the SDK tree.

## 15.1 Version number

A version number is of the form `MAJOR.MINOR.PATCH`.

- `MAJOR` is incremented when a backward-incompatible
  change is made to the documented public interface of
  the SDK, the documented architecture, or the documented
  precedence chain.
- `MINOR` is incremented when a backward-compatible
  feature is added to the SDK, a new specification
  document is added, or a new layer is introduced.
- `PATCH` is incremented when a backward-compatible
  correction is made to a specification, a defect is
  corrected in the SDK, or a documentation error is
  corrected.

## 15.2 Pre-release labels

Pre-release versions use the Semantic Versioning
pre-release identifier syntax. Examples: `0.1.0a1`,
`0.2.0b1`, `1.0.0rc1`.

## 15.3 Initial development

Versions prior to `1.0.0` are considered initial
development. The interface may change between minor
releases within the initial development series.

## 15.4 Patch increment

A patch increment is reserved for:

- correction of a defect that does not alter documented
  behaviour;
- correction of a documentation error that does not
  change the intent of the document;
- addition of a clarifying note that does not change the
  meaning of the document;
- correction of a typographical or formatting error.

A patch increment SHALL NOT be used to introduce a new
feature.

## 15.5 Minor increment

A minor increment is reserved for:

- addition of a new public class, function, method, or
  attribute;
- addition of a new optional parameter with a default
  value to an existing public function;
- addition of a new specification document;
- addition of a new layer;
- deprecation of a documented public interface, with the
  deprecation period defined in `000_PROJECT_CHARTER.md`
  section 10.5.

## 15.6 Major increment

A major increment is reserved for:

- removal of a documented public interface;
- change in the name, signature, or semantic behaviour of
  a documented public interface;
- change in the documented exception behaviour of a
  public function;
- change in the type of a documented public attribute;
- change in the documented return type of a documented
  public function;
- change in the precedence chain recorded in section 2;
- change in the governance rules recorded in this
  document.

## 15.7 Versioning of specification documents

Each specification document is versioned independently of
the SDK. The metadata block of every document records the
document version. The version of a specification document
is incremented when the document changes; the version of
the SDK is incremented when the SDK changes. A
specification change that is binding on the SDK SHALL be
reflected in the SDK version in the same release.

## 15.8 Versioning of the protocol

This document is itself versioned. Changes to the rules in
this document require a major version increment of the
protocol and a corresponding update to the changelog.

---

# 16. Escalation Rules

The executor SHALL stop the task and request clarification
whenever any of the following conditions is observed. The
executor SHALL NOT proceed by guessing.

## 16.1 Requirements conflict

The task description conflicts with a specification
document, with a documented upstream API behaviour, or
with a recorded decision. The conflict SHALL be recorded
in `TASK_LOG.md` together with the conflicting sources.

## 16.2 Documentation inconsistency

Two specification documents disagree on a point that the
task depends on. The disagreement SHALL be recorded in
`TASK_LOG.md` together with the document versions and
timestamps.

## 16.3 Multiple architectural choices

The task admits more than one architectural outcome and
the choice is not constrained by a specification
document. The candidate outcomes SHALL be listed in
`TASK_LOG.md` and the requester SHALL be asked to select
one.

## 16.4 API behaviour uncertainty

The task depends on an upstream API behaviour that cannot
be verified by the executor. The verification step that
the executor attempted SHALL be recorded in `TASK_LOG.md`
together with the observed error or absence of evidence.

## 16.5 Repository state ambiguity

The repository state is inconsistent with the
documentation, with the changelog, with the task log, or
with the expected layout. The inconsistency SHALL be
recorded and the requester SHALL be asked to clarify the
intended state.

## 16.6 Ambiguity of scope

The task scope is ambiguous. The candidate scopes SHALL be
listed and the requester SHALL be asked to choose one.

## 16.7 Format of an escalation

Every escalation SHALL include:

- the condition that triggered the escalation;
- the artefacts that were inspected;
- the candidate resolutions;
- the recommended resolution;
- the impact on the task timeline.

The escalation is recorded in `TASK_LOG.md` and is also
delivered to the requester through the completion summary.

---

# 17. Repository Integrity Rules

The executor SHALL preserve the integrity of the
repository. The rules below are normative.

## 17.1 Folder structure

The executor SHALL NOT add, rename, or remove a folder
without updating `002_ARCHITECTURE.md` and the relevant
specification documents. The folder structure described in
`000_PROJECT_CHARTER.md` section 8 is the canonical
layout.

## 17.2 Naming conventions

The executor SHALL NOT introduce a file or folder name
that does not follow the documented naming convention. The
naming convention is recorded in the relevant
specification document for the layer to which the
artefact belongs.

## 17.3 Public interfaces

The executor SHALL NOT modify a documented public
interface without updating the specification that defines
the interface and recording a decision in `DECISIONS.md`.

## 17.4 Documentation links

The executor SHALL NOT introduce a documentation link
that does not resolve. A broken link is a defect and
SHALL be corrected in the same task that introduced it.

## 17.5 Cross references

The executor SHALL NOT introduce a cross-reference
between documents that is not honoured by the source
documents. A cross-reference that is not honoured is a
defect and SHALL be corrected in the same task that
introduced it.

## 17.6 Specified file paths

The executor SHALL NOT place a file at a path that
contradicts the path recorded in the relevant
specification document. Where a path is not specified, the
executor SHALL use the canonical path described in
`002_ARCHITECTURE.md` section "Repository Layout".

## 17.7 Import hygiene

Once the source tree exists, the executor SHALL NOT
introduce an import that crosses a layer boundary
contrary to the layering recorded in
`000_PROJECT_CHARTER.md` section 9. The cross-layer import
is a defect and SHALL be corrected in the same task.

## 17.8 Tracking the layout

The canonical repository layout is recorded in
`000_PROJECT_CHARTER.md` section 8 and is refined in
`002_ARCHITECTURE.md`. The executor SHALL consult the
canonical layout before placing any file in the
repository.

---

# 18. Pull Request Checklist

Every implementation task SHALL verify the items below
before the task is closed. The checklist is normative; a
PR that does not satisfy every item is rejected.

- [ ] Documentation updated
- [ ] Task Log updated
- [ ] Changelog updated
- [ ] Version updated
- [ ] Timestamp updated
- [ ] Formatting checked
- [ ] Scope respected
- [ ] No undocumented assumptions
- [ ] Public API unchanged or documented
- [ ] Tests updated or created (when applicable)
- [ ] Cross-references verified
- [ ] Out-of-scope findings recorded
- [ ] Completion summary delivered

The checklist is recorded in the task completion summary
and is verified by the reviewer before the PR is merged.

## 18.1 When tests are applicable

Tests are applicable to every implementation task that
introduces or modifies executable code. Tests are not
applicable to pure-documentation tasks. A pure-documentation
task SHALL record in the completion summary that the
"Tests updated or created" item is `Not Applicable`.

## 18.2 When the public API is unchanged

Where the public API is unchanged, the "Public API
unchanged or documented" item is satisfied by the absence
of a change. Where the public API is changed, the
modification SHALL be documented in the relevant
specification document, recorded in `CHANGELOG.md`, and
versioned according to section 15.

## 18.3 Reviewer responsibility

The reviewer SHALL verify the checklist independently and
SHALL NOT rely on the executor's self-report. A reviewer
who is unable to verify an item SHALL mark the item as
`Unverified` and SHALL request a clarification from the
executor.

---

# 19. Communication Standard

Every completed task ends with a completion summary. The
completion summary is the only deliverable that the
executor returns to the requester in chat, in addition to
the file artefacts committed to the repository. The
completion summary contains the sections below.

## 19.1 Summary

A one-paragraph summary of what was produced and the
state of the deliverable.

## 19.2 Files Created

A list of files created by the task, with absolute paths.

## 19.3 Files Modified

A list of files modified by the task, with absolute paths
and a one-line note on the nature of the modification.

## 19.4 Decisions Made

A list of decisions taken during the task, with
references to `DECISIONS.md` where applicable.

## 19.5 Assumptions

A list of assumptions relied on during the task, with
verification status. Assumptions that are not yet
verified SHALL be flagged for follow-up.

## 19.6 Known Limitations

A list of known limitations of the deliverable. A
limitation is a documented deficiency, not a defect.

## 19.7 Open Questions

A list of open questions raised during the task, with
the question identifier used in `TASK_LOG.md`.

## 19.8 Recommended Next Task

The identifier of the next task in the workflow, together
with a one-sentence rationale.

## 19.9 Format

The completion summary is plain text. Where a section
is empty, the section header is preserved with the word
`None`. The completion summary is also appended to
`TASK_LOG.md` under the task entry.

---

# 20. Future Documents

Every future specification document, decision record,
task log entry, and changelog entry SHALL follow the
metadata format, the versioning rules, and the governance
model established by this protocol and by
`000_PROJECT_CHARTER.md`.

## 20.1 Metadata format

The metadata block of every future document SHALL include
the fields recorded in `000_PROJECT_CHARTER.md`. A document
that does not include a metadata block SHALL be rejected.

## 20.2 Versioning rules

The versioning rules in section 15 SHALL apply to every
future document. A document version that does not follow
the rules is treated as a defect.

## 20.3 Governance model

The governance model established by this protocol —
mandatory reading order, task lifecycle, documentation
update rules, change governance, escalation rules, and
completion standard — SHALL apply to every future task
without re-statement. A future document that contradicts
the governance model SHALL be rejected.

## 20.4 Inherited contract

The contract established by this document and by
`000_PROJECT_CHARTER.md` is inherited by every future
document and by every future task. A future document
that wishes to relax the contract SHALL do so by amending
this document and `000_PROJECT_CHARTER.md` through the
recorded change-governance process, not by silence.

## 20.5 Single source of truth

`docs/` is the single source of truth for the design of
the repository. No source file, no test, no example, no
notebook, and no script SHALL be committed that
contradicts the current revision of the documents in
`docs/`.

---

# End of document
