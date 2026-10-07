"""Closed, synthetic log-summary workflow. Candidate Markdown/code never runs."""

from .checks import action_denial
from .inputs import digest
from .json_values import json_equal
from .limits import MAX_ACTIONS
from .model import Finding, InputError
from .parsing import parse_json


def run_fixture(scenario, declarations, policy, trace):
    findings = []
    records = []
    sources = []
    trace["contract"] = {"schema_version": 1, "actions": scenario["actions"], "expected": scenario["expected"]}

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
        rule = action_denial(tool, path, declarations, policy)
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
            content = scenario["files"][path]
            rows = parse_json(content, "virtual log")
            if not isinstance(rows, list) or any(not isinstance(row, dict) or not isinstance(row.get("level"), str) for row in rows):
                raise ValueError("expected log array")
        except (ValueError, InputError, RecursionError):
            event.update(outcome="tool_error", rule="MOCK_LOG_INVALID")
            fail("MOCK_LOG_INVALID", f"actions[{sequence - 1}]", "Virtual log must contain JSON records with level strings.")
            break
        event.update(outcome="allowed", records_read=len(rows))
        trace["observations"].append({"sequence": sequence, "records": len(rows),
                                      "error_count": sum(row["level"] == "error" for row in rows),
                                      "content_sha256": digest(content.encode("utf-8"))})
        records.extend(rows)
        sources.append(path)
    final = None
    if not findings:
        final = {"error_count": sum(row["level"] == "error" for row in records),
                 "records": len(records), "sources": sources}
        trace["final"] = final
        if not json_equal(final, scenario["expected"]):
            fail("MOCK_OUTPUT_MISMATCH", "expected", "Observed summary does not match independently specified expected JSON.")
    trace["state"] = "failed" if findings else "completed"
    return final, findings
