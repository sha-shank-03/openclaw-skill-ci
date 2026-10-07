"""Supplied-environment predictions and independently selected team policy."""

from .model import Finding


def eligibility(manifest, environment):
    findings = []

    def fail(rule, field, message):
        findings.append(Finding(rule, "eligibility_simulation", field, message))

    if manifest["os"] and environment["platform"] not in manifest["os"]:
        fail("DEP_OS_MISMATCH", "metadata.openclaw.os", "The supplied platform is incompatible.")
        return False, findings
    if manifest["always"]:
        return True, findings
    requires = manifest["requires"]
    for name in requires["bins"]:
        if name not in environment["bins"]:
            fail("DEP_MISSING_BIN", "requires.bins", f"Fixture lacks required binary: {name}.")
    if requires["anyBins"] and not set(requires["anyBins"]) & environment["bins"]:
        fail("DEP_MISSING_ANY_BIN", "requires.anyBins", "Fixture lacks every alternative binary.")
    for name in requires["env"]:
        if name not in environment["env_names"]:
            fail("DEP_MISSING_ENV", "requires.env", f"Fixture lacks environment name: {name}.")
    for path in requires["config"]:
        if environment["config"].get(path) is not True:
            fail("DEP_MISSING_CONFIG", "requires.config", f"Fixture configuration is not true: {path}.")
    return not findings, findings


def check_declarations(declarations, policy):
    findings = []
    for field in ("tools", "read_paths"):
        if not declarations[field] <= policy[field]:
            findings.append(Finding("PERMISSION_DECLARATION_DENIED", "team_policy", "skill-ci.json:" + field,
                                    "Declared authority exceeds the independently selected team policy."))
    return findings


def action_denial(tool, path, declarations, policy):
    from .inputs import valid_virtual_path
    if not valid_virtual_path(path):
        return "MOCK_PATH_INVALID"
    if tool not in declarations["tools"] or (tool == "read" and path not in declarations["read_paths"]):
        return "PERMISSION_UNDECLARED"
    if tool not in policy["tools"] or (tool == "read" and path not in policy["read_paths"]):
        return "PERMISSION_DENIED"
    if tool != "read":
        return "MOCK_TOOL_UNAVAILABLE"
    return None
