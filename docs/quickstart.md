# Worked examples: one source and a small catalog

Run commands from the checkout root after the [input installation](input_installation.md).
No manual IceCube download or PDF construction is required. These are real
full14 DR2 observed-data fits, not toy data or background-trial calibration.
You can run these commands without an AI assistant. A line ending in `\`
continues on the next line: copy the whole command, not just its first line.
`.venv/bin/python` selects the Python environment created by `install.sh`.

Both examples explicitly select time-integrated spatial+energy, fitted ns and
Gamma, frozen background v3 and the installed SEpdf tables. They impose no
extra event or source cuts. Bounds, seeds and the pooled IC86 definition are
recorded in the [scientific baseline](release_scientific_baseline.md).

The fitted `ns` is the signal-event count and `Gamma` is the index in
`dN/dE` proportional to `(E/E0)^(-Gamma)`. `TS` compares the best-fitting
signal-plus-background model with background alone; it is not a significance
in sigma. See the [quantity definitions](../README.md#what-do-the-fitted-quantities-mean).

## 1. Single source: NGC 1068

```bash
.venv/bin/python run_agent_wrap.py create-single \
  --request "DR2 NGC 1068 release example; fit ns and Gamma" \
  --name "NGC 1068" --ra-deg 40.6696 --dec-deg -0.0133 \
  --data-sample icecube_public_ps_14yr_dr2 \
  --likelihood-mode spatial_energy --gamma-mode fitted
```

This first command saves the request; it does not yet run the fit. It prints
a JSON response (a text list of named fields), including `task_id` and `status`.
Copy the returned identifier, which begins with `task_`, into the assignment
below in place of `task_REPLACE_WITH_RETURNED_ID`. Keep the rest of the commands
unchanged: `$task_id` then refers to your saved identifier.

`READY` means the required settings and inputs are available. If the response
asks a question or reports an error, resolve it before running. `show` displays
the saved request; `run` performs the likelihood fit. Neither command here
starts background trials.

```bash
task_id=task_REPLACE_WITH_RETURNED_ID
.venv/bin/python run_agent_wrap.py show --task "$task_id"
.venv/bin/python run_agent_wrap.py run --task "$task_id"
```

## 2. Three-source scan plus stack

The [example catalog](../configs/examples/catalog_sources_example.csv) contains
TXS 0506+056, PKS 1502+106 and 3C 279. Coordinates are in degrees. This example
uses uniform intrinsic source weights (1/3 each); it deliberately ignores the
CSV's illustrative `radio_weight` column. Detector acceptance still contributes
to the likelihood's source weighting; uniform intrinsic weights do not imply
equal detected signal contributions.

```bash
.venv/bin/python run_agent_wrap.py create-catalog \
  --request "Scan and stack this three-source example with uniform weights" \
  --catalog configs/examples/catalog_sources_example.csv \
  --name-column name --ra-column ra_deg --dec-column dec_deg \
  --catalog-operation scan_and_stack --weight-mode uniform \
  --data-sample icecube_public_ps_14yr_dr2 \
  --likelihood-mode spatial_energy --gamma-mode fitted
```

Use the **new** returned task ID, not the single-source ID. Check `READY`, then run:

```bash
task_id=task_REPLACE_WITH_RETURNED_ID
.venv/bin/python run_agent_wrap.py show --task "$task_id"
.venv/bin/python run_agent_wrap.py run --task "$task_id"
```

The scan independently fits each source with the same settings. The stack is a
separate joint fit with one ns and one common Gamma. This command is not a time
search, a catalog-global significance calculation or the historical large-catalog
benchmark. See [catalog columns and weights](../configs/examples/README.md).

Do not add the individual-source TS values and interpret the sum as the
stacking result: the stack fits a different, joint source hypothesis.
For a large catalog the scan can take substantial time because it repeats a
fit for every row; begin with a small subset to assess the computing time.

## Read the outputs

When the fit finishes, the printed response gives its completion status and
`artifacts.run_directory`, the folder containing this calculation's results.
You need not parse JSON programmatically: read that path and open the folder.
Start with `report.md` and `review.md`, which are readable text, then examine
the CSV tables. Files ending in `.yaml` or `.json` retain detailed settings and
checks as text that the software can read back. The principal files are:

| Location | Contents |
| --- | --- |
| `data_output/agent_tasks/<task_id>/` | Persistent `task.json`, request YAML, `agent_review.json` and `agent_review.md` |
| `data_output/runs/<run_id>/` | `report.md`, `report.yaml`, `config.original.yaml`, `config.normalized.yaml`, `provenance.yaml`, `review.json`, `review.md` |
| Same run directory, `fit_results.csv` | Single-source or joint-stack fit |
| Same run directory, `source_results.csv` | Scan fits, one-based `source_number` in original CSV order |

`config.original.yaml` records the submitted settings; `config.normalized.yaml`
records them after unit/convention conversion and application of defaults.
`provenance.yaml` records the code version, input-file checksums and random seed
needed to identify the calculation. `review.md` explains calculation checks
and warnings; it is not an independent scientific peer review.

Per-source fit details are nested in `report.yaml`; per-source review checks are
part of `review.json`. Separate per-source directories are not promised. DR2
does not generate the DR1 PDF figures or optional workbook. Read both the run
review and the central agent review before quoting a result.

Expected completion for these checks is `COMPLETED`, when all other review checks
pass. Report local analytic p-values and their one-sided Gaussian significances
together; zero background trials and absent empirical/catalog-global calibration
are method information, not warnings on their own. Actual fit or artifact warnings
still produce `COMPLETED_WITH_WARNINGS`. If a review fails,
do not treat its numerical output as valid or change scientific settings merely
to match the reference numbers.

## Observed numerical references

The local clean-install checks on 2026-10-16 produced the following rounded
values with the settings above. Gamma here is positive SkyLLH Gamma in
`dN/dE` proportional to `E^-Gamma`; the CLI's `--gamma` uses the negative
power-law exponent. These are reproducibility references on the tested macOS
environment, not detection claims or cross-platform guarantees.

| Fit | TS | ns | Gamma |
| --- | ---: | ---: | ---: |
| NGC 1068 | 22.991619 | 68.567453 | 3.059035 |
| Three-source stack | 7.004486 | 18.813651 | 2.290629 |
| Scan: TXS 0506+056 | 8.665655 | 10.936394 | 2.129534 |
| Scan: PKS 1502+106 | 0.255117 | 5.030084 | 2.514923 |
| Scan: 3C 279 | 0 | 0 | Unidentifiable at ns = 0 |

The table does not establish unbiased parameters or calibrated significance.
Record warnings and input/configuration hashes when comparing runs. For a
nonzero reference, report signed relative difference `(result-reference)/reference`
first, then signed absolute difference `result-reference`; for zero references,
the relative difference is undefined. The [installation verification](input_installation_verification.md)
records the checks already performed; [scientific status](scientific_status.md)
explains the remaining limitations.

## Other supported settings

- To fit ns at a fixed spectrum in DR2 spatial+energy, replace
  `--gamma-mode fitted` with `--gamma-mode fixed --gamma -2.53` in a creation
  command and adjust its request text. Supplying `--gamma` alone does not fix
  Gamma in the default spatial+energy fit.
- For DR2 spatial-only, replace the likelihood/Gamma flags with
  `--likelihood-mode spatial_only --gamma-mode fixed --gamma -2.5`.
  This Gamma sets detector acceptance, not a fitted spectrum. The smaller input
  installation must be selected explicitly; see the installation guide.
- For catalog scan only, replace `--catalog-operation scan_and_stack` with
  `--catalog-operation scan`; stacking weights are then not required.
- To retain the DR1 path, install its separate inputs, then use
  `--data-sample icecube_public_ps_10yr --likelihood-mode spatial_only
  --gamma-mode fixed --gamma -2.53` in a creation command. DR2 reference numbers
  and frozen v3 definitions do not apply to DR1.

Ordinary `run` commands execute **zero background trials**, even if the request
YAML contains a default `background.n_trials`. The separate, restricted
[empirical workflow](dr2_empirical_scrambling.md) must not be presented as general
calibration for a user's catalog or these single-source/scan examples.
