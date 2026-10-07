"""Stable reports contain synthetic observations and hashes, not fixture payloads."""

import json
from pathlib import Path

from . import OPENCLAW_COMMIT, OPENCLAW_VERSION, __version__


def new_report(execution_kind):
    return {"schema_version": 1, "tool_version": __version__, "milestone": "M2",
            "profile": "openclaw-portable-m2", "openclaw_version": OPENCLAW_VERSION,
            "openclaw_commit": OPENCLAW_COMMIT, "execution_kind": execution_kind,
            "model_execution": False, "status": "pending", "exit_code": None,
            "simulated_eligibility": None, "fixture_state": "not_requested" if execution_kind == "static" else "not_started",
            "adapter_invocations": 0, "input_hashes": {}, "inspected_files": [], "findings": [], "summary": None,
            "trace_origin": None, "origin_authenticated": False}


def new_trace():
    return {"schema_version": 1, "execution_kind": "mock_fixture", "trace_origin": "synthetic_mock",
            "model_execution": False, "state": "not_started", "adapter_invocations": 0,
            "input_hashes": {}, "events": [], "final": None, "contract": None, "observations": []}


def _json(value):
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n"


def write_reports(out, report, trace=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(_json(report), encoding="utf-8")
    lines = ["# Skill CI result", "", f"Status: **{report['status']}** (exit {report['exit_code']}).",
             f"Execution: `{report['execution_kind']}`; model execution: **false**.",
             "", "When supplied, eligibility uses a synthetic environment. Permissions govern only this fixture harness.",
             f"Adapter invocations: {report['adapter_invocations']}.", "", "```json", _json(report).rstrip(), "```", ""]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")
    if trace is not None:
        (out / "trace.json").write_text(_json(trace), encoding="utf-8")


def print_summary(report):
    print(f"{report['status'].upper()} execution_kind={report['execution_kind']} model_execution=false")
    value = report["simulated_eligibility"]
    label = "unknown" if value is None else str(value).lower()
    print(f"simulated_eligibility={label} fixture_state={report['fixture_state']} adapter_invocations={report['adapter_invocations']}")
    if report["execution_kind"] == "recorded_replay":
        print(f"trace_origin={report['trace_origin']} origin_authenticated=false recorded_adapter_invocations={report.get('recorded_adapter_invocations', 'unknown')}")
    for finding in report["findings"]:
        print(f"{finding['severity'].upper()} {finding['rule']} category={finding['category']} location={json.dumps(finding['location'])}")
    if report["summary"] is not None:
        print("summary=" + json.dumps(report["summary"], sort_keys=True))
