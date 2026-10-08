# Versions, sources and licenses

The supported native target is fixed to the official sources researched on
2026-10-07. It is not a promise of compatibility with a later OpenClaw release.
M3 retains tool version 0.2.0 and the accepted M2 runtime unchanged.

| Reference | Pinned version / revision | Purpose |
| --- | --- | --- |
| OpenClaw | 2026.9.8 / `fc23bc864e4553c2d215e479eeec47b67a0bf943` | Portable native metadata semantics |
| Agent Skills | `69ef37e9424c0a7ea9dd2293b559e43ec8176379` | Format comparison and overlap |
| ClawHub | `c23e34ad353d9ff71fa0d2a0fbdd601d7b3134ef` | Existing audits and example licensing convention |
| Python | 3.11.9, x64 | Local verified interpreter and prepared CI |
| PyYAML | 6.0.3, MIT | Restricted YAML data parsing |
| json5 | 0.12.1, Apache-2.0 library | JSON5 data parsing |

Primary native references are the pinned [skills guide](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/docs/tools/skills.md),
[frontmatter loader](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/src/skills/loading/frontmatter.ts),
[metadata types](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/src/skills/types.ts),
[gating evaluator](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/src/shared/config-eval.ts)
and [tool dispatch](https://github.com/openclaw/openclaw/blob/fc23bc864e4553c2d215e479eeec47b67a0bf943/src/skills/runtime/tool-dispatch.ts).
[PLAN.md](../PLAN.md) records the original comparison, all source URLs and
retrieval date; raw research snapshots and their SHA-256 index remain ignored
local research artifacts. Upstream implementation code is not vendored.

## Runtime distribution attribution

`requirements.lock` selects only Python 3.11 Windows AMD64 and Linux x86_64
binary wheels, enforces SHA-256 and installs no selected transitive dependencies.
No sdist compilation or candidate-provided dependency installation occurs.

| Artifact | SHA-256 |
| --- | --- |
| PyYAML 6.0.3 Windows CPython 3.11 wheel | `9f3bfb4965eb874431221a3ff3fdcddc7e74e3b07799e0e84ca4a0f867d449bf` |
| PyYAML 6.0.3 Linux CPython 3.11 wheel | `b8bb0864c5a28024fac8a632c443c87c5aa6f215c0b126c449ae1a150412f31d` |
| json5 0.12.1 universal wheel | `d9c9b3bc34a5f54d43c35e11ef7cb87d8bdd098c6ace87117a7b7e83e705c1d5` |

Full licenses extracted from the downloaded M1 wheels are in `licenses/`.
json5's upstream benchmark exceptions are recorded but no benchmark fixtures
are copied. M3 reuses the existing venv and cached wheels; no new download or
installation is executed. See [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

## Prepared CI attribution and execution boundary

The workflow uses only these Actions pins, resolved from official GitHub tag
refs on 2026-10-07 and recorded during planning:

| Action | Full commit pin | License |
| --- | --- | --- |
| actions/checkout v5 | `fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09` | MIT, GitHub Inc. and contributors |
| actions/setup-python v6 | `ece7cb06caefa5fff74198d8649806c4678c61a1` | MIT, GitHub Inc. and contributors |

Pinned [checkout license](https://github.com/actions/checkout/blob/fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09/LICENSE)
and [setup-python license](https://github.com/actions/setup-python/blob/ece7cb06caefa5fff74198d8649806c4678c61a1/LICENSE)
copies are in `licenses/actions-checkout-LICENSE.txt` and
`licenses/actions-setup-python-LICENSE.txt`. Neither Action executes locally.
Runner images `windows-2022` and `ubuntu-24.04` are versioned labels, not immutable
image digests. Python is exactly 3.11.9; dependency artifacts are hash locked.

The prepared workflow downloads trusted interpreter/dependency artifacts during
CI setup, then runs offline tests and the asserting demo. It requires no model
credentials, paid APIs or third-party service accounts. Checkout credentials
are not persisted and job permissions are read-only. It is prepared locally;
no hosted job, POSIX execution, publication or GitHub account change is claimed.

Code/documentation is MIT. Independently authored `examples/` and `fixtures/`
are MIT-0. OpenClaw is an external project with no claimed endorsement. Static
candidate installer metadata does not verify an installer's artifact availability,
version, license or security.
