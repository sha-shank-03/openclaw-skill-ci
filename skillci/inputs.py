"""Bounded data reads. No input controls code loading or process execution."""

import hashlib
import json
import stat
from pathlib import Path

from .model import InputError

MAX_JSON_BYTES = 1024 * 1024
MAX_SKILL_BYTES = 64 * 1024


def read_bytes(path, limit=MAX_JSON_BYTES):
    path = Path(path)
    try:
        info = path.lstat()
        reparse = getattr(info, "st_file_attributes", 0) & 0x400
        if not stat.S_ISREG(info.st_mode) or path.is_symlink() or reparse:
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


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("non-finite JSON")


def read_json(path):
    data = read_bytes(path)
    try:
        result = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_pairs,
                            parse_constant=_reject_constant)
    except (UnicodeError, ValueError, RecursionError):
        raise InputError("INPUT_JSON", Path(path).name, "Expected valid UTF-8 JSON with unique keys.") from None
    return result, digest(data)


def object_v1(value, location, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
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
            and not any(char in value for char in "\\:\x00\r\n")
            and all(part not in ("", ".", "..") for part in value.split("/")))


def load_permissions(path):
    data, sha = read_json(path)
    object_v1(data, Path(path).name, {"schema_version", "tools", "read_paths"})
    tools = string_set(data["tools"], "tools")
    paths = string_set(data["read_paths"], "read_paths")
    if any(not valid_virtual_path(p) for p in paths):
        raise InputError("INPUT_PATH", "read_paths", "Only canonical relative virtual file paths are supported.")
    return {"tools": tools, "read_paths": paths}, sha


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
    for action in data["actions"]:
        if (not isinstance(action, dict) or set(action) != {"tool", "path"}
                or any(not isinstance(action[k], str) or not action[k] for k in action)):
            raise InputError("INPUT_SCHEMA", "actions", "Each action requires a tool and path string.")
    if not isinstance(data["expected"], dict):
        raise InputError("INPUT_SCHEMA", "expected", "Expected an independently specified final JSON object.")
    return data, sha
