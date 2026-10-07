"""Validate recorded synthetic data. No adapter or tool execution occurs."""

import json
import re
from pathlib import Path

from .checks import action_denial
from .inputs import digest, object_v1, read_json, valid_virtual_path
from .json_values import json_equal
from .limits import MAX_ACTIONS, MAX_TRACE_EVENTS
from .model import Finding, InputError

TRACE_KEYS = {"schema_version", "execution_kind", "trace_origin", "model_execution", "state",
              "adapter_invocations", "input_hashes", "events", "final", "contract", "observations"}
DENIALS = {"MOCK_PATH_INVALID", "PERMISSION_UNDECLARED", "PERMISSION_DENIED", "MOCK_TOOL_UNAVAILABLE"}
TOOL_ERRORS = {"MOCK_FILE_MISSING", "MOCK_LOG_INVALID"}


def _invalid(message):
    raise InputError("TRACE_INCONSISTENT", "trace", message)


def _count(value):
    return type(value) is int and value >= 0


def load_trace(path):
    trace, sha = read_json(path)
    object_v1(trace, Path(path).name, TRACE_KEYS)
    if (trace["execution_kind"] != "mock_fixture" or trace["model_execution"] is not False
            or trace["trace_origin"] != "synthetic_mock"
            or trace["state"] not in ("blocked", "completed", "failed")):
        _invalid("Unsupported execution/origin/state fields; provenance is not authenticated.")
    if not isinstance(trace["events"], list) or not isinstance(trace["observations"], list):
        _invalid("Expected event and observation arrays.")
    if len(trace["events"]) > MAX_TRACE_EVENTS or len(trace["observations"]) > MAX_TRACE_EVENTS:
        raise InputError("INPUT_TRACE_LIMIT", "trace", "Trace exceeds 256 events/observations.")
    if (not _count(trace["adapter_invocations"]) or not isinstance(trace["input_hashes"], dict)
            or any(not isinstance(v, str) or not re.fullmatch(r"[a-f0-9]{64}", v) for v in trace["input_hashes"].values())):
        _invalid("Invalid adapter count or input hash declarations.")
    if trace["state"] == "blocked":
        if trace["events"] or trace["observations"] or trace["final"] is not None or trace["adapter_invocations"] != 0:
            _invalid("A blocked trace cannot contain executed observations.")
        if trace["contract"] is not None:
            _invalid("A blocked preflight trace must not claim an executed contract.")
        return trace, sha
    if not {"bundle", "environment", "policy", "scenario", "bundle/SKILL.md", "bundle/skill-ci.json"} <= set(trace["input_hashes"]):
        _invalid("Executed trace is missing its bundle/environment/policy/scenario fingerprints.")
    bundle_hashes = {key.removeprefix("bundle/"): value for key, value in trace["input_hashes"].items()
                     if key.startswith("bundle/")}
    if (any(not valid_virtual_path(key) for key in bundle_hashes)
            or digest(json.dumps(bundle_hashes, sort_keys=True).encode("utf-8")) != trace["input_hashes"]["bundle"]):
        _invalid("Recorded bundle map contradicts its aggregate fingerprint.")
    contract = trace["contract"]
    object_v1(contract, "trace.contract", {"schema_version", "actions", "expected"})
    if (not isinstance(contract["actions"], list) or not contract["actions"]
            or len(contract["actions"]) > MAX_ACTIONS or not isinstance(contract["expected"], dict)):
        _invalid("A replayable contract needs 1–32 actions and an expected object.")
    for action in contract["actions"]:
        if (not isinstance(action, dict) or set(action) != {"tool", "path"}
                or any(not isinstance(v, str) or not v for v in action.values())):
            _invalid("Invalid recorded action shape.")
    if not trace["events"] or len(trace["events"]) > len(contract["actions"]):
        _invalid("Events must cover an executed prefix of the declared actions.")
    observations = {}
    for observation in trace["observations"]:
        if (not isinstance(observation, dict) or set(observation) != {"sequence", "records", "error_count", "content_sha256"}
                or not _count(observation["sequence"]) or observation["sequence"] == 0
                or not _count(observation["records"]) or not _count(observation["error_count"])
                or observation["error_count"] > observation["records"]
                or not isinstance(observation["content_sha256"], str)
                or not re.fullmatch(r"[a-f0-9]{64}", observation["content_sha256"])
                or observation["sequence"] in observations):
            _invalid("Invalid or duplicate recorded observation.")
        observations[observation["sequence"]] = observation
    allowed_sequences = set()
    invocation_count = 0
    terminal = False
    for sequence, event in enumerate(trace["events"], 1):
        if (not isinstance(event, dict) or type(event.get("sequence")) is not int
                or event["sequence"] != sequence or terminal):
            _invalid("Event ordering is invalid or continues after a terminal failure.")
        action = contract["actions"][sequence - 1]
        if not json_equal({"tool": event.get("tool"), "path": event.get("path")}, action):
            _invalid("Event does not match its recorded action.")
        base = {"sequence", "tool", "path", "outcome"}
        if event.get("outcome") == "allowed":
            if (set(event) != base | {"records_read"} or event["tool"] != "read"
                    or not valid_virtual_path(event["path"]) or not _count(event["records_read"])):
                _invalid("Invalid allowed event from the closed read adapter.")
            allowed_sequences.add(sequence)
            invocation_count += 1
            if sequence not in observations or event["records_read"] != observations[sequence]["records"]:
                _invalid("Allowed read is missing its matching observation.")
        elif event.get("outcome") in ("denied", "tool_error"):
            rules = DENIALS if event["outcome"] == "denied" else TOOL_ERRORS
            if (set(event) != base | {"rule"} or not isinstance(event.get("rule"), str)
                    or event["rule"] not in rules):
                _invalid("Invalid terminal failure event.")
            if event["outcome"] == "denied":
                if event["rule"] == "MOCK_PATH_INVALID" and valid_virtual_path(event["path"]):
                    _invalid("Path-invalid denial contradicts a canonical virtual path.")
                if event["rule"] != "MOCK_PATH_INVALID" and not valid_virtual_path(event["path"]):
                    _invalid("Invalid paths must fail before permission or adapter selection.")
                if event["rule"] == "MOCK_TOOL_UNAVAILABLE" and event["tool"] == "read":
                    _invalid("The supported read adapter cannot be recorded as unavailable.")
            if event["outcome"] == "tool_error":
                if event["tool"] != "read" or not valid_virtual_path(event["path"]):
                    _invalid("Only canonical virtual reads can produce recorded tool errors.")
                invocation_count += 1
            terminal = True
        else:
            _invalid("An attempted event needs a recorded outcome; missing outcomes are not invented.")
    if set(observations) != allowed_sequences or invocation_count != trace["adapter_invocations"]:
        _invalid("Observation coverage or adapter count contradicts the recorded events.")
    if terminal:
        if trace["state"] != "failed" or trace["final"] is not None:
            _invalid("A terminal failure cannot claim a completed final result.")
    else:
        if len(trace["events"]) != len(contract["actions"]):
            _invalid("Successful event coverage is incomplete.")
        final = trace["final"]
        if (not isinstance(final, dict) or set(final) != {"records", "error_count", "sources"}
                or not _count(final["records"]) or not _count(final["error_count"])):
            _invalid("Final result must contain recorded integer counts and sources.")
        aggregate = {"records": sum(v["records"] for v in observations.values()),
                     "error_count": sum(v["error_count"] for v in observations.values()),
                     "sources": [event["path"] for event in trace["events"]]}
        if not json_equal(final, aggregate):
            _invalid("Final result contradicts recorded observations.")
        matched = json_equal(final, contract["expected"])
        if (trace["state"] == "completed") != matched:
            _invalid("Recorded completion state contradicts its expected-output contract.")
    return trace, sha


def evaluate_replay(trace, declarations, policy, bundle_sha, scenario=None):
    findings = []

    def fail(rule, message, category="recorded_replay"):
        findings.append(Finding(rule, category, "trace", message))

    if trace["state"] == "blocked":
        fail("REPLAY_INCOMPLETE", "Blocked execution contains no completed behavior to evaluate.")
        return None, findings
    if trace["input_hashes"].get("bundle") != bundle_sha:
        fail("REPLAY_BUNDLE_CHANGED", "The selected bundle differs from the recorded input fingerprint.")
    if scenario is not None and not json_equal(scenario["actions"], trace["contract"]["actions"]):
        fail("REPLAY_ACTIONS_CHANGED", "Selected scenario actions differ from recorded coverage.")
    for event in trace["events"]:
        rule = action_denial(event["tool"], event["path"], declarations, policy)
        if rule:
            fail(rule, "Recorded action is rejected by the current declaration/policy.",
                 "team_policy" if rule.startswith("PERMISSION_") else "recorded_replay")
    if scenario is not None:
        for observation in trace["observations"]:
            path = trace["events"][observation["sequence"] - 1]["path"]
            if path not in scenario["files"] or digest(scenario["files"][path].encode("utf-8")) != observation["content_sha256"]:
                fail("REPLAY_CONTENT_CHANGED", "Selected fixture content differs from recorded observation hashes.")
    if trace["state"] != "completed":
        fail("REPLAY_RECORDED_FAILURE", "The original recorded workflow failed; no replacement execution is performed.")
    expected = scenario["expected"] if scenario is not None else trace["contract"]["expected"]
    if trace["final"] is not None and not json_equal(trace["final"], expected):
        fail("MOCK_OUTPUT_MISMATCH", "Recorded final result does not match the selected expected-output contract.")
    return trace["final"], findings
