"""The demo must detect false passes and exercise actual subprocess examples."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.demo import DemoFailure, specs, verify

ROOT = Path(__file__).resolve().parents[1]


class AssertingDemoAcceptance(unittest.TestCase):
    def minimal(self, name):
        case = next(case for case in specs() if case["name"] == name)
        return case, {"exit_code": case["exit"], "trace": None,
                      "report": {"exit_code": case["exit"], "status": "pass" if case["exit"] == 0 else "fail",
                                 "findings": [{"rule": rule} for rule in case["rules"]], "execution_kind": "recorded_replay",
                                 "model_execution": False, "origin_authenticated": False,
                                 "adapter_invocations": 0, "fixture_state": case["state"], "summary": case.get("summary"),
                                 "trace_origin": "synthetic_mock", "recorded_adapter_invocations": 1, "simulated_eligibility": None}}

    def test_demo_rejects_wrong_expected_negative_exit_or_rule(self):
        case, good = self.minimal("wrong-replay")
        verify(case, good)
        for field in ("exit_code", "rules"):
            bad = copy.deepcopy(good)
            if field == "exit_code":
                bad["exit_code"] = 0
            else:
                bad["report"]["findings"] = [{"rule": "REPLAY_CONTENT_CHANGED"}]
            with self.subTest(field=field), self.assertRaises(DemoFailure):
                verify(case, bad)

    def test_demo_rejects_misleading_replay_labels_or_adapters(self):
        case, good = self.minimal("replay")
        verify(case, good)
        for field, value in (("model_execution", True), ("adapter_invocations", 1),
                             ("trace_origin", "claimed_live"), ("origin_authenticated", True)):
            bad = copy.deepcopy(good)
            bad["report"][field] = value
            with self.subTest(field=field), self.assertRaises(DemoFailure):
                verify(case, bad)

    def test_actual_demo_asserts_nine_cases_preserves_trace_and_refuses_reuse(self):
        (ROOT / "work").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "work") as scratch:
            out = Path(scratch) / "demo"
            argv = [sys.executable, "scripts/demo.py", "--out", str(out)]
            result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["passed"])
            self.assertEqual(len(summary["cases"]), 9)
            self.assertEqual([case["exit_code"] for case in summary["cases"]], [0, 0, 1, 1, 0, 1, 0, 1, 1])
            self.assertIs(summary["model_execution"], False)
            self.assertTrue(summary["input_bytes_preserved"])
            self.assertTrue(summary["source_trace_bytes_preserved"])
            replay = next(case for case in summary["cases"] if case["name"] == "replay")
            self.assertEqual(replay["report"]["adapter_invocations"], 0)
            before = (out / "summary.json").read_bytes()
            repeated = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertEqual(repeated.returncode, 1)
            self.assertEqual((out / "summary.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
