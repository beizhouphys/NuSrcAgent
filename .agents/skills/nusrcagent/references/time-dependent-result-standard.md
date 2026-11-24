# Fixed-window time-dependent result standard

This presentation contract applies only to reviewed DR2 tasks with
`scope=per_source_catalog_windows`. It does not change task creation,
clarification, likelihood construction, fitting, trial authorization,
scrambling, checkpointing, scientific review, or time-independent output.

## When to render

- An observed-only fit remains preliminary. Report its fitted quantities and
  unavailable empirical calibration through the existing NuSrcAgent artifacts.
  For fitted s, evaluate and validate the immutable observed likelihood for
  the top three observed-TS sources (or all sources when fewer than three) and
  the applicable stack, then render their contour figures before offering
  background trials. This does not create the post-trial standard result bundle.
- Start matched background trials only after the user explicitly requests them
  with an agreed fixed count.
- Build the standard result bundle only after the full recorded ensemble is
  complete. Require the reviewed baseline, all observed and trial fits, finite
  TS/ns values, the requested trial count, unique seeds, and contiguous indices.
- On any failed check, retain diagnostic artifacts, identify the failure, and do
  not render or claim a successful standard result.

Explicit `legacy_time_profile` Gaussian/box searches retain their existing
NuSrcAgent presentation because matched background calibration is unavailable.

## Required all-source timeline after background trials

After every complete, validated fixed-profile background ensemble, generate
and embed the all-source pre-trial/post-trial p-value-versus-year PNG in the
final answer, with IceCube detector-phase labels. Link its PDF and full source
data table; a saved artifact or link alone does not satisfy the display rule.
Include all selected sources, including those with TS=0 and p=1. This applies
to standalone, scan, stack and scan_and_stack tasks. A stack-only label does
not exclude the supporting individual-source fits from this presentation.

Use the saved source fits and shared trial statistics. The upper panel shows
add-one empirical local p-values; the lower panel defaults to the response-phase
Sidak correction described below and must identify it as an analytic
multiplicity approximation. Show calendar years, use box stop or Gaussian
center as the time coordinate, and keep the empirical shared-trial maximum-TS
correction available separately. Preserve Monte Carlo precision and inherited
fit warnings. Do not substitute the stacking p-value for source p-values.

If normal reporting omits the timeline or fails for a stack-only task, inspect
the observed source results and saved trial arrays before concluding that
source calibration is unavailable. Verify matching source order, valid fits,
complete trial count and seed/index integrity. For existing ensembles with
saved source fits, use the public output-only recovery command:

```bash
.venv/bin/python run_agent_wrap.py td-background-trials --action report \
  --output-directory <completed-trial-directory> \
  --source-diagnostics-directory <new-report-directory>
```

This uses the canonical adapter and renderer, preserves the original ensemble
and any partial report, and validates required likelihood surfaces without
repeating maximization or trials. Keep execution/resume identity checks intact;
the reporting command records allowed reporting-code revisions and rejects
numerical-code, package, baseline or input changes. Inspect its validation and
plot manifest, then verify that the displayed timeline contains every source.
Do not create a new observed task, relabel the recorded scientific operation,
or rerun trials merely to expose existing source results. If source statistics
are actually missing or invalid, report the specific blocker and retain the
scientific validation gate; never fabricate the timeline or silently omit it.

## Saved artifacts

Completed ensembles are finalized below the trial output directory in
`standard_results/`. The directory contains `inputs.json`, `validation.json`,
`analysis_summary.json`, `report.md`, observed JSON/NPZ/source manifest,
one merged background JSON/NPZ/source manifest, applicable `single_src/` and
`stacking/` numerical products, and `standardized_report/` figures plus
`plot_manifest.json`.

The numerical bundle is produced by
`agent_core.time_dependent_standard_results`; it does not repeat maximization
or any background trial. For fitted s it evaluates the immutable observed
likelihood on the saved contour grid as specified below. Figures are rendered internally with
`agent_core/plot_time_dependent_standard_report.py`. The public analysis interface
remains `run_agent_wrap.py`.

The default source timeline uses the box stop or Gaussian center for its time
coordinate. Its lower panel displays the response-phase Sidak estimate
`1 - (1 - p_pre)**N_phase`, using the saved joint-fit local p-value. Count all
selected IC86 I–XI seasons as one detector-response phase. If an anchor falls
outside every selected response period, use a sole fixed-window overlap and
record that assignment; ambiguous assignments fail. Preserve the empirical
shared-trial maximum-TS result separately as the full-scan calibration.

NuSrcAgent does not apply time-integrated asymptotic significance formulas to
time-dependent fits. Local source and stacking p-values, and the empirical
catalog-maximum result, use the matched scrambled distributions. The default
timeline's response-phase Sidak series is explicitly an analytic multiplicity
estimate of those local p-values; it is not a background-trial calibration of
the phase-restricted or full-catalog maximum. Omit analytic half-chi-square
overlays unless a future reviewed workflow explicitly authorizes them.

For a fitted-s analysis, the observed stage reconstructs the immutable
reviewed likelihood and saves surfaces for the top observed-TS sources and the
applicable stack. After trials, the standard bundle may reconstruct the
empirical leading-source and applicable stacking surfaces for its calibrated
presentation. Each
`*_likelihood_contour.npz` must contain `ns`, `gamma`, `log_lambda`,
`minus_2_delta_log_likelihood`, `native_gamma`, phase selected/event counts,
and the saved best-fit `ns`, s and TS. Validate that the evaluated surface
reproduces the saved MLE and TS. A missing, mismatched or nonfinite required
surface fails the standard-result validation gate; retain diagnostics and do
not issue the polished presentation. Fixed-s analyses do not create a
two-dimensional surface.

Never fabricate a surface or call likelihood-drop contours calibrated
confidence regions. At `ns=0`, save and plot the s-independent maximum
ridge and report s as unidentified.

Match the time-integrated notation in all human-facing products: write `s`
in prose and render the positive spectral index as `s` in equations,
titles, legends and axes, with `dN/dE` proportional to `E^{-s}`. The
lowercase `gamma` spelling is reserved for existing CLI/API/JSON/NPZ field names
and does not denote a different or signed parameter.

## User-facing result

For a validated completed ensemble, lead with the s treatment and number of
background trials. Present a two-column table containing the leading source,
best fit, add-one local p-value and exceedances, default response-phase Sidak post-trial result,
empirical shared-trial maximum-TS result, and weighted-stack result when those
components apply. Treat empirical maximum TS as the primary catalog-wide scan
calibration.

Immediately state validation and NuSrcAgent review status, requested/produced
trial counts, seed uniqueness, index contiguity, and material inherited
warnings. Preserve the existing fixed-N Monte Carlo intervals. For `p=1`, say
"no excess" instead of displaying negative-infinite significance.

Embed the applicable standardized PNG figures and link their PDFs, numerical
tables, `report.md`, `analysis_summary.json`, `validation.json`, and plot
manifest. All tasks display the required all-source timeline above; other
figures follow the hypotheses whose statistics were computed and validated.
