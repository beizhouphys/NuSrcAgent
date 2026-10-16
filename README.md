# NuSrcAgent

NuSrcAgent coordinates natural-language requests, parameter confirmation,
deterministic high-energy neutrino likelihood analysis, provenance and scientific
review using IceCube public point-source data.

This is the 0.2.0 time-integrated development snapshot, not a tagged public
release. Project-provided inputs are hosted on GitHub and installed automatically.
The complete first-release scope is not yet implemented or validated.

Verified on 2026-10-16: a fresh GitHub clone completed plain `bash install.sh`
and both real DR2 examples. See the [verification record](docs/input_installation_verification.md#github-hosted-one-command-verification).

## Current support

| Data / mode | Implemented analysis | Status |
| --- | --- | --- |
| DR2 full14, time-integrated spatial+energy | Single source, individual catalog scan, stacking | Default; fits ns and Gamma |
| DR2 full14, time-integrated spatial-only | Single source, individual catalog scan, stacking | Fixed acceptance Gamma; no energy term |
| DR1 10-year, time-integrated spatial-only | Existing single-source and catalog scan+stack paths | Separate inputs and definitions |
| DR2 time-dependent | Planned single source, catalog scan and stacking | Not implemented in this copy; integration and validation pending |

The approved first-release scope includes time-dependent analysis, with
collaborator stacking code still pending. The current time-integrated paths do
not by themselves complete that scope.

## Installation

Prerequisites: Python 3.12 on macOS/Linux and read access to this private GitHub
repository. The installer reuses your existing `gh auth login`, Git HTTPS
credentials, or `GH_TOKEN`/`GITHUB_TOKEN`. An SSH-only clone does not supply HTTPS
download credentials; in that case log in with `gh auth login` once.
From the checkout root:

```bash
bash install.sh
```

The installer creates `.venv`, installs hash-locked dependencies and fetches our
matching raw IceCube and frozen v3/SEpdf bundles. It extracts files to the required
paths and verifies archive and per-file SHA-256 values. No manual IceCube download
or PDF precalculation is needed. Re-running keeps already verified inputs.

The default DR2 download is about 1.52 GB and extracts about 3.8 GiB, in addition
to the environment and retained download/staging cache. Python itself is not
installed by the script. See [installation options and recovery](docs/input_installation.md)
and [data attribution](docs/data_attribution.md).

## Natural-language use

After installation, open this checkout in Codex and invoke its repository skill,
`$he-neutrino-analysis`, for example:

```text
$he-neutrino-analysis Analyze NGC 1068 at RA 40.6696 deg, Dec -0.0133 deg
with full14 DR2, time-integrated spatial+energy. Fit ns and Gamma.
```

The skill records parameter interpretations, creates a persistent task, checks
the READY gate, executes the likelihood and reads the resulting reviews.
Unresolved choices affecting the analysis are clarified before execution.

The skill interprets natural language; the CLI does not parse the `--request`
text into parameters. CLI users must supply the intended flags themselves.

## Minimal examples and outputs

Follow the [quickstart](docs/quickstart.md) for two complete CLI examples:

1. NGC 1068 single-source fit.
2. Three-source individual scan plus uniform-weight stack using the bundled CSV.

Both start from task creation, require `READY` before execution, and show where
to find reports, CSV tables, configuration, provenance and scientific reviews.
The guide includes observed numerical references from the local clean-install
checks. DR2 currently produces numerical reports/tables, not PDF figures or an
Excel workbook.

## Scientific limitations

- Ordinary fits execute no background trials. Their analytic local p-values are
  approximations, not empirical or catalog-global significance.
- Frozen background v3 retains IC79 Dec–energy residuals; ns, Gamma and inferred
  flux may be biased. Hash verification establishes input identity, not scientific validity.
- Warning-bearing results are preliminary; failed reviews are not valid results.
  At ns = 0, Gamma is unidentifiable. Spatial-only Gamma describes acceptance,
  not a measured spectrum.
- The existing empirical workflow is limited to its documented random-catalog
  stack; it is not general calibration for these examples. Time-dependent
  analysis is not available yet.

See [scientific status](docs/scientific_status.md) and the
[fixed scientific baseline](docs/release_scientific_baseline.md) before interpreting outputs.

## Repository layout

- `run_agent_wrap.py`: sole public analysis entry point.
- `agent_core/`: planning, task state, execution, provenance and review.
- `analysis_backend/`: supported LLH, PDF evaluation and generic diagnostics.
- `.agents/skills/`: natural-language workflow and review policies.
- `tools/`: the optional workbook builder, not PDF construction tools.
- `docs/`: definitions, input requirements, scientific limitations and release status.

Owner tests, dedicated catalog comparisons, PDF precalculation, historical
research scripts and conversation transcripts are excluded.

See [catalog workflow](docs/dr2_catalog_workflow.md),
[release preparation](docs/testing_and_release.md) and
[release adaptations](docs/release_copy_changes.md).
Current code version: `0.2.0`; the previous snapshot is identified as `0.1.0`.
Author: Bei Zhou. License and final citation/publication metadata remain pending.
No open-source license is granted by this preparation copy.
See the [metadata decisions and remaining work](docs/release_metadata_draft.md)
and [draft release notes](docs/release_notes.md).
