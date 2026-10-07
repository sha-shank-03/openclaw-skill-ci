"""M2 adversarial contracts, numeric bounds and replay without adapters."""

import copy
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from skillci.cli import main
from skillci.harness import run_fixture
from skillci.inputs import load_scenario
from skillci.limits import MAX_BUNDLE_BYTES, MAX_JSON_BYTES, MAX_SKILL_BYTES
from skillci.model import InputError
from skillci.parsing import parse_json
from skillci.report import new_trace

ROOT = Path(__file__).resolve().parents[1]
PASSING = ROOT / "examples/passing/log-summary"
ENV = ROOT / "fixtures/environments/ready.json"
POLICY = ROOT / "fixtures/policies/read-only.json"
SCENARIO = ROOT / "fixtures/scenarios/summary-pass.json"


class M2Acceptance(unittest.TestCase):
    def setUp(self):
        (ROOT / "work").mkdir(exist_ok=True)
        self.scratch = tempfile.TemporaryDirectory(dir=ROOT / "work")
        self.addCleanup(self.scratch.cleanup)
        self.base = Path(self.scratch.name)
        self.skill = self.base / "log-summary"
        shutil.copytree(PASSING, self.skill)
        self.counter = 0

    def write(self, name, value):
        path = self.base / name
        path.write_text(json.dumps(value, allow_nan=False), encoding="utf-8")
        return path

    def scenario(self, **changes):
        value = json.loads(SCENARIO.read_text(encoding="utf-8"))
        value.update(changes)
        return self.write("scenario.json", value)

    def manifest(self, header):
        (self.skill / "SKILL.md").write_text("---\nname: log-summary\ndescription: Synthetic test.\n" + header + "\n---\nRead fictional logs.\n", encoding="utf-8")

    def metadata(self, value):
        self.manifest("metadata: " + json.dumps(json.dumps(value)))

    def invoke(self, command="run-fixture", scenario=SCENARIO, policy=POLICY, environment=ENV, trace=None, out=None):
        self.counter += 1
        out = out or self.base / ("out" + str(self.counter))
        args = [command, str(self.skill), "--policy", str(policy), "--out", str(out)]
        if environment is not None:
            args += ["--environment", str(environment)]
        if command != "check" and scenario is not None:
            args += ["--scenario", str(scenario)]
        if trace is not None:
            args += ["--trace", str(trace)]
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(args)
        report_path = out / "report.json"
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else None
        trace_path = out / "trace.json"
        observed = json.loads(trace_path.read_text(encoding="utf-8")) if trace_path.exists() else None
        self.assertNotIn("Traceback", stderr.getvalue())
        return code, report, observed, out, stderr.getvalue()

    def assert_failure(self, result, rule, code=1, calls=0):
        self.assertEqual(result[0], code, result[4])
        self.assertIn(rule, [f["rule"] for f in result[1]["findings"]])
        self.assertEqual(result[1]["adapter_invocations"], calls)
        if calls == 0 and result[2] is not None:
            self.assertTrue(all(event["outcome"] == "denied" for event in result[2]["events"]))

    def record(self, scenario=SCENARIO):
        result = self.invoke(scenario=scenario)
        self.assertEqual(result[0], 0)
        return result[3] / "trace.json", result[2]

    def test_canonical_json5_comments_trailing_commas_and_nested_yaml(self):
        self.manifest("metadata: |\n  { // fictional fixture; braces in comments [[[[\n    openclaw: {os: ['win32',], requires: {anyBins: ['absent', 'python'],},},\n  }")
        result = self.invoke()
        self.assertEqual(result[0], 0)
        self.assertEqual(result[1]["summary"]["error_count"], 2)
        self.manifest("metadata:\n  openclaw:\n    os: [win32]\n    requires:\n      bins: [python]")
        self.assertEqual(self.invoke()[0], 0)

    def test_json5_rejects_duplicate_nonfinite_overflow_and_depth(self):
        for text in ("{openclaw: {}, openclaw: {always:true}}", "{openclaw:{x:NaN}}", "{openclaw:{x:Infinity}}",
                     "{openclaw:{x:-Infinity}}", "{openclaw:{x:1e999}}", "{openclaw:()=>1}",
                     "{x:" + "[" * 33 + "0" + "]" * 33 + "}"):
            with self.subTest(text=text[:80]):
                self.manifest("metadata: " + json.dumps(text))
                self.assert_failure(self.invoke(), "METADATA_JSON5")

    def test_yaml_duplicate_tags_aliases_malformed_and_non_json_values(self):
        cases = [("description: Duplicate", "MANIFEST_DUPLICATE"),
                 ("metadata: !!python/object:os.system {}", "PROFILE_YAML_TAG"),
                 ("metadata: &x {openclaw: {}}", "PROFILE_YAML_ALIAS"),
                 ("metadata: [", "MANIFEST_YAML"), ("metadata: 2026-10-07", "MANIFEST_VALUE"),
                 ("metadata: {openclaw: {always: .nan}}", "MANIFEST_VALUE"),
                 ("metadata: {1: anything}", "MANIFEST_KEY_TYPE"),
                 ("metadata: " + "[" * 33 + "0" + "]" * 33, "MANIFEST_DEPTH")]
        for header, rule in cases:
            with self.subTest(rule=rule):
                self.manifest(header)
                self.assert_failure(self.invoke(), rule)

    def test_unsupported_metadata_and_requirement_types(self):
        cases = [("metadata: {clawdbot: {}}", "PROFILE_UNSUPPORTED_METADATA"),
                 ("metadata: {openclaw: {requires: {network: true}}}", "PROFILE_REQUIREMENT"),
                 ("metadata: {openclaw: {requires: {bins: python}}}", "MANIFEST_TYPE"),
                 ("metadata: {openclaw: {os: [windows]}}", "MANIFEST_TYPE"),
                 ("metadata: {openclaw: {always: 'true'}}", "MANIFEST_TYPE"),
                 ("metadata: '[]'", "PROFILE_METADATA"),
                 ("command-dispatch: shell", "PROFILE_DISPATCH")]
        for header, rule in cases:
            with self.subTest(header=header):
                self.manifest(header)
                self.assert_failure(self.invoke(), rule)
        self.manifest("extra-field: kept\nallowed-tools: read")
        result = self.invoke(command="check")
        self.assertEqual(result[0], 0)
        self.assertEqual({f["rule"] for f in result[1]["findings"]},
                         {"PROFILE_UNCHECKED_FIELD", "PROFILE_ALLOWED_TOOLS_ADVISORY"})
        self.assertTrue(all(f["severity"] == "warning" for f in result[1]["findings"]))

    def test_installer_static_checks_known_kinds_no_installation(self):
        specs = [{"kind": "node", "package": "@fictional/log-cli@1.2.3"},
                 {"kind": "uv", "package": "fictional-log-cli==1.2.3"},
                 {"kind": "go", "module": "example.invalid/log-cli@v1.2.3"},
                 {"kind": "download", "url": "https://example.invalid/log.zip", "sha256": "a" * 64,
                  "targetDir": "tools/log", "extract": True, "stripComponents": 1},
                 {"kind": "brew", "formula": "fictional/log-cli", "os": ["darwin"]}]
        self.metadata({"openclaw": {"install": specs}})
        result = self.invoke(command="check")
        self.assertEqual(result[0], 0)
        self.assertEqual([f["rule"] for f in result[1]["findings"]], ["INSTALL_BREW_VERSION_UNVERIFIED"])
        self.assertEqual(result[1]["adapter_invocations"], 0)

    def test_installer_unsafe_unpinned_unknown_kind_and_types(self):
        cases = [({"kind": "node", "package": "x;echo-secret"}, "INSTALL_UNSAFE_TARGET"),
                 ({"kind": "node", "package": "git+https://example.invalid/x"}, "INSTALL_UNSAFE_TARGET"),
                 ({"kind": "node", "package": "fictional@latest"}, "INSTALL_UNPINNED"),
                 ({"kind": "go", "module": "example.invalid/x@latest"}, "INSTALL_UNPINNED"),
                 ({"kind": "uv", "package": "fictional>=1.0"}, "INSTALL_UNPINNED"),
                 ({"kind": "download", "url": "http://example.invalid/x", "sha256": "a" * 64}, "INSTALL_UNSAFE_URL"),
                 ({"kind": "download", "url": "https://name:secret@example.invalid/x", "sha256": "a" * 64}, "INSTALL_UNSAFE_URL"),
                 ({"kind": "download", "url": "https://example.invalid/x"}, "INSTALL_DIGEST_REQUIRED"),
                 ({"kind": "download", "url": "https://example.invalid/x", "sha256": "a" * 64, "targetDir": "../escape"}, "INSTALL_UNSAFE_PATH"),
                 ({"kind": "node", "package": "fictional@1.2.3", "os": ["windows"]}, "INSTALL_TYPE"),
                 ({"kind": "node", "package": "fictional@1.2.3", "extract": 1}, "INSTALL_TYPE"),
                 ({"kind": "process", "package": "x"}, "INSTALL_KIND"), ({"kind": "node"}, "INSTALL_TARGET")]
        for spec, rule in cases:
            with self.subTest(spec=spec):
                self.metadata({"openclaw": {"install": [spec]}})
                self.assert_failure(self.invoke(), rule)

    def test_prerequisites_and_os_before_always(self):
        self.metadata({"openclaw": {"os": ["linux"], "always": True, "requires": {"bins": ["absent"]}}})
        self.assert_failure(self.invoke(), "DEP_OS_MISMATCH")
        self.metadata({"openclaw": {"os": ["win32"], "always": True, "requires": {"bins": ["absent"]}}})
        self.assertEqual(self.invoke()[0], 0)
        self.metadata({"openclaw": {"requires": {"bins": ["python", "absent"], "anyBins": ["absent"],
                                               "env": ["FICTIONAL_TOKEN"], "config": ["missing.enabled"]}}})
        result = self.invoke()
        self.assertEqual(result[0], 1)
        self.assertEqual({f["rule"] for f in result[1]["findings"]},
                         {"DEP_MISSING_BIN", "DEP_MISSING_ANY_BIN", "DEP_MISSING_ENV", "DEP_MISSING_CONFIG"})
        self.assertEqual(result[1]["adapter_invocations"], 0)

    def test_bundle_snapshots_support_references_and_missing_traversal(self):
        (self.skill / "notes").mkdir()
        support = self.skill / "notes" / "facts.txt"
        support.write_text("Fictional support data.", encoding="utf-8")
        sidecar = json.loads((self.skill / "skill-ci.json").read_text(encoding="utf-8"))
        sidecar["references"] = ["notes/facts.txt"]
        (self.skill / "skill-ci.json").write_text(json.dumps(sidecar), encoding="utf-8")
        result = self.invoke()
        self.assertEqual(result[0], 0)
        self.assertIn("notes/facts.txt", result[1]["inspected_files"])
        self.assertIn("bundle/notes/facts.txt", result[1]["input_hashes"])
        before = result[1]["inspected_bundle_sha256"]
        support.write_text("Changed support.", encoding="utf-8")
        self.assertNotEqual(before, self.invoke()[1]["inspected_bundle_sha256"])
        sidecar["references"] = ["notes/absent.txt"]
        (self.skill / "skill-ci.json").write_text(json.dumps(sidecar), encoding="utf-8")
        self.assert_failure(self.invoke(), "BUNDLE_REFERENCE_MISSING")
        sidecar["references"] = ["../outside"]
        (self.skill / "skill-ci.json").write_text(json.dumps(sidecar), encoding="utf-8")
        self.assert_failure(self.invoke(), "CONTRACT_INVALID")

    def test_bundle_file_and_total_byte_boundaries(self):
        path = self.skill / "SKILL.md"
        raw = path.read_bytes()
        path.write_bytes(raw + b"x" * (MAX_SKILL_BYTES - len(raw)))
        self.assertEqual(self.invoke(command="check")[0], 0)
        path.write_bytes(path.read_bytes() + b"x")
        self.assert_failure(self.invoke(), "BUNDLE_FILE_SIZE")
        path.write_bytes(raw)
        support = self.skill / "asset.bin"
        support.write_bytes(b"x" * MAX_JSON_BYTES)
        self.assertEqual(self.invoke(command="check")[0], 0)
        support.write_bytes(b"x" * (MAX_JSON_BYTES + 1))
        self.assert_failure(self.invoke(), "BUNDLE_FILE_SIZE")
        support.unlink()
        base_size = sum(file.stat().st_size for file in self.skill.iterdir())
        for index in range(7):
            (self.skill / ("block" + str(index))).write_bytes(b"x" * MAX_JSON_BYTES)
        tail = self.skill / "tail"
        tail.write_bytes(b"x" * (MAX_BUNDLE_BYTES - base_size - 7 * MAX_JSON_BYTES))
        self.assertEqual(self.invoke(command="check")[0], 0)
        with tail.open("ab") as stream:
            stream.write(b"x")
        self.assert_failure(self.invoke(), "BUNDLE_TOTAL_SIZE")

    def test_bundle_256_file_and_depth32_boundaries(self):
        for index in range(254):
            (self.skill / ("file" + str(index))).write_bytes(b"")
        self.assertEqual(self.invoke(command="check")[0], 0)
        extra = self.skill / "extra"
        extra.write_bytes(b"")
        self.assert_failure(self.invoke(), "BUNDLE_FILE_LIMIT")
        for file in list(self.skill.iterdir()):
            if file.name not in ("SKILL.md", "skill-ci.json"):
                file.unlink()
        deep = self.skill
        for _ in range(32):
            deep = deep / "d"
            deep.mkdir()
        self.assertEqual(self.invoke(command="check")[0], 0)
        (deep / "d").mkdir()
        self.assert_failure(self.invoke(), "BUNDLE_DEPTH")

    def test_hardlinks_rejected_for_bundle_selected_input_and_output(self):
        os.link(self.skill / "SKILL.md", self.skill / "linked.md")
        self.assert_failure(self.invoke(), "BUNDLE_LINK")
        (self.skill / "linked.md").unlink()
        selected = self.base / "environment.json"
        selected.write_bytes(ENV.read_bytes())
        os.link(selected, self.base / "environment-alias.json")
        self.assert_failure(self.invoke(environment=selected), "INPUT_FILE_TYPE", code=2)
        out = self.base / "linked-out"
        out.mkdir()
        os.link(selected, out / "report.json")
        before = selected.read_bytes()
        result = self.invoke(out=out)
        self.assertEqual(result[0], 2)
        self.assertIn("OUTPUT_CONFLICT", result[4])
        self.assertEqual(selected.read_bytes(), before)

    def test_symlink_or_windows_junction_rejected(self):
        target = self.base / "outside"
        target.mkdir()
        link = self.skill / "linked-dir"
        try:
            os.symlink(target, link, target_is_directory=True)
        except OSError:
            if os.name != "nt":
                raise
            # Trusted test setup only. A junction requires no developer-mode symlink privilege.
            import subprocess
            test_env = dict(os.environ, SKILLCI_TEST_LINK=str(link), SKILLCI_TEST_TARGET=str(target))
            result = subprocess.run(["powershell", "-NoProfile", "-Command",
                                     "New-Item -ItemType Junction -Path $env:SKILLCI_TEST_LINK -Target $env:SKILLCI_TEST_TARGET | Out-Null"],
                                    env=test_env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
        try:
            self.assert_failure(self.invoke(), "BUNDLE_LINK")
            self.assert_failure(self.invoke(environment=link / "missing.json"), "INPUT_FILE_TYPE", code=2)
        finally:
            # Remove only the checked link, not its target; let TemporaryDirectory clean regular files.
            link.rmdir() if os.name == "nt" else link.unlink()

    def test_selected_json_duplicate_nonfinite_depth_and_size(self):
        inputs = [('{' + '"schema_version":1,"schema_version":1}', "INPUT_JSON"),
                  ('{"value":NaN}', "INPUT_JSON"), ('{"value":1e999}', "INPUT_JSON"),
                  ("[" * 33 + "0" + "]" * 33, "INPUT_DEPTH"), (" " * (MAX_JSON_BYTES + 1), "INPUT_TOO_LARGE")]
        for text, rule in inputs:
            with self.subTest(rule=rule):
                path = self.base / "selected.json"
                path.write_text(text, encoding="utf-8")
                self.assert_failure(self.invoke(environment=path), rule, code=2)
        self.assertEqual(parse_json("[" * 32 + "0" + "]" * 32, "boundary"),
                         json.loads("[" * 32 + "0" + "]" * 32))

    def test_action_32_boundary_and_33_preflight_limit(self):
        actions = [{"tool": "read", "path": "logs/events.json"}] * 32
        scenario = self.scenario(actions=actions, expected={"error_count": 64, "records": 128,
                                                          "sources": ["logs/events.json"] * 32})
        result = self.invoke(scenario=scenario)
        self.assertEqual(result[0], 0)
        self.assertEqual(len(result[2]["events"]), 32)
        self.assertEqual(result[1]["adapter_invocations"], 32)
        scenario = self.scenario(actions=actions + actions[:1])
        self.assert_failure(self.invoke(scenario=scenario), "INPUT_ACTION_LIMIT", code=2)

    def test_virtual_depth_file_count_and_traversal_preflight(self):
        scenario = self.scenario(files={"logs/events.json": "[" * 33 + "0" + "]" * 33})
        self.assert_failure(self.invoke(scenario=scenario), "INPUT_DEPTH", code=2)
        scenario = self.scenario(files={"file" + str(i): "[]" for i in range(257)})
        self.assert_failure(self.invoke(scenario=scenario), "INPUT_FILE_LIMIT", code=2)
        for path in ("../outside", "/absolute", "C:/host", "logs//events", "logs\\events"):
            with self.subTest(path=path):
                scenario = self.scenario(actions=[{"tool": "read", "path": path}])
                self.assert_failure(self.invoke(scenario=scenario), "MOCK_PATH_INVALID")

    def test_missing_malformed_duplicate_and_nonfinite_virtual_logs(self):
        self.assert_failure(self.invoke(scenario=self.scenario(files={})), "MOCK_FILE_MISSING", calls=1)
        for content in ("not JSON", '{"level":"error"}', '[{"level":3}]',
                        '[{"level":"info","level":"error"}]', '[{"level":"error","n":1e999}]'):
            with self.subTest(content=content):
                result = self.invoke(scenario=self.scenario(files={"logs/events.json": content}))
                self.assert_failure(result, "MOCK_LOG_INVALID", calls=1)
                self.assertIsNone(result[1]["summary"])
                self.assertEqual(result[2]["events"][0]["outcome"], "tool_error")

    def test_unavailable_adapter_and_runtime_policy_denial(self):
        declaration = {"schema_version": 1, "tools": ["unavailable"], "read_paths": []}
        (self.skill / "skill-ci.json").write_text(json.dumps(declaration), encoding="utf-8")
        policy = self.write("policy.json", declaration)
        scenario = self.scenario(actions=[{"tool": "unavailable", "path": "logs/events.json"}])
        self.assert_failure(self.invoke(scenario=scenario, policy=policy), "MOCK_TOOL_UNAVAILABLE")
        # Exercise defense-in-depth authorization directly; CLI rejects this policy earlier at declaration checking.
        raw, _ = load_scenario(SCENARIO)
        trace = new_trace()
        final, findings = run_fixture(raw, {"tools": {"read"}, "read_paths": {"logs/events.json"}},
                                      {"tools": set(), "read_paths": set()}, trace)
        self.assertIsNone(final)
        self.assertEqual([f.rule for f in findings], ["PERMISSION_DENIED"])
        self.assertEqual(trace["adapter_invocations"], 0)

    def test_unknown_selected_and_candidate_versions(self):
        for key, original in (("environment", ENV), ("policy", POLICY), ("scenario", SCENARIO)):
            value = json.loads(original.read_text(encoding="utf-8"))
            value["schema_version"] = 2
            with self.subTest(key=key):
                self.assert_failure(self.invoke(**{key: self.write(key + ".json", value)}), "INPUT_VERSION", code=2)
        value = json.loads((self.skill / "skill-ci.json").read_text(encoding="utf-8"))
        value["schema_version"] = 2
        (self.skill / "skill-ci.json").write_text(json.dumps(value), encoding="utf-8")
        self.assert_failure(self.invoke(), "CONTRACT_INVALID")

    def test_replay_is_read_only_zero_adapters_with_original_mock_label(self):
        path, trace = self.record()
        before = path.read_bytes()
        with patch("skillci.cli.run_fixture", side_effect=AssertionError("replay invoked adapter workflow")):
            result = self.invoke(command="replay", trace=path, scenario=None, environment=None)
        self.assertEqual(result[0], 0)
        self.assertEqual(result[1]["execution_kind"], "recorded_replay")
        self.assertEqual(result[1]["trace_origin"], "synthetic_mock")
        self.assertIs(result[1]["origin_authenticated"], False)
        self.assertIs(result[1]["model_execution"], False)
        self.assertEqual(result[1]["adapter_invocations"], 0)
        self.assertEqual(result[1]["recorded_adapter_invocations"], 1)
        self.assertEqual(result[1]["summary"], trace["final"])
        self.assertIsNone(result[2])
        self.assertEqual(path.read_bytes(), before)

    def test_replay_changed_policy_expected_actions_content_and_bundle_fail(self):
        path, _ = self.record()
        original = path.read_bytes()
        result = self.invoke(command="replay", trace=path, policy=ROOT / "fixtures/policies/deny-all.json")
        self.assert_failure(result, "PERMISSION_DECLARATION_DENIED")
        changed = json.loads(SCENARIO.read_text(encoding="utf-8"))
        changed["expected"]["error_count"] = 99
        self.assert_failure(self.invoke(command="replay", trace=path, scenario=self.write("wrong-expected.json", changed)), "MOCK_OUTPUT_MISMATCH")
        changed["expected"]["error_count"] = 2
        changed["actions"].append(changed["actions"][0])
        self.assert_failure(self.invoke(command="replay", trace=path, scenario=self.write("wrong-actions.json", changed)), "REPLAY_ACTIONS_CHANGED")
        changed = json.loads(SCENARIO.read_text(encoding="utf-8"))
        changed["files"]["logs/events.json"] = "[]"
        self.assert_failure(self.invoke(command="replay", trace=path, scenario=self.write("wrong-content.json", changed)), "REPLAY_CONTENT_CHANGED")
        (self.skill / "support.txt").write_text("New support bytes.", encoding="utf-8")
        self.assert_failure(self.invoke(command="replay", trace=path), "REPLAY_BUNDLE_CHANGED")
        self.assertEqual(path.read_bytes(), original)

    def test_replay_typed_expectation_boolean_fails_and_numeric_float_passes(self):
        scenario = self.scenario(files={"logs/events.json": "[]"}, expected={"error_count": 0, "records": 0, "sources": ["logs/events.json"]})
        path, _ = self.record(scenario)
        for value, code in ((False, 1), (0.0, 0)):
            changed = json.loads(scenario.read_text(encoding="utf-8"))
            changed["expected"].update(error_count=value, records=value)
            result = self.invoke(command="replay", trace=path, scenario=self.write("expectation.json", changed))
            self.assertEqual(result[0], code)
            self.assertEqual(result[1]["adapter_invocations"], 0)
            if code:
                self.assertIn("MOCK_OUTPUT_MISMATCH", [f["rule"] for f in result[1]["findings"]])

    def test_replay_rejects_missing_coverage_results_sequence_counts_and_origin(self):
        _, original = self.record()
        variants = []
        for key, value in (("events", []), ("observations", []), ("final", None), ("adapter_invocations", 0),
                           ("trace_origin", "claimed_live"), ("model_execution", True), ("state", "failed")):
            changed = copy.deepcopy(original)
            changed[key] = value
            variants.append(changed)
        changed = copy.deepcopy(original)
        changed["events"][0]["sequence"] = 2
        variants.append(changed)
        changed = copy.deepcopy(original)
        changed["events"][0]["outcome"] = "attempted"
        variants.append(changed)
        changed = copy.deepcopy(original)
        changed["events"][0]["path"] = "logs/private.json"
        variants.append(changed)
        changed = copy.deepcopy(original)
        changed["final"]["records"] = 99
        variants.append(changed)
        changed = copy.deepcopy(original)
        changed["observations"][0]["records"] = True
        variants.append(changed)
        changed = copy.deepcopy(original)
        changed["contract"]["actions"].append(changed["contract"]["actions"][0])
        variants.append(changed)
        changed = copy.deepcopy(original)
        changed["input_hashes"].pop("bundle")
        variants.append(changed)
        changed = copy.deepcopy(original)
        changed["input_hashes"]["bundle/SKILL.md"] = "0" * 64
        variants.append(changed)
        changed = copy.deepcopy(original)
        changed["events"][0] = {"sequence": 1, "tool": "read", "path": "logs/events.json", "outcome": "denied", "rule": []}
        variants.append(changed)
        for index, changed in enumerate(variants):
            with self.subTest(index=index):
                self.assert_failure(self.invoke(command="replay", trace=self.write("tampered.json", changed)), "TRACE_INCONSISTENT", code=2)

    def test_replay_terminal_failure_incomplete_blocked_and_wrong_expected(self):
        failed = self.invoke(scenario=ROOT / "fixtures/scenarios/undeclared-read.json")
        self.assertEqual(failed[0], 1)
        path = failed[3] / "trace.json"
        self.assert_failure(self.invoke(command="replay", trace=path, scenario=None), "REPLAY_RECORDED_FAILURE")
        changed = copy.deepcopy(failed[2])
        changed["events"].append(copy.deepcopy(changed["events"][0]))
        changed["events"][1]["sequence"] = 2
        changed["contract"]["actions"].append(changed["contract"]["actions"][0])
        self.assert_failure(self.invoke(command="replay", trace=self.write("continued-after-denial.json", changed)), "TRACE_INCONSISTENT", code=2)
        blocked = self.invoke(scenario=SCENARIO, environment=self.base / "absent.json")
        self.assert_failure(self.invoke(command="replay", trace=blocked[3] / "trace.json", environment=None, scenario=None), "REPLAY_INCOMPLETE")
        scenario = self.scenario(expected={"error_count": 99, "records": 4, "sources": ["logs/events.json"]})
        failed = self.invoke(scenario=scenario)
        self.assert_failure(self.invoke(command="replay", trace=failed[3] / "trace.json", scenario=None), "REPLAY_RECORDED_FAILURE")

    def test_trace_256_event_bound_unknown_version_nonfinite_depth_and_size(self):
        _, original = self.record()
        changed = copy.deepcopy(original)
        changed["events"] *= 257
        self.assert_failure(self.invoke(command="replay", trace=self.write("long-trace.json", changed)), "INPUT_TRACE_LIMIT", code=2)
        excessive_observations = copy.deepcopy(original)
        excessive_observations["observations"] *= 257
        self.assert_failure(self.invoke(command="replay", trace=self.write("long-observations.json", excessive_observations)), "INPUT_TRACE_LIMIT", code=2)
        changed["events"] = original["events"] * 256
        # 256 is within the byte/event limit, but exceeds 1-action recorded coverage; no events invented.
        self.assert_failure(self.invoke(command="replay", trace=self.write("boundary-trace.json", changed)), "TRACE_INCONSISTENT", code=2)
        changed = copy.deepcopy(original)
        changed["schema_version"] = 2
        self.assert_failure(self.invoke(command="replay", trace=self.write("unknown-trace.json", changed)), "INPUT_VERSION", code=2)
        for text, rule in ((json.dumps(original).replace('"records": 4', '"records": 1e999'), "INPUT_JSON"),
                           ("[" * 33 + "0" + "]" * 33, "INPUT_DEPTH"),
                           (" " * (MAX_JSON_BYTES + 1), "INPUT_TOO_LARGE")):
            path = self.base / "bad-trace.json"
            path.write_text(text, encoding="utf-8")
            self.assert_failure(self.invoke(command="replay", trace=path), rule, code=2)

    def test_output_alias_and_candidate_output_rejected_without_writing_inputs(self):
        path, _ = self.record()
        alias = self.base / "alias-out"
        alias.mkdir()
        selected = alias / "report.json"
        selected.write_bytes(path.read_bytes())
        before = selected.read_bytes()
        result = self.invoke(command="replay", trace=selected, out=alias)
        self.assertEqual(result[0], 2)
        self.assertIn("OUTPUT_CONFLICT", result[4])
        self.assertEqual(selected.read_bytes(), before)
        result = self.invoke(out=self.skill / "reports")
        self.assertEqual(result[0], 2)
        self.assertFalse((self.skill / "reports").exists())


if __name__ == "__main__":
    unittest.main()
