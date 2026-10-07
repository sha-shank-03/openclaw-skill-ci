"""Static installer declaration checks. Nothing is installed or fetched."""

import re
from urllib.parse import urlsplit

from .inputs import valid_virtual_path
from .model import Finding

KINDS = {"brew", "node", "go", "uv", "download"}
SEMVER = r"[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?(?:\+[A-Za-z0-9.-]+)?"
PACKAGE = r"(?:@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*"


def check_installers(specs):
    findings = []

    def fail(rule, index, message, severity="error"):
        findings.append(Finding(rule, "portable_profile", f"metadata.openclaw.install[{index}]", message, severity))

    if not isinstance(specs, list):
        fail("INSTALL_TYPE", 0, "Installer metadata must be an array.")
        return findings
    known = {"kind", "id", "label", "bins", "os", "formula", "cask", "package", "module",
             "url", "sha256", "archive", "extract", "stripComponents", "targetDir"}
    for index, spec in enumerate(specs):
        if not isinstance(spec, dict) or not isinstance(spec.get("kind"), str) or spec["kind"] not in KINDS:
            fail("INSTALL_KIND", index, "Supported kinds: brew, node, go, uv, download.")
            continue
        kind = spec["kind"]
        target = spec.get({"brew": "formula", "node": "package", "uv": "package", "go": "module", "download": "url"}[kind])
        if kind == "brew" and target is None:
            target = spec.get("cask")
        if not isinstance(target, str) or not target:
            fail("INSTALL_TARGET", index, "Installer target is required.")
            continue
        if any(char.isspace() or char in "$;|&`\\" for char in target) or target.startswith("-"):
            fail("INSTALL_UNSAFE_TARGET", index, "Target is outside the static portable profile.")
            continue
        if kind == "brew":
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9@+._/-]*", target) or ".." in target:
                fail("INSTALL_UNSAFE_TARGET", index, "Expected a portable brew formula/cask.")
            else:
                fail("INSTALL_BREW_VERSION_UNVERIFIED", index, "Formula names do not prove an immutable dependency version.", "warning")
        elif kind == "node":
            if not re.fullmatch(PACKAGE + r"(?:@[^/]+)?", target):
                fail("INSTALL_UNSAFE_TARGET", index, "Only registry package names are supported.")
            elif not re.fullmatch(PACKAGE + "@" + SEMVER, target):
                fail("INSTALL_UNPINNED", index, "The portable profile requires an exact npm version.")
        elif kind == "uv":
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*(?:[=<>!~]+[A-Za-z0-9_.+*-]+)?", target):
                fail("INSTALL_UNSAFE_TARGET", index, "Only named Python packages are supported.")
            elif not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*==[0-9][A-Za-z0-9_.+-]*", target):
                fail("INSTALL_UNPINNED", index, "The portable profile requires an exact Python package version.")
        elif kind == "go":
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._~+/-]*(?:@[A-Za-z0-9._+-]+)?", target) or ".." in target:
                fail("INSTALL_UNSAFE_TARGET", index, "Expected a portable Go module.")
            elif not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._~+/-]*@v" + SEMVER, target):
                fail("INSTALL_UNPINNED", index, "The portable profile requires an exact Go module version.")
        else:
            try:
                url = urlsplit(target)
                safe = url.scheme == "https" and bool(url.hostname) and url.username is None and url.password is None
                url.port
            except ValueError:
                safe = False
            if not safe:
                fail("INSTALL_UNSAFE_URL", index, "The portable profile requires a credential-free HTTPS URL.")
            if not isinstance(spec.get("sha256"), str) or not re.fullmatch(r"[a-fA-F0-9]{64}", spec.get("sha256", "")):
                fail("INSTALL_DIGEST_REQUIRED", index, "A 64-digit SHA-256 declaration is required; no artifact is downloaded.")
        for field in ("id", "label", "archive"):
            if field in spec and (not isinstance(spec[field], str) or not spec[field]):
                fail("INSTALL_TYPE", index, "Optional installer text fields must be non-empty strings.")
        for field in ("bins", "os"):
            if field in spec and (not isinstance(spec[field], list)
                    or any(not isinstance(v, str) or not v for v in spec[field])):
                fail("INSTALL_TYPE", index, "Optional bins/os must be string lists.")
            elif field == "os" and field in spec and any(v not in ("win32", "linux", "darwin") for v in spec[field]):
                fail("INSTALL_TYPE", index, "Unsupported installer platform.")
        if "extract" in spec and type(spec["extract"]) is not bool:
            fail("INSTALL_TYPE", index, "extract must be boolean.")
        if "stripComponents" in spec and (type(spec["stripComponents"]) is not int or spec["stripComponents"] < 0):
            fail("INSTALL_TYPE", index, "stripComponents must be a non-negative integer.")
        if "targetDir" in spec and not valid_virtual_path(spec["targetDir"]):
            fail("INSTALL_UNSAFE_PATH", index, "targetDir must be a canonical relative path.")
        if set(spec) - known:
            fail("PROFILE_UNCHECKED_INSTALL_FIELD", index, "Additional installer fields are not checked.", "warning")
    return findings
