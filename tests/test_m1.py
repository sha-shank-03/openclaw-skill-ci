"""M1 acceptance through the real CLI, with independent expected observations."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASSING = ROOT / "examples/passing/log-summary"
FAILING = ROOT / "examples/failing/missing-tool"
ENV = ROOT / "fixtures/environments/ready.json"
POLICY = ROOT / "fixtures/policies/read-only.json"
SCENARIO = ROOT / "fixtures/scenarios/summary-pass.json"


class CliAcceptance(unittest.TestCase):
    def invoke(self, command="run-fixture", skill=PASSING, scenario=SCENARIO, policy=POLICY, environment=ENV):
        with tempfile.TemporaryDirectory() as scratch:
            out = Path(scratch) / "out"
            args = [sys.executable, "-m", "skillci", command, str(skill), "--environment", str(environment),
                    "--policy", str(policy), "--out", str(out)]
            if command == "run-fixture":
                args += ["--scenario", str(scenario)]
            result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertNotIn("Traceback", result.stderr)
            report = json.loads((out / "report.json").read_text(encoding="utf-8"))
            markdown = (out / "report.md").read_text(encoding="utf-8")
            self.assertIn("model execution: **false**", markdown)
            trace_file = out / "trace.json"
            trace = json.loads(trace_file.read_text(encoding="utf-8")) if trace_file.exists() else None
            return result, report, trace

    def test_passing_summary_is_mock_and_counts_fixture_records(self):
        result, report, trace = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["exit_code"], 0)
        self.assertEqual(report["execution_kind"], "mock_fixture")
        self.assertIs(report["model_execution"], False)
        self.assertIs(report["simulated_eligibility"], True)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["summary"], {"error_count": 2, "records": 4, "sources": ["logs/events.json"]})
        self.assertEqual(trace["trace_origin"], "synthetic_mock")
        self.assertEqual(trace["adapter_invocations"], 1)
        self.assertEqual(trace["events"], [{"sequence": 1, "tool": "read", "path": "logs/events.json",
                                           "outcome": "allowed", "records_read": 4}])
        self.assertIn("PASS execution_kind=mock_fixture model_execution=false", result.stdout)

    def test_missing_binary_blocks_mock_before_adapter(self):
        result, report, trace = self.invoke(skill=FAILING)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(report["exit_code"], 1)
        self.assertIs(report["simulated_eligibility"], False)
        self.assertEqual([f["rule"] for f in report["findings"]], ["DEP_MISSING_BIN"])
        self.assertEqual(report["findings"][0]["category"], "eligibility_simulation")
        self.assertEqual(trace["state"], "blocked")
        self.assertEqual(trace["events"], [])
        self.assertEqual(trace["adapter_invocations"], 0)
        self.assertIsNone(report["summary"])
        self.assertIn('ERROR DEP_MISSING_BIN category=eligibility_simulation location="requires.bins"', result.stdout)

    def test_undeclared_read_is_denied_before_adapter(self):
        result, report, trace = self.invoke(scenario=ROOT / "fixtures/scenarios/undeclared-read.json")
        self.assertEqual(result.returncode, 1)
        self.assertEqual([f["rule"] for f in report["findings"]], ["PERMISSION_UNDECLARED"])
        self.assertEqual(report["findings"][0]["category"], "team_policy")
        self.assertIs(report["simulated_eligibility"], True)
        self.assertEqual(trace["state"], "failed")
        self.assertEqual(trace["adapter_invocations"], 0)
        self.assertEqual(trace["events"][0]["outcome"], "denied")
        self.assertEqual(trace["events"][0]["rule"], "PERMISSION_UNDECLARED")
        self.assertNotIn("records_read", trace["events"][0])
        self.assertIsNone(report["summary"])

    def test_selected_policy_rejects_candidate_declarations(self):
        result, report, trace = self.invoke(policy=ROOT / "fixtures/policies/deny-all.json")
        self.assertEqual(result.returncode, 1)
        self.assertEqual([f["rule"] for f in report["findings"]],
                         ["PERMISSION_DECLARATION_DENIED", "PERMISSION_DECLARATION_DENIED"])
        self.assertEqual(trace["events"], [])
        self.assertEqual(trace["adapter_invocations"], 0)

    def test_static_check_does_not_run_a_workflow(self):
        result, report, trace = self.invoke(command="check")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["execution_kind"], "static")
        self.assertEqual(report["fixture_state"], "not_requested")
        self.assertEqual(report["adapter_invocations"], 0)
        self.assertIsNone(trace)

    def test_bad_caller_input_is_exit_two_with_report(self):
        result, report, trace = self.invoke(environment=ROOT / "fixtures/environments/absent.json")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(report["exit_code"], 2)
        self.assertEqual(report["status"], "error")
        self.assertEqual([f["rule"] for f in report["findings"]], ["INPUT_READ"])
        self.assertEqual(trace["adapter_invocations"], 0)

    def test_wrong_expected_output_fails_without_rewriting_expectation(self):
        with tempfile.TemporaryDirectory() as scratch:
            changed = json.loads(SCENARIO.read_text(encoding="utf-8"))
            changed["expected"]["error_count"] = 99
            path = Path(scratch) / "scenario.json"
            path.write_text(json.dumps(changed), encoding="utf-8")
            result, report, trace = self.invoke(scenario=path)
        self.assertEqual(result.returncode, 1)
        self.assertEqual([f["rule"] for f in report["findings"]], ["MOCK_OUTPUT_MISMATCH"])
        self.assertEqual(report["summary"]["error_count"], 2)
        self.assertEqual(trace["adapter_invocations"], 1)


if __name__ == "__main__":
    unittest.main()
