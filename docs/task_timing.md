# Progress and elapsed time

Every project task reports an estimate of time remaining in its chat progress
updates. The estimate uses comparable completed work from the current invocation:

`remaining seconds = elapsed seconds for completed units / completed units × remaining units`

For 100 of 1000 source fits completed in 60 seconds, the source-fit phase has
about 540 seconds remaining (600 seconds total). An estimate for one phase does
not include unmeasured later stacking, figures or review. Estimates are refreshed
when more units finish; the fit procedure, worker configuration and work size
can affect the rate. Restored checkpoints are excluded from new timing samples.
Before a first usable sample, a reliable estimate is pending. Continuous trials
without a target have no scheduled end time. Neither case changes the analysis.

The public wrapper writes `NuSrcAgent progress:` JSON events to stderr at start,
at completed units and every 30 seconds while running. Its stdout response keeps
its existing JSON structure and adds `execution_timing` with `elapsed_seconds`,
`remaining_seconds` (null if unknown), `estimate_status`, and
`report_total_duration`. Sampled phases also include `phase`, `completed_units`,
`total_units`, `phase_elapsed_seconds`, `estimate_age_seconds` and
`estimate_scope=current_phase_only`. The elapsed time uses a monotonic wall clock.
The terminal stderr event records time through command termination, including
failure or interruption. Each phase starts its own rate sample; no fit inputs,
likelihood evaluation, optimizer settings or numerical results are changed.

The Agent translates this metadata into a readable progress update. For work
outside the wrapper (including coding, plotting and verification), it estimates
remaining time from completed work where possible, or gives a labelled rough
range or an explicit reason why an estimate is unavailable. The final chat answer
includes the whole current request's elapsed time only when it exceeds 60 seconds.
This includes unsuccessful work. Time waiting for a later user reply is excluded;
primary and authorized flux stages report the duration of their respective turns.
The last command's duration must not substitute for the whole request's duration.

## Remaining time during a joint stacking fit

After its first completed objective evaluation, a multi-source DR2 stacking fit
reports a numeric, explicitly rough ETA while the optimizer is running. The
current rolling evaluation duration is multiplied by the estimated number of
remaining evaluations. The first cold-cache evaluation is excluded once warm
samples exist; a long in-flight evaluation also revises the speed estimate.

The evaluation-count prior is the median of up to five reviewed converged local
fits with the same ordered coordinates/weights, fit seeds/bounds, random seed,
event selection/counts, PDF settings, input hashes and NumPy/SciPy/SkyLLH versions.
Only historical evaluation counts are used, never historical speed. Without a
match, the initial heuristic budget is 32 evaluations for fitted Gamma or 12 for
fixed Gamma. An exceeded budget is extended; it is never an optimizer limit.

Events have `phase=joint stacking fit`, `estimate_scope=stacking_fit_only`,
`completed_evaluations`, `estimated_total_evaluations`, `remaining_seconds` and
`remaining_seconds_range`. The range uses half to 1.5 times the revisable call
budget and current speed; it is a heuristic range, not a statistical confidence
interval. Do not describe the budget as a known endpoint or convert it into a
completion percentage. Artifacts and review require additional time. The final
report's `fit_timing` records evaluation durations and reference reports.

Timing wraps each unchanged objective call once and forwards its return value
without modification. SkyLLH retains its own optimizer defaults, bounds, stopping
conditions, trial procedure and numerical results. A failed evaluation propagates
its original exception and is not counted as completed work.
