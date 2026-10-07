# OpenClaw Skill CI — proposed implementation plan

Status: **planning only; awaiting the main chat's accepted milestone assignment**.
Research retrieved: **2026-10-07**. No application implementation, dependency installation, tests, OpenClaw execution, paid calls, or publication has occurred.

## 1. Problem and developer journey

A team keeps OpenClaw skills in Git. A change can break frontmatter, omit a prerequisite, add an unexpected installer, or widen a tool/file-access contract. Discovering that only after deployment is expensive. The team needs a repeatable pull-request check with actionable findings and inspectable evidence, even when its CI has no Gateway, credentials, or model budget.

Build a small Python CLI that checks a local skill bundle and evaluates explicitly declared behavior contracts against safe fixtures. Each finding identifies its rule, file/field, severity, and whether it comes from the supported OpenClaw metadata subset or this project's stricter team policy.

Proposed journey:

1. Author a normal `SKILL.md` and an optional `skill-ci.json` beside it. The latter is **this project's CI contract**, not an official OpenClaw manifest.
2. Select a trusted team policy and a synthetic environment fixture on the CLI. The skill cannot select or relax that policy.
3. Run static validation and the deterministic mock fixture harness; receive a concise console summary plus JSON and Markdown reports.
4. Commit the policy, scenarios, and CI invocation. Expected-negative examples must assert both exit status and specific findings.
5. Re-evaluate saved synthetic traces with the replay command when a contract changes. Replay never reissues the original tool calls.

Illustrative commands, to be implemented only after assignment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
.\.venv\Scripts\python.exe -m skillci check examples\passing\log-summary --environment fixtures\environments\ready.json --policy fixtures\policies\read-only.json --out work\demo\check
.\.venv\Scripts\python.exe -m skillci run-fixture examples\passing\log-summary --scenario fixtures\scenarios\summary-pass.json --environment fixtures\environments\ready.json --policy fixtures\policies\read-only.json --out work\demo\run
.\.venv\Scripts\python.exe -m skillci replay examples\passing\log-summary --trace work\demo\run\trace.json --policy fixtures\policies\read-only.json --out work\demo\replay
```

Installing the two pinned dependencies initially needs a package source or a pre-populated wheelhouse. All check, fixture, replay, demo, and test execution thereafter is offline and requires no model or OpenClaw installation. Also document `pip download`/`--no-index --find-links` for an offline bootstrap.

## 2. Verified format and execution model

Compatibility target: **OpenClaw 2026.9.8**, release tag `v2026.9.8`, commit **`fc23bc864e4553c2d215e479eeec47b67a0bf943`**. GitHub's latest-stable API returned that tag on the research date. The Agent Skills specification has no version number used here; pin its source snapshot at **`69ef37e9424c0a7ea9dd2293b559e43ec8176379`**. Do not invent a skill-protocol version.

The official skills guide describes a directory with `SKILL.md`, YAML frontmatter, and instructions. OpenClaw accepts nested metadata and JSON5 metadata strings. Its runtime can tolerate forms beyond a portable authoring profile. Dependency gates live under `metadata.openclaw.requires`; `os` and `always` affect eligibility. A skill teaches use of tools. Direct slash-command dispatch uses a registered tool and still passes runtime policy checks. These statements are grounded in the pinned [skills guide](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/docs/tools/skills.md), [metadata loader](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/src/skills/loading/frontmatter.ts), [eligibility evaluator](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/src/shared/config-eval.ts), and [dispatch implementation](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/src/skills/runtime/tool-dispatch.ts).

Permissions need explicit terminology. The [Agent Skills specification](https://github.com/agentskills/agentskills/blob/69ef37e9424c0a7ea9dd2293b559e43ec8176379/docs/specification.mdx) calls `allowed-tools` experimental; support varies by implementation. The inspected OpenClaw metadata types do not establish a per-skill security boundary from it. Skill allowlists control visibility, and runtime tool policy controls authority. This project may inspect simple `allowed-tools` declarations as advisory metadata; its sidecar permission declarations and selected team policy govern **only its own fixture harness**. Passing does not grant authority or configure a Gateway.

The [sandbox documentation](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/docs/gateway/sandboxing/what-gets-sandboxed.md) distinguishes sandboxed tool execution from the Gateway process and elevated execution. The MVP needs no containers. An in-memory fixture filesystem and a closed adapter registry prevent this harness from deliberately executing candidate code; they are not an OS isolation guarantee. Ordinary containers share host resources and may expose mounted data, credentials, networking, or a daemon socket. Never present them as eliminating all risk.

## 3. Existing tools and original contribution

| Existing capability | Overlap | Proposed contribution |
| --- | --- | --- |
| [OpenClaw skills CLI](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/docs/cli/skills.md) | Inventory, readiness, visibility, installation, and registry verification | Local Git-bundle CI with a supplied environment and no Gateway requirement |
| [Agent Skills `skills-ref`](https://github.com/agentskills/agentskills/blob/69ef37e9424c0a7ea9dd2293b559e43ec8176379/skills-ref/README.md) | Format validation and prompt/property helpers; README identifies it as a demonstration library | OpenClaw-specific prerequisite checks plus team policy and fixture contract evidence |
| [ClawHub audits](https://github.com/openclaw/clawhub/blob/c23e34ad353d9ff71fa0d2a0fbdd601d7b3134ef/docs/security-audits.md) | Artifact, authority, metadata, installation, and risk analysis | Offline regression assertions under a team's own versioned policy; no replacement for audit verdicts |

The original work is the integration of a narrow version-pinned metadata profile, explicit dependency simulation, permission-subset checks, and reproducible mock/trace contracts in one CI report. This is a scoped engineering contribution, not a claim to be the first skill validator, vulnerability scanner, or evaluation framework.

## 4. Narrow MVP and non-goals

### Static checks

- Accept one local skill directory with canonical `SKILL.md`. Support valid YAML frontmatter, nested `metadata.openclaw`, and a string containing JSON5 metadata. Require explicit name/description and a non-empty body under the portable CI profile.
- Check portable name/parent-directory alignment and field types. Unknown keys produce profile warnings rather than unsupported claims that OpenClaw rejects them. Legacy aliases, permissive fallback parsing, and ambiguous scalars get explicit compatibility diagnostics.
- Validate supported `requires.bins`, `anyBins`, `env`, `config`, `os`, `always`, invocation flags, `primaryEnv`, and direct-dispatch key relationships. Compare gating with a supplied environment fixture: platform, available binary names, available environment-variable names, and explicit boolean configuration paths. No real env values or secret stores are inspected.
- Validate the known installer kinds and required target fields. A selected team reproducibility policy can require exact package versions or download SHA-256 declarations. Native syntax errors and team-policy failures remain distinct. Never run installers, fetch packages requested by a candidate skill, or pretend a binary name proves its version.
- Check explicitly declared bundled references for existence and containment; do not promise to discover every prose or shell reference. Hash the inspected bundle for evidence. Reject links/reparse-point escapes and unsupported special files in the inspected bundle; use bounded counts and sizes.
- Validate `skill-ci.json` permission declarations against a separately selected policy. Initially support a small exact-name tool set and relative virtual read paths. Shell glob authorization syntax, arbitrary URL permissions, and full OpenClaw configuration evaluation are outside the MVP.

### Behavior contracts

- Sample skill: `log-summary`, which instructs an agent to read a fictional JSON event log and return error counts with a source path. Its ordinary Markdown can be read by OpenClaw; no new runtime plugin is required.
- `run-fixture` executes a **scripted mock agent**, not an LLM. It emits declared action requests, invokes a fixed in-memory `read` adapter, and computes a deterministic summary from fixture data. It does not interpret the Markdown or measure whether a real model will obey it.
- The harness rejects undeclared/disallowed tools, virtual path traversal, missing fixture files, malformed log content, output mismatches, and exceeded step budgets. Tool errors are explicit events. No candidate scripts, shell commands, dynamic imports, real HTTP, or account operations execute.
- `replay` validates a saved bounded trace against the current contract/policy and expected observations, without re-executing side effects. Reports label `execution_kind` as `static`, `mock_fixture`, or `recorded_replay` and retain `trace_origin=synthetic_mock` for this repository's traces. No supplied fixture will be labeled a real OpenClaw recording.
- A failing skill/scenario demonstrates independent failures for a missing prerequisite and undeclared read access. Other focused fixtures cover manifest and installer defects. The passing demo emits an inspectable report and trace.

Initial data contracts remain deliberately small. `skill-ci.json` v1 declares exact `tools` and `read_paths`; the separate policy supplies maximum allowed sets. A scenario v1 supplies virtual file content, a finite action list, and independently written expected final JSON. The fixed mock workflow reads the requested log and counts records marked `error`; it has no expression evaluation or arbitrary Python callback. A trace v1 records ordered tool attempts, allowed/denied outcomes, results/errors, final output, origin, bundle hash, and contract/policy hashes. Replay accepts this format only; importing native OpenClaw traces is not claimed.

Initial limits: 64 KiB `SKILL.md`, 1 MiB per JSON/fixture/support file, 256 inspected bundle files, 8 MiB total inspected bundle data, nesting depth 32, 32 fixture actions, and 256 trace events. These are this tool's defaults, not universal OpenClaw limits. The supplied team policy may tighten them. Parse/validate bounds before invoking adapters; tests use small limit overrides so they stay lightweight.

### Explicit non-goals

No Gateway client/server, live model adapter, browser automation, registry publishing, package installation from skill manifests, Docker runtime, arbitrary script execution, malware or prompt-injection classifier, full YAML/loader equivalence, recursive multi-root precedence, remote-node inventory, secret resolution, security certification, or benchmark/adoption claims. No REST API or service is needed; a small Python API and module CLI suffice. Permissions drift/baseline diff, SARIF, and third-party adapters are deferred until after the agreed MVP and require a new assignment.

## 5. Architecture and dependencies

Choose **Python 3.11**: it suits frontmatter parsing, local fixture orchestration, and CI; a Java service or Node wrapper would add deployment/build work without improving this narrow tool. `py -3.11 --version` actually returned **3.11.9**. Plain `python` resolves to **3.12.7**, so Windows quickstart must select the intended interpreter explicitly. No machine-wide installation is planned.

| Component | Responsibility |
| --- | --- |
| `skillci/__main__.py`, `cli.py` | `check`, `run-fixture`, `replay`; strict argument handling and exit contract |
| `manifest.py`, `bundle.py` | Bounded file reads, parser/normalizer, canonical model, content hashes |
| `checks.py`, `environment.py` | Rule findings and local fixture eligibility; no ambient configuration |
| `contracts.py`, `policy.py` | Project-owned v1 schemas and permission subset checks |
| `harness.py`, `replay.py` | Scripted mock state machine, closed adapters, bounded trace validation |
| `report.py` | Stable JSON/Markdown/console output; relative paths and no secret values |
| `examples/`, `fixtures/`, `tests/` | Passing/failing skills, independently stated expectations, failure coverage |

Pipeline: load bounded bundle -> parse and normalize -> static/profile findings -> evaluate supplied prerequisites and team policy -> optionally run safe mock or evaluate trace -> assert expected outputs -> persist report. A prerequisite or policy failure prevents fixture invocation. Exits: **0** all requested checks pass, **1** validation/contract failure, **2** invocation or operational input failure. Reports still identify the stage and completed checks; no failure is reported as successful execution.

Only two runtime packages:

| Pin | Need and availability | License |
| --- | --- | --- |
| `PyYAML==6.0.3` | YAML parsing. PyPI has CPython 3.11 Windows AMD64 and Linux wheels; Windows wheel HEAD returned 200. Use a restricted SafeLoader, reject duplicate keys, aliases/custom tags/multiple documents, and bound nesting/input. YAML 1.1 coercion differs from other parsers; ambiguous values must be quoted under our profile. | MIT |
| `json5==0.12.1` | OpenClaw's JSON5 metadata form. Universal wheel HEAD returned 200; no runtime dependencies. Use duplicate-key rejection, reject non-finite numbers, and bound input. | Apache-2.0 for library; upstream benchmark fixture exceptions are not copied |

Use standard-library `argparse`, `dataclasses`, `json`, `hashlib`, `pathlib`, `unittest`, and `tempfile`. Do not add pytest, a database, schema framework, model SDK, web framework, Maven, or Docker. `requirements.lock` includes hashes for explicitly supported wheels; avoid an editable-install build dependency by using `python -m skillci` from the repository. Project-owned contract, scenario, trace, environment, policy, and report formats each start at schema version **1** and reject unknown format versions.

Proposed CI pins, verified through official GitHub tag refs:

- `actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09` (`v5`, MIT).
- `actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1` (`v6`, MIT).
- Python `3.11.9` on `windows-latest` and `ubuntu-latest`; hosted OS images remain moving infrastructure and must be described as such. No paid API calls or repository secrets. Grant only `contents: read`; disable persisted Git credentials. Do not use `pull_request_target` to execute candidate changes.

OpenClaw's published npm artifact `openclaw@2026.9.8` declares MIT and Node **`>=24.16.0 <25 || >=26.1.0`**; artifact HEAD returned 200. The installed Node **24.11.1** does not satisfy it. No OpenClaw package payload was downloaded and no runtime integration will be claimed. This does not block the standalone MVP.

Repository code license: MIT. Independently authored example skills/fixtures: MIT-0, with explicit scoped notices, matching the current ClawHub publication convention should publication ever be separately authorized. Include `THIRD_PARTY_NOTICES.md` with direct dependencies and upstream reference licenses. No upstream implementation code is planned to be vendored. Research captures stay under `work/` and are not shipped as product files.

## 6. Bounded milestones

### M1 — first runnable end-to-end slice

Implement the canonical YAML/nested metadata path, fixture eligibility, exact tool/read-path declarations, minimal selected policy, and one scripted read/summary scenario. Deliver module CLI, passing and intentionally failing skills, report/trace output, minimal quickstart, licenses, and direct-dependency pins. Add only the meaningful tests needed for this slice: passing result, missing binary, undeclared read access, and failure exit/report behavior. Execute the quickstart locally using Python 3.11.9 and record actual commands and reports. **Stop at milestone review unless the assignment explicitly includes later milestones.**

### M2 — required failure cases and compatibility boundaries

Add JSON5 metadata, known installer checks, bounded bundle and trace reading, portable/profile diagnostics, explicit replay, and failure coverage in the acceptance table below. Keep policy external to the skill. Document the mock state machine and all supported/unsupported fields. Do not expand to real skill code execution to make a demo appear more realistic.

### M3 — reproducible demo, docs, and local CI-equivalent verification

Deliver a demo command that asserts positive and expected-negative results, architecture/design and limitations docs, source/version provenance, dependency attribution, CI workflow, and an evidence report. Run the documented local acceptance suite once on the assigned HP. Record hosted Windows/Linux CI as unexecuted until actually run; preparing a workflow does not establish that it passed. Main performs independent verification.

Small scoped wheel downloads and this unit suite should be lightweight; any heavy install/build, Docker/integration suite, or OpenClaw download requires an explicit lease naming this slug in the main-owned `coordination/resources.json`. Do not change that file.

## 7. Tests and concrete acceptance

Use behavior assertions, not tests that merely duplicate the implementation. Unit inputs and expected findings are fixed independently of production rules. CLI subprocess tests assert exits and parse actual generated reports. Virtual adapters record attempted access so negative tests can show denial occurred before adapter execution.

| Case | Required observation |
| --- | --- |
| Passing local bundle + summary scenario | Exit 0; `simulated_eligibility=true`; `execution_kind=mock_fixture`; observed error count matches independent fixture expectation; trace names its synthetic origin |
| Intentionally failing skill | Exit 1; rule `DEP_MISSING_BIN`; mock adapter invocation count is zero |
| Undeclared read/tool action | Exit 1; `PERMISSION_UNDECLARED` or `PERMISSION_DENIED`; no fixture read completed |
| `../`, Windows absolute/drive/UNC paths, linked bundle reference | Containment finding before read; fixture filesystem never exposes host files |
| Missing description, malformed YAML/JSON5, duplicate keys, wrong types | Stable format/profile findings; no uncaught traceback or success report |
| OS mismatch with `always=true` | Still ineligible; matched OS with `always=true` bypasses required-bin gating, as covered by pinned native-source semantics |
| `bins` versus `anyBins`, missing env name/config flag | AND/OR behavior and explicit fixture names; no real env value in output |
| Unpinned installer or missing download digest under strict policy | Policy finding distinguished from native field validity; installer never executed |
| Missing or malformed log, unavailable adapter | Explicit tool error/contract failure and exit 1; no invented summary |
| Exceeded steps, oversized/deep input, unknown schema version | Bounded failure with stable reason; no sleep-based timeout demonstration |
| Replay of saved synthetic trace | `execution_kind=recorded_replay`, `trace_origin=synthetic_mock`; zero tool execution; changed permission/expectation fails |
| Two identical deterministic runs | Stable report fields and content hashes match, excluding any explicitly documented timing field |

Expected final acceptance commands (not run during planning):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m skillci demo --out work\acceptance-demo
.\.venv\Scripts\python.exe -m skillci check examples\passing\log-summary --environment fixtures\environments\ready.json --policy fixtures\policies\read-only.json --out work\acceptance-check
.\.venv\Scripts\python.exe -m skillci run-fixture examples\passing\log-summary --scenario fixtures\scenarios\summary-pass.json --environment fixtures\environments\ready.json --policy fixtures\policies\read-only.json --out work\acceptance-run
.\.venv\Scripts\python.exe -m skillci replay examples\passing\log-summary --trace work\acceptance-run\trace.json --policy fixtures\policies\read-only.json --out work\acceptance-replay
```

The demo must finish with `expected_failures_verified=true` and `unexpected_failures=0`; it succeeds only after checking the negative cases actually fail with their stated rules. It must print that behavior is mock fixture execution. README gives individual failing commands and their expected exit 1, not just a reassuring success banner. Linux equivalents use the same module arguments with POSIX paths.

## 8. Risks, decisions, and unresolved questions

- **Native compatibility drift:** target one source commit, distinguish team policy from native semantics, and document unsupported loader fallback, alias/remote/secret/config-default behavior. A test against fixtures is not full runtime conformance.
- **False confidence from mock behavior:** scripted actions test tooling/contracts, not a model's instruction following. Every report, demo, and README labels that boundary. No real trace/model results are fabricated.
- **Candidate input/parser risks:** no candidate code runs; bounded reads, restricted parsers, duplicate rejection, virtual tooling, and no real network reduce the implemented surface. Parsing and path checks still require review and do not prove security.
- **Permission declarations can lie:** the independently selected team policy limits the harness, but cannot enforce an external Gateway or reveal unobserved behavior. Trace review is limited to recorded events.
- **Offline bootstrap versus offline execution:** exact dependency wheels require initial acquisition. Provide hash-checked wheelhouse instructions; do not claim a first install works without packages.
- **Host differences:** use `py -3.11`, not ambient `python`; do not upgrade Node or install OpenClaw for this MVP. Windows and Linux CI remain separate evidence until run.
- **Scope:** no baseline drift engine, generic security scanner, service, or container executor in this plan. Routine choices are resolved above; no essential human product question blocks work.

Required next assignment: main reviews this plan, accepts/refines the narrow MVP, and explicitly assigns **M1** or a specified set of milestones. Implementation remains prohibited until that message arrives.

## 9. Research provenance and planning evidence

All URLs below were actually read on **2026-10-07**, through web page reads or small primary-source HTTP requests. Raw snapshots and metadata are in `work/research/`; downloaded source snapshots have SHA-256 hashes in the research index. Failed guessed paths were corrected through official directory listings; no failed URL is treated as evidence.

| Primary source | Exact pin / use |
| --- | --- |
| [GitHub latest release API](https://api.github.com/repos/openclaw/openclaw/releases/latest), [tag ref](https://api.github.com/repos/openclaw/openclaw/git/ref/tags/v2026.9.8), [release](https://github.com/openclaw/openclaw/releases/tag/v2026.9.8) | Verified stable release, annotated tag, peeled commit; released 2026-10-03 |
| [npm metadata](https://registry.npmjs.org/openclaw/2026.9.8) | Published package, MIT license, engine requirement, tarball URL/integrity; HEAD verified, payload not downloaded |
| [OpenClaw skills](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/docs/tools/skills.md), [authoring](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/docs/tools/creating-skills.md), [config](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/docs/tools/skills-config.md) | Native format, supported execution, visibility/environment boundaries; MIT repository reference |
| [Metadata types](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/src/skills/types.ts), [frontmatter](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/src/skills/loading/frontmatter.ts), [gating](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/src/shared/config-eval.ts) | Supported installer metadata/digest field and OS-before-always semantics; inspected source, no vendored code |
| [Tool permissions](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/docs/gateway/security/tool-permissions.md), [sandbox execution](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/docs/gateway/sandboxing/what-gets-sandboxed.md), [Docker backend](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/docs/gateway/sandboxing/docker-backend.md) | Correct isolation terminology and external authority boundary |
| [Agent Skills specification](https://github.com/agentskills/agentskills/blob/69ef37e9424c0a7ea9dd2293b559e43ec8176379/docs/specification.mdx), [reference library](https://github.com/agentskills/agentskills/blob/69ef37e9424c0a7ea9dd2293b559e43ec8176379/skills-ref/README.md) | Snapshot pin; format constraints and overlap; code Apache-2.0, docs CC-BY-4.0; paraphrase with links |
| [ClawHub format](https://github.com/openclaw/clawhub/blob/c23e34ad353d9ff71fa0d2a0fbdd601d7b3134ef/docs/skill-format.md), [audits](https://github.com/openclaw/clawhub/blob/c23e34ad353d9ff71fa0d2a0fbdd601d7b3134ef/docs/security-audits.md) | Published-skill licensing convention and existing audit overlap; current source snapshot pin |
| [PyYAML 6.0.3](https://pypi.org/pypi/PyYAML/6.0.3/json), [official parser docs](https://pyyaml.org/wiki/PyYAMLDocumentation) | Runtime artifact/metadata/license and restricted parser selection |
| [json5 0.12.1](https://pypi.org/pypi/json5/0.12.1/json), [pinned README](https://github.com/dpranke/pyjson5/blob/v0.12.1/README.md) | Artifact/license, no runtime dependencies, duplicate-key rejection API |
| [checkout pin](https://api.github.com/repos/actions/checkout/git/ref/tags/v5), [setup-python pin](https://api.github.com/repos/actions/setup-python/git/ref/tags/v6) | Actual commit resolution; pinned LICENSE files read, both MIT |

Observed planning commands: read assigned `AGENTS.md`, own status, and human authorization; `rg --files --hidden`; `git status --short`; `git log -1` (expected failure: unborn `main`, no commits); primary source GET/HEAD reads; `py -3.11 --version` (3.11.9); `python --version` (3.12.7); `node --version` (24.11.1). No application test or demo result is claimed. Main-owned coordination files were not changed.

Artifact hash examples, verified against published metadata rather than downloaded payloads:

- PyYAML Windows CPython 3.11 wheel SHA-256: `9f3bfb4965eb874431221a3ff3fdcddc7e74e3b07799e0e84ca4a0f867d449bf`.
- json5 universal wheel SHA-256: `d9c9b3bc34a5f54d43c35e11ef7cb87d8bdd098c6ace87117a7b7e83e705c1d5`.
- OpenClaw npm integrity: `sha512-G+JkNUhtpDE3cXR4AEi2NyyG9fqI/T2WUSl8ZnR8AATH8Dh1kC3qYFL7wwPoZtgHiP/cszA86PEiE0PDysxb9Q==`.

Unexecuted: dependency install, all acceptance commands, native OpenClaw integration, container checks, and hosted CI. Native integration is outside the agreed proposed MVP unless main later explicitly expands it.
