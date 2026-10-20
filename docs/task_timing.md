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
