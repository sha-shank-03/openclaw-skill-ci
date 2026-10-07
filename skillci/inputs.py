"""Bounded data reads. No input controls code loading or process execution."""

import hashlib
import os
import stat
from pathlib import Path

from .model import InputError
from .limits import MAX_ACTIONS, MAX_BUNDLE_BYTES, MAX_BUNDLE_FILES, MAX_JSON_BYTES, MAX_SKILL_BYTES
from .parsing import check_text_depth, parse_json


def ensure_unlinked_path(path, allow_missing=False):
    path = Path(os.path.abspath(path))
    for component in list(reversed(path.parents)) + [path]:
        try:
            info = component.lstat()
        except FileNotFoundError:
            if allow_missing:
                continue
            raise InputError("INPUT_READ", path.name, "Could not read the selected input.") from None
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise InputError("INPUT_FILE_TYPE", path.name, "Linked path components are unsupported.")
    return path


def read_bytes(path, limit=MAX_JSON_BYTES):
    path = Path(os.path.abspath(path))
    try:
        ensure_unlinked_path(path)
        info = path.lstat()
        reparse = getattr(info, "st_file_attributes", 0) & 0x400
        if not stat.S_ISREG(info.st_mode) or path.is_symlink() or reparse or info.st_nlink > 1:
            raise InputError("INPUT_FILE_TYPE", path.name, "Expected a regular, unlinked file.")
        with path.open("rb") as source:
            data = source.read(limit + 1)
    except (OSError, ValueError):
        raise InputError("INPUT_READ", path.name, "Could not read the selected input.") from None
    if len(data) > limit:
        raise InputError("INPUT_TOO_LARGE", path.name, f"Input exceeds {limit} bytes.")
    return data


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json_data(data, location):
    if len(data) > MAX_JSON_BYTES:
        raise InputError("INPUT_TOO_LARGE", location, "JSON input exceeds 1 MiB.")
    try:
        result = parse_json(data.decode("utf-8"), location)
    except UnicodeError:
        raise InputError("INPUT_JSON", location, "Expected UTF-8 JSON.") from None
    return result, digest(data)


def read_json(path):
    return read_json_data(read_bytes(path), Path(path).name)


def object_v1(value, location, keys, optional=()):
    if not isinstance(value, dict) or not set(keys) <= set(value) or set(value) - set(keys) - set(optional):
        raise InputError("INPUT_SCHEMA", location, "Unexpected or missing v1 object fields.")
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise InputError("INPUT_VERSION", location, "Only schema_version 1 is supported.")


def string_set(value, location):
    if (not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value)
            or len(value) != len(set(value))):
        raise InputError("INPUT_SCHEMA", location, "Expected unique, non-empty string entries.")
    return frozenset(value)


def valid_virtual_path(value):
    """Exact POSIX virtual keys; never translate these to host filesystem paths."""
    return (isinstance(value, str) and bool(value) and not value.startswith("/")
            and not any(char in value for char in "\\:")
            and not any(ord(char) < 32 for char in value)
            and all(part not in ("", ".", "..") for part in value.split("/")))


def load_permissions(path, raw=None, allow_references=False):
    data, sha = read_json(path) if raw is None else read_json_data(raw, Path(path).name)
    object_v1(data, Path(path).name, {"schema_version", "tools", "read_paths"},
              {"references"} if allow_references else ())
    tools = string_set(data["tools"], "tools")
    paths = string_set(data["read_paths"], "read_paths")
    if any(not valid_virtual_path(p) for p in paths):
        raise InputError("INPUT_PATH", "read_paths", "Only canonical relative virtual file paths are supported.")
    references = string_set(data.get("references", []), "references")
    if any(not valid_virtual_path(p) for p in references):
        raise InputError("INPUT_PATH", "references", "References must stay inside the candidate bundle.")
    return {"tools": tools, "read_paths": paths, "references": references}, sha


def load_environment(path):
    data, sha = read_json(path)
    object_v1(data, Path(path).name, {"schema_version", "platform", "bins", "env_names", "config"})
    if data["platform"] not in ("win32", "linux", "darwin"):
        raise InputError("INPUT_SCHEMA", "platform", "Expected win32, linux, or darwin.")
    data["bins"] = string_set(data["bins"], "bins")
    data["env_names"] = string_set(data["env_names"], "env_names")
    if (not isinstance(data["config"], dict)
            or any(not isinstance(k, str) or not k or type(v) is not bool
                   for k, v in data["config"].items())):
        raise InputError("INPUT_SCHEMA", "config", "Expected explicit boolean configuration paths.")
    return data, sha


def load_scenario(path):
    data, sha = read_json(path)
    object_v1(data, Path(path).name, {"schema_version", "files", "actions", "expected"})
    if (not isinstance(data["files"], dict)
            or any(not valid_virtual_path(k) or not isinstance(v, str)
                   for k, v in data["files"].items())):
        raise InputError("INPUT_SCHEMA", "files", "Expected virtual file paths mapped to text content.")
    if not isinstance(data["actions"], list) or not data["actions"]:
        raise InputError("INPUT_SCHEMA", "actions", "Expected a non-empty finite action list.")
    if len(data["actions"]) > MAX_ACTIONS:
        raise InputError("INPUT_ACTION_LIMIT", "actions", "Fixture exceeds 32 actions.")
    if len(data["files"]) > MAX_BUNDLE_FILES:
        raise InputError("INPUT_FILE_LIMIT", "files", "Fixture exceeds 256 virtual files.")
    total = 0
    for content in data["files"].values():
        size = len(content.encode("utf-8"))
        total += size
        if size > MAX_JSON_BYTES or total > MAX_BUNDLE_BYTES:
            raise InputError("INPUT_TOO_LARGE", "files", "Virtual file byte limit exceeded.")
        check_text_depth(content, "files")
    for action in data["actions"]:
        if (not isinstance(action, dict) or set(action) != {"tool", "path"}
                or any(not isinstance(action[k], str) or not action[k] for k in action)):
            raise InputError("INPUT_SCHEMA", "actions", "Each action requires a tool and path string.")
    if not isinstance(data["expected"], dict):
        raise InputError("INPUT_SCHEMA", "expected", "Expected an independently specified final JSON object.")
    return data, sha
