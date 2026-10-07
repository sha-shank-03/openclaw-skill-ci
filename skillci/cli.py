"""A local module CLI. Replay, installers and JSON5 parsing are deferred."""

import argparse
import json
import sys
from pathlib import Path

from .checks import check_declarations, eligibility
from .harness import run_fixture
from .inputs import digest, load_environment, load_permissions, load_scenario
from .manifest import load_manifest
from .model import Finding, InputError, has_errors
from .report import new_report, new_trace, print_summary, write_reports


def parser():
    root = argparse.ArgumentParser(description="Offline OpenClaw portable-profile checks and synthetic mock fixtures (M1).")
    sub = root.add_subparsers(dest="command", required=True)
    for name in ("check", "run-fixture"):
        command = sub.add_parser(name)
        command.add_argument("skill", type=Path)
        command.add_argument("--environment", type=Path, required=True)
        command.add_argument("--policy", type=Path, required=True, help="Independently selected team policy; not loaded from the skill.")
        command.add_argument("--out", type=Path, required=True)
        if name == "run-fixture":
            command.add_argument("--scenario", type=Path, required=True)
    return root


def execute(args):
    mock = args.command == "run-fixture"
    report = new_report("mock_fixture" if mock else "static")
    trace = new_trace() if mock else None
    findings = []
    exit_code = 1
    try:
        environment, environment_sha = load_environment(args.environment)
        policy, policy_sha = load_permissions(args.policy)
        report["input_hashes"].update(environment=environment_sha, policy=policy_sha)
        manifest, manifest_findings, file_hashes = load_manifest(args.skill)
        findings.extend(manifest_findings)
        report["inspected_files"] = sorted(file_hashes)
        report["input_hashes"].update(file_hashes)
        if not has_errors(findings):
            try:
                declarations, declaration_sha = load_permissions(args.skill / "skill-ci.json")
            except InputError as exc:
                # Candidate contract failures are validation failures, not caller invocation errors.
                finding = exc.finding
                findings.append(Finding("CONTRACT_INVALID", "team_policy", "skill-ci.json", finding.message))
            else:
                report["input_hashes"]["skill-ci.json"] = declaration_sha
                report["inspected_files"].append("skill-ci.json")
                eligible, prerequisite_findings = eligibility(manifest, environment)
                report["simulated_eligibility"] = eligible
                findings.extend(prerequisite_findings)
                findings.extend(check_declarations(declarations, policy))
                if mock and not has_errors(findings):
                    scenario, scenario_sha = load_scenario(args.scenario)
                    report["input_hashes"]["scenario"] = scenario_sha
                    trace["state"] = "running"
                    final, behavior_findings = run_fixture(scenario, declarations, policy, trace)
                    findings.extend(behavior_findings)
                    report["summary"] = final
        # This is a fingerprint of inspected files, not a claim to hash every support file.
        inspected_hashes = {k: report["input_hashes"][k] for k in report["inspected_files"]}
        report["inspected_bundle_sha256"] = digest(json.dumps(inspected_hashes, sort_keys=True).encode("utf-8"))
        exit_code = 1 if has_errors(findings) else 0
    except InputError as exc:
        findings.append(exc.finding)
        exit_code = 2
    if trace is not None:
        if trace["state"] == "not_started":
            trace["state"] = "blocked"
        trace["input_hashes"] = dict(report["input_hashes"])
        report["fixture_state"] = trace["state"]
        report["adapter_invocations"] = trace["adapter_invocations"]
    report["findings"] = [finding.to_dict() for finding in findings]
    report["status"] = "error" if exit_code == 2 else "fail" if exit_code else "pass"
    report["exit_code"] = exit_code
    return report, trace


def main(argv=None):
    args = parser().parse_args(argv)
    report, trace = execute(args)
    try:
        write_reports(args.out, report, trace)
    except OSError:
        print("ERROR REPORT_WRITE: could not save reports to the selected output directory.", file=sys.stderr)
        return 2
    print_summary(report)
    return report["exit_code"]
