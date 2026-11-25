# NuSrcAgent

Give NuSrcAgent a source name, sky coordinates or a catalog to search for high-energy neutrino emission in public IceCube data. The agent runs the likelihood fit and saves the inputs, settings and results so you can repeat it.

## Get started

Ask Codex or Claude Code to install NuSrcAgent.

```text
Install NuSrcAgent from https://github.com/beizhouphys/NuSrcAgent
```

Then continue in the same chat from the NuSrcAgent folder.

```text
Analyze NGC 1068
```

The agent looks up NGC 1068 and runs a time-integrated fit using all 14 years of IceTracks-DR2. To invoke the skill by name, use `$nusrcagent` in Codex or `/nusrcagent` in Claude Code.

For either installation method, you need Python 3.12 and Git on macOS or Linux. This private repository contains version `0.2.0`. To download the files, sign in with a GitHub account that has access, using Git HTTPS credentials or `gh auth login`.

To install from a terminal, run

```bash
git clone https://github.com/beizhouphys/NuSrcAgent.git
cd NuSrcAgent
bash install.sh
```

The installer downloads and verifies the IceTracks-DR2 data and precomputed probability density tables. To add IceTracks-DR1, run `bash install.sh --data-sample icecube_public_ps_10yr`. See the [installation guide](docs/input_installation.md) or [run a fit from the terminal](docs/quickstart.md).

## What analyses can I run?

- **Single-source analysis** tests for a neutrino excess at one sky position.
- **Catalog-wide single-source analysis** fits each source independently, giving one result per source.
- **Stacking analysis** tests a catalog’s combined emission. Choose a weighting scheme, such as equal weighting or weighting by a measured source flux. The fit accounts for detector acceptance at each source position.

| Data and analysis | What you can test |
| --- | --- |
| IceTracks-DR2 (2008–2022), time-integrated | All three analyses. The default fit uses event directions and energy proxies. You can also request a spatial-only fit. |
| IceTracks-DR2, time-dependent | All three analyses with a fixed box or Gaussian time profile for each source. For one source or for each catalog source independently, you can also request a [fitted-time search](docs/time_dependent.md). |
| IceTracks-DR1 (2008–2018), time-integrated | Spatial-only single-source analysis, or a catalog-wide single-source analysis with stacking. |

## Examples from the paper

- **NGC 1068.** We gave the agent turbulent corona model code and compared the resulting non-power-law fit with a power-law fit in a time-integrated analysis. To test your own model, supply a table of energy and differential flux for a fixed spectral shape. See [spectrum inputs](docs/requested_spectra.md).
- **32 magnetars.** We asked the agent to find an IceCube stacking analysis in the literature and fit the same 32 magnetars with equal weighting. To reproduce the study’s flux upper limit, the agent wrote signal-injection simulations for this comparison.

Try both catalog analyses with the [three-source example](docs/quickstart.md#2-three-source-scan-plus-stack). You can also use the [catalog of 3,386 radio-bright AGN](data_input/sources/README.md).

## What do the fitted quantities mean?

For the default NGC 1068 analysis, the first fit gives you the best-fit signal count `n`, the power-law spectral index `s` (differential flux proportional to $E^{-s}$), the likelihood-ratio test statistic `TS`, the estimated local p-value and the corresponding one-sided significance. A larger `TS` favors signal plus background over background alone. At `n = 0`, the fit cannot determine `s`.

If you choose to continue, you get 95% profile-likelihood flux upper limits and, when `TS > 9`, a flux measurement. See the [single-source workflow](docs/single_source_stages.md) and [stacking flux results](docs/stacking_flux.md).

For a more precise significance, request background trials that repeat the fit on randomized data. [Time-integrated DR2 trials](docs/dr2_empirical_scrambling.md) calibrate the significance of a specified single-source or stacking analysis. A fixed-profile time-dependent fit gives a significance only after matched trials. To test the most significant source in the catalog, those trials must repeat the full catalog search and record its largest `TS`. See [time-dependent trials](docs/time_dependent_catalog.md).

Open `report.md` and `review.md` in the run directory for the results and warnings. The same directory holds the CSV tables and records of the settings and inputs. Flux figures are under `figures/runs/<run_id>/`. Treat results with warnings as preliminary. Residuals in the DR2 background model for the IC79 detector season can bias `n`, `s` and flux. See [output files](docs/quickstart.md#read-the-outputs) and [scientific limitations](docs/scientific_status.md).

For numerical details, see the [catalog fit procedure](docs/dr2_catalog_workflow.md#independent-fit-procedure-for-source-scans), [single-source spectral interpolation](docs/single_source_linear_interpolation.md) and [stacking performance](docs/stacking_performance.md).

## Citation

If you use NuSrcAgent in a publication, please cite Bei Zhou, Po-Wen Chang and Kohta Murase, *NuSrcAgent: An AI Agent for High-Energy Neutrino Source Searches*. For the observations, see the [IceCube dataset citations](docs/data_attribution.md).
