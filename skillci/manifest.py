"""M1 canonical YAML/nested metadata profile, not the whole OpenClaw loader."""

import re
from pathlib import Path

import yaml

from .inputs import MAX_SKILL_BYTES, digest, read_bytes
from .model import Finding, InputError


class UniqueSafeLoader(yaml.SafeLoader):
    pass


def _mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise yaml.constructor.ConstructorError(None, None, "invalid or duplicate mapping key", key_node.start_mark)
        result[key] = loader.construct_object(value_node)
    return result


UniqueSafeLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def load_manifest(skill_dir):
    skill_dir = Path(skill_dir)
    findings = []
    location = "SKILL.md"

    def fail(rule, field, message, category="portable_profile", severity="error"):
        findings.append(Finding(rule, category, field, message, severity))

    try:
        if skill_dir.is_symlink() or getattr(skill_dir.lstat(), "st_file_attributes", 0) & 0x400:
            raise InputError("INPUT_FILE_TYPE", location, "Skill directory cannot be a link.")
        raw = read_bytes(skill_dir / location, MAX_SKILL_BYTES)
    except (InputError, OSError):
        fail("SKILL_READ", location, "Expected a readable canonical SKILL.md in an unlinked directory.", "native_syntax")
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
        tokens = yaml.scan(header)
        if any(isinstance(t, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken)) for t in tokens):
            fail("PROFILE_YAML_ALIAS", location, "Aliases and anchors are outside the M1 portable profile.")
            return None, findings, hashes
        front = yaml.load(header, Loader=UniqueSafeLoader)
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
    known_front = {"name", "description", "metadata", "license", "compatibility"}
    for key in sorted(set(front) - known_front):
        fail("M1_UNCHECKED_FIELD", "SKILL.md", "Additional frontmatter field is not checked in M1.", severity="warning")
    metadata = front.get("metadata", {})
    if not isinstance(metadata, dict):
        fail("PROFILE_METADATA", "SKILL.md:metadata", "M1 supports nested YAML metadata only; JSON5 strings are deferred.")
        return None, findings, hashes
    claw = metadata.get("openclaw", {})
    if not isinstance(claw, dict):
        fail("MANIFEST_TYPE", "SKILL.md:metadata.openclaw", "Expected an object.")
        return None, findings, hashes
    for key in sorted(set(metadata) - {"openclaw"}):
        if key in ("clawdbot", "clawdis"):
            fail("M1_UNSUPPORTED_METADATA", "SKILL.md:metadata", "Legacy metadata aliases are outside the canonical M1 profile.")
        else:
            fail("M1_UNCHECKED_FIELD", "SKILL.md:metadata", "Additional metadata block is not checked in M1.", severity="warning")
    for key in sorted(set(claw) - {"requires", "os", "always"}):
        fail("M1_UNCHECKED_FIELD", "SKILL.md:metadata.openclaw", "Additional OpenClaw field is not checked in M1.", severity="warning")
    requires = claw.get("requires", {})
    if not isinstance(requires, dict):
        fail("MANIFEST_TYPE", "SKILL.md:metadata.openclaw.requires", "Expected an object.")
        return None, findings, hashes
    unknown = set(requires) - {"bins", "anyBins", "env", "config"}
    if unknown:
        fail("PROFILE_REQUIREMENT", "SKILL.md:metadata.openclaw.requires", "Unsupported requirement field in the simulated M1 profile.")
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
    if not isinstance(platforms, list) or any(p not in ("win32", "linux", "darwin") for p in platforms):
        fail("MANIFEST_TYPE", "SKILL.md:metadata.openclaw.os", "Expected a list of supported platform names.")
    always = claw.get("always", False)
    if type(always) is not bool:
        fail("MANIFEST_TYPE", "SKILL.md:metadata.openclaw.always", "Expected a boolean.")
    manifest = {"name": name, "requires": normalized, "os": platforms, "always": always}
    return manifest, findings, hashes
