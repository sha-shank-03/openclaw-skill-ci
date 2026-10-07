# M2: bounded portable checks and recorded replay

M2 extends the independently accepted M1 mock workflow with canonical JSON5
metadata, installer declaration checks, full bounded bundle snapshots and a
non-executing recorded-data validator. It uses the same two pinned dependencies.
CI integration remains M3 work; no hosted CI or live OpenClaw run is claimed.

## Data flow and authority

`check` validates selected environment/policy inputs, captures candidate bundle
bytes, parses `SKILL.md`, validates the candidate sidecar and explicit support
references, checks installer declarations and predicts eligibility. Candidate
declarations must be subsets of the independently selected policy.

`run-fixture` adds bounded scenario validation before any adapter invocation.
Each scripted action is authorized, then dispatched only to the closed virtual
`read` adapter. The adapter reads the scenario's in-memory dictionary. A valid
log is an array of objects containing string `level` values; only exact `error`
levels count. Missing/malformed logs yield terminal `tool_error` events.
Unavailable adapters and undeclared/disallowed reads yield `denied` events
before invocation. The CLI's static declaration check usually detects policy
denial first; the harness also checks policy on every action.

`replay` reads and validates an existing trace, inspects the selected candidate,
rechecks current policy and optionally evaluates a selected scenario contract.
It never calls the fixture workflow or any adapter. It writes reports only,
never a replacement trace. Output guards reject candidate-contained outputs,
input/report collisions, linked output paths and hardlinked existing targets.
Use a new output directory for each command to avoid stale artifacts.

## Profile compatibility

The target is OpenClaw 2026.9.8, commit
`fc23bc864e4553c2d215e479eeec47b67a0bf943`, researched on 2026-10-07. Primary
references and capture hashes remain in [PLAN.md](../PLAN.md). In particular,
[official skills documentation](https://docs.openclaw.ai/tools/skills) and the
[pinned frontmatter loader](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/src/skills/loading/frontmatter.ts)
describe canonical `metadata.openclaw` parsing. This CLI implements a stricter
profile, rather than reproducing every native fallback/default.

Frontmatter must be UTF-8 YAML with opening/closing `---`, unique text keys,
matching portable name, description and nonempty body. Nested YAML metadata
and JSON5 object strings are supported. YAML anchors/aliases, explicit tags,
non-JSON scalar types, duplicate keys, non-finite numbers and excessive nesting
are rejected. JSON5 is parsed as data, never JavaScript. JSON5 comments, quoted
or unquoted keys, single quotes and trailing commas are supported. Unknown
ordinary fields produce explicit unchecked-field warnings; legacy metadata
aliases and unsupported prerequisite keys fail the canonical profile.

`requires.bins` is AND, `anyBins` is OR, environment names and true boolean
configuration paths are explicit fixtures. OS filtering runs before `always`
bypasses other prerequisites. Invocation flags and direct-tool dispatch key
relationships are checked without dispatching a tool. Experimental
`allowed-tools` is advisory and cannot grant this harness authority.

Known installer kinds are `brew`, `node`, `go`, `uv`, `download`. Required
targets, optional metadata types and supported platforms are checked. This
fixed profile rejects process/shell-like targets, local/VCS package sources,
credentials in download URLs and traversal in `targetDir`. Node requires a
registry name with exact three-part version; Go requires `@v` with an exact
three-part version; uv requires a named package with `==` exact version text.
Download requires credential-free HTTPS and a 64-digit SHA-256 declaration.
These checks do not prove a package exists, is immutable or has a valid license,
nor verify the artifact against its declared digest. Brew formula/cask names
produce a version-unverified warning. Nothing is installed or downloaded.
This profile can reject otherwise native-valid declarations, including download
queries containing `&`. Limits/reproducibility rules are fixed in M2; they are
not configurable through the candidate or external permission policy.

## Bounds and bundle snapshots

| Input | Bound |
| --- | --- |
| Canonical `SKILL.md` | 64 KiB |
| Each selected JSON/trace and each support/virtual file | 1 MiB |
| Inspected bundle / virtual files | 256 files |
| Inspected bundle / virtual content | 8 MiB total |
| Parsed containers / bundle directory nesting | Depth 32 |
| Fixture actions | 32 |
| Recorded event / observation arrays | 256 entries each |
| Bundle directories | 256, including empty directories |

Byte reads are capped before parsing. JSON/JSON5 lexical nesting scans and YAML
token scans precede parsing; parsed data is validated again. Bundle inspection
checks file count/size/total before reading the next entry and bounds directory
enumeration. Malformed virtual logs are parsed only in the authorized adapter;
their byte/depth bounds are checked during scenario preflight. Selected-input
errors exit 2; candidate/profile errors exit 1. No preflight failure invokes an
adapter. Trace consistency can reject an otherwise size-valid 256-event trace
because the supported fixture contract permits only 32 actions.

Bundle inspection rejects symlinks, Windows reparse points (including junctions),
hardlinks and special files; selected inputs reject linked ancestors and
hardlinks. Explicit sidecar `references` use canonical relative `/` keys and
must exist in the captured bundle. Every regular support file is captured and
hashed, including undeclared files; support payloads remain opaque bytes.
Prose references are not automatically extracted or recursively followed.

The bundle fingerprint hashes a sorted relative-filename-to-SHA256 map.
Reports carry each `bundle/<path>` digest and the aggregate `bundle` digest.
Fixture execution uses the captured manifest/sidecar, with no candidate file
reads by adapters. This is bounded local validation, not an OS sandbox or
race-resistant filesystem transaction. A concurrently hostile writer could
change files between checks and reads; run against a stable local checkout.

## Trace v1 and replay guarantees

M2 trace v1 contains the scripted actions and original expected JSON in
`contract`, ordered events, per-allowed-read counts/content hashes in
`observations`, a final result, adapter count and input fingerprints. It omits
log payloads. The original M1 trace shape lacked coverage/observations and is
explicitly unsupported for replay; missing data is never reconstructed.

Validation requires unique keys, finite values, supported versions and exact
field shapes, sequential events matching the recorded action prefix, complete
coverage for a successful workflow, one observation per allowed read, no events
after terminal failure, consistent counts and adapter totals, and a final/state
matching recorded observations and typed expected JSON. Blocked traces contain
no observations/contract/final; they fail replay as incomplete. Failed runs
remain failed even if a current expectation could pass them. Invalid recorded
data exits 2; completed data failing current checks exits 1.

Replay requires the selected bundle fingerprint to match. Current policy must
permit the candidate declarations and recorded actions. Optional `--scenario`
must retain recorded actions and content hashes; its expected output replaces
the original expectation for comparison. Optional `--environment` adds a
current eligibility prediction; without it eligibility remains unknown.
Changing permissions, bundle, actions, content or expected output can fail the
replay without executing a replacement workflow.

Reports say `execution_kind=recorded_replay`, `trace_origin=synthetic_mock`,
`model_execution=false`, `adapter_invocations=0`, and
`origin_authenticated=false`. The historical count is separately reported as
`recorded_adapter_invocations`. These are declared synthetic recordings, not
authenticated provenance; hashes and internal consistency do not prove that
observations actually happened. Replay does not verify raw-content counts or
infer missing tool results. It does not import native OpenClaw recordings.

Expected-output equality preserves corrected M1 semantics: booleans differ
from numbers; objects ignore key order; arrays preserve order/length; integers
and finite floats with the same parsed value compare equal without tolerance.
Binary floats can lose decimal precision; no arbitrary-precision decimal claim
is made. Exponent overflow and non-finite values are rejected before adapters.

## Tests and limitations

The suite retains all 12 M1 tests and adds metadata/installer, permission/log,
path/link, exact-limit and replay consistency cases. Replay tests patch the
fixture workflow to fail if called and verify input trace bytes are identical
after evaluation. Windows test setup uses a trusted PowerShell junction helper
when symlink privilege is absent; candidate code never controls that helper.
Acceptance expectations live in tests/scenarios outside candidate instructions.

The original contribution is the combination of independently selected fixture
authority, bounded portable metadata checking and inspectable replay consistency
in a small offline CLI. Passing does not establish security, native loader
conformance, real dependency readiness or real model behavior. Containers are
not used, and ordinary containers would not eliminate all execution risk.
