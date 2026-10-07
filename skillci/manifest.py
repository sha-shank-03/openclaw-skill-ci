"""Canonical YAML/JSON5 portable metadata profile, not the whole OpenClaw loader."""

import re
from pathlib import Path

import yaml

from .inputs import MAX_SKILL_BYTES, digest, read_bytes
from .installers import check_installers
from .limits import MAX_DEPTH
from .model import Finding, InputError
from .parsing import parse_json, validate_tree


class UniqueSafeLoader(yaml.SafeLoader):
    pass


class ManifestIssue(Exception):
    def __init__(self, rule):
        self.rule = rule


def _mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str):
            raise ManifestIssue("MANIFEST_KEY_TYPE")
        if key in result:
            raise ManifestIssue("MANIFEST_DUPLICATE")
        result[key] = loader.construct_object(value_node)
    return result


UniqueSafeLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def load_manifest(skill_dir, raw=None):
    skill_dir = Path(skill_dir)
    findings = []
    location = "SKILL.md"

    def fail(rule, field, message, category="portable_profile", severity="error"):
        findings.append(Finding(rule, category, field, message, severity))

    if raw is None:
        try:
            raw = read_bytes(skill_dir / location, MAX_SKILL_BYTES)
        except (InputError, OSError):
            fail("SKILL_READ", location, "Expected a readable canonical SKILL.md.", "native_syntax")
            return None, findings, {}
    hashes = {location: digest(raw)}
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        fail("MANIFEST_ENCODING", location, "SKILL.md must be UTF-8.", "native_syntax")
        return None, findings, hashes
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        fail("MANIFEST_FRONTMATTER", location, "Expected opening and closing YAML frontmatter delimiters.", "portable_profile")
        return None, findings, hashes
    end = lines.index("---", 1)
    header = "\n".join(lines[1:end])
    try:
        depth = 0
        for token in yaml.scan(header):
            if isinstance(token, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken)):
                raise ManifestIssue("PROFILE_YAML_ALIAS")
            if isinstance(token, yaml.tokens.TagToken):
                raise ManifestIssue("PROFILE_YAML_TAG")
            if isinstance(token, (yaml.tokens.BlockMappingStartToken, yaml.tokens.BlockSequenceStartToken,
                                  yaml.tokens.FlowMappingStartToken, yaml.tokens.FlowSequenceStartToken)):
                depth += 1
                if depth > MAX_DEPTH:
                    raise ManifestIssue("MANIFEST_DEPTH")
            elif isinstance(token, (yaml.tokens.BlockEndToken, yaml.tokens.FlowMappingEndToken,
                                    yaml.tokens.FlowSequenceEndToken)):
                depth -= 1
        front = yaml.load(header, Loader=UniqueSafeLoader)
        validate_tree(front, location)
    except ManifestIssue as exc:
        fail(exc.rule, location, "YAML form is outside the strict portable profile.")
        return None, findings, hashes
    except InputError as exc:
        fail("MANIFEST_DEPTH" if exc.finding.rule == "INPUT_DEPTH" else "MANIFEST_VALUE", location, exc.finding.message)
        return None, findings, hashes
    except (yaml.YAMLError, RecursionError):
        fail("MANIFEST_YAML", location, "Malformed or unsupported YAML frontmatter.", "native_syntax")
        return None, findings, hashes
    if not isinstance(front, dict):
        fail("MANIFEST_TYPE", location, "Expected a frontmatter object.")
        return None, findings, hashes
    name = front.get("name")
    if (not isinstance(name, str) or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?", name)
            or "--" in name or name != skill_dir.name):
        fail("PROFILE_NAME", "SKILL.md:name", "Use a portable name matching the skill directory.")
    description = front.get("description")
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        fail("PROFILE_DESCRIPTION", "SKILL.md:description", "Provide a non-empty description of at most 1024 characters.")
    if not "\n".join(lines[end + 1:]).strip():
        fail("PROFILE_BODY", location, "Provide Markdown instructions after the frontmatter.")
    known_front = {"name", "description", "metadata", "license", "compatibility", "homepage",
                   "user-invocable", "disable-model-invocation", "command-dispatch", "command-tool",
                   "command-arg-mode", "allowed-tools"}
    for key in sorted(set(front) - known_front):
        fail("PROFILE_UNCHECKED_FIELD", "SKILL.md:" + key, "Additional frontmatter field is not checked.", severity="warning")
    for key in ("user-invocable", "disable-model-invocation"):
        if key in front and type(front[key]) is not bool:
            fail("MANIFEST_TYPE", "SKILL.md:" + key, "Invocation flags must be booleans under the portable profile.")
    if "command-dispatch" in front and front["command-dispatch"] != "tool":
        fail("PROFILE_DISPATCH", "SKILL.md:command-dispatch", "Only direct tool dispatch is supported.")
    if front.get("command-dispatch") == "tool" and (not isinstance(front.get("command-tool"), str) or not front["command-tool"].strip()):
        fail("PROFILE_DISPATCH", "SKILL.md:command-tool", "Direct dispatch requires a tool name.")
    if "command-arg-mode" in front and front["command-arg-mode"] != "raw":
        fail("PROFILE_DISPATCH", "SKILL.md:command-arg-mode", "Only raw direct-dispatch arguments are supported.")
    if "allowed-tools" in front:
        if not isinstance(front["allowed-tools"], str):
            fail("MANIFEST_TYPE", "SKILL.md:allowed-tools", "Expected experimental advisory text.")
        else:
            fail("PROFILE_ALLOWED_TOOLS_ADVISORY", "SKILL.md:allowed-tools", "This declaration does not enforce OpenClaw authority.", severity="warning")
    metadata = front.get("metadata", {})
    if isinstance(metadata, str):
        try:
            metadata = parse_json(metadata, "SKILL.md:metadata", json5_mode=True)
        except InputError as exc:
            fail("METADATA_JSON5", "SKILL.md:metadata", exc.finding.message)
            return None, findings, hashes
    if not isinstance(metadata, dict):
        fail("PROFILE_METADATA", "SKILL.md:metadata", "Expected nested YAML or a JSON5 object string.")
        return None, findings, hashes
    claw = metadata.get("openclaw", {})
    if not isinstance(claw, dict):
        fail("MANIFEST_TYPE", "SKILL.md:metadata.openclaw", "Expected an object.")
        return None, findings, hashes
    for key in sorted(set(metadata) - {"openclaw"}):
        if key in ("clawdbot", "clawdis"):
            fail("PROFILE_UNSUPPORTED_METADATA", "SKILL.md:metadata", "Legacy metadata aliases are outside the canonical profile.")
        else:
            fail("PROFILE_UNCHECKED_FIELD", "SKILL.md:metadata." + key, "Additional metadata block is not checked.", severity="warning")
    known_claw = {"requires", "os", "always", "install", "primaryEnv", "skillKey", "emoji", "homepage"}
    for key in sorted(set(claw) - known_claw):
        fail("PROFILE_UNCHECKED_FIELD", "SKILL.md:metadata.openclaw." + key, "Additional OpenClaw field is not checked.", severity="warning")
    for key in ("primaryEnv", "skillKey", "emoji", "homepage"):
        if key in claw and (not isinstance(claw[key], str) or not claw[key]):
            fail("MANIFEST_TYPE", "SKILL.md:metadata.openclaw." + key, "Expected non-empty text.")
    findings.extend(check_installers(claw.get("install", [])))
    requires = claw.get("requires", {})
    if not isinstance(requires, dict):
        fail("MANIFEST_TYPE", "SKILL.md:metadata.openclaw.requires", "Expected an object.")
        return None, findings, hashes
    unknown = set(requires) - {"bins", "anyBins", "env", "config"}
    if unknown:
        fail("PROFILE_REQUIREMENT", "SKILL.md:metadata.openclaw.requires", "Unsupported requirement field in the simulated profile.")
    normalized = {}
    for key in ("bins", "anyBins", "env", "config"):
        values = requires.get(key, [])
        if (not isinstance(values, list)
                or any(not isinstance(v, str) or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.+-]*", v) for v in values)
                or len(values) != len(set(values))):
            fail("MANIFEST_TYPE", "SKILL.md:requires." + key, "Expected unique portable prerequisite names.")
        else:
            normalized[key] = values
    platforms = claw.get("os", [])
    if (not isinstance(platforms, list) or any(p not in ("win32", "linux", "darwin") for p in platforms)
            or len(platforms) != len(set(platforms))):
        fail("MANIFEST_TYPE", "SKILL.md:metadata.openclaw.os", "Expected a list of supported platform names.")
    always = claw.get("always", False)
    if type(always) is not bool:
        fail("MANIFEST_TYPE", "SKILL.md:metadata.openclaw.always", "Expected a boolean.")
    manifest = {"name": name, "requires": normalized, "os": platforms, "always": always}
    return manifest, findings, hashes
