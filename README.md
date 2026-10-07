# OpenClaw Skill CI

Validate a local OpenClaw skill against a portable metadata profile and run
synthetic behavior contracts before deploying it. This **M1 slice** provides a
Python CLI, explicit fixture prerequisites, a separately selected team policy,
and a closed mock read/summary workflow. It targets the metadata subset in
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
setup. Thereafter both CLI commands and all tests are offline. The lock contains
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
allowed/denied/error outcomes. They omit virtual log payloads.

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

Run the CLI acceptance suite:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests assert real command exit codes and generated report/trace contents,
including passing counts, missing prerequisite, pre-invocation denial,
independent policy denial, output mismatch, static-only behavior, and a bad
caller input. Expected-negative demonstrations are also runnable individually.

## Supply your own contracts

A candidate skill directory needs canonical YAML `SKILL.md` and this project's
`skill-ci.json`. The frontmatter accepts explicit name/description and nested
`metadata.openclaw` with `requires.bins`, `anyBins`, `env`, `config`, `os`, and
`always`. The name must match the parent directory under this portable profile.
The body is checked for presence, never executed. Unsupported fields produce
explicit warnings; legacy metadata aliases and JSON5 strings are outside M1.
Valid YAML forms accepted by OpenClaw may be rejected by this stricter profile.

The project-owned sidecar and separately selected policy share this v1 shape:

```json
{"schema_version": 1, "tools": ["read"], "read_paths": ["logs/events.json"]}
```

The sidecar declares intent; the policy is the maximum permitted set. Paths are
exact virtual keys, with `/` separators and no wildcard/absolute/traversal
syntax. M1 has only a virtual `read` adapter. A fixture scenario supplies text
files, a finite action list, and independent expected final JSON; see
`fixtures/scenarios/summary-pass.json`. There is no extensible code/plugin DSL.

Environment fixtures supply platform, available binary names, environment
variable **names**, and explicit boolean config paths. They predict readiness
under that supplied state. They do not inspect your PATH, environment values,
OpenClaw defaults, credentials, or remote nodes. Missing requirements block
fixture execution. `always` bypasses requirements after the OS filter.

Exit contracts: **0** checks pass; **1** candidate validation or behavior contract
fails; **2** invocation, selected-input, or report-writing failure. Finding
categories distinguish `native_syntax`, `portable_profile`,
`eligibility_simulation`, `team_policy`, `mock_behavior`, and `operational`.

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
JSON5 parsing, installer checks, replay, full bundle/reference handling, the wider
failure suite, and hosted CI are deliberately deferred to accepted later
milestones. No hosted CI or live OpenClaw execution has been claimed.

See [M1 design](docs/M1-DESIGN.md), [observed evidence](docs/M1-EVIDENCE.md),
[accepted planning scope](PLAN.md), and [dependency attribution](THIRD_PARTY_NOTICES.md).
Code is MIT; independently authored examples and fixtures are MIT-0.
