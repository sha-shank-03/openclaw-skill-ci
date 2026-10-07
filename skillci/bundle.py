"""Bounded immutable byte snapshots of a local candidate bundle."""

import json
import os
import stat
from pathlib import Path

from .inputs import digest, ensure_unlinked_path, read_bytes
from .limits import (MAX_BUNDLE_BYTES, MAX_BUNDLE_DIRECTORIES, MAX_BUNDLE_FILES,
                     MAX_DEPTH, MAX_SKILL_BYTES, MAX_SUPPORT_BYTES)
from .model import Finding, InputError


def inspect_bundle(root):
    root = Path(root).absolute()
    files, findings = {}, []
    total = 0
    directories = 0
    pending = [(root, 0)]
    try:
        ensure_unlinked_path(root)
        if not root.is_dir():
            raise InputError("BUNDLE_READ", "bundle", "Expected a skill directory.")
        while pending:
            directory, depth = pending.pop()
            if depth > MAX_DEPTH:
                raise InputError("BUNDLE_DEPTH", "bundle", "Directory nesting exceeds depth 32.")
            # Bound directory enumeration before sorting; no unbounded list of entries.
            entries = []
            with os.scandir(directory) as scan:
                for entry in scan:
                    entries.append(entry)
                    if len(entries) + len(files) + directories > MAX_BUNDLE_FILES + MAX_BUNDLE_DIRECTORIES:
                        raise InputError("BUNDLE_ENTRY_LIMIT", "bundle", "Bundle entry limit exceeded.")
            for entry in sorted(entries, key=lambda item: item.name):
                path = Path(entry.path)
                relative = path.relative_to(root).as_posix()
                info = entry.stat(follow_symlinks=False)
                if entry.is_symlink() or getattr(info, "st_file_attributes", 0) & 0x400:
                    raise InputError("BUNDLE_LINK", relative, "Linked or reparse-point bundle entries are rejected.")
                if stat.S_ISDIR(info.st_mode):
                    directories += 1
                    if directories > MAX_BUNDLE_DIRECTORIES:
                        raise InputError("BUNDLE_DIRECTORY_LIMIT", "bundle", "Bundle exceeds 256 directories.")
                    pending.append((path, depth + 1))
                    continue
                if not stat.S_ISREG(info.st_mode) or info.st_nlink > 1:
                    raise InputError("BUNDLE_LINK", relative, "Expected regular, single-link bundle files.")
                if len(files) >= MAX_BUNDLE_FILES:
                    raise InputError("BUNDLE_FILE_LIMIT", "bundle", "Bundle exceeds 256 files.")
                limit = MAX_SKILL_BYTES if relative == "SKILL.md" else MAX_SUPPORT_BYTES
                if info.st_size > limit:
                    raise InputError("BUNDLE_FILE_SIZE", relative, "Bundle file exceeds its byte limit.")
                if total + info.st_size > MAX_BUNDLE_BYTES:
                    raise InputError("BUNDLE_TOTAL_SIZE", "bundle", "Bundle exceeds 8 MiB.")
                content = read_bytes(path, limit)
                total += len(content)
                if total > MAX_BUNDLE_BYTES:
                    raise InputError("BUNDLE_TOTAL_SIZE", "bundle", "Bundle exceeds 8 MiB.")
                files[relative] = content
    except InputError as exc:
        rule = "BUNDLE_LINK" if exc.finding.rule == "INPUT_FILE_TYPE" else exc.finding.rule
        findings.append(Finding(rule, "portable_profile", exc.finding.location, exc.finding.message))
    except OSError:
        findings.append(Finding("BUNDLE_READ", "portable_profile", "bundle", "Could not inspect the candidate bundle."))
    hashes = {name: digest(content) for name, content in sorted(files.items())}
    fingerprint = digest(json.dumps(hashes, sort_keys=True).encode("utf-8"))
    return files, hashes, fingerprint, findings
