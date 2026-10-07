"""Closed, synthetic log-summary workflow. Candidate Markdown/code never runs."""

import json

from .inputs import valid_virtual_path
from .model import Finding

MAX_ACTIONS = 32


def run_fixture(scenario, declarations, policy, trace):
    findings = []
    records = []
    sources = []

    def fail(rule, location, message, category="mock_behavior"):
        findings.append(Finding(rule, category, location, message))

    if len(scenario["actions"]) > MAX_ACTIONS:
        fail("MOCK_STEP_LIMIT", "actions", "Fixture exceeds the 32-action budget.")
        trace["state"] = "failed"
        return None, findings
    for sequence, action in enumerate(scenario["actions"], 1):
        tool, path = action["tool"], action["path"]
        event = {"sequence": sequence, "tool": tool, "path": path, "outcome": "attempted"}
        trace["events"].append(event)
        if not valid_virtual_path(path):
            rule = "MOCK_PATH_INVALID"
        elif tool not in declarations["tools"] or (tool == "read" and path not in declarations["read_paths"]):
            rule = "PERMISSION_UNDECLARED"
        elif tool not in policy["tools"] or (tool == "read" and path not in policy["read_paths"]):
            rule = "PERMISSION_DENIED"
        elif tool != "read":
            rule = "MOCK_TOOL_UNAVAILABLE"
        else:
            rule = None
        if rule:
            event.update(outcome="denied", rule=rule)
            category = "team_policy" if rule.startswith("PERMISSION_") else "mock_behavior"
            fail(rule, f"actions[{sequence - 1}]", "Action rejected before adapter invocation.", category)
            break
        # This is the only adapter. It reads a virtual dictionary, never a host path.
        trace["adapter_invocations"] += 1
        if path not in scenario["files"]:
            event.update(outcome="tool_error", rule="MOCK_FILE_MISSING")
            fail("MOCK_FILE_MISSING", f"actions[{sequence - 1}]", "No virtual file exists at the requested path.")
            break
        try:
            rows = json.loads(scenario["files"][path])
            if not isinstance(rows, list) or any(not isinstance(row, dict) or not isinstance(row.get("level"), str) for row in rows):
                raise ValueError("expected log array")
        except (ValueError, RecursionError):
            event.update(outcome="tool_error", rule="MOCK_LOG_INVALID")
            fail("MOCK_LOG_INVALID", f"actions[{sequence - 1}]", "Virtual log must contain JSON records with level strings.")
            break
        event.update(outcome="allowed", records_read=len(rows))
        records.extend(rows)
        sources.append(path)
    final = None
    if not findings:
        final = {"error_count": sum(row["level"] == "error" for row in records),
                 "records": len(records), "sources": sources}
        trace["final"] = final
        if final != scenario["expected"]:
            fail("MOCK_OUTPUT_MISMATCH", "expected", "Observed summary does not match independently specified expected JSON.")
    trace["state"] = "failed" if findings else "completed"
    return final, findings
