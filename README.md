# NuSrcAgent

If you use NuSrcAgent in a publication, please cite our paper (arXiv link to be added when available).

NuSrcAgent helps astrophysicists and particle physicists search for high-energy
neutrino emission from individual objects or catalogs of candidate sources,
using IceCube public point-source data. You can describe an analysis in natural
language to an AI assistant, or run the same analysis directly from a terminal.
The numerical results come from the likelihood code, not from the language model.

The tool assumes basic familiarity with physics/astronomy; familiarity with
AI or software architecture is not required. Start with installation below,
then run the two [worked examples](docs/quickstart.md).

The current version is `0.2.0`, a time-integrated development version shared
through a private repository. Input data and precomputed probability-density
tables are provided automatically. Time-dependent analysis is not available yet.

Verified on 2026-10-16: a fresh GitHub clone completed plain `bash install.sh`
and both real DR2 examples. See the [verification record](docs/input_installation_verification.md#github-hosted-one-command-verification).

## What analyses can I run?

| Data / mode | Implemented analysis | Status |
| --- | --- | --- |
| DR2 full14, time-integrated spatial+energy | Single source, individual catalog scan, stacking | Default; fits ns and Gamma |
| DR2 full14, time-integrated spatial-only | Single source, individual catalog scan, stacking | Fixed acceptance Gamma; no energy term |
| DR1 10-year, time-integrated spatial-only | Existing single-source and catalog scan+stack paths | Separate inputs and definitions |
| DR2 time-dependent | Planned single source, catalog scan and stacking | Not implemented in this copy; integration and validation pending |

### Data and analysis terminology

- **IceCube public point-source data** are released samples of track-like
  event candidates for searches for neutrino emission from localized sources.
  They include reconstructed directions, angular uncertainties, energy proxies
  and arrival times, together with detector uptime, effective areas and
  **instrument response functions (IRFs)** describing the relation between true
  neutrino quantities and reconstructed quantities. The event energy proxy is
  not the true neutrino energy, and the event sample is not a list of confirmed
  astrophysical neutrinos.
- **DR1** denotes the earlier 10-year release, covering 2008–2018. See the
  [official data description](https://icecube.wisc.edu/data-releases/2021/01/all-sky-point-source-icecube-data-years-2008-2018/),
  [data download](https://doi.org/10.7910/DVN/VKL316) and
  [data-release paper, arXiv:2101.09836](https://arxiv.org/abs/2101.09836).
  NuSrcAgent retains its separate spatial-only analysis and input definitions.
- **DR2** denotes IceTracks-DR2, the 14-year release covering 2008–2022,
  with updated event selection and detector calibration; it is not simply DR1
  with four more years appended. See the
  [official data description](https://icecube.wisc.edu/data-releases/2026/05/icecube-second-track-data-release-icetracks-dr2-data-from-2008-2022-for-neutrino-source-searches/),
  [data download](https://doi.org/10.7910/DVN/MMIIZA) and
  [data-release paper, arXiv:2605.19040](https://arxiv.org/abs/2605.19040).
  **full14** means all 14 observation periods of this release.
- **Time-integrated** analysis combines the selected observation periods
  without searching for flares or using an event-time probability density.
- **Spatial** information consists of reconstructed event directions and their
  angular uncertainties, used to compare events with the source positions and
  the background directional distribution.
- **Energy** information is the reconstructed event energy proxy, interpreted
  through the detector response and the assumed signal/background distributions.
  The **energy term** is the likelihood's contribution from these probability
  densities, not a direct substitution of the energy proxy for neutrino energy.
- **Spatial+energy** analysis uses both directional and energy information.
  By default it fits the signal count `ns` and spectral index `Gamma`.
- **Spatial-only** analysis omits the energy term. It uses directional
  information and fixes `Gamma` to calculate detector acceptance; this Gamma
  is not a measured source spectrum.
- **Time-dependent** analysis also uses event arrival times to test emission
  over a specified or fitted time profile, for example a flare. This capability
  is planned but is not implemented in the current version.
- **Single source** analysis fits for a neutrino excess at one specified
  sky position.
- **Individual catalog scan** fits each catalog source independently,
  producing one result per source rather than a joint detection of the catalog.
- **Stacking** analysis tests the catalog's combined emission using specified
  relative source weights, a total signal count and a common spectral index.
  Detector acceptance is applied separately, so equal intrinsic source weights
  do not imply equal expected detected signal counts.

### What do the fitted quantities mean?

- **ns** is the fitted total number of signal events in the selected data;
  it is not a flux by itself. In a stack it describes the total signal
  contribution from the catalog, not a separate count for every source.
- **Gamma** is the positive spectral index in `dN/dE` proportional to
  `(E/E0)^(-Gamma)`, where `E` is neutrino energy and `E0` is a reference energy.
  The command-line option `--gamma -2.53` denotes the spectrum with `Gamma=2.53`.
  When `ns=0`, Gamma is not identifiable from the fit.
- **TS** is the likelihood-ratio test statistic after maximization. A larger
  value favors the signal model relative to background alone; it is not itself
  a significance in sigma. See [interpretation cautions](#before-interpreting-a-result).

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
IceCube data, pre-calculated signal energy PDFs and background energy and
spatial PDFs. Here **PDF** means probability density function, not a document
file; **SEpdf** means signal energy PDF. You do not need
to select files on the IceCube website or calculate the PDFs yourself.

The Python libraries are installed in **.venv/**, an environment kept inside
this project so they do not replace your system's libraries. The script checks
each downloaded file against its recorded **SHA-256 checksum**, a file fingerprint
used to detect incomplete or changed inputs. Successful installation ends with
`Installation and input verification complete.` Re-running reuses verified inputs.

Because the repository and data downloads are private, installation uses your
own GitHub login. It reuses Git HTTPS credentials or an existing `gh auth login`
(the GitHub command-line tool). If you cloned using only an SSH key, log in
with `gh auth login` once for the HTTPS data downloads. Do not use someone else's
account or token. See [authentication and installation options](docs/input_installation.md).

The default DR2 download is about 1.52 GB and extracts about 3.8 GiB, in addition
to the Python environment and retained download/staging cache. Most extracted
space is used by the IceCube event data and detector response files (about
2.61 GB); pre-calculated PDFs add about 1.44 GB. These tables require modest
additional disk space but make likelihood evaluation much faster by reusing
pre-calculated distributions rather than recalculating them during each fit.
The raw-data files compress particularly
well, so the PDFs account for most of the download size, despite using a
smaller share of the extracted disk space. Python itself is not installed by
the script. See [installation options and recovery](docs/input_installation.md)
and [data attribution](docs/data_attribution.md).

## Ask for an analysis in natural language

**Natural-language interaction** means describing the scientific request in
your own words rather than assembling Python commands. You may use any natural
language supported by your AI assistant, including English, Chinese or a
mixture of languages. Interpretation quality can vary by language; unresolved
scientific ambiguities must still be clarified before running an analysis.

Replies follow your explicitly requested language or an explicitly established
personal language preference. Otherwise, they follow the language of your
request. If there is no preference or language cue, such as a bare
`$nusrcagent` invocation, replies default to English. The language used to
write project instructions is not treated as your language preference.

After installation, open the project folder in Codex. The project provides
the **NuSrcAgent skill**, a set of instructions that tells the
assistant how to set up, run and check these analyses. For example, ask:

```text
$nusrcagent Analyze NGC 1068 at RA 40.6696 deg, Dec -0.0133 deg
with full14 DR2, time-integrated spatial+energy. Fit ns and Gamma.
```

The assistant records your source positions, spectrum and weighting choices,
asks about unresolved choices that would change the analysis, then runs the
likelihood fit and reads its checks. Each request has a saved analysis record
with an identifier, so you can locate its settings and results later. **READY**
means the required inputs/settings are complete; it is not a scientific result.

The assistant interprets natural language. The Python command-line interface
does not: its `--request` text is only a description kept with the analysis.
When using Python commands directly, provide positions and settings explicitly.

## Minimal examples and outputs

Codex is not required for the numerical fits. Follow the
[worked examples](docs/quickstart.md) for complete terminal commands:

1. NGC 1068 single-source fit.
2. Three-source individual scan plus uniform-weight stack using the bundled CSV.

Both explain how to save a request, check `READY` and run the fit. They show
where to find readable reports, CSV result tables, the settings used, and
records of the code/data versions (called **provenance**).
The guide includes observed numerical references from the local clean-install
checks. DR2 currently produces numerical reports/tables, not PDF figures or an
Excel workbook.

## Radio-bright AGN catalog for testing

The 3386-source RFC 2019c radio-bright AGN catalog is
included in [data_input/sources/](data_input/sources/README.md), with column definitions,
selection and attribution. The CSV retains full stored coordinate precision,
X-band flux density and source identifiers; it supports uniform or radio-flux
weighting. This small table comes with the Git clone, separately from the IceCube bundles.
For example, ask `$nusrcagent` to inspect the bundled radio-bright AGN catalog
without running fits. A full individual scan requires 3386 fits; start small
when testing. See the [catalog notes](data_input/sources/README.md).

## Before interpreting a result

- An ordinary fit runs no background trials. Its local p-value uses an analytic
  approximation, not a measured background TS distribution. A source scan also
  requires accounting for the search over multiple sources before quoting a
  catalog-wide significance.
- The background PDFs retain IC79 Dec–energy residuals; ns, Gamma and inferred
  flux may be biased. Hash verification establishes input identity, not scientific validity.
- Report fitted quantities, TS, p-value and corresponding one-sided Gaussian
  significance in sigma, with local/post-trial and analytic/empirical labels.
  Ordinary local p-values and significances are estimates: use half-chi-square
  dof=2 for free Gamma and dof=1 for fixed Gamma; empirical calibration is separate.
  Zero background trials alone do not create a warning: an otherwise passing
  ordinary fit returns **COMPLETED**.
- **COMPLETED_WITH_WARNINGS** means the calculation finished but issues remain to
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
- `analysis_backend/`: **likelihood (LLH)** calculations, PDF evaluation and diagnostics.
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

New DR2 single-source tasks and individual catalog fits default to a source-centered
declination window: minimum half-width 20 degrees and at least 20% of each
dataset. Use `--full-sky-events` at task creation for all events, or
`--source-dec-window-deg 30` for a larger minimum half-width. The stack part of
`scan_and_stack` retains its existing event selection. Scans reuse complete
loaded data and validated PDF tables. [Settings and limitations](docs/single_source_performance.md).
