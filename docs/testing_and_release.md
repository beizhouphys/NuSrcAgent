# Release preparation status

For users, the main distinction is between checking that a calculation can be
installed/reproduced and checking that its physical and statistical assumptions
are adequate. This page records those checks for maintainers and collaborators;
it is not extra work you must do before running the
[examples](quickstart.md). The installation/check record is in
[installation verification](input_installation_verification.md).

This directory is a separately prepared source copy with neutral names and an
explicit file allowlist. It contains no owner tests, transcripts, private catalogs,
PDF construction tools, source-specific comparisons or historical research code.

## Automatic CI: no scientific data

CI (continuous integration) is the automatic set of checks run by GitHub when
code or documentation is updated. A green GitHub check means the listed software
checks passed, not that the likelihood or a detection significance was validated.

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

These are checks required before claiming a tested release, separate from the
automatic checks above. A clean clone means a newly downloaded copy with no
pre-existing Python environment or scientific inputs. A commit identifies the
exact recorded code revision being tested.

1. Start from a clean clone of the exact candidate commit with no existing
   environment or inputs and no owner `PYTHONPATH`. Run `bash install.sh` using
   the published project-provided raw/v3/SEpdf bundles. Require archive and
   extracted-file SHA-256 verification and the full selected-data preflight.
   For this private repository use authenticated GitHub asset downloads;
   local `--bundle-dir` verification is not their substitute.
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
source/metadata files. Initially this was local-only evidence. Subsequently the
GitHub Ubuntu/Python 3.12 job passed for hosted-installer commit
`8cd000eae9203a82d80e71912e1afc815cc6e291`
([run 38943454604](https://github.com/beizhouphys/NuSrcAgent/actions/runs/38943454604)).
This Linux no-data CI does not establish data-dependent scientific validation.

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

The authenticated GitHub clean-clone check subsequently passed: plain
`bash install.sh` downloaded and hash-verified the six DR2 bundles, then both
real examples reproduced the references with no failed reviews. The optional
DR1 bundle also downloaded and passed all 20 input hashes. All seven downloaded
archives matched the pinned hashes. Owner unit tests passed 222 checks with no
skips; the golden language cases passed 20/20. See the
[GitHub-hosted verification record](input_installation_verification.md#github-hosted-one-command-verification).

Remaining before a complete public release (not blockers for private collaborator installation):

The [metadata draft and ordered checklist](release_metadata_draft.md) separates
collaborator code synchronization from completing the approved first release.
[Snapshot notes](release_notes.md) describe implemented behavior only.
The owner approved code version 0.2.0 and author Bei Zhou; license and final
citation/publication metadata remain pending. No tag or GitHub Release is implied.

- The seven raw-data/PDF assets are now hosted on the existing GitHub Release,
  with a fixed HTTPS location, pinned asset IDs and verified GitHub SHA-256 values.
  The authenticated GitHub clean-clone check is recorded above and in the
  installation verification page.
- Keep optional workbook limitations explicit; workbook portability is not
  required for the numerical/CSV/PDF analysis paths.
- Time-dependent integration and validation, including collaborator stacking code,
  are deferred by the owner until their integration is ready. They remain part
  of the full first-release target, but do not block the current source-code sync.
- License and final CITATION/publication metadata; current author and code version
  are already approved.
- Explicit choice of public Git history; this directory does not copy private history.

No push, tag, license grant or public publication is performed by preparing this copy.

## Catalog reporting verification — 2026-10-19

The owner development checkout passed 244 unit tests, 21 focused catalog
reporting/review checks, 20 golden language cases and input hash verification.
New tests cover the paper's analytic correction, extreme probability tails,
TS=0, complete source counts, stable top-five order, compact separate columns,
histogram bin counts, missing/altered artifacts and failed-review suppression.
Tests remain excluded from the distributed repository.

Real public-wrapper single-source and two-source scan-plus-stacking tasks
completed with passing review in both the development and release copies.
For TS, ns and Gamma, release-versus-development signed relative differences
are 0 and signed absolute differences are 0, including both individual source
fits. Tables, figures, configurations, provenance and reviews were checked.
The new histogram PDF was rendered and visually inspected. No background
trials were executed. The isolated publication checkout imported all 22 public
agent modules and passed CLI startup without owner runtime imports.
These are implementation/output checks, not empirical significance or coverage
validation. Existing warning-bearing results retain their original cautions.

## Source-scan fit procedure safeguard — 2026-10-19

The owner checkout passed the 266-test unit suite, 20 golden cases and input
hash verification. Eight focused policy checks passed in each development,
release, isolated publication and test checkout, including final review
handling of missing fit records. The private tests are not distributed.

Six real public-wrapper tasks completed with passing review: a fixed-Gamma
single source (Gamma=2.5, upper-limit fits omitted) and a fitted-Gamma two-source
scan plus uniform stack in each development, release and test checkout.
Every individual scan fit records `skyllh_lbfgs_v1`, with no additional Gamma
maximum search. Source fits, tables, normalized settings, provenance, review
checks and histogram hashes were verified; the histogram PDF was rendered
and visually inspected. All TS, ns and Gamma comparisons against the
development tasks have signed relative differences 0 and signed absolute
differences 0. Zero background trials were executed. The stopped 501-source
task remains stopped. These checks establish execution/procedure consistency,
not statistical calibration or parameter coverage.
