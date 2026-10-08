# Data contracts and limits

These are this project's v1 fixture contracts, not official OpenClaw schemas.
All selected JSON is UTF-8 with unique string keys, finite JSON values and
integer `schema_version: 1` (boolean `true` is not a version). Extra or missing
fields fail, apart from optional candidate `references`. Candidate metadata
has the separately documented portable YAML/JSON5 profile.

## Candidate and independent policy

The candidate sidecar `skill-ci.json` is required even for `check` in this MVP:

```json
{"schema_version": 1, "tools": ["read"], "read_paths": ["logs/events.json"], "references": ["notes.md"]}
```

`references` is optional and only allowed in the candidate sidecar. It names
support files that must exist in the bounded bundle snapshot. Every ordinary
bundle file is inspected and hashed regardless of explicit reference.

The caller-selected policy contains exactly `schema_version`, `tools` and
`read_paths`. Candidate sets must be subsets of policy sets. Tools and paths
are unique nonempty string arrays. Paths are exact relative virtual keys with
`/` separators: no absolute paths, backslashes, drive prefixes, control
characters, empty components, `.` or `..`. There are no wildcards. The only
supported adapter is `read`; a declared/permitted other tool fails as unavailable.

## Supplied environment

```json
{"schema_version": 1, "platform": "win32", "bins": ["python"], "env_names": [], "config": {"browser.enabled": true}}
```

Platform is `win32`, `linux` or `darwin`; binary and environment-variable names
are unique string arrays; config maps nonempty paths to explicit booleans.
This predicts eligibility from supplied facts. It does not inspect host PATH,
environment values, credentials or native defaults. The default fixture remains
`win32` even when a prepared Linux CI job evaluates it; it is synthetic input.
OS filtering precedes `always`; required binaries use AND, alternatives use OR.

## Scenario and final output

```json
{
  "schema_version": 1,
  "files": {"logs/events.json": "[{\"level\":\"info\"},{\"level\":\"error\"}]"},
  "actions": [{"tool": "read", "path": "logs/events.json"}],
  "expected": {"error_count": 1, "records": 2, "sources": ["logs/events.json"]}
}
```

Files map canonical virtual keys to text, actions are a nonempty bounded array
of exact `tool`/`path` string pairs, and expected is an independently selected
JSON object. The authorized adapter accepts an array of objects with string
`level` fields. Exact `error` levels count. Reads are counted in action order,
including repeated reads. Missing/malformed logs produce terminal tool errors.

Successful final output contains integer `error_count`, integer `records` and
ordered `sources`. Equality is recursive: booleans differ from numbers, object
key order is ignored, arrays preserve order/length, and finite integer/float
values compare without tolerance. Decimal/exponent tokens use binary floats;
arbitrary decimal precision is not claimed. Overflow/non-finite values fail.

## Report and recorded trace

Reports have v1 schema, tool/native/profile pins, execution labels, status/exit,
eligibility prediction, current adapter count, input fingerprints, inspected
filenames, findings and optional final summary. A finding identifies rule,
category, location, message and severity. Report/trace shapes can be inspected
in a fresh demo's per-case files and `summary.json`.

M2 trace v1 requires exactly: `schema_version`, `execution_kind`, `trace_origin`,
`model_execution`, `state`, `adapter_invocations`, `input_hashes`, `events`,
`final`, `contract`, `observations`. Its kind is `mock_fixture`, origin is
`synthetic_mock`, and model execution is false. Contract has v1 actions/expected.
Allowed reads include sequential tool/path/outcome/record count events and one
observation with sequence, records, error_count and raw-content SHA-256. Denied
or tool-error events carry an explicit rule. Terminal failure stops the prefix.

Replay validates exact shapes, sequence/action coverage, observation coverage,
counts, original expectation/state and bundle fingerprint consistency. Current
candidate bundle must match. Current policy must permit declarations/actions.
Optional selected scenario must retain actions and content hashes but may change
expected JSON. Failed/blocked recordings stay failed/incomplete. Missing
events/results are never inferred. Original M1 traces lacked these required
coverage fields and are unsupported; native OpenClaw recordings are not imported.

Replay reports `recorded_replay`, original `synthetic_mock`, false model
execution, zero current adapter calls, separate historical count and
`origin_authenticated=false`. Source bytes are preserved. Hashes/consistency do
not authenticate that observations occurred or verify counts against raw logs.

## Fixed bounds and exits

| Limit | Value |
| --- | --- |
| `SKILL.md` bytes | 65,536 |
| Selected JSON/trace or individual support/virtual file bytes | 1,048,576 |
| Bundle / virtual file count | 256 |
| Bundle / virtual content total bytes | 8,388,608 |
| Parsed container / bundle directory nesting | 32 |
| Bundle directories, including empty directories | 256 |
| Fixture actions | 32 |
| Trace events / observations | 256 each |

These tool-profile limits are not configurable through a candidate or policy
and are not universal native OpenClaw limits. Byte/depth/action preflight occurs
before adapters. Bundle/selected input reads reject links, Windows reparse points
and hardlinks. Reports must be outside the candidate and must not alias inputs.

| Exit | Meaning |
| --- | --- |
| 0 | Checks pass |
| 1 | Candidate, policy or behavior/recorded-contract failure |
| 2 | Invocation, selected-input or report-writing failure |

Categories distinguish native syntax, portable profile, eligibility simulation,
team policy, mock behavior, recorded replay and operational errors. The demo
returns 0 only when all nine actual results match the expected outcomes; a
wrong negative exit, changed rule, misleading label or output reuse fails it.
