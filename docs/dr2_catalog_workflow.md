# Fitting individual catalog sources and their combined emission

A source catalog is a table of candidate objects and their sky coordinates.
A scan asks whether each object has an individual neutrino excess; a stack asks
whether their combined emission is favored under a specified weighting model.
These are different statistical hypotheses, so their TS values need not agree.

## Choose the analysis

Use `stack` for a joint fit, `scan` for independent fits of every catalog row,
or `scan_and_stack` for both. A scan fits each source's own `n` and, in the
default spatial+energy analysis, its own `s`. A stack fits one total `n`
and one common `spectral index` for the catalog.

`create-catalog --catalog-operation stack|scan|scan_and_stack` selects the
requested operation. Scan-only requires no intrinsic stacking weights.
Stacking weights must identify the intended physical quantity or be explicitly
uniform/manual; a common unknown multiplicative unit cancels on normalization.
Intrinsic weights specify the relative source contributions assumed before
applying detector acceptance. Uniform intrinsic weights are equal model weights,
not equal expected detected event counts. If using a measured source quantity,
identify which column it is and what it represents; the software does not know
the physical meaning of an arbitrary numeric column.

## Read the source and stacking tables

The scan uses identical single-source LLH settings for each input source and
writes input-ordered `source_results.csv`. Per-source fit details are nested in
`report.yaml`, source review checks in `review.json`, with run-level input and
configuration provenance in `provenance.yaml`; separate per-source directories
are not required. `scan_and_stack` additionally writes `fit_results.csv` for the stack.
Both spatial+energy and spatial-only use the same supported DR2 backend.
The general scan reuses complete loaded inputs and validated PDF tables; each source gets its own selected event sample. See [individual-source settings](single_source_performance.md).

Use `source_results.csv` for the individual-source results, and
`fit_results.csv` for the joint stack when requested. Open `report.md` and
`review.md` first for a readable account of the fit and its warnings. Provenance
means the saved record of data/code versions and settings used in that calculation.

## Significance and example inputs

Ordinary time-integrated local p-values and significances are estimates: half-chi-square dof=2
for fitted spectral index and dof=1 for fixed spectral index. The source CSV records the method,
dof and estimate flag alongside each result. An analytic independent-source catalog correction is reported; no empirical
catalog post-trial significance is produced. The excluded 3386-source reproduction
workflow's six stacks, signed fits and paper comparison products are not
implicitly invoked by this general scan.
A local p-value refers to one specified source hypothesis. Selecting the most
interesting source after scanning a catalog introduces a search over sources;
that search must also be repeated in the background trials used for a global
significance. A table of local approximations does not perform that calibration.

The [three-row example](../configs/examples/catalog_sources_example.csv)
contains public source coordinates and illustrative relative radio weights.
Use `--name-column name --ra-column ra_deg --dec-column dec_deg`.
The [quickstart](quickstart.md) gives a complete uniform-weight scan+stack
command and its observed numerical outputs; [column metadata](../configs/examples/README.md)
explains which values are illustrative.
The selected 3386-source radio-bright AGN CSV is bundled in
`data_input/sources/`; use it with `--catalog`. The optional built-in reader
instead requires the original raw RFC file, which is not bundled. See the
[catalog notes](../data_input/sources/README.md) for columns, selection and attribution.

New DR2 single-source tasks and individual catalog fits default to a source-centered
declination window: minimum half-width 20 degrees and at least 20% of each
dataset. Use `--full-sky-events` at task creation for all events, or
`--source-dec-window-deg 30` for a larger minimum half-width. The stack part of
`scan_and_stack` retains its existing event selection. Scans reuse complete
loaded data and validated PDF tables. [Settings and limitations](single_source_performance.md).

## Fixed-spectrum point-source flux limits, 2026-10-19

New DR2 spatial+energy single-source tasks default to three separate fixed-spectrum fits (E^-2, E^-2.5, E^-3), preliminary one-sided 95% profile-likelihood upper limits, and a spectrum figure with published NGC 1068 and diffuse bands. Catalog scans keep these per-source outputs opt-in with `--flux-upper-limits`; stacking retains its existing definition. Coverage and detector/PDF systematics remain unvalidated/excluded. Historical tasks retain their recorded definitions. See [flux-limit definitions and plotting conventions](flux_upper_limits.md).

## Catalog scan reporting

For each completed DR2 scan, the default report and the wrapper's
`catalog_scan_summary.chat_table` show the five most significant sources (or
all sources when fewer than five). Use that compact monospaced table in the
chat response. It separates local/global **p value** and **significance**
columns and puts `σ` in significance cells. The CSV stays in input order and
adds a significance rank. Do not report failed-review results as valid.

The analytic catalog estimate follows [Sec. IV A of arXiv:2103.12813](https://arxiv.org/pdf/2103.12813):
`p_global = 1 - (1 - p_local)^N_sources`, using every selected source,
including TS=0 fits, rather than just the five displayed sources. It assumes
independent source tests; nearby source hypotheses can be correlated.
This correction covers the selected catalog only. It does not include extra
catalog selections, weighting or spectral hypotheses, and does not correct
the separate joint stacking fit. It is not empirical calibration.

The CSV's `post_trial_significance` retains signed `Phi^-1(1-p_global)`;
`post_trial_excess_significance` is `max(0, Z)` for the paper Table I display.
`post_trial_p_approx`, `post_trial_method` and `post_trial_n_sources` record
the probability, approximation and source count. The report also records the
best selected source threshold as `catalog_post_trial_p`, with its signed
`catalog_post_trial_significance` and explicit `catalog_post_trial_method`;
this is the source scan result, not the joint stacking significance. Local dof and method labels
remain recorded. At n=0, spectral index is not a spectral measurement.

Each scan also writes `sqrt_ts_distribution_bins.csv` and PDF/PNG
figures under `figures/<run_id>/`, with bin width 0.25, counts on a logarithmic
axis and sqrt(N) error bars, following Fig. 3. All selected sources, including
TS=0, enter the histogram. Empty bins remain in the numeric table; zero lower
error endpoints are clipped only in the logarithmic drawing. No normal
distribution is fitted. For fitted spectral index, sqrt(TS) is a plotting coordinate,
not the local Gaussian significance. The review checks the correction,
ranking, histogram counts and figure hashes. Historical run artifacts are
not rewritten and retain their original review requirements.

## Independent fit procedure for source scans

New DR2 `scan` and the individual-source part of `scan_and_stack` explicitly
record `scan_fit_procedure=skyllh_lbfgs_v1` in the task, request and normalized
configuration. This is the original SkyLLH optimizer, without an additional
search over every spectral-index interpolation interval and stencil switch. The
separate single-source and joint stacking settings are preserved. The backend
passes the recorded scan procedure explicitly and review rejects an absent or
different procedure declaration, or an extra maximum search under the original-optimizer label.

The CLI records this through a dedicated catalog-default helper, independently
of single-source flux-reporting defaults. Loading, showing or recovering a
historical task never injects this new default. A historical task without the
field retains its supported recorded procedure, with the original optimizer
as the fallback when no procedure was recorded. Stopped tasks are not restarted.
No coordinates, catalog membership, PDFs, spectral hypotheses, optimizer
bounds or background-trial settings are changed by this recording safeguard.

## Exact stacking PDF caches

Multi-source DR2 spatial+energy fits use exact observed-energy interpolation
lookups with a 16 MiB payload limit per dataset. Fitted-index stacks additionally
share a lossless spatial PDF block cache with a 1 GiB compressed-payload limit
per fit. Cache misses and exhausted budgets use the original calculation.
New trials invalidate the previous geometry and energy lookups. This preserves
event/source membership, weights at the current spectral index, three-node spectral-index interpolation,
its derivative and weighted reduction order. It changes no CPU configuration
or recorded optimizer procedure.

Use the ordinary create/READY/run/review sequence. Inspect
`working_set.datasets.<dataset>.spatial_cache` and
`energy_interpolation_cache` in `report.yaml` when checking runtime.
See [stacking performance](stacking_performance.md) for memory accounting
and bitwise verification requirements.

## Joint-stack flux output

New DR2 spatial+energy joint stacks use separate, recorded stacking flux settings.
The primary result is reviewed and reported in a final answer. The Agent asks
whether to continue and ends that turn. Only after the user replies does the same
task continue with `run --task <id> --stage flux --flux-user-reply "<actual user reply>"`. Three fixed-spectrum 95% limits are default;
upper-limit spectrum figures are generated and reported regardless of primary
TS. Primary TS > 9 additionally enables measured intensity and its uncertainty.
Individual scan limits
remain opt-in. See [stacking flux and two-stage reporting](stacking_flux.md).

## Time-dependent catalog scans

DR2 single-source analysis and independent catalog scans also support explicit
Gaussian/box time profiles. Supplied t0/width are fixed unless explicitly used
as fit seeds; omitted parameters require bounds, seeds and search settings
before READY. These scans write time_dependent_results.csv, temporal search
traces and profile figures, with unavailable p-values/significances. They do
not use the time-integrated analytic formulas or catalog correction above.
Time-dependent stacking awaits collaborator code; time-dependent background
trials await owner approval. See [the guide](time_dependent.md).
