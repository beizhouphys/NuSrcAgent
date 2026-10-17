# NuSrcAgent

NuSrcAgent helps astrophysicists and particle physicists search for high-energy
neutrino emission from individual objects or catalogs of candidate sources,
using IceCube public track data. You can describe an analysis in ordinary
language to an AI assistant, or run the same analysis directly from a terminal.
The numerical results come from the likelihood code, not from the language model.

The documentation assumes familiarity with physics, not with AI or software
architecture. Start with installation below, then run the two
[worked examples](docs/quickstart.md).

The current version is `0.2.0`, a time-integrated development version shared
through a private repository. Input data and precomputed probability-density
tables are provided automatically. Time-dependent analysis is not available yet.

Verified on 2026-10-16: a fresh GitHub clone completed plain `bash install.sh`
and both real DR2 examples. See the [verification record](docs/input_installation_verification.md#github-hosted-one-command-verification).

## What analyses can I run?

- **Single source:** fit for a neutrino excess at one specified sky position.
- **Catalog scan:** fit each catalog source independently, producing one result
  per source. These are individual fits, not a joint detection of the catalog.
- **Stacking:** test the combined emission from the catalog with specified
  relative source weights, a total signal count and a common spectral index.

Time-integrated means that the fit combines the selected observation periods
without searching for flares or using an event-time probability density.
Spatial+energy uses event directions, angular uncertainties and reconstructed
energy information; spatial-only omits the energy term.

| Data / mode | Implemented analysis | Status |
| --- | --- | --- |
| DR2 full14, time-integrated spatial+energy | Single source, individual catalog scan, stacking | Default; fits ns and Gamma |
| DR2 full14, time-integrated spatial-only | Single source, individual catalog scan, stacking | Fixed acceptance Gamma; no energy term |
| DR1 10-year, time-integrated spatial-only | Existing single-source and catalog scan+stack paths | Separate inputs and definitions |
| DR2 time-dependent | Planned single source, catalog scan and stacking | Not implemented in this copy; integration and validation pending |

DR2 is the 14-year IceTracks data release; `full14` means all its observation
periods. DR1 is the earlier 10-year release and uses separate inputs and analysis
definitions. The future release plan includes time-dependent analysis, but that
plan should not be read as a list of features already implemented.

### What do the fitted quantities mean?

| Quantity | Physical or statistical meaning |
| --- | --- |
| `ns` | Fitted total number of signal events in the selected data; not a flux by itself |
| `Gamma` | Positive index of the assumed neutrino spectrum, `dN/dE` proportional to `(E/E0)^(-Gamma)` |
| `TS` | Likelihood-ratio test statistic after maximization; a larger value favors the signal model, but is not itself a significance in sigma |

Here `E` is neutrino energy and `E0` is a reference energy. The fit accounts
for detector response; the event energy proxy is not identified with true
neutrino energy. Spatial+energy fits `ns` and `Gamma` by default. Spatial-only
fixes `Gamma` to calculate detector acceptance, so it does not measure a spectrum.
In command-line options, `--gamma -2.53` denotes the spectrum with `Gamma=2.53`.

## Installation

You need Python 3.12 on macOS/Linux, Git, internet access and access to this
private GitHub repository. In a terminal, download the code and enter its folder:

```bash
git clone https://github.com/beizhouphys/NuSrcAgent.git
cd NuSrcAgent
```

If you have already cloned the repository, simply open a terminal in that
folder. Then install with one command:

```bash
bash install.sh
```

The script installs the required Python libraries and downloads the matching
IceCube data, frozen v3 background PDFs and signal energy PDFs (SEpdfs). Here
PDF means probability density function, not a document file. You do not need
to select files on the IceCube website or calculate the PDFs yourself.

The Python libraries are installed in `.venv/`, an environment kept inside
this project so they do not replace your system's libraries. The script checks
each downloaded file against its recorded SHA-256 checksum, a file fingerprint
used to detect incomplete or changed inputs. Successful installation ends with
`Installation and input verification complete.` Re-running reuses verified inputs.

Because the repository and data downloads are private, installation uses your
own GitHub login. It reuses Git HTTPS credentials or an existing `gh auth login`
(the GitHub command-line tool). If you cloned using only an SSH key, log in
with `gh auth login` once for the HTTPS data downloads. Do not use someone else's
account or token. See [authentication and installation options](docs/input_installation.md).

The default DR2 download is about 1.52 GB and extracts about 3.8 GiB, in addition
to the environment and retained download/staging cache. Python itself is not
installed by the script. See [installation options and recovery](docs/input_installation.md)
and [data attribution](docs/data_attribution.md).

## Ask for an analysis in ordinary language

After installation, open the project folder in Codex. The project provides
`$he-neutrino-analysis`, a set of instructions that tells the assistant how to
set up, run and check these analyses. For example, ask:

```text
$he-neutrino-analysis Analyze NGC 1068 at RA 40.6696 deg, Dec -0.0133 deg
with full14 DR2, time-integrated spatial+energy. Fit ns and Gamma.
```

The assistant records your source positions, spectrum and weighting choices,
asks about unresolved choices that would change the analysis, then runs the
likelihood fit and reads its checks. Each request has a saved analysis record
with an identifier, so you can locate its settings and results later. `READY`
means the required inputs/settings are complete; it is not a scientific result.

The assistant interprets ordinary language. The Python command-line interface
does not: its `--request` text is only a description kept with the analysis.
When using Python commands directly, provide positions and settings explicitly.

## Minimal examples and outputs

Codex is not required for the numerical fits. Follow the
[worked examples](docs/quickstart.md) for complete terminal commands:

1. NGC 1068 single-source fit.
2. Three-source individual scan plus uniform-weight stack using the bundled CSV.

Both explain how to save a request, check `READY` and run the fit. They show
where to find readable reports, CSV result tables, the settings used, and
records of the code/data versions (called provenance).
The guide includes observed numerical references from the local clean-install
checks. DR2 currently produces numerical reports/tables, not PDF figures or an
Excel workbook.

## Before interpreting a result

- An ordinary fit runs no background trials. Its local p-value uses an analytic
  approximation, not a measured background TS distribution. A source scan also
  requires accounting for the search over multiple sources before quoting a
  catalog-wide significance.
- Frozen background v3 retains IC79 Dec–energy residuals; ns, Gamma and inferred
  flux may be biased. Hash verification establishes input identity, not scientific validity.
- `COMPLETED_WITH_WARNINGS` means the calculation finished but issues remain to
  be read in the report; results are preliminary. Failed reviews are not valid results.
  At ns = 0, Gamma is unidentifiable. Spatial-only Gamma describes acceptance,
  not a measured spectrum.
- The existing background-trial procedure is limited to its documented
  random-catalog stack; it cannot simply be used to calibrate any new catalog
  or these examples. Time-dependent analysis is not available yet.

See [scientific status](docs/scientific_status.md) and the
[fixed scientific baseline](docs/release_scientific_baseline.md) before interpreting outputs.

## Repository layout

- `run_agent_wrap.py`: the Python command used to request and run analyses.
- `agent_core/`: records analysis requests, runs calculations and checks outputs.
- `analysis_backend/`: likelihood (LLH) calculations, PDF evaluation and diagnostics.
- `.agents/skills/`: instructions for the assistant, including result-checking rules.
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
