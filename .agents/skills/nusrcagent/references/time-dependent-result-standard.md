# Fixed-window time-dependent result standard

This presentation contract applies only to reviewed DR2 tasks with
`scope=per_source_catalog_windows`. It does not change task creation,
clarification, likelihood construction, fitting, trial authorization,
scrambling, checkpointing, scientific review, or time-independent output.

## When to render

- An observed-only fit remains preliminary. Report its fitted quantities and
  unavailable empirical calibration through the existing NuSrcAgent artifacts.
- Start matched background trials only after the user explicitly requests them
  with an agreed fixed count.
- Build the standard result bundle only after the full recorded ensemble is
  complete. Require the reviewed baseline, all observed and trial fits, finite
  TS/ns values, the requested trial count, unique seeds, and contiguous indices.
- On any failed check, retain diagnostic artifacts, identify the failure, and do
  not render or claim a successful standard result.

Explicit `legacy_time_profile` Gaussian/box searches retain their existing
NuSrcAgent presentation because matched background calibration is unavailable.

## Saved artifacts

Completed ensembles are finalized below the trial output directory in
`standard_results/`. The directory contains `inputs.json`, `validation.json`,
`analysis_summary.json`, `report.md`, observed JSON/NPZ/source manifest,
one merged background JSON/NPZ/source manifest, applicable `single_src/` and
`stacking/` numerical products, and `standardized_report/` figures plus
`plot_manifest.json`.

The numerical bundle is produced by
`agent_core.time_dependent_standard_results`; it does not repeat maximization
or any background trial. For fitted Gamma it evaluates the immutable observed
likelihood on the saved contour grid as specified below. Figures are rendered internally with
`scripts/plot_time_dependent_standard_report.py`. The public analysis interface
remains `run_agent_wrap.py`.

The source timeline uses an explicitly recorded physical time anchor when one
exists. Otherwise it uses the fixed-window midpoint and records
`time_anchor_definition=fixed_window_midpoint` in machine-readable products.

NuSrcAgent does not apply time-integrated asymptotic significance formulas to
time-dependent fits. The standard plots therefore use the matched scrambled
distribution as their null calibration and omit analytic half-chi-square
overlays unless a future reviewed workflow explicitly authorizes them.

For a fitted-Gamma analysis, reconstruct the immutable reviewed observed
likelihood after the shared trials identify the leading source. Evaluate and
save the leading-source and applicable stacking surfaces before rendering. Each
`*_likelihood_contour.npz` must contain `ns`, `gamma`, `log_lambda`,
`minus_2_delta_log_likelihood`, `native_gamma`, phase selected/event counts,
and the saved best-fit `ns`, Gamma and TS. Validate that the evaluated surface
reproduces the saved MLE and TS. A missing, mismatched or nonfinite required
surface fails the standard-result validation gate; retain diagnostics and do
not issue the polished presentation. Fixed-Gamma analyses do not create a
two-dimensional surface.

Never fabricate a surface or call likelihood-drop contours calibrated
confidence regions. At `ns=0`, save and plot the Gamma-independent maximum
ridge and report Gamma as unidentified.

Match the time-integrated notation in all human-facing products: write `Gamma`
in prose and render the positive spectral index as `\Gamma` in equations,
titles, legends and axes, with `dN/dE` proportional to `E^{-\Gamma}`. The
lowercase `gamma` spelling is reserved for existing CLI/API/JSON/NPZ field names
and does not denote a different or signed parameter.

## User-facing result

For a validated completed ensemble, lead with the Gamma treatment and number of
background trials. Present a two-column table containing the leading source,
best fit, add-one local p-value and exceedances, Sidak post-trial result,
empirical shared-trial maximum-TS result, and weighted-stack result when those
components apply. Treat empirical maximum TS as the primary catalog-wide scan
calibration.

Immediately state validation and NuSrcAgent review status, requested/produced
trial counts, seed uniqueness, index contiguity, and material inherited
warnings. Preserve the existing fixed-N Monte Carlo intervals. For `p=1`, say
"no excess" instead of displaying negative-infinite significance.

Embed the applicable standardized PNG figures and link their PDFs, numerical
tables, `report.md`, `analysis_summary.json`, `validation.json`, and plot
manifest. Scan-only, stack-only, and single-source tasks show only the relevant
components.
