# M1 design and supported boundaries

This is the first accepted slice of PLAN.md, not the completed multi-milestone
product. `python -m skillci` runs entirely in the local process.

```text
Explicit caller-selected environment + policy
                  |
Local SKILL.md -> restricted YAML profile -> supplied prerequisite prediction
skill-ci.json -> declared authority subset of selected policy
                  |
           error? block workflow
                  |
Scenario data -> scripted mock action -> declaration check -> policy check
                  |                             |
            denied event                 fixed virtual read adapter
                                                |
                                  count JSON records marked error
                                                |
                                 compare independent expected JSON
                                                |
                                  report.json / report.md / trace.json
```

The permission sequence is implemented outside the mock action producer.
An action cannot install an adapter or select a new policy. The only adapter
reads from the scenario's in-memory dictionary. It never translates a virtual
path to an OS path. Denial precedes adapter invocation and is visible in the
trace count. Static prerequisite/policy failures produce a blocked trace with
no attempted actions. A denied attempted read produces a failed trace and an
event documenting denial, without a successful read result.

The scripted producer does not read or understand the skill's Markdown. Its
workflow is fixed Python code driven by a finite list of tool/path requests.
The expected summary is independently specified by the scenario and is not
rewritten to match the result. Output comparison can fail even after permitted
reads succeed. `model_execution=false` appears in both reports and traces.

`manifest.py` uses restricted PyYAML SafeLoader behavior and canonical nested
metadata. These are portable-profile rules, not an exact port of OpenClaw's
permissive loader. Native YAML/encoding failures are identified separately from
name/shape restrictions. Unknown metadata is reported as unchecked, and legacy
aliases are rejected in M1 so their requirements cannot be silently simulated.
JSON5 is pinned/installed but not yet used; its parser path belongs to M2.

The simulated environment stores names and boolean flags, never secrets. Its
local-platform/prerequisite subset follows the inspected native OS-before-always
order, but does not reproduce config defaults, secret injection or remote-node
behavior. `simulated_eligibility` is a prediction for that fixture only.

Reports hash selected inputs and the two inspected candidate files. The
`inspected_bundle_sha256` is a stable fingerprint of those inspected file hashes;
it is not a full recursive bundle inventory. Other supporting files and prose
references are not inspected in M1. Report/trace schemas and caller inputs use
version 1; unknown caller schemas fail with exit 2. No replay importer exists.

M1 inputs are capped at 64 KiB for SKILL.md and 1 MiB for each selected JSON file.
Direct linked files/skill roots are rejected. A 32-action budget bounds fixture
iteration. These basic constraints are not a complete adversarial-input defense:
full bundle traversal/link handling, parser-depth/trace bounds, exhaustive
failure cases, and external-process isolation are not established in M1.

Compatibility reference: OpenClaw 2026.9.8, commit
`fc23bc864e4553c2d215e479eeec47b67a0bf943`. The official
[metadata loader](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/src/skills/loading/frontmatter.ts),
[eligibility evaluator](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/src/shared/config-eval.ts),
and [dispatch policy seam](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/src/skills/runtime/tool-dispatch.ts)
were read during planning on 2026-10-07. No upstream implementation code is copied.
