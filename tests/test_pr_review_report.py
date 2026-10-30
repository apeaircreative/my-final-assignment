from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pr_review_report.sh"

MOCK_GH = r'''#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
root = Path(os.environ["MOCK_ROOT"])
assert "GH_TOKEN" not in os.environ
assert "GITHUB_TOKEN" not in os.environ
assert "GH_DEBUG" not in os.environ
assert os.environ["GH_PAGER"] == "cat"

with (root / "calls.jsonl").open("a") as stream:
    stream.write(json.dumps(args) + "\n")

if args == ["--version"]:
    print("gh version mock")
    sys.exit(0)

assert args[:2] in (["pr", "view"], ["pr", "diff"])
assert args[2:5] == ["11", "--repo", "apeaircreative/my-final-assignment"]
scenario = os.environ.get("MOCK_SCENARIO", "success")

if args[:2] == ["pr", "diff"]:
    assert args[5:] == ["--color", "never"]
    if scenario == "diff_failure":
        print("simulated retrieval failure", file=sys.stderr)
        sys.exit(23)
    sys.stdout.write("diff --git a/example b/example\n+$(touch NEVER_EXECUTE)\n+END\n")
    sys.exit(0)

assert args[5] == "--json"
counter = root / "view_count"
index = int(counter.read_text()) + 1 if counter.exists() else 1
counter.write_text(str(index))

if (
    (scenario == "initial_failure" and index == 1)
    or (scenario == "evidence_failure" and index == 2)
):
    print("simulated metadata retrieval failure", file=sys.stderr)
    sys.exit(19)
if scenario == "final_failure" and index == 3:
    print("simulated final lookup failure", file=sys.stderr)
    sys.exit(17)
if scenario == "malformed_json" and index == 2:
    print("{not-json")
    sys.exit(0)

payload = {
    "number": 11,
    "url": "https://github.com/apeaircreative/my-final-assignment/pull/11",
    "state": "MERGED",
    "baseRefOid": "a" * 40,
    "headRefOid": "b" * 40,
    "headRefName": 'test/$(touch NEVER_EXECUTE)',
    "headRepositoryOwner": {"login": "aprewards35-coder"},
    "commits": [{"oid": "b" * 40}],
    "files": [{"path": "example"}],
    "changedFiles": 1,
    "statusCheckRollup": [],
}
if scenario in ("head_change", "base_change") and index == 3:
    key = "headRefOid" if scenario == "head_change" else "baseRefOid"
    payload[key] = "c" * 40
if scenario == "invalid_sha":
    payload["headRefOid"] = []
if scenario == "wrong_identity":
    payload["number"] = 12
if scenario == "incomplete_files":
    payload["changedFiles"] = 2
if scenario == "failed_checks":
    payload["statusCheckRollup"] = [
        {"name": "test", "status": "COMPLETED", "conclusion": "FAILURE"}
    ]
if scenario == "pending_checks":
    payload["statusCheckRollup"] = [
        {"name": "test", "status": "IN_PROGRESS", "conclusion": None}
    ]
print(json.dumps(payload))
'''


@pytest.fixture
def collect(tmp_path):
    executable = tmp_path / "gh"
    executable.write_text(MOCK_GH, encoding="utf-8")
    executable.chmod(0o700)
    reports = []

    def run(scenario="success", arguments=None):
        env = os.environ.copy()
        env.update(
            PATH=f"{tmp_path}{os.pathsep}{env['PATH']}",
            MOCK_ROOT=str(tmp_path),
            MOCK_SCENARIO=scenario,
            GH_TOKEN="SYNTHETIC_TOKEN_NOT_A_SECRET",
            GITHUB_TOKEN="SYNTHETIC_TOKEN_NOT_A_SECRET",
            GH_DEBUG="api",
        )
        result = subprocess.run(
            [
                "bash",
                str(SCRIPT),
                *(arguments if arguments is not None else [
                    "apeaircreative/my-final-assignment", "11"
                ]),
            ],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        report = None
        for line in result.stdout.splitlines():
            if line.startswith("Report directory: "):
                report = Path(line.removeprefix("Report directory: "))
                assert report.parent == Path("/tmp")
                reports.append(report)
        return result, report

    yield run
    for report in reports:
        shutil.rmtree(report)


@pytest.mark.parametrize(
    "arguments",
    [[], ["owner/repo"], ["owner/repo", "0"], ["owner/repo", "-1"],
     ["owner/repo", "1;echo"], ["--bad/repo", "11"]],
)
def test_invalid_arguments_do_not_call_gh(collect, tmp_path, arguments):
    result, report = collect(arguments=arguments)
    assert result.returncode == 2
    assert report is None
    assert not (tmp_path / "calls.jsonl").exists()


def test_success_retains_evidence_and_private_permissions(collect, tmp_path):
    result, report = collect()
    assert result.returncode == 0, result.stderr
    assert report is not None
    assert result.stdout.count("Report directory: ") == 1
    manifest = json.loads((report / "manifest.json").read_text())
    assert manifest["errors"] == []
    assert manifest["repository"] == "apeaircreative/my-final-assignment"
    assert manifest["pr_number"] == 11
    assert all(code == 0 for code in manifest["command_exit_codes"].values())
    assert (report / "diff.stdout").read_text() == (
        "diff --git a/example b/example\n+$(touch NEVER_EXECUTE)\n+END\n"
    )
    assert "NOT REVIEW APPROVAL" in (report / "REPORT.md").read_text()
    assert stat.S_IMODE(report.stat().st_mode) == 0o700
    assert not report.is_relative_to(ROOT)
    assert not (tmp_path / "NEVER_EXECUTE").exists()
    for path in report.iterdir():
        assert stat.S_IMODE(path.stat().st_mode) & 0o077 == 0
        assert "SYNTHETIC_TOKEN_NOT_A_SECRET" not in path.read_text()
    calls = [
        json.loads(line)
        for line in (tmp_path / "calls.jsonl").read_text().splitlines()
    ]
    assert len(calls) == 5
    assert calls[0] == ["--version"]


@pytest.mark.parametrize(
    "scenario",
    ["initial_failure", "evidence_failure",
     "head_change", "base_change", "final_failure", "diff_failure",
     "malformed_json", "wrong_identity", "incomplete_files", "invalid_sha"],
)
def test_invalid_collection_still_generates_failure_report(collect, scenario):
    result, report = collect(scenario)
    assert result.returncode != 0
    assert report is not None
    manifest = json.loads((report / "manifest.json").read_text())
    assert manifest["errors"]
    assert "INCOMPLETE OR INVALID" in manifest["outcome"]
    if scenario == "diff_failure":
        assert manifest["command_exit_codes"]["diff"] == 23
        assert "simulated retrieval failure" in (report / "diff.stderr").read_text()
    if scenario == "final_failure":
        assert manifest["command_exit_codes"]["final"] == 17


@pytest.mark.parametrize("scenario", ["failed_checks", "pending_checks"])
def test_check_outcomes_are_not_collection_failures(collect, scenario):
    result, report = collect(scenario)
    assert result.returncode == 0, result.stderr
    evidence = json.loads((report / "evidence.stdout").read_text())
    assert evidence["statusCheckRollup"]
    assert "point-in-time snapshot" in (report / "REPORT.md").read_text()


def test_output_directory_creation_failure_does_not_call_gh(collect, tmp_path):
    executable = tmp_path / "mktemp"
    executable.write_text(
        "#!/bin/sh\nprintf 'simulated creation failure\\n' >&2\nexit 31\n"
    )
    executable.chmod(0o700)

    result, report = collect()

    assert result.returncode != 0
    assert report is None
    assert "Cannot create private report directory" in result.stderr
    assert not (tmp_path / "calls.jsonl").exists()


def test_exit_artifact_write_failure_cannot_succeed(collect, tmp_path):
    executable = tmp_path / "gh"
    source = executable.read_text()
    old = 'if args == ["--version"]:\n'
    new = (
        'if args == ["--version"]:\n'
        '    target = Path(os.readlink("/proc/self/fd/1")).parent\n'
        '    (target / "version.exit").mkdir()\n'
    )
    assert source.count(old) == 1
    executable.write_text(source.replace(old, new, 1))

    result, report = collect()

    assert result.returncode != 0
    assert report is not None
    assert not (report / "manifest.json").exists()
    assert "COLLECTED" not in result.stdout
    assert "version.exit" in result.stderr
