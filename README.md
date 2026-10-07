# OpenClaw Skill CI

Validate a local OpenClaw skill against a portable metadata profile and run
synthetic behavior contracts before deploying it. This **M2 slice** provides a
Python CLI, YAML/JSON5 metadata and installer declaration checks, bounded bundle
inspection, explicit prerequisites, a separately selected team policy, a closed
mock read/summary workflow, and non-executing recorded replay. It targets the metadata subset in
OpenClaw **2026.9.8** at `fc23bc864e4553c2d215e479eeec47b67a0bf943`.

The behavior runner is a scripted mock agent. It executes virtual reads and
counts fixture log records; it does not interpret candidate Markdown, execute
candidate code, call a model, or connect to a Gateway. Its traces are labeled
`synthetic_mock`. Static checks and mock execution are separate commands.

## Quickstart on Windows

Use PowerShell in the repository root and the existing Python 3.11 interpreter.
No OpenClaw, Node, Docker, credentials, or model account is needed.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip --isolated --disable-pip-version-check download --index-url https://pypi.org/simple --only-binary=:all: --require-hashes --no-deps -r requirements.lock --dest work\wheelhouse
.\.venv\Scripts\python.exe -m pip --isolated --disable-pip-version-check install --no-index --find-links work\wheelhouse --only-binary=:all: --require-hashes --no-deps -r requirements.lock
.\.venv\Scripts\python.exe -m skillci check examples\passing\log-summary --environment fixtures\environments\ready.json --policy fixtures\policies\read-only.json --out work\quickstart\check
.\.venv\Scripts\python.exe -m skillci run-fixture examples\passing\log-summary --environment fixtures\environments\ready.json --policy fixtures\policies\read-only.json --scenario fixtures\scenarios\summary-pass.json --out work\quickstart\passing
```

The dependency download initially needs internet access. Copy a prepared
wheelhouse to another machine and run the `--no-index` install for offline
setup. Thereafter all CLI commands and tests are offline. The lock contains
only Python 3.11 Windows AMD64 and Linux x86_64 wheels; source builds are excluded.
On Linux use `python3.11 -m venv .venv`, `.venv/bin/python`, and `/` paths.

Expected passing fixture console output:

```text
PASS execution_kind=mock_fixture model_execution=false
simulated_eligibility=true fixture_state=completed adapter_invocations=1
summary={"error_count": 2, "records": 4, "sources": ["logs/events.json"]}
```

The chosen output directory receives `report.json`, `report.md`, and, for a
fixture run, `trace.json`. Use distinct output directories for each command.
Reports contain input hashes, inspected filenames, categories, eligibility
prediction, invocation count, and summary. Traces contain attempted actions and
allowed/denied/error outcomes, recorded contracts and count/content-hash
observations. They omit virtual log payloads. Outputs must be outside the skill
bundle and must not overwrite selected inputs.

Replay the generated trace without invoking the adapter again:

```powershell
.\.venv\Scripts\python.exe -m skillci replay examples\passing\log-summary --trace work\quickstart\passing\trace.json --policy fixtures\policies\read-only.json --out work\quickstart\replay
```

Expect exit 0, `execution_kind=recorded_replay`, `model_execution=false`,
`adapter_invocations=0` and the same two errors/four records. The report retains
`trace_origin=synthetic_mock` and explicitly says `origin_authenticated=false`.
The source trace bytes are preserved. This command validates recorded
consistency; it is not fresh execution or authenticated evidence. Optional
`--environment` adds a current eligibility prediction. Optional `--scenario`
checks the current expectation and requires recorded actions/content hashes.

## Reproduce the important failures

The intentionally failing skill lacks a prerequisite in the supplied fixture:

```powershell
.\.venv\Scripts\python.exe -m skillci run-fixture examples\failing\missing-tool --environment fixtures\environments\ready.json --policy fixtures\policies\read-only.json --scenario fixtures\scenarios\summary-pass.json --out work\quickstart\missing
$LASTEXITCODE # 1
```

Its only finding is `DEP_MISSING_BIN` in `eligibility_simulation`. The workflow
is `blocked`; the trace has zero events and zero adapter invocations.

An undeclared read is independently demonstrated with the passing skill:

```powershell
.\.venv\Scripts\python.exe -m skillci run-fixture examples\passing\log-summary --environment fixtures\environments\ready.json --policy fixtures\policies\read-only.json --scenario fixtures\scenarios\undeclared-read.json --out work\quickstart\undeclared
$LASTEXITCODE # 1
```

`logs/private.json` exists in that scenario and is permitted by the team policy,
but the skill's own declaration omits it. The result is
`PERMISSION_UNDECLARED` in `team_policy`, with a denied trace event and **zero**
adapter invocations. The policy file being separate matters: changing the
candidate declaration cannot widen the independently selected team policy.

JSON5 metadata and an explicitly declared support reference are demonstrated by
`examples/passing/json5-summary`. The fictional installer is checked as data:

```powershell
.\.venv\Scripts\python.exe -m skillci run-fixture examples\passing\json5-summary --environment fixtures\environments\ready.json --policy fixtures\policies\read-only.json --scenario fixtures\scenarios\summary-pass.json --out work\quickstart\json5
.\.venv\Scripts\python.exe -m skillci run-fixture examples\failing\unsafe-installer --environment fixtures\environments\ready.json --policy fixtures\policies\read-only.json --scenario fixtures\scenarios\summary-pass.json --out work\quickstart\installer
.\.venv\Scripts\python.exe -m skillci replay examples\passing\log-summary --trace work\quickstart\passing\trace.json --policy fixtures\policies\read-only.json --scenario fixtures\scenarios\wrong-expected.json --out work\quickstart\wrong-replay
```

Expected exits are 0, 1 and 1. The installer failure is `INSTALL_UNSAFE_TARGET`
with zero adapter calls. The replay failure is `MOCK_OUTPUT_MISMATCH`, also with
zero calls, and leaves the original trace unchanged. Replay with
`fixtures/policies/deny-all.json` likewise fails before any adapter invocation.

Run the CLI acceptance suite:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests assert real command exit codes and generated report/trace contents,
including passing counts, missing prerequisite, pre-invocation denial,
independent policy denial, output mismatch, static-only behavior, and a bad
caller input. M2 adds parsing, installer, link/traversal and exact numeric limit
cases, missing/malformed logs, unavailable adapters, unknown versions and trace
consistency/coverage failures. The 37 tests include the original 12 M1 tests.
Expected-negative demonstrations are also runnable individually.

## Supply your own contracts

A candidate skill directory needs canonical YAML `SKILL.md` and this project's
`skill-ci.json`. The frontmatter accepts explicit name/description and nested
`metadata.openclaw` with `requires.bins`, `anyBins`, `env`, `config`, `os`, and
`always`; a JSON5 object string is also accepted. The name must match the parent
directory under this portable profile. The body is checked for presence, never
executed. Ordinary unchecked fields produce explicit warnings; legacy metadata
aliases, unsupported prerequisite fields, duplicate keys, explicit YAML tags,
aliases/anchors and non-finite/non-JSON values fail the profile.
Valid YAML forms accepted by OpenClaw may be rejected by this stricter profile.

The project-owned sidecar and separately selected policy share this v1 shape:

```json
{"schema_version": 1, "tools": ["read"], "read_paths": ["logs/events.json"]}
```

The sidecar declares intent; the policy is the maximum permitted set. Paths are
exact virtual keys, with `/` separators and no wildcard/absolute/traversal
syntax. The sidecar may additionally declare a `references` array of relative
support-file keys. Referenced files must exist; every regular bundle file is
inspected and hashed. This tool has only a virtual `read` adapter. A fixture scenario supplies text
files, a finite action list, and independent expected final JSON; see
`fixtures/scenarios/summary-pass.json`. There is no extensible code/plugin DSL.

Expected-output comparison is recursive and type aware: booleans never match
numbers, objects ignore key order, and arrays retain their order and length.
Finite integers and floats are one numeric category, so `0` and `0.0` match;
there is no comparison tolerance. Decimal/exponent tokens use Python's binary
float representation and may lose decimal precision. The selected JSON reader
rejects non-finite values, including exponent overflow such as `1e999`, with
input exit 2 before adapter invocation.

Environment fixtures supply platform, available binary names, environment
variable **names**, and explicit boolean config paths. They predict readiness
under that supplied state. They do not inspect your PATH, environment values,
OpenClaw defaults, credentials, or remote nodes. Missing requirements block
fixture execution. `always` bypasses requirements after the OS filter.

Exit contracts: **0** checks pass; **1** candidate validation or behavior contract
fails; **2** invocation, selected-input, or report-writing failure. Finding
categories distinguish `native_syntax`, `portable_profile`,
`eligibility_simulation`, `team_policy`, `mock_behavior`, `recorded_replay`, and `operational`.

Bounds are 64 KiB `SKILL.md`, 1 MiB per selected JSON/trace or support/virtual
file, 256 files, 8 MiB bundle content, depth 32, 32 actions and 256 trace events
or observations. Directory count is additionally limited to 256. Linked files,
linked ancestors, Windows junctions and hardlinks are rejected. These fixed
bounds belong to this tool's profile, not universal OpenClaw limits.

Installer checks recognize brew/node/go/uv/download but never install or fetch
anything. The portable profile requires exact package versions or an HTTPS
download with SHA-256 declaration; brew versions remain unverified warnings.
See [M2 design](docs/M2-DESIGN.md) for exact supported forms and compatibility
restrictions. Artifact availability, licenses, content and actual versions are
not verified by these static candidate declarations.

## Scope and evidence

This tool complements OpenClaw readiness checks, Agent Skills format validation,
and ClawHub audits by making team policy and fixture regressions runnable offline
in one small CLI. It does not claim novel security analysis or full runtime
conformance. Skill visibility/dependency metadata and experimental `allowed-tools`
are not an authorization boundary. This project's policy governs only its mock
harness, not an OpenClaw Gateway.

The in-memory tool adapter is not an OS sandbox. No candidate process or network
request is launched. These checks do not prove a skill safe or predict a real
model's instruction following. Ordinary containers would not remove all risk.
Concurrent hostile filesystem mutation is outside the guarantee; inspect a
stable checkout. Trace provenance is unauthenticated. Replay accepts only this
project's M2 trace v1 shape; older M1 traces lack required recorded evidence and
cannot be reconstructed. Hosted CI is deferred to M3. No hosted CI or live
OpenClaw execution has been claimed.

See [M2 design](docs/M2-DESIGN.md), [M2 observed evidence](docs/M2-EVIDENCE.md),
[historical M1 design](docs/M1-DESIGN.md), [historical M1 evidence](docs/M1-EVIDENCE.md),
[accepted planning scope](PLAN.md), and [dependency attribution](THIRD_PARTY_NOTICES.md).
Code is MIT; independently authored examples and fixtures are MIT-0.
