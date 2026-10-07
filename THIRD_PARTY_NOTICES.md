# Dependency and reference attribution

M1 uses two pinned distributions from their official PyPI metadata, retrieved
2026-10-07. Installation uses binary wheels, SHA-256 checks, and no dependencies.
There are no selected runtime transitive dependencies.

| Distribution | License | Purpose / source |
| --- | --- | --- |
| PyYAML 6.0.3 | MIT; Copyright Ingy döt Net and Kirill Simonov | Canonical YAML parsing. [Version metadata](https://pypi.org/pypi/PyYAML/6.0.3/json), [official documentation](https://pyyaml.org/wiki/PyYAMLDocumentation). |
| json5 0.12.1 | Apache-2.0 library; Copyright Google Inc. | Pinned for accepted M2 JSON5 metadata parsing; installed but not invoked in M1. [Version metadata](https://pypi.org/pypi/json5/0.12.1/json), [pinned source](https://github.com/dpranke/pyjson5/tree/v0.12.1). |

Full license records extracted from the actually downloaded wheels are in
`licenses/PyYAML-6.0.3.txt` and `licenses/json5-0.12.1.txt`. json5's license record
also identifies upstream benchmark fixture exceptions; this repository copies
none of those benchmark fixtures. Runtime wheel files and the venv are ignored
local artifacts, not vendored distribution code.

Official reference material, read during planning, is linked and paraphrased:

- OpenClaw **2026.9.8** / `fc23bc864e4553c2d215e479eeec47b67a0bf943`:
  MIT, OpenClaw Foundation. [Skills guide](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/docs/tools/skills.md),
  [repository license](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/LICENSE).
- Agent Skills specification / `69ef37e9424c0a7ea9dd2293b559e43ec8176379`:
  documentation CC-BY-4.0, code Apache-2.0. [Specification](https://github.com/agentskills/agentskills/blob/69ef37e9424c0a7ea9dd2293b559e43ec8176379/docs/specification.mdx).
- ClawHub docs / `c23e34ad353d9ff71fa0d2a0fbdd601d7b3134ef`:
  [skill format/licensing convention](https://github.com/openclaw/clawhub/blob/c23e34ad353d9ff71fa0d2a0fbdd601d7b3134ef/docs/skill-format.md),
  [existing audit capabilities](https://github.com/openclaw/clawhub/blob/c23e34ad353d9ff71fa0d2a0fbdd601d7b3134ef/docs/security-audits.md).

Examples and fixtures are independently authored fictional content under MIT-0.
OpenClaw is an external project; no endorsement, affiliation, or security
certification is claimed. Planned GitHub Actions are not installed or used in M1.
