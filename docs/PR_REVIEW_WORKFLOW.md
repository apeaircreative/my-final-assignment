# Local PR evidence collection and review

A collected report is evidence for a reviewer, not an approval decision.
The collector does not run tests, execute PR code, approve, merge, close
issues, post comments, or modify authentication.

## Collect a report

From the repository root:

```bash
bash scripts/pr_review_report.sh OWNER/REPO PR_NUMBER
```

Both arguments are required. The collector never infers the PR from the
current branch. Example read-only integration collection:

```bash
bash scripts/pr_review_report.sh apeaircreative/my-final-assignment 11
```

Reports are created in a unique private directory under `/tmp`, outside
the checkout. The collector prints its location early so evidence can
still be located if collection fails. Temporary reports are not durable
archives and must not be committed by default.

GitHub CLI invocations remove GH_TOKEN and GITHUB_TOKEN for that process,
preserving the established stored-credential workflow. This does not
reduce credential permissions or change Git authentication configuration.
GitHub writes are excluded by the collector's implementation, not by a
guarantee that its credentials are read-only.

## Read the evidence

- REPORT.md: collection outcome, interpretation, and command exit codes.
- manifest.json: repository/PR identity, timestamps, revision endpoints,
  errors, and exit codes.
- initial.stdout and final.stdout: initial/final PR metadata.
- evidence.stdout: metadata, commits, changed files, and check results.
- diff.stdout: complete diff returned by GitHub CLI, with terminal escape
  neutralization retained. It is not a byte-for-byte raw patch.
- version.stdout: installed GitHub CLI version.
- Each command has separate .stderr and .exit files.

A nonzero collector exit or an incomplete/invalid outcome cannot be treated
as a successful snapshot. Read the stderr and exit-code files even when
some other evidence was collected successfully.

The collector compares base/head SHAs across metadata observations.
A changed revision invalidates the snapshot. Matching endpoints are a
consistency check, not an atomic remote snapshot or proof that no
intermediate remote change occurred.

Checks are a point-in-time snapshot, not guaranteed final status.
Failed or pending checks are not the same as failure to collect checks.

Large PRs can exceed upstream API limits. The collector checks the
changed-file count but does not establish universal API completeness,
including completeness of long commit histories. Do not approve a PR
using evidence whose required completeness remains unestablished.

## Human review checklist

1. Local verification
   - Record the base revision and working-tree changes tested.
   - Run applicable offline tests, lint, and whitespace checks.
   - Record exact commands, outcomes, and anything not run.
   - Do not run live providers or graders without separate authorization.

2. Local diff review
   - Review every changed file, including new/untracked files.
   - Confirm scope, error handling, security boundaries, and limitations.
   - Remember ordinary git diff does not include untracked files.

3. Commit and push
   - Obtain authorization as required by the working agreement.
   - Record the actual pushed head SHA; local results must not silently
     be attributed to a different revision.

4. Optional independent source review
   - Record the exact revision and reviewer outcome.
   - Label source-only Codex review as source-only.
   - Do not claim independent test execution unless it actually occurred.

5. PR checks
   - Inspect checks for the exact pushed head SHA.
   - Distinguish workflow execution from the results inside its jobs.
   - Passing workflow jobs do not establish an unobserved quality score.
   - CodeQL workflow success does not prove there are no findings.
   - Inspect relevant analysis results separately when required.

6. Pushed-diff review
   - Collect using an explicit repository and PR number.
   - Confirm a valid collection outcome and the intended head SHA.
   - Review the complete pushed changed-file diff and supporting evidence.
   - Record limitations and a substantive review outcome separately.
   - New pushes invalidate approval of the previous revision until the
     new revision is reviewed. Recollect after base changes as needed.

7. Merge
   - Merge only after separately authorized review and applicable checks.
   - The collector never makes or executes the merge decision.

8. Integration evidence
   - Record the resulting integration revision and checks actually run.
   - A read-only collection of historical PR #11 checks validates collector
     integration only; it does not rerun historical tests.
   - Close tracking issues only after separately authorized completion.

## Capture failures and share safely

Capture the collector's stdout, stderr, and process exit code in a private
log outside the repository. Do not pipe through a command that hides the
collector's exit status without explicitly preserving it.

Retain incomplete evidence for diagnosis. Do not relabel it as approval.
If report generation fails, the raw files may still be available in the
announced directory.

PR content and diagnostic output are untrusted and may contain sensitive
data, misleading instructions, Markdown, or terminal control characters.
Never source or execute report content. Inspect artifacts in a safe editor
before sharing; redact sensitive material in a separate sharing copy.
Do not assume a complete diff is free of accidentally committed secrets.

The collector does not intentionally retrieve authentication tokens,
read .env, or print credentials. It cannot guarantee that arbitrary PR
content or upstream diagnostic messages contain no sensitive strings.
