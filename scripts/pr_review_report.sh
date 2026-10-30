#!/usr/bin/env bash
# Collect evidence only. Never approve, merge, execute PR code, or alter auth.
set +x
set -u
set -o pipefail
umask 077

if [[ $# -ne 2 ]]; then
    printf 'Usage: bash scripts/pr_review_report.sh OWNER/REPO PR_NUMBER\n' >&2
    exit 2
fi

repo=$1
pr=$2

if [[ ! $repo =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9_.-]+$ ]] ||
   [[ ! $pr =~ ^[1-9][0-9]*$ ]]; then
    printf 'Expected OWNER/REPO and a positive decimal PR number.\n' >&2
    exit 2
fi

for tool in python3 gh mktemp chmod date; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        printf 'Required command unavailable: %s\n' "$tool" >&2
        exit 1
    fi
done

# Use an absolute directory, independent of TMPDIR and the checkout.
if ! report_dir=$(mktemp -d /tmp/pr-review-report.XXXXXXXX); then
    printf 'Cannot create private report directory.\n' >&2
    exit 1
fi

printf 'Report directory: %s\n' "$report_dir"
if ! chmod 700 "$report_dir"; then
    printf 'Cannot restrict report directory permissions.\n' >&2
    exit 1
fi

started_at=$(date -u '+%Y-%m-%dT%H:%M:%SZ') || exit 1

capture() {
    local name=$1
    shift
    local status

    if env -u GH_TOKEN -u GITHUB_TOKEN \
        -u GH_DEBUG -u DEBUG \
        GH_PAGER=cat PAGER=cat GH_PROMPT_DISABLED=1 \
        GH_HOST=github.com GH_COLOR_LABELS= NO_COLOR=1 \
        gh "$@" >"$report_dir/$name.stdout" 2>"$report_dir/$name.stderr"
    then
        status=0
    else
        status=$?
    fi

    printf '%s\n' "$status" >"$report_dir/$name.exit" || return 1
    chmod 600 "$report_dir/$name.stdout" "$report_dir/$name.stderr" \
        "$report_dir/$name.exit" || return 1
}

fields='number,url,state,baseRefOid,headRefOid,headRefName,headRepositoryOwner'
evidence_fields='number,url,state,baseRefOid,headRefOid,headRefName,headRepositoryOwner,commits,files,changedFiles,statusCheckRollup'

capture version --version || exit 1
capture initial pr view "$pr" --repo "$repo" --json "$fields" || exit 1
capture evidence pr view "$pr" --repo "$repo" --json "$evidence_fields" || exit 1
capture diff pr diff "$pr" --repo "$repo" --color never || exit 1
capture final pr view "$pr" --repo "$repo" --json "$fields" || exit 1

python3 - "$report_dir" "$repo" "$pr" "$started_at" <<'PY'
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

directory = Path(sys.argv[1])
repo, pr, started = sys.argv[2:]
errors = []
statuses = {}
payloads = {}

for name in ("version", "initial", "evidence", "diff", "final"):
    try:
        status = int((directory / f"{name}.exit").read_text().strip())
    except (OSError, ValueError) as error:
        errors.append(f"{name}: unreadable exit status ({type(error).__name__})")
        continue
    statuses[name] = status
    if status:
        errors.append(f"{name}: command failed, exit {status}")
    if name in ("initial", "evidence", "final") and status == 0:
        try:
            payload = json.loads((directory / f"{name}.stdout").read_text())
            if not isinstance(payload, dict):
                raise ValueError("expected an object")
            payloads[name] = payload
        except (OSError, ValueError) as error:
            errors.append(f"{name}: invalid metadata ({type(error).__name__})")

expected_url = f"https://github.com/{repo}/pull/{pr}"
for name, payload in payloads.items():
    if payload.get("number") != int(pr) or payload.get("url") != expected_url:
        errors.append(f"{name}: repository/PR identity mismatch")
    for key in ("baseRefOid", "headRefOid", "headRefName", "state"):
        if not isinstance(payload.get(key), str) or not payload[key]:
            errors.append(f"{name}: missing or invalid {key}")
    for key in ("baseRefOid", "headRefOid"):
        value = payload.get(key)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", value):
            errors.append(f"{name}: invalid SHA in {key}")
    owner = payload.get("headRepositoryOwner")
    if not isinstance(owner, dict) or not isinstance(owner.get("login"), str):
        errors.append(f"{name}: missing head owner")

if len(payloads) != 3:
    errors.append("Cannot establish revision consistency: metadata is incomplete.")
else:
    for key in ("baseRefOid", "headRefOid"):
        values = [payloads[name].get(key) for name in ("initial", "evidence", "final")]
        if not all(isinstance(value, str) for value in values):
            errors.append(f"{key}: cannot compare invalid revision metadata.")
        elif len(set(values)) != 1:
            errors.append(f"{key} changed during collection; snapshot invalid.")

evidence = payloads.get("evidence", {})
for key in ("commits", "files", "statusCheckRollup"):
    if not isinstance(evidence.get(key), list):
        errors.append(f"evidence: missing or invalid {key}")

files = evidence.get("files")
count = evidence.get("changedFiles")
if not isinstance(count, int) or not isinstance(files, list) or len(files) != count:
    errors.append("Changed-file listing is incomplete or cannot be verified.")

outcome = (
    "INCOMPLETE OR INVALID — not a valid review snapshot"
    if errors
    else "COLLECTED — revision endpoints consistent; NOT REVIEW APPROVAL"
)
manifest = {
    "schema": "pr-review-report.v1",
    "repository": repo,
    "pr_number": int(pr),
    "started_at": started,
    "finished_at": datetime.now(timezone.utc).isoformat(),
    "outcome": outcome,
    "command_exit_codes": statuses,
    "errors": errors,
    "initial": payloads.get("initial"),
    "final": payloads.get("final"),
}
(directory / "manifest.json").write_text(
    json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
)
lines = [
    "# PR evidence collection",
    "",
    outcome,
    "",
    f"Repository: {repo}",
    f"PR: {pr}",
    f"Started: {started}",
    f"Finished: {manifest['finished_at']}",
    "",
    "## Interpretation",
    "",
    "- Checks are a point-in-time snapshot, not guaranteed final status.",
    "- Matching revision endpoints do not establish an atomic remote snapshot.",
    "- No tests, graders, or PR code were executed by this collector.",
    "- No substantive review, approval, or security finding determination is implied.",
    "- The diff preserves CLI terminal-escape neutralization; it is not a raw patch.",
    "- Raw evidence may contain sensitive or hostile content. Inspect before sharing.",
    "- Large PRs may exceed upstream API limits; do not assume universal completeness.",
    "",
    "## Evidence files",
    "",
    "- initial.stdout / final.stdout: revision and identity metadata",
    "- evidence.stdout: commits, changed files, and check states (JSON)",
    "- diff.stdout: complete diff returned by the CLI",
    "- version.stdout: GitHub CLI version",
    "- Each command has matching .stderr and .exit files.",
    "",
    "## Command exit codes",
    "",
]
lines.extend(f"- {name}: {status}" for name, status in statuses.items())
lines.extend(["", "## Collection errors", ""])
lines.extend(f"- {error}" for error in errors)
if not errors:
    lines.append("None detected by this collector.")
(directory / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
for artifact in directory.iterdir():
    artifact.chmod(0o600)
sys.exit(1 if errors else 0)
PY
result=$?

printf 'Collector exit code: %s\n' "$result"
if [[ $result -ne 0 ]]; then
    printf 'Collection failed or snapshot invalid. Retain evidence; do not treat as approval.\n' >&2
fi
exit "$result"
