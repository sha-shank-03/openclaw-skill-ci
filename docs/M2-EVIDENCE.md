# Observed M2 evidence

Captured on 2026-10-07 at 16:08:46 UTC on the assigned Windows checkout using
CPython 3.11.9 (AMD64). The M1 venv was reused with PyYAML 6.0.3 and json5 0.12.1;
no M2 dependency download, installation or heavyweight lease was needed.
This is evidence for M2 slice review, not final project or hosted-CI acceptance.

[M2-EVIDENCE.json](M2-EVIDENCE.json) records actual argument arrays, working
directory, exits, stdout/stderr, elapsed times, report/trace snapshots, artifact
hashes, 47 source/input file hashes and assertions. Outputs remain under ignored
`work/m2-evidence/` in the local checkout. M1 evidence remains a historical
snapshot of the previously independently accepted implementation.

## Tests and dependency health

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip --isolated --disable-pip-version-check check
.\.venv\Scripts\python.exe -m skillci --help
```

The final captured suite exited **0**: **37 tests**, **zero skips**, with all
12 original M1 tests unchanged and 25 M2 tests. The subprocess took 8.050373
seconds. Dependency health exited 0 with `No broken requirements found`; CLI
help exited 0 and exposes `check`, `run-fixture`, `replay`.

Before final capture, the first expanded suite reported two failures: a
hardlink was correctly rejected but its bundle finding needed normalization,
and the trusted Windows junction setup passed arguments incorrectly. Both were
corrected and the whole suite passed. Privileged symlink creation was unavailable
on this machine; an actual Windows junction exercised reparse-point rejection.

The passing boundary probes use the real limits: 64 KiB SKILL, 1 MiB support,
8 MiB total bundle, 256 files, directory depth 32 and 32 actions. Each adjacent
over-limit case fails before adapter invocation. A 256-event input remains
within the event limit but fails recorded action coverage; 257 events or
observations fail the trace limit. Deep/oversized trace inputs fail before replay.

Failure coverage also includes YAML/JSON5 duplicates, custom tags, aliases,
nonfinite/overflow values and unsupported metadata; unsafe/unpinned installer
targets; OS-before-always and AND/OR/env/config prerequisites; missing references,
traversal and hardlinks; selected/candidate unknown versions; missing/malformed
logs; unavailable adapters; static and per-action policy denial; and typed JSON
expectations. The M2 CLI checks execute in process, while unchanged M1 acceptance
and the cases below invoke the module in real subprocesses.

## Observed CLI cases

All 14 CLI cases below asserted the exact exit, finding rules and adapter count.
Their full actual argv and outputs are in the JSON evidence. README commands
reproduce the public examples using distinct `work/quickstart/` output folders.

| Case | Exit | Exact finding rules | Current adapter calls |
| --- | --- | --- | --- |
| Passing static check | 0 | None | 0 |
| Passing synthetic mock | 0 | None | 1 |
| Missing prerequisite | 1 | `DEP_MISSING_BIN` | 0 |
| Undeclared read | 1 | `PERMISSION_UNDECLARED` | 0 |
| JSON5/support-file example | 0 | None | 1 |
| Unsafe installer example | 1 | `INSTALL_UNSAFE_TARGET` | 0 |
| Recorded replay, original expectation | 0 | None | 0 |
| Recorded replay, selected unchanged scenario | 0 | None | 0 |
| Recorded replay, deny-all policy | 1 | `PERMISSION_DECLARATION_DENIED` twice | 0 |
| Recorded replay, expected error count 99 | 1 | `MOCK_OUTPUT_MISMATCH` | 0 |
| Main-owned original boolean expectation | 1 | `MOCK_OUTPUT_MISMATCH` | 1 |
| Numeric zero with float expectation | 0 | None | 1 |
| Exponent overflow expectation | 2 | `INPUT_JSON` | 0 |
| Replay missing recorded observations | 2 | `TRACE_INCONSISTENT` | 0 |

The passing mocks and successful replays report **2 errors, 4 records** and
source `logs/events.json`. Replay explicitly reports `recorded_replay`, original
`synthetic_mock`, `model_execution=false`, zero current calls and
`origin_authenticated=false`. Its historical invocation count is 1. A replay
with no selected environment keeps eligibility unknown.

The original source trace was byte-identical after every replay, including
changed-policy, wrong-expectation and malformed-trace cases. The main-owned
boolean probe was also byte-identical after its run. SHA-256 receipts appear in
the evidence's `preservation` section. Tests additionally reject an output path
that aliases the input trace and patch the fixture workflow to raise if replay
attempts to call it.

Replay never reconstructs missing observations/results or treats a blocked/
failed run as successful. Event ordering, action/observation coverage, terminal
failure position, adapter totals, final count aggregation, original expected
contract and bundle-map fingerprint consistency are checked. These establish
internal consistency only; synthetic origin claims are not authenticated.

## Unexecuted checks

- Fresh M2 bootstrap, Linux or another OS, and hosted GitHub Actions (M3).
- Privileged Windows symlink creation; ordinary junction and hardlink rejection
  were tested locally.
- Live OpenClaw/Gateway/Node integration or real model execution.
- Candidate installer execution, artifact retrieval, availability, version or
  license verification.
- Real tool/network/account operations and concurrent hostile file mutation.
- Native OpenClaw trace import or authenticated provenance.
- Publication, push or deployment.

No paid calls, candidate code/commands/installers, live tools or runtime network
requests were made. The in-memory adapter is not an OS sandbox, and passing
these checks does not establish security or real model behavior.
