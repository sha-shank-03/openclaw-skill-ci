# Final local M3 evidence

Captured on **2026-10-08 at 02:15:18 UTC** (07:45:18 Asia/Calcutta) in the
assigned Windows checkout. CPython **3.11.9 x64**, PyYAML **6.0.3** and json5
**0.12.1** reuse the existing M1 venv. There was no M3 download, dependency
installation, native OpenClaw setup, paid call or publication.

[M3-EVIDENCE.json](M3-EVIDENCE.json) contains actual argv, exits, stdout/stderr,
elapsed times, demo reports/traces/assertions, literal Windows CLI reports,
57 source SHA-256 values, 37 preserved accepted-file receipts and static CI
configuration assertions. Raw outputs and command receipts remain under
ignored `work/m3-evidence-<id>/`. This is the final worker review package;
whole-repository independent acceptance belongs to the main chat.

## Actual local commands and results

The capture used the current venv interpreter for:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/demo.py --out work/m3-evidence-<id>/demo
.\.venv\Scripts\python.exe -m pip --isolated --disable-pip-version-check check
```

The full suite exited **0**: **40 tests, zero skips** in **9.006450 seconds**
(subprocess elapsed time). All 12 M1 and 25 M2 tests remain unchanged. The three
M3 tests reject wrong expected-negative exits/findings, misleading replay
model/origin/adapter claims, and execute the real nine-case demo, including
refusal to reuse existing output without modifying its prior summary.

The fresh demo exited **0** in **2.055131 seconds**. Its actual results were:

| Case | Asserted actual exit | Exact finding rules | Current adapters |
| --- | --- | --- | --- |
| Static check | 0 | None | 0 |
| Passing mock | 0 | None | 1 |
| Missing prerequisite | 1 | `DEP_MISSING_BIN` | 0 |
| Undeclared read | 1 | `PERMISSION_UNDECLARED` | 0 |
| JSON5/support example | 0 | None | 1 |
| Unsafe installer | 1 | `INSTALL_UNSAFE_TARGET` | 0 |
| Recorded replay | 0 | None | 0 |
| Changed replay expectation | 1 | `MOCK_OUTPUT_MISMATCH` | 0 |
| Changed replay policy | 1 | `PERMISSION_DECLARATION_DENIED` twice | 0 |

Passing mocks/replay report integer **2 errors, 4 records** and source
`logs/events.json`. Every case checks its literal exit, rule list, status,
execution kind, false model execution, state and adapter count. Replay retains
`synthetic_mock`, historical count 1, unknown current eligibility and
`origin_authenticated=false`. It emits no new trace. Each replay preserves the
original trace bytes, and all example/fixture hashes remain unchanged.

Three additional Windows README commands independently ran static check, fresh
mock and recorded replay, with actual exits **0,0,0**, current adapter counts
**0,1,0**, no findings and the literal four/two summary where applicable. Their
full argv, selected paths and reports are recorded in the evidence JSON.
Dependency health exited 0 with `No broken requirements found`.

## Prepared CI and preservation checks

The first final capture caught an invalid YAML plain scalar containing the pip
command's trailing colon. The command was changed to a folded block scalar,
and the final capture passed YAML parsing and configuration assertions. No
hosted workflow or dependency install step was run.

Static checks confirm full checkout/setup-python commit pins match the existing
official-ref planning record, Python 3.11.9 x64, Windows 2022/Ubuntu 24.04 matrix,
10-minute timeout, read-only permissions, non-persisted checkout credentials,
hash-locked binary install flags, unchanged unit suite and asserting demo steps.
Both Action LICENSE copies match their pinned research captures byte-for-byte.
Parsing/configuration checks do not establish hosted execution success.

Accepted M2 runtime modules, lock, candidate examples, scenarios/policies and
M1/M2 tests still match the prior M2 source hashes. Historical M1/M2 evidence
JSON/Markdown is unmodified and matches its prior Git content. M3 changes are
the demo and its assertions, prepared workflow, final docs and license attribution.
Relative links in the current review documents were checked locally. Source
hashes describe the actual tested checkout, not an immutable runner-image claim.

## Review entry points and unexecuted checks

Start with [README](../README.md), [architecture/contribution](ARCHITECTURE.md),
[contracts/limits](CONTRACTS.md), [provenance/licenses](PROVENANCE.md), the
[asserting demo](../scripts/demo.py) and
[prepared workflow](../.github/workflows/ci.yml). The accepted runtime profile
remains version 0.2.0 / `openclaw-portable-m2`; M3 did not change its semantics.

Unexecuted:

- Fresh M3 interpreter/dependency setup and all POSIX quickstart/Linux commands.
- Hosted Windows/Linux GitHub Actions; runner labels are not immutable images.
- Native OpenClaw/Gateway/Node or live model integration.
- Candidate code/process/installer/plugin execution, artifact retrieval/version/
  license verification, or real network/account operations.
- Authenticated provenance, native trace import, concurrent hostile file mutation,
  general native conformance or security guarantees.
- Publication, push and deployment.

The fixtures are scripted synthetic mocks. Replay validates recorded internal
consistency and current contracts with zero tools; it is not fresh model
execution or authenticated evidence. The adapter is not an OS sandbox, and
ordinary containers would not remove all risk. This prepared local repository
does not imply any external service or CI has passed.
