# Observed M1 evidence

Recorded on **2026-10-07** on the assigned Windows HP, using the repository-local
Python **3.11.9** venv. This records commands actually executed, not proposed
acceptance outcomes. No model calls or live OpenClaw execution occurred.

## Bootstrap

These commands completed with exit 0:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip --isolated --disable-pip-version-check download --index-url https://pypi.org/simple --only-binary=:all: --require-hashes --no-deps -r requirements.lock --dest work\wheelhouse
.\.venv\Scripts\python.exe -m pip --isolated --disable-pip-version-check install --no-index --find-links work\wheelhouse --only-binary=:all: --require-hashes --no-deps -r requirements.lock
.\.venv\Scripts\python.exe -m pip --isolated --disable-pip-version-check check
```

Observed: two binary wheels downloaded, then installed from the local wheelhouse.
Installed app dependencies: PyYAML **6.0.3**, json5 **0.12.1**.
`pip check` printed `No broken requirements found.` Distribution metadata shows
no selected runtime transitive dependencies. Pip/setuptools supplied by the
standard venv bootstrap are not application runtime imports.

The actual wheel payload hashes were independently computed and match the lock:

| Wheel | SHA-256 |
| --- | --- |
| `pyyaml-6.0.3-cp311-cp311-win_amd64.whl` | `9f3bfb4965eb874431221a3ff3fdcddc7e74e3b07799e0e84ca4a0f867d449bf` |
| `json5-0.12.1-py3-none-any.whl` | `d9c9b3bc34a5f54d43c35e11ef7cb87d8bdd098c6ace87117a7b7e83e705c1d5` |

Both wheel license files were read from their distribution metadata and copied
to `licenses/`. Downloads/install logs and computed hashes remain under
`work/bootstrap/`, which is ignored scratch output. This small setup was
explicitly authorized as lightweight M1 work; no heavyweight resource lease was
used or modified.

## Quickstart and negative examples

All four CLI invocations use the documented fixture environment and independently
selected read-only policy. The full actual argument vectors, console output,
reports, traces, and hashes are stored in [M1-EVIDENCE.json](M1-EVIDENCE.json).

| Actual CLI case | Exit | Finding rules | Fixture state | Adapter invocations |
| --- | --- | --- | --- | --- |
| `check examples/passing/log-summary` | 0 | none | not requested | 0 |
| `run-fixture examples/passing/log-summary` with `summary-pass.json` | 0 | none | completed | 1 |
| `run-fixture examples/failing/missing-tool` with `summary-pass.json` | 1 | `DEP_MISSING_BIN` | blocked | 0 |
| `run-fixture examples/passing/log-summary` with `undeclared-read.json` | 1 | `PERMISSION_UNDECLARED` | failed | 0 |

Passing summary: `error_count=2`, `records=4`, `sources=["logs/events.json"]`.
The trace says `trace_origin=synthetic_mock` and `model_execution=false`.
The missing-prerequisite trace has no attempted events. The undeclared-read trace
contains one denied event, no read result, and zero adapter invocations even
though the virtual file exists and the selected policy would permit that path.

Original generated files are in `work/quickstart/{check,passing,missing,undeclared}/`;
corrected reruns are in `work/m1-correction/{check,passing,missing,undeclared}-output/`.
The persisted JSON evidence includes snapshots of these results so the report
remains reviewable without retaining scratch directories. It also records source
file hashes for the tested Python implementation and tests.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Observed corrected run: **12 tests passed**, exit **0**, with no skipped tests. This
suite exercises the actual CLI in fresh subprocesses and reads generated files.
Coverage includes passing summary, missing binary, undeclared read, selected
policy denying a candidate's declarations, static-only behavior, invalid
caller-selected input with exit 2, and independently wrong expected output.
It also covers boolean-versus-zero counts, valid integer/float zero counts,
nested boolean/number comparisons, and finite-token overflow rejection.
It asserts exact finding rules, exits, origin labels, and adapter counts.

The staged tree passed `git diff --cached --check`. A separate planning/evidence
integrity check confirmed that each recorded Python source hash still matches
the tested source and that all four CLI result snapshots are present. This was
an evidence check, not an additional application test run.

The original seven-test suite passed before independent review. Main then
reproduced a false pass: expected JSON boolean `false` matched an actual numeric
zero because the original implementation used Python container equality. That
defect required the bounded correction below. Corrected suite output is captured
verbatim in the evidence JSON; its elapsed time is an observed test duration,
not a benchmark.
`python -m skillci --help` also completed with exit 0 and lists only `check` and
`run-fixture` for M1.

## Bounded M1 correction

Recursive JSON type-aware comparison now distinguishes booleans from numbers,
including nested objects/arrays. Finite integers/floats share a numeric category
and compare their parsed Python values with no tolerance; `0` and `0.0` are
equivalent. Decimal/exponent tokens use binary floats, not arbitrary precision.

The selected JSON reader rejects exponent overflow such as `1e999` instead of
accepting Python infinity. This correction adds no JSON5, installer, or replay
implementation and requires no new dependency or setup.

The exact main-owned boolean scenario was read without modifying its source
or main's acceptance output directories. Fresh worker-owned output now reports
exit **1**, only `MOCK_OUTPUT_MISMATCH`, actual integer zero counts, and one
permitted virtual read. Matching zero expectations (`0` and `0.0`) pass with
exit **0**. A selected scenario with `1e999` fails with exit **2**, only
`INPUT_JSON`, no events, and **zero** adapter invocations. The four documented
examples were rerun and retain exits **0/0/1/1** and their original findings.
The updated evidence JSON includes these correction receipts and source hashes.

## Unexecuted and deferred

- No native OpenClaw loading, Gateway integration, paid model call, or fresh model
  evaluation. Installed Node 24.11.1 does not satisfy the pinned OpenClaw engine
  requirement; this standalone slice does not use Node.
- No candidate script/installer, actual network tool, container, or account action.
- No Linux runtime tests or hosted CI. Linux wheel hash is pinned from published
  metadata, but that payload/runtime was not exercised locally.
- JSON5 parsing, installer policy, replay, recursive bundle handling, exhaustive
  parser/trace hardening, and the later CI/demo milestones remain unimplemented.
- No GitHub creation, push, deployment, or publication.

This is M1 evidence for independent slice review, not final project acceptance or
a security guarantee. A scripted fixture does not establish model obedience to
candidate Markdown.
