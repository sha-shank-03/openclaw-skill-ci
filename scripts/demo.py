"""Assert fixed local examples through the real CLI; no model or installer calls."""

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = {"error_count": 2, "records": 4, "sources": ["logs/events.json"]}


class DemoFailure(Exception):
    pass


def require(condition, message):
    if not condition:
        raise DemoFailure(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def specs():
    common = {"skill": "examples/passing/log-summary", "policy": "fixtures/policies/read-only.json"}
    return [dict(common, name="static", command="check", exit=0, rules=[], calls=0, state="not_requested"),
            dict(common, name="passing", command="run-fixture", exit=0, rules=[], calls=1, state="completed", summary=SUMMARY),
            dict(common, name="missing", command="run-fixture", skill="examples/failing/missing-tool",
                 exit=1, rules=["DEP_MISSING_BIN"], calls=0, state="blocked"),
            dict(common, name="undeclared", command="run-fixture", scenario="fixtures/scenarios/undeclared-read.json",
                 exit=1, rules=["PERMISSION_UNDECLARED"], calls=0, state="failed"),
            dict(common, name="json5", command="run-fixture", skill="examples/passing/json5-summary",
                 exit=0, rules=[], calls=1, state="completed", summary=SUMMARY),
            dict(common, name="installer", command="run-fixture", skill="examples/failing/unsafe-installer",
                 exit=1, rules=["INSTALL_UNSAFE_TARGET"], calls=0, state="blocked"),
            dict(common, name="replay", command="replay", exit=0, rules=[], calls=0, state="replayed", summary=SUMMARY),
            dict(common, name="wrong-replay", command="replay", scenario="fixtures/scenarios/wrong-expected.json",
                 exit=1, rules=["MOCK_OUTPUT_MISMATCH"], calls=0, state="replay_failed", summary=SUMMARY),
            dict(common, name="denied-replay", command="replay", policy="fixtures/policies/deny-all.json",
                 exit=1, rules=["PERMISSION_DECLARATION_DENIED", "PERMISSION_DECLARATION_DENIED"], calls=0, state="blocked")]


def verify(case, result):
    """Literal acceptance expectations, independent of the runtime comparator."""
    name, report, trace = case["name"], result["report"], result["trace"]
    expected_kind = {"check": "static", "run-fixture": "mock_fixture", "replay": "recorded_replay"}[case["command"]]
    require(result["exit_code"] == case["exit"], name + ": unexpected process exit")
    require(type(report["exit_code"]) is int and report["exit_code"] == case["exit"], name + ": unexpected report exit")
    require(report["status"] == ("pass" if case["exit"] == 0 else "fail"), name + ": unexpected status")
    require([finding["rule"] for finding in report["findings"]] == case["rules"], name + ": unexpected finding rules")
    require(report["execution_kind"] == expected_kind and report["model_execution"] is False, name + ": misleading execution label")
    require(report["origin_authenticated"] is False, name + ": unexpected provenance authentication")
    require(type(report["adapter_invocations"]) is int and report["adapter_invocations"] == case["calls"], name + ": unexpected adapter calls")
    require(report["fixture_state"] == case["state"], name + ": unexpected workflow state")
    expected_summary = case.get("summary")
    require(report["summary"] == expected_summary, name + ": unexpected summary")
    if expected_summary is not None:
        require(type(report["summary"]["records"]) is int and type(report["summary"]["error_count"]) is int,
                name + ": summary counts must be integers, not booleans")
    if case["command"] == "run-fixture":
        require(trace is not None and trace["execution_kind"] == "mock_fixture" and trace["trace_origin"] == "synthetic_mock",
                name + ": missing or misleading synthetic trace")
        require(trace["model_execution"] is False and trace["adapter_invocations"] == case["calls"], name + ": contradictory trace execution")
        require(trace["state"] == case["state"], name + ": contradictory trace state")
        if case["state"] == "blocked":
            require(trace["events"] == [] and trace["observations"] == [] and trace["final"] is None, name + ": blocked run claims observations")
        elif name == "undeclared":
            require(trace["events"] == [{"sequence": 1, "tool": "read", "path": "logs/private.json",
                                         "outcome": "denied", "rule": "PERMISSION_UNDECLARED"}], name + ": denial was not before invocation")
            require(trace["observations"] == [] and trace["final"] is None, name + ": denied read claims results")
        else:
            require(trace["final"] == SUMMARY and len(trace["events"]) == 1 and trace["events"][0]["outcome"] == "allowed",
                    name + ": missing successful recorded read")
    else:
        require(trace is None, name + ": static/replay unexpectedly produced a trace")
    if case["command"] == "replay":
        require(report["trace_origin"] == "synthetic_mock" and report["recorded_adapter_invocations"] == 1,
                name + ": replay lost original synthetic history")
        require(report["simulated_eligibility"] is None, name + ": replay invented an environment prediction")


def create_output(selected):
    work = Path(os.path.abspath(ROOT / "work"))
    out = Path(os.path.abspath(selected)) if selected else work / ("demo-" + uuid4().hex[:12])
    if out == work or work not in out.parents:
        raise DemoFailure("Demo output must be a fresh directory beneath repository work/.")
    for path in list(reversed(out.parents)) + [out]:
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise DemoFailure("Linked output path components are unsupported.")
    out.mkdir(parents=True, exist_ok=False)
    return out


def run(out):
    inputs = {str(path.relative_to(ROOT).as_posix()): sha(path)
              for folder in (ROOT / "examples", ROOT / "fixtures") for path in sorted(folder.rglob("*")) if path.is_file()}
    cases, original_trace = [], None
    for case in specs():
        target = out / case["name"]
        argv = [sys.executable, "-m", "skillci", case["command"], case["skill"],
                "--policy", case["policy"], "--out", str(target)]
        if case["command"] != "replay":
            argv += ["--environment", "fixtures/environments/ready.json"]
        if case["command"] == "run-fixture":
            argv += ["--scenario", case.get("scenario", "fixtures/scenarios/summary-pass.json")]
        if case["command"] == "replay":
            argv += ["--trace", str(out / "passing/trace.json")]
            if "scenario" in case:
                argv += ["--scenario", case["scenario"]]
        started = time.perf_counter()
        process = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=15)
        report_file, trace_file = target / "report.json", target / "trace.json"
        result = {"name": case["name"], "argv": argv, "cwd": str(ROOT), "exit_code": process.returncode,
                  "elapsed_seconds": round(time.perf_counter() - started, 6), "stdout": process.stdout, "stderr": process.stderr,
                  "report": json.loads(report_file.read_text(encoding="utf-8")),
                  "trace": json.loads(trace_file.read_text(encoding="utf-8")) if trace_file.exists() else None,
                  "report_sha256": sha(report_file), "trace_sha256": sha(trace_file) if trace_file.exists() else None}
        verify(case, result)
        result["assertions_passed"] = True
        cases.append(result)
        if case["name"] == "passing":
            original_trace = trace_file.read_bytes()
        if case["command"] == "replay":
            require((out / "passing/trace.json").read_bytes() == original_trace, "Replay modified original trace bytes")
        print(f"PASS {case['name']} expected_exit={case['exit']} execution_kind={result['report']['execution_kind']} adapter_invocations={case['calls']}")
    require(all(sha(ROOT / path) == value for path, value in inputs.items()), "Demo changed example or fixture input bytes")
    summary = {"schema_version": 1, "passed": True, "model_execution": False, "candidate_code_execution": False,
               "cases": cases, "input_sha256": inputs, "input_bytes_preserved": True,
               "source_trace_bytes_preserved": True, "source_trace_sha256": sha(out / "passing/trace.json"),
               "hosted_ci_execution": False, "scope": "Local synthetic mocks and recorded replay; origin unauthenticated."}
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    lines = ["# Asserting demo", "", "All 9 cases passed their expected exit/finding/execution assertions.",
             "Model execution: false. Replay adapter calls: zero. Trace origin: synthetic_mock, unauthenticated.",
             "Example/fixture and original trace bytes preserved.", "", "| Case | Expected/actual exit | Adapter calls |",
             "| --- | --- | --- |"]
    lines.extend(f"| {case['name']} | {case['exit_code']} | {case['report']['adapter_invocations']} |" for case in cases)
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"PASS demo cases={len(cases)} model_execution=false source_trace_bytes_preserved=true out={out}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Assert nine fixed offline CLI examples with the current Python interpreter.")
    parser.add_argument("--out", type=Path, help="Fresh directory below repository work/; default creates a unique directory.")
    args = parser.parse_args(argv)
    try:
        out = create_output(args.out)
        run(out)
    except (DemoFailure, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        print(f"FAIL demo: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
