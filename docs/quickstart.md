# Worked examples: one source and a small catalog

Run commands from the checkout root after the [input installation](input_installation.md).
No manual IceCube download or PDF construction is required. These are real
full14 DR2 observed-data fits, not toy data or background-trial calibration.
You can run these commands without an AI assistant. A line ending in `\`
continues on the next line: copy the whole command, not just its first line.
`.venv/bin/python` selects the Python environment created by `install.sh`.

Both examples explicitly select time-integrated spatial+energy, fitted ns and
s_nu, frozen background v3 and the installed SEpdf tables. Individual fits
use the default adaptive source-centered declination window; the joint stack
uses all events. No source cuts are added. Bounds, seeds and the pooled IC86 definition are
recorded in the [scientific baseline](release_scientific_baseline.md).

The fitted `ns` is the signal-event count and `s_nu` is the index in
`dN/dE` proportional to `(E/E0)^(-s_nu)`. `TS` compares the best-fitting
signal-plus-background model with background alone; it is not a significance
in sigma. See the [quantity definitions](../README.md#what-do-the-fitted-quantities-mean).

## 1. Single source: NGC 1068

```bash
.venv/bin/python run_agent_wrap.py create-single \
  --request "DR2 NGC 1068 release example; fit ns and s_nu" \
  --name "NGC 1068" --ra-deg 40.6696 --dec-deg -0.0133 \
  --data-sample icecube_public_ps_14yr_dr2 \
  --likelihood-mode spatial_energy --s-nu-mode fitted
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

The first `run` now returns the reviewed primary fit. Read the best-fit ns and
s_nu, TS, local p value and significance in `single_source_llh_summary`.
When its status is `AWAITING_FLUX`, report the primary result and wait for the
user to reply. Only after that reply continue with:

```bash
.venv/bin/python run_agent_wrap.py run --stage flux --task "$task_id" --flux-user-reply "<actual user reply>"
```

The Agent ends the first turn with the primary values in a final answer and
asks whether to continue. This command belongs to the later user-authorized turn. The second result
contains reviewed flux limits and/or measurements and figures. The two stages
retain separate reports, and the primary fit is not repeated. See
[single-source stage states and recovery](single_source_stages.md).

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
  --likelihood-mode spatial_energy --s-nu-mode fitted
```

Use the **new** returned task ID, not the single-source ID. Check `READY`, then run:

```bash
task_id=task_REPLACE_WITH_RETURNED_ID
.venv/bin/python run_agent_wrap.py show --task "$task_id"
.venv/bin/python run_agent_wrap.py run --task "$task_id"
```

This first command returns the source scan and reviewed joint-stack primary
fit at AWAITING_FLUX. The Agent reports the primary result in its final answer,
asks whether to continue and ends the turn. After the user replies, run:

```bash
.venv/bin/python run_agent_wrap.py run --task "$task_id" --stage flux --flux-user-reply "<actual user reply>"
```

The scan independently fits each source with the same settings. The stack is a
separate joint fit with one ns and one common s_nu. This command is not a time
search, a catalog-global significance calculation or the historical large-catalog
benchmark. See [catalog columns and weights](../configs/examples/README.md).

Do not add the individual-source TS values and interpret the sum as the
stacking result: the stack fits a different, joint source hypothesis.
For a large catalog the scan can take substantial time because it repeats a
fit for every row; begin with a small subset to assess the computing time.

## Radio-bright AGN catalog: inspect before a large run

The [bundled catalog notes](../data_input/sources/README.md) describe the
3386-source RFC 2019c table. The CSV retains full stored coordinate
precision and X-band flux density. This command only inspects its rows/columns:

```bash
.venv/bin/python run_agent_wrap.py inspect-catalog \
  --catalog data_input/sources/radio_bright_agn_rfc2019c_xband_ge_0p15_dec_lt87_3386.csv \
  --name-column source_name --ra-column ra_deg --dec-column dec_deg \
  --weight-column xband_flux_jy
```

To use it in a later analysis, pass that file to `create-catalog --catalog`;
choose uniform or radio-flux weights as a scientific choice. Do not use the
optional raw-RFC built-in reader for this bundled CSV. A complete source scan
would run 3386 fits; the inspection command above runs no fits or trials.

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

The first run of these two-stage examples returns `AWAITING_FLUX`. After the
user-authorized flux stage, completion is `COMPLETED` when all review checks
pass. Report local p-value and one-sided Gaussian significance estimates
together: half-chi-square dof=2 for fitted s_nu, dof=1 for fixed s_nu; zero background trials and absent empirical/catalog-global calibration
are method information, not warnings on their own. Actual fit or artifact warnings
still produce `COMPLETED_WITH_WARNINGS`. If a review fails,
do not treat its numerical output as valid or change scientific settings merely
to match the reference numbers.

## Observed numerical references

The local clean-install checks on 2026-10-16 produced the following rounded
values with the original all-event selection. To reproduce this historical
table, add `--full-sky-events` to each creation command above. The new default
windowed individual fits can differ; the joint stack is unchanged.
The historical SkyLLH fit parameter equals s_nu. These are reproducibility references on the tested macOS
environment, not detection claims or cross-platform guarantees.

| Fit | TS | ns | s_nu |
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
  `--s-nu-mode fitted` with `--s-nu-mode fixed --s-nu 2.53` in a creation
  command and adjust its request text. Supplying `--s-nu` fixes the index unless `--s-nu-mode fitted` is also specified.
- For DR2 spatial-only, replace the likelihood/s_nu flags with
  `--likelihood-mode spatial_only --s-nu-mode fixed --s-nu 2.5`.
  This s_nu sets detector acceptance, not a fitted spectrum. The smaller input
  installation must be selected explicitly; see the installation guide.
- For catalog scan only, replace `--catalog-operation scan_and_stack` with
  `--catalog-operation scan`; stacking weights are then not required.
- To retain the DR1 path, install its separate inputs, then use
  `--data-sample icecube_public_ps_10yr --likelihood-mode spatial_only
  --s-nu-mode fixed --s-nu 2.53` in a creation command. DR2 reference numbers
  and frozen v3 definitions do not apply to DR1.

Ordinary `run` commands execute **zero background trials**, even if the request
YAML contains a default `background.n_trials`. The separate, restricted
[empirical workflow](dr2_empirical_scrambling.md) must not be presented as general
calibration for a user's catalog or these single-source/scan examples.

New DR2 single-source tasks and individual catalog fits default to a source-centered
declination window: minimum half-width 20 degrees and at least 20% of each
dataset. Use `--full-sky-events` at task creation for all events, or
`--source-dec-window-deg 30` for a larger minimum half-width. The stack part of
`scan_and_stack` retains its existing event selection. Scans reuse complete
loaded data and validated PDF tables. [Settings and limitations](single_source_performance.md).

### Fixed-spectrum flux limits

After the user-authorized second stage, the single-source and joint-stack examples write limits for E^-2, E^-2.5 and E^-3 and reference-spectrum figures. Add `--no-flux-upper-limits` when creating a task to omit these extra fits. Scans omit them by default; add `--flux-upper-limits` to `create-catalog --catalog-operation scan` or `scan_and_stack` when per-source limits and figures are wanted. See [definitions and limitations](flux_upper_limits.md).
