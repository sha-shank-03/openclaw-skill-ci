"""Local portable-profile checks, closed mock fixtures and recorded replay."""

import argparse
import os
import stat
import sys
from pathlib import Path

from .bundle import inspect_bundle
from .checks import check_declarations, eligibility
from .harness import run_fixture
from .inputs import ensure_unlinked_path, load_environment, load_permissions, load_scenario
from .manifest import load_manifest
from .model import Finding, InputError, has_errors
from .replay import evaluate_replay, load_trace
from .report import new_report, new_trace, print_summary, write_reports


def parser():
    root = argparse.ArgumentParser(description="Offline OpenClaw portable-profile checks, synthetic mocks and recorded replay (M2).")
    sub = root.add_subparsers(dest="command", required=True)
    for name in ("check", "run-fixture", "replay"):
        command = sub.add_parser(name)
        command.add_argument("skill", type=Path)
        command.add_argument("--environment", type=Path, required=name != "replay")
        command.add_argument("--policy", type=Path, required=True, help="Independently selected team policy; not loaded from the skill.")
        command.add_argument("--out", type=Path, required=True)
        if name != "check":
            command.add_argument("--scenario", type=Path, required=name == "run-fixture")
        if name == "replay":
            command.add_argument("--trace", type=Path, required=True)
    return root


def guard_outputs(args):
    """Never overwrite candidate/selected input bytes, including a replay trace."""
    out = Path(os.path.abspath(args.out))
    skill = Path(os.path.abspath(args.skill))
    try:
        ensure_unlinked_path(out, allow_missing=True)
        if out == skill or skill in out.parents:
            raise InputError("OUTPUT_CONFLICT", "out", "Reports must be outside the candidate bundle.")
        if out.exists() and not out.is_dir():
            raise InputError("OUTPUT_CONFLICT", "out", "Output must be a directory.")
        names = ("report.json", "report.md", "trace.json") if args.command == "run-fixture" else ("report.json", "report.md")
        selected = [Path(os.path.abspath(getattr(args, key))) for key in ("environment", "policy", "scenario", "trace")
                    if getattr(args, key, None) is not None]
        for name in names:
            target = out / name
            ensure_unlinked_path(target, allow_missing=True)
            if target in selected:
                raise InputError("OUTPUT_CONFLICT", "out", "Report target aliases a selected input.")
            if target.exists():
                info = target.lstat()
                if not stat.S_ISREG(info.st_mode) or info.st_nlink > 1:
                    raise InputError("OUTPUT_CONFLICT", "out", "Existing report targets must be regular single-link files.")
    except (OSError, ValueError):
        raise InputError("OUTPUT_CONFLICT", "out", "Could not validate the selected output path.") from None


def execute(args):
    mock = args.command == "run-fixture"
    replay = args.command == "replay"
    report = new_report("recorded_replay" if replay else "mock_fixture" if mock else "static")
    trace = new_trace() if mock else None
    findings = []
    exit_code = 1
    try:
        environment = None
        if args.environment is not None:
            environment, environment_sha = load_environment(args.environment)
            report["input_hashes"]["environment"] = environment_sha
        policy, policy_sha = load_permissions(args.policy)
        report["input_hashes"]["policy"] = policy_sha
        recorded = None
        if replay:
            recorded, trace_sha = load_trace(args.trace)
            report["input_hashes"]["trace"] = trace_sha
            report["trace_origin"] = recorded["trace_origin"]
            report["recorded_state"] = recorded["state"]
            report["recorded_adapter_invocations"] = recorded["adapter_invocations"]
        files, hashes, fingerprint, bundle_findings = inspect_bundle(args.skill)
        findings.extend(bundle_findings)
        report["inspected_files"] = sorted(hashes)
        report["input_hashes"].update({"bundle/" + key: value for key, value in hashes.items()})
        report["input_hashes"]["bundle"] = fingerprint
        report["inspected_bundle_sha256"] = fingerprint
        if not has_errors(findings):
            if "SKILL.md" not in files:
                findings.append(Finding("SKILL_READ", "native_syntax", "SKILL.md", "Candidate has no canonical SKILL.md file."))
            else:
                manifest, manifest_findings, _ = load_manifest(args.skill, raw=files["SKILL.md"])
                findings.extend(manifest_findings)
                if not has_errors(findings):
                    try:
                        if "skill-ci.json" not in files:
                            raise InputError("INPUT_READ", "skill-ci.json", "Candidate has no fixture declaration sidecar.")
                        declarations, _ = load_permissions(args.skill / "skill-ci.json", raw=files["skill-ci.json"], allow_references=True)
                    except InputError as exc:
                        findings.append(Finding("CONTRACT_INVALID", "team_policy", "skill-ci.json", exc.finding.message))
                    else:
                        for reference in sorted(declarations["references"]):
                            if reference not in files:
                                findings.append(Finding("BUNDLE_REFERENCE_MISSING", "portable_profile", reference,
                                                        "Declared support reference is absent from the bundle snapshot."))
                        if environment is not None:
                            eligible, prerequisite_findings = eligibility(manifest, environment)
                            report["simulated_eligibility"] = eligible
                            findings.extend(prerequisite_findings)
                        findings.extend(check_declarations(declarations, policy))
                        if (mock or replay) and not has_errors(findings):
                            scenario = None
                            if args.scenario is not None:
                                scenario, scenario_sha = load_scenario(args.scenario)
                                report["input_hashes"]["scenario"] = scenario_sha
                            if mock:
                                trace["state"] = "running"
                                final, behavior_findings = run_fixture(scenario, declarations, policy, trace)
                            else:
                                final, behavior_findings = evaluate_replay(recorded, declarations, policy, fingerprint, scenario)
                                report["fixture_state"] = "replay_failed" if has_errors(behavior_findings) else "replayed"
                            findings.extend(behavior_findings)
                            report["summary"] = final
        exit_code = 1 if has_errors(findings) else 0
    except InputError as exc:
        findings.append(exc.finding)
        exit_code = 2
    if trace is not None:
        if trace["state"] == "not_started":
            trace["state"] = "blocked"
        trace["input_hashes"] = dict(report["input_hashes"])
        report["trace_origin"] = trace["trace_origin"]
        report["fixture_state"] = trace["state"]
        report["adapter_invocations"] = trace["adapter_invocations"]
    elif replay and report["fixture_state"] == "not_started":
        report["fixture_state"] = "blocked"
    report["findings"] = [finding.to_dict() for finding in findings]
    report["status"] = "error" if exit_code == 2 else "fail" if exit_code else "pass"
    report["exit_code"] = exit_code
    return report, trace


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        guard_outputs(args)
    except InputError as exc:
        print(f"ERROR {exc.finding.rule}: {exc.finding.message}", file=sys.stderr)
        return 2
    report, trace = execute(args)
    try:
        write_reports(args.out, report, trace)
    except OSError:
        print("ERROR REPORT_WRITE: could not save reports to the selected output directory.", file=sys.stderr)
        return 2
    print_summary(report)
    return report["exit_code"]
