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

The current version is `0.2.0`, a development version shared
through a private repository. Input data and precomputed probability-density
tables are provided automatically. DR2 time-dependent single-source analysis
and catalog scans support explicit Gaussian/box profiles; time-dependent
stacking awaits collaborator code.

Verified on 2026-10-16: a fresh GitHub clone completed plain `bash install.sh`
and both real DR2 examples. See the [verification record](docs/input_installation_verification.md#github-hosted-one-command-verification).

## Analysis interface

The analysis interface connects your requests to the likelihood calculation and
its reviewed results. Three features help you manage calculations that can take
substantial time, especially large catalog searches and repeated background fits:

1. **Estimated time remaining during calculation.** Progress updates report a
   rough estimate of time remaining (ETA) from work completed in the current run.
   Single-source fits, joint stacks, catalog scans and flux calculations report
   the relevant fit or stage; an estimate for one stage excludes later stages
   that have not been timed. Before a usable timing sample, the estimate is
   pending. Optimizer call counts are uncertain, so the ETA is approximate and
   never changes the fit's stopping conditions. Continuous background trials
   without a target count have no scheduled end time. Final chat answers include
   total elapsed time when a request takes more than one minute.
   See [progress and elapsed time](docs/task_timing.md).
2. **Number of workers and CPU budget.** Add `--workers N` to
   `run --task <task_id>` to select computing resources (default 1). Independent
   catalog fits use N worker processes with one numerical-library thread each.
   For one single-source or joint stacking fit, the same option sets the
   numerical-library thread budget. More workers can require more memory;
   speedup depends on the calculation. The choice is recorded with the run and
   preserves the scientific settings. Pass it again for a user-authorized flux
   stage. Background-trial tasks use their separately recorded scheduler size.
   See [CPU selection](docs/cpu_execution.md).
3. **Background-trial guidance and empirical significance.** Every reported
   analytic significance estimate is followed by a reminder that a more precise
   significance requires background trials; an estimate strictly above 2 sigma
   receives an explicit reminder that trials are needed. Ordinary fits do not
   start trials automatically. A separate, checkpointed event-right-ascension
   trial workflow follows an existing reviewed DR2 single-source analysis or
   stacking analysis, retaining its sources, weighting factors, event selection,
   spectrum, PDFs and fitting procedure. It reports empirical p-value and
   significance, 68%/95% Monte Carlo intervals and trial-distribution figures,
   with checkpoints, stopping and resumption. Catalog-scan maxima and
   time-dependent trials remain outside this workflow.
   See [background trials](docs/dr2_empirical_scrambling.md).

## What analyses can I run?

| Data / mode | Implemented analysis | Status |
| --- | --- | --- |
| DR2 full14, time-integrated spatial+energy | Single source, individual catalog scan, stacking | Default; fits ns and s_nu |
| DR2 full14, time-integrated spatial-only | Single source, individual catalog scan, stacking | Fixed acceptance s_nu; no energy term |
| DR1 10-year, time-integrated spatial-only | Existing single-source and catalog scan+stack paths | Separate inputs and definitions |
| DR2 time-dependent | Single source and individual catalog scan | Gaussian/box profiles; explicit fixed parameters or time searches; stacking awaits collaborator code |

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
  By default it fits the signal count `ns` and spectral index `s_nu`.
- **Spatial-only** analysis omits the energy term. For DR1 and DR2, it assumes
  `dN/dE` proportional to `(E/E0)^(-2.5)` by default when calculating detector
  acceptance with `s_nu=2.5` (`--s-nu 2.5`). The spectral index is fixed, not fitted. An explicitly
  supplied spectrum overrides this default; this s_nu is not a measured source
  spectrum. Historical tasks keep their recorded spectrum settings.
- **Time-dependent** analysis also uses event arrival times to test emission
  over a specified or fitted time profile, for example a flare. This capability
  supports DR2 single-source analysis and independent catalog scans with Gaussian
  or box profiles. See the [time-dependent guide](docs/time_dependent.md) for
  explicit search settings and the current calibration limits.
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
- **s_nu** is the spectral index in `dN/dE` proportional to
  `(E/E0)^(-s_nu)`, where `E` is neutrino energy and `E0` is a reference energy.
  Use `--s-nu 2.5` for a falling `E^-2.5` differential number spectrum.
  When `ns=0`, the fit cannot determine `s_nu`.
- **Energy flux per logarithmic energy interval** is `E_nu F_(E_nu)`,
  where `F_(E_nu) = E_nu dN/(dE_nu dA dt)`. Point-source flux
  measurements give this quantity at 1 TeV in GeV cm^-2 s^-1. Stack intensity
  divides the summed flux by 4 pi sr and uses `E_nu I_(E_nu)`.
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

After installation, start a local Claude Code session in the project folder and
enter the request below. In Codex, use `$nusrcagent` with the same request. Both
assistants follow the **NuSrcAgent skill** and call the same local Python commands.

```text
/nusrcagent Analyze NGC 1068 at RA 40.6696 deg, Dec -0.0133 deg
with full14 DR2, time-integrated spatial+energy. Fit ns and s_nu.
```

The assistant records your source positions, spectrum and weighting choices,
asks about unresolved choices that would change the analysis, then runs the
likelihood fit and reads its checks. Each request has a saved analysis record
with an identifier, so you can locate its settings and results later. **READY**
means the required inputs/settings are complete; it is not a scientific result.

The assistant interprets natural language. The Python command-line interface
does not: its `--request` text is only a description kept with the analysis.
When using Python commands directly, provide positions and settings explicitly.

Under the default analysis settings, the minimum information a researcher
needs to provide is the sky coordinates or a resolvable name of each source.
NuSrcAgent accepts ICRS RA/Dec and Galactic l/b, converting them to backend
RA/Dec. Degrees, radians and RA hourangle are supported. It asks when the
coordinate system or units are unclear; original inputs and the conversion
are recorded. This applies to all currently supported analyses. The Python
wrapper requires coordinates; name lookup is performed by the natural-language
agent. See [coordinate input and conversion](docs/coordinates.md).

For new single-source requests, the Agent first reports best-fit ns and s_nu,
TS, local p value and one-sided significance in a final answer after LLH review.
It asks whether to continue and ends that turn. Only after the user replies does
it continue the flux calculation and report upper limits
and/or measurements, figures and tables in a second chat output. Terminal users
run `run --stage flux --task <task_id> --flux-user-reply "<actual user reply>"`
after the first-stage result and continuation reply. The primary fit is
saved and is not maximized again. See the [two-stage workflow](docs/single_source_stages.md).

## Minimal examples and outputs

To run the numerical fits directly in a terminal, follow the
[worked examples](docs/quickstart.md) for complete terminal commands:

1. NGC 1068 single-source fit.
2. Three-source individual scan plus uniform-weight stack using the bundled CSV.

Both explain how to save a request, check `READY` and run the fit. They show
where to find readable reports, CSV result tables, the settings used, and
records of the code/data versions (called **provenance**).
The guide includes observed numerical references from the local clean-install
checks. DR2 produces numerical reports/tables, catalog sqrt(TS) PDF/PNG figures,
and the documented single-source flux-limit figures; no Excel workbook is generated.

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
- IC79 declination–energy residuals persist in the background PDFs; ns, s_nu and inferred
  flux may be biased. Hash verification establishes input identity, not scientific validity.
- Report fitted quantities, TS, p-value and corresponding one-sided Gaussian
  significance in sigma, with local/post-trial and analytic/empirical labels.
  Ordinary local p-values and significances are estimates: use half-chi-square
  dof=2 for free s_nu and dof=1 for fixed s_nu; empirical calibration is separate.
  Zero background trials alone do not create a warning: an otherwise passing
  ordinary fit returns **COMPLETED**.
- Whenever an estimated significance is reported, a more precise significance
  requires background trials. If the estimate exceeds 2 sigma, background
  trials are needed to calibrate the result. This applies to every analysis,
  including single sources, catalog scans and stacks. Trials must repeat the
  corresponding fit and search/hypothesis family; this reminder does not
  start trials or change the review status.
- **COMPLETED_WITH_WARNINGS** means the calculation finished but issues remain to
  be read in the report; results are preliminary. Failed reviews are not valid results.
  At ns = 0, s_nu is unidentifiable. Spatial-only s_nu describes acceptance,
  not a measured spectrum.
- Background trials can follow a reviewed DR2 single-source or stacking
  analysis. Catalog-scan maxima and time-dependent trials remain unavailable.

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

New DR1 and DR2 single-source tasks and individual catalog fits default to a source-centered
declination window: minimum half-width 20 degrees and at least 20% of each
dataset. Use `--full-sky-events` at task creation for all events, or
`--source-dec-window-deg 30` for a larger minimum half-width. The stack part of
`scan_and_stack` retains its existing event selection. Scans reuse complete
loaded data and validated PDF tables. [Settings and limitations](docs/single_source_performance.md).

New DR2 time-integrated spatial+energy single-source tasks also report preliminary one-sided 95% flux upper limits for E^-2, E^-2.5 and E^-3, with a spectrum figure including published NGC 1068 and diffuse uncertainty bands. Use `--no-flux-upper-limits` to omit them; catalog scans enable the per-source limits and figures only with `--flux-upper-limits`. See [flux limits and reference spectra](docs/flux_upper_limits.md) for definitions, units, files and coverage limitations.

Catalog scans now automatically report the top five sources with separate local/global
p value and significance columns, an analytic independent-source catalog correction,
and a Fig. 3-style sqrt(TS) histogram without a normal-distribution fit.
See [catalog reporting](docs/dr2_catalog_workflow.md#catalog-scan-reporting) for assumptions, files and display conventions.

New DR2 time-integrated spatial+energy **single-source** tasks also report the primary-spectrum flux measurement when **TS > 9**, with 68.27%/95% profile intervals, spectrum shading and joint flux and spectral-index contours. Existing fixed-spectrum upper limits remain. Catalog scans do not enable this measurement calculation. See [single-source measurements](docs/flux_measurements.md).

New catalog scans explicitly record the original SkyLLH optimizer separately
from single-source and joint stacking defaults. See [catalog fit procedure](docs/dr2_catalog_workflow.md#independent-fit-procedure-for-source-scans).

DR2 spatial+energy stacking reduces repeated PDF calculations with a lossless
spatial PDF block cache (1 GiB shared per stack with a fitted spectral index) and exact observed-
energy interpolation lookups (16 MiB per dataset). Budgets apply per analysis
process; CPU settings and scientific fit definitions retain their existing values.
See [stacking performance and cache lifecycle](docs/stacking_performance.md).

New DR2 time-integrated spatial+energy stacks report the primary ns, s_nu, TS, p-value and
one-sided significance first. Continue the same task with `run --task <id>
--stage flux --flux-user-reply "<actual user reply>"` for default s_nu=2, 2.5, 3 upper limits and primary intensity
measurements when TS > 9. The Agent ends the first turn with the primary result
and asks whether to continue. After the user replies, it runs the flux stage with
`--flux-user-reply "<actual user reply>"` and reports that stage in a new final answer. Upper-limit spectrum figures are generated and reported
regardless of primary TS; TS > 9 adds the measured spectrum and its uncertainty.
Joint-stack figures use total flux / (4*pi sr),
with only the two diffuse references. [Stacking flux definitions and workflow](docs/stacking_flux.md).

New DR2 time-integrated spatial+energy standalone single-source tasks use two-node linear s_nu
interpolation for the signal energy PDF in both the primary fit and flux
calculation. Catalog scan and joint stacking defaults retain their original
quadratic interpolation. Optimizer, tolerances and the flux-profile consistency
guard remain unchanged. See [single-source interpolation](docs/single_source_linear_interpolation.md).

## Spectra beyond the conventional power law

A specified PL exponent is fixed unless fitting is requested. Conventional
spectra use the existing signal-energy PDF tables. An explicit rising or steep
spectrum, a fitted range outside those tables, or a supplied modeled spectrum
triggers preparation of the matching signal-energy PDFs and detector acceptance
before interpolation and likelihood fitting. The agent explains the preparation
and reports a current measured ETA. Spatial-only analyses calculate acceptance
without using energy PDFs. This applies to individual sources, catalog scans
and stacking. See [requested spectra](docs/requested_spectra.md) for the input
format, energy support, preparation command and current scope.
