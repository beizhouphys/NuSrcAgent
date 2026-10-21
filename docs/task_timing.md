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

ETA uses **only the current invocation**, never old reports, matching catalogs,
historical timing files, input-hash comparisons or stored cost sequences. There
is no history lookup or transfer of old call counts or speeds.

The optimizer does not declare how many calls remain. A clearly labelled,
uncalibrated reporting assumption starts at 24 calls for fitted Gamma or 12
for fixed Gamma. After the first completed call, the observer multiplies its
estimated remaining call count by a measured current-run call cost. The first-call estimate removes measured one-time cache construction:

`recurring call seconds = cold call seconds - retained geometry construction - compression - energy lookup construction + estimated cached-read seconds`

Only geometry for blocks successfully retained in the cache is subtracted;
uncached geometry remains recurring work when the cache budget is saturated.
Compression and energy-lookup construction use counter deltas measured within
that call. Read cost is estimated from the current compressed payloads: up to
three blocks per dataset (first, middle, last) are decompressed once, and their
median measured seconds per uncompressed byte is multiplied by cached bytes.
The probe leaves cache payloads, hits/misses and numerical values unchanged.
Its own elapsed time is recorded separately and is not charged to every future
call. No extra objective-function calculation is performed.

This corrected recurring cost supplies the first forecast. Later full-PDF calls
replace it with the median of the last eight full-PDF durations. Cached calls never enter the
full-PDF rate. Fixed-Gamma fits with only cached calls after setup use their
own measured cached-call rate. Free-Gamma fits conservatively assume future
calls can require PDF recomputation, even after a cheap cached burst.

When the assumed workload is reached, it expands by one quarter of the initial
assumption (at least three calls). An active call exceeding its predicted cost
revises that cost upward using its elapsed time; ETA remains explicitly rough
and does not count down to zero while optimization is active. Before any call
finishes, the first timing sample is pending. These assumptions never change
the actual optimizer, its call limit, parameters or stopping conditions. They
can be substantially wrong; a numerical estimate is not a completion guarantee.

`fit_timing` in the result records cost classes, durations, completion times,
first-call cost components and forecasts made while the fit was active. After completion,
each forecast is compared with the actual remaining fit time. Signed error is
`predicted remaining seconds - actual remaining seconds`; positive means the
prediction was too long. Summary fields include mean/median absolute error,
90th-percentile absolute error and signed bias. No current run's future is used
for a live forecast. No history-based error interval is calculated;
`remaining_seconds_range` stays null. Error summaries describe the completed
run and do not calibrate a confidence interval for the next run.

## Named stages and total remaining time

AnalysisAgent records request preparation, numerical analysis, output generation
(including figures) and scientific review separately. Subphases identify input
loading/analysis setup, saved-primary likelihood reconstruction/verification and
fixed-spectrum likelihood profiling. The existing per-spectrum completion counts
remain available. Primary and flux stages are separate user-authorized turns.

Events include `current_stage`, `stage_elapsed_seconds`, `stage_remaining_seconds`,
`pending_stages` and `request_remaining_seconds`. Stage timing also uses only this invocation. There is no matching of prior
settings, inputs or environments. A fit-only forecast is not a whole-request
forecast: when later output/review stages have no current measurement, report
the fit ETA explicitly and identify the unestimated later stages. Do not invent
a fixed review allowance. Stages and subphases retain actual elapsed times.

The run's `timing.json` records stage durations, reference runs and whole-request
forecasts/errors through numerical execution, files and review. It does not include
initial chat latency, preflight outside AnalysisAgent or final answer composition;
the chat must separately report the whole current user turn's elapsed time.

## Validation

Run a fresh catalog through the real wrapper without a reference run. Verify
numerical rough ETA coverage after the first completed call, then compare each
prediction with actual remaining time. Report mean/median absolute error,
90th-percentile absolute error and signed bias. Verify observer and stage
construction cannot read historical run directories. Check scientific-call
invariance separately. Presence of a numerical ETA does not establish accuracy,
and one catalog does not establish general predictive coverage.
