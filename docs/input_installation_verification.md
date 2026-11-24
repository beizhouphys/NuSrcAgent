# Input-bundle installation verification — 2026-10-16

This is a dated reproducibility record, not a sequence of steps for users to
repeat. For installation use [these instructions](input_installation.md); for
analysis use the [worked examples](quickstart.md). A clean clone is a newly
downloaded copy without existing inputs or a Python environment. File hashes
are content fingerprints; matching them shows that the same files were used.
The task/run identifiers below let maintainers locate each saved calculation.
The recorded warnings remain scientific limitations even when reproduction
checks pass.

## GitHub-hosted one-command verification

**Completed:** an actual fresh clone from GitHub main at
`8cd000eae9203a82d80e71912e1afc815cc6e291` ran plain `bash install.sh`.
It initially had no `.venv`, scientific inputs, download cache or local bundles.
Owner PYTHONPATH was unset and user-site imports disabled. The command created
its own Python 3.12.3 environment, installed all 20 hash-locked dependencies,
downloaded all six DR2 bundles from GitHub and finished with
`Installation and input verification complete.` All 52 preflight paths and
archive/member hashes passed. No `--bundle-dir` or `--base-url` was supplied.

The seven assets (including optional DR1) were added to the existing mutable
`v0.2.0-private-alpha.4` Release. Its existing tag was not moved; no new tag or
GitHub Release was created. The private download route uses the installer's own
GitHub login and fixed asset IDs, not maintainer credentials. The separate DR1
bundle also downloaded successfully and all 20 DR1 input hashes passed; this
does not claim an additional DR1 analysis run. All seven downloaded archive
hashes matched the manifest and GitHub asset digests.

Both creation commands were taken directly from `quickstart.md`, reached READY,
and completed in one attempt with unchanged scientific settings:

| Example | Task | Run |
| --- | --- | --- |
| NGC 1068 | `task_20261016T180002901256Z` | `run_20261016T180953290567Z` |
| Three-source scan+stack | `task_20261016T181004706647Z` | `run_20261016T182531691327Z` |

Both returned COMPLETED_WITH_WARNINGS and zero failed run/agent review checks.
Read-only independent reviews exactly reproduced the saved reviews. Reports,
CSV tables, original/normalized configurations, all 31 runtime code hashes,
52/53 single/catalog input-provenance hashes and request hashes passed checks.
All runtime inputs resolved inside the clone. Configuration matched the earlier
references: full14, spatial+energy, fitted n and s, frozen v3, all 1,643,355
events, no extra cuts, unchanged bounds/seeds, and 1/3 intrinsic catalog weights.
Both examples executed zero background trials. For every nonzero compared
single/stack/scan TS, n and s, signed relative difference was 0, then
signed absolute difference 0. Zero TS/ns references had undefined relative
differences and absolute differences 0. spectral index at ns = 0 remains unidentifiable.
Numerical reference values are in the historical table below and `quickstart.md`.

All 51 DR2 bundle input/provenance files and 71 shipped source inventory entries
retained their hashes after analysis. Git status stayed clean. Default input
reinstallation reused the verified bundles. Owner tests passed 222/222 with no
skips (including 15 installer tests); 20 golden cases passed. Ubuntu/Python 3.12
no-data GitHub CI passed for this commit.

The verified platform is macOS 15.3.1 x86_64; Linux CI covers no-data engineering
only, not these fits. Analytic p-value and absent empirical/catalog-global
calibration warnings remain, as do v3 residuals and possible parameter bias.
This closes the private GitHub installation gate, not public-access licensing,
time-dependent support or scientific calibration. Subsequent verification-note
updates do not change the tested installer, dependencies or scientific code.

## Earlier local-bundle verification (historical)

A new temporary source-only directory, with no virtual environment or numerical
inputs, completed the single `install.sh --bundle-dir ...` command. It created
its own Python 3.12 environment, installed hash-locked dependencies, extracted
all default DR2 raw/v3/SEpdf inputs and passed full input hash verification.
PYTHONPATH was unset. The assets came from the project-prepared local bundle
directory, not directly from the official IceCube website.

Default DR2 assets: six archives, 1,522,756,289 bytes downloaded; 51 unique
extracted input/provenance files, 4,051,798,595 bytes. The code checkout supplies
the 52nd required preflight path, the pinned PDF mapping manifest. The optional
DR1 archive is 61,601,326 bytes and installed/verified all 20 supported inputs
in the same new directory. Repeated installation reused verified files.

Nine installer tests cover successful local installation/reuse, a simulated
HTTPS download, corrupt archives/files, altered existing inputs, manifest
tampering, unexpected members, unsafe paths/symlinks and spatial-only selection.
The owner development suite passed 216 tests, with no skips; 20 golden language
cases and development input hashes also passed. Test code is not distributed.

The newly installed environment then ran an NGC 1068 single-source task and a
three-source uniform-weight individual scan plus stack, using full14 DR2,
spatial+energy, fitted n and s and unchanged approved bounds/defaults. Both
reached COMPLETED_WITH_WARNINGS, with no failed review checks; warnings report
analytic p-value approximation and unavailable empirical/catalog-global calibration.
Reports, CSVs, configuration, provenance and reviews were readable.

Against the preceding release-copy observed-fit references, TS, n and s
signed relative differences are 0, followed by signed absolute differences 0,
for both the single-source fit and stack. This confirms these installation
checks preserved the fitted outputs on the tested platform; it does not validate
calibrated significance, coverage or another platform.

The public asset upload/HTTPS URL is still pending. No public download-path test
or publication is claimed; no commit, push, release or tag was created.
See [installation instructions](input_installation.md).

## Local Git clean-clone verification

A second, independent check on 2026-10-16 used an actual local `git clone
--no-hardlinks`, not a copy of an existing installation. Because the preparation
repository has no commit yet, its current 70-file allowlist was exported into
a temporary repository and committed there as snapshot
`fdd7c2d6cdad2743c7ef067ef7874e66dbfda93e`. This is a temporary verification
identity, not the final release commit; the project repositories were not
committed, pushed or tagged. The validation record below was added afterward.

The clone initially had a clean Git status, no `.venv`, no scientific raw data
or numerical PDFs, no owner tests and no bundled asset directory. Following
the README's local-bundle route, `bash install.sh --bundle-dir ...` created an
independent environment and installed all six prepared DR2 bundles. Owner
`PYTHONPATH` was unset and user-site imports disabled. Python 3.12.3 on macOS
15.3.1 x86_64 matched all 20 locked dependency versions; `pip check` passed.
Archive/member hashes and the full preflight passed, including all 52 required
paths. The 51 unique bundle input/provenance files were hashed again after fits,
with no changes. All 69 source/metadata inventory entries also remained unchanged.

The creation commands were extracted directly from the
[quickstart](quickstart.md). Both returned READY and completed in one attempt,
without retries or scientific-setting changes:

| Example | Task | Run |
| --- | --- | --- |
| NGC 1068 | `task_20261016T152335536814Z` | `run_20261016T152441368085Z` |
| Three-source scan+stack | `task_20261016T152336244920Z` | `run_20261016T152911950315Z` |

Both tasks reached **COMPLETED_WITH_WARNINGS**, with zero failed run or agent
review checks. Independent read-only `review-run` calls reproduced the saved
reviews exactly. The single-source warning concerns analytic local p-values;
the catalog also warns that empirical catalog-global calibration is absent.
Neither warning was suppressed, and both executed zero background trials.

| Fit | TS | ns | spectral index (SkyLLH) |
| --- | ---: | ---: | ---: |
| NGC 1068 | 22.991618557054025 | 68.56745260524343 | 3.0590345620224406 |
| Three-source stack | 7.004486283592772 | 18.81365067323916 | 2.2906293703278 |
| Scan: TXS 0506+056 | 8.66565511739514 | 10.936393720336774 | 2.129534273085857 |
| Scan: PKS 1502+106 | 0.25511669236778944 | 5.030084337350434 | 2.514923107052178 |
| Scan: 3C 279 | 0 | 0 | Unidentifiable at ns = 0 |

Against the earlier installation references, all compared nonzero TS/n and s
values have signed relative difference 0, then signed absolute difference 0.
The zero TS/ns references have undefined relative differences and absolute
differences 0. No spectral measurement is assigned to 3C 279 at ns = 0.

Normalized configurations were identical to the controlled references: full14
DR2, time-integrated spatial+energy, fitted n and s, all 1,643,355 events,
no extra cuts, spectral index seed 3 and ns seed 10, unchanged bounds and random seed
12345. The stack used intrinsic weights 1/3 each; source order was preserved.
The original/normalized configuration hashes, request-attempt hashes, all
31 runtime code hashes and 52/53 single/catalog input-provenance hashes were
verified. Provenance recorded the temporary Git snapshot correctly, and every
runtime input path resolved inside the clone. Reports, CSVs and review artifacts
were readable; no DR2 workbook or PDF figures were expected. Git status stayed
clean after installation and both analyses. No runtime/path/output fix was needed.

### Remaining at the time of the local-only check

- Public bundle upload, pinned HTTPS URL and installation through that URL.
- Clean clone from the final published GitHub candidate, rather than this local
  snapshot; repeat installation and the examples for that exact candidate.
- Linux runner verification and other release gates in
  [release preparation](testing_and_release.md), including the additional
  supported paths and time-dependent integration/validation.

This establishes local installation and observed-fit reproducibility only.
The [scientific limitations](scientific_status.md), including v3 residuals,
possible parameter bias and unavailable empirical significance, still apply.
The later GitHub-hosted check above closes the first two historical pending items.
