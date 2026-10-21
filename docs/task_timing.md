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

## Cost-aware remaining time during a joint stacking fit

An optimizer call is not a uniform amount of work. The observer compares the
existing source-weighted PDF cache keys before and after each unchanged call:
`cold_start` identifies the first call, `pdf_recomputed` identifies a changed key,
and `pdf_reused` identifies an unchanged key. It does not change caching,
likelihood evaluation, optimizer settings, bounds, seeds or stopping conditions.

Reviewed converged runs with matching ordered coordinates/weights, scientific
settings, input hashes and package versions can supply call-count references.
Version-2 traces additionally record each call's cost class and duration.
Only traces from the same host, machine and thread environment supply speeds.
Their already-recorded cost sequences forecast the remaining work; the median
of current/reference duration ratios within each cost class rescales its speed.
Cached calls therefore cannot reduce the estimated cost of future full-PDF calls.
If the current class sequence diverges, its sequence template is rejected.
Legacy count-only references use measured full-PDF speed as a coarse fallback.

There are no arbitrary 32/12-call defaults or half-to-1.5-budget intervals.
An unknown optimizer stopping count stays unknown without a comparable completed
fit. If a forecast becomes overdue or reaches the reference endpoint while the
optimizer is active, the ETA becomes unavailable with an explicit reason; it
does not count down to an artificial positive floor or imply completion.

`fit_timing` in the result records cost classes, durations, completion times,
reference reports and forecasts made while the fit was active. After completion,
each forecast is compared with the actual remaining fit time. Signed error is
`predicted remaining seconds - actual remaining seconds`; positive means the
prediction was too long. Summary fields include mean/median absolute error,
90th-percentile absolute error and signed bias. No current run's future is used
for a live forecast. A displayed interval needs at least three independent prior
error histories; it uses their 90th-percentile absolute errors and is an empirical
error band, not a confidence interval or guaranteed bound.

## Named stages and total remaining time

AnalysisAgent records request preparation, numerical analysis, output generation
(including figures) and scientific review separately. Subphases identify input
loading/analysis setup, saved-primary likelihood reconstruction/verification and
fixed-spectrum likelihood profiling. The existing per-spectrum completion counts
remain available. Primary and flux stages are separate user-authorized turns.

Events include `current_stage`, `stage_elapsed_seconds`, `stage_remaining_seconds`,
`pending_stages` and `request_remaining_seconds`. Exact normalized settings, input
hashes, host/thread environment and primary/flux mode must match for stage timing
history. A request ETA sums the current-stage forecast and the measured histories
of pending stages. It remains unavailable if later stages lack references; do not
add an invented review allowance. Stages and subphases still report their names
and actual durations during a first run without history.

The run's `timing.json` records stage durations, reference runs and whole-request
forecasts/errors through numerical execution, files and review. It does not include
initial chat latency, preflight outside AnalysisAgent or final answer composition;
the chat must separately report the whole current user turn's elapsed time.

## Validation

Check prediction error on a later run whose measurements were unavailable to the
reference fit. Compare old and new forecasts at identical timestamps and report
absolute error, signed bias, coverage and numerical invariance. A successful
presence/format check alone does not validate ETA accuracy. A single held-out run
can reveal a regression but cannot establish general predictive coverage.
