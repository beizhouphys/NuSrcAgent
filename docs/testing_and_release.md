# Release preparation status

This directory is a separately prepared source copy with neutral names and an
explicit file allowlist. It contains no owner tests, transcripts, private catalogs,
PDF construction tools, source-specific comparisons or historical research code.

## Automatic CI: no scientific data

The [public workflow](../.github/workflows/agent-tests.yml) uses Ubuntu 24.04,
Python 3.12 and the same `requirements_skyllh_v26_lock.txt` as installation.
It installs with `--require-hashes`, caches against that lock, runs `pip check`
and checks every locked package version. Repository permissions are read-only.

| CI check | What it establishes |
| --- | --- |
| Python compilation and module imports | Public runtime imports without owner tests, raw data, PDF tables or neighboring-project helpers |
| CLI help and shell-bootstrap syntax | Public commands are loadable; the installer is syntactically valid |
| Three-row example catalog inspection | Column/coordinate parsing works without running a likelihood |
| Pinned bundle/PDF mapping metadata and source inventory hashes | Shipped metadata and small source files have their recorded identities |

CI never runs `install.sh` without `--help`, downloads scientific input bundles,
executes a fit/trial, or calls the full data preflight/hash verifier. In particular,
checking a PDF manifest is not checking the absent numerical PDF files. Owner
tests are not distributed and are not discovered by CI. There is no fallback to
old private-alpha dependencies, no `continue-on-error`, and no data-dependent
test reported as passed because it was skipped. A green CI means only that the
listed engineering checks passed, not that a release is scientifically validated.
When changing shipped source/documents, regenerate `release_file_manifest.json`
from the intended release files (excluding the inventory itself).

## Required manual release checks: real inputs

These are separate release gates, not optional tests silently skipped in CI:

1. Start from a clean clone of the exact candidate commit with no existing
   environment or inputs and no owner `PYTHONPATH`. Run `bash install.sh` using
   the published project-provided raw/v3/SEpdf bundles. Require archive and
   extracted-file SHA-256 verification and the full selected-data preflight.
   Until a pinned public URL exists, mark this public-download check **pending**;
   local `--bundle-dir` verification is not its substitute.
2. For default full14 DR2, run the full verifier explicitly:

   ```bash
   .venv/bin/python verify_private_alpha_setup.py --hashes
   ```

   Then run both [quickstart examples](quickstart.md) through the public wrapper:
   NGC 1068 single source and the three-source uniform scan+stack. Require each
   task to reach `READY` before execution; inspect completion and scientific
   reviews, not just command exit codes. No failed review check is acceptable.
   `COMPLETED_WITH_WARNINGS` must be recorded as such, not as a warning-free pass.
3. Inspect the reports, normalized/original configurations, provenance, CSV
   tables, per-source review checks and central agent reviews listed in the
   quickstart. Confirm input hashes, source order, intrinsic weights, Gamma
   mode, event selection, optimizer settings and actual executed-trial counts.
   Compare TS/ns/Gamma to the controlled numerical references, recording signed
   relative differences first and then signed absolute differences (relative
   difference is undefined at a zero reference). Review discrepancies; do not
   change scientific settings merely to obtain a match.
4. Before declaring the additional documented paths release-checked, install
   their matching inputs and execute real DR2 spatial-only and DR1 single-source
   and catalog scan+stack checks. Use fixed acceptance Gamma for spatial-only;
   DR1 must retain its own inputs, definitions and expected CSV/PDF artifacts.
   Record optional workbook availability/warnings separately. Installing DR1
   inputs alone does not validate DR1 analysis or workbook portability.
5. Record the exact candidate commit, platform/Python/package versions, input
   manifest and hashes, commands, task/run IDs, outputs, numerical comparisons,
   review findings and remaining warnings. An engineering reproduction does
   not establish calibrated significance, unbiased parameters or coverage;
   retain the [scientific limitations](scientific_status.md).

## Evidence and remaining gates

On 2026-10-16 the workflow's seven shell steps passed locally on macOS in a
new source-only directory with its own Python 3.12 environment, empty owner
`PYTHONPATH` and no IceCube raw data or numerical PDFs. This checked all 20
locked dependency versions, imported 32 runtime modules and verified 69 shipped
source/metadata files. The GitHub Ubuntu job itself has not been run: no push
or workflow dispatch was performed. Local command checks do not establish
Linux runner compatibility or data-dependent scientific validation.

Completed locally: source-only installation with our prepared bundles, full
DR2 input hash verification, optional DR1 input verification, and a real DR2
single-source task plus three-source scan+stack. Both analysis tasks completed
with warnings and no failed review checks. See the
[dated installation record](input_installation_verification.md) and the
[reproducible example instructions](quickstart.md). This is local-bundle
evidence, not a successful public-URL clean-clone test or scientific calibration.

Step 5 additionally completed an actual local Git clone of an isolated
70-file preparation snapshot, installed through the README's local-bundle
command, and reran both quickstart examples. All nonzero numerical comparisons
had signed relative difference 0, followed by signed absolute difference 0;
configuration/provenance/input hashes and independent reviews passed. Both
tasks retained COMPLETED_WITH_WARNINGS, with no failed review checks, and the
clone remained clean. See the [local Git clean-clone record](input_installation_verification.md#local-git-clean-clone-verification).
This did not create a commit in the project repositories or change runtime code.

Pending before a complete public release:

The [metadata draft and ordered checklist](release_metadata_draft.md) separates
collaborator code synchronization from completing the approved first release.
[Draft release notes](release_notes.md) describe implemented behavior only;
license, authorship and public version remain unapproved.

- Upload the prepared raw-data/PDF assets and pin their HTTPS download location.
- Clone from the final published GitHub candidate and install using its pinned
  public HTTPS bundles, followed by both real examples and artifact reviews.
  The local-snapshot/local-bundle check above does not close this public-path gate.
- Keep optional workbook limitations explicit; workbook portability is not
  required for the numerical/CSV/PDF analysis paths.
- Time-dependent integration and validation, including collaborator stacking code,
  are deferred by the owner until their integration is ready. They remain part
  of the full first-release target, but do not block the current source-code sync.
- License, author/contributor list, CITATION metadata and final version approval.
- Explicit choice of public Git history; this directory does not copy private history.

No push, tag, license grant or public publication is performed by preparing this copy.
