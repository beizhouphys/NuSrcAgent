---
name: nusrcagent
description: Coordinate supported IceCube time-integrated single-source searches, catalog scans and stacking through persistent tasks and scientific review.
---

# NuSrcAgent

Use the repository wrapper for every analysis. Read `AGENTS.md` and
`docs/scientific_status.md`; numerical success does not establish scientific validity.


## Progress estimates and final elapsed time

For every project task, record wall-clock time from the current user request.
Include a remaining-time estimate in every progress update, using completed
comparable work under the current fit procedure and worker configuration:
`remaining = completed_work_seconds / completed_units * remaining_units`.
For example, 100 of 1000 sources in 60 seconds predicts another 540 seconds.
Update the estimate as work completes and label a phase-only estimate as such;
allow separately for later stacking, artifacts and review. Never count restored
checkpoints as newly timed work. Read `NuSrcAgent progress:` stderr events and
`execution_timing` in wrapper JSON; translate these into natural chat updates.
During a joint stacking fit, read `remaining_seconds`, `estimate_basis`,
`cost_class_counts`, `uses_history` and `estimate_quality`. The observer separates
the cold first call, PDF recomputation and cached-PDF calls from actual cache
state. Read `cold_call_cost`: the first forecast subtracts measured one-time
cache construction and adds a read-cost probe of this run's cached payloads.
Never multiply the whole cold-call duration by future calls. Only retained
geometry is subtracted; uncached work remains in recurring cost. The probe's
own time is recorded separately. Later full-PDF samples replace the first
estimate. Only current measurements update cost; the assumed remaining call
count is explicitly uncertain. Do not treat cheap calls as full likelihood timings.
Use `current_stage`, `stage_remaining_seconds`, `request_remaining_seconds` and
`pending_stages` to distinguish preparation, numerical analysis, output/figures
and scientific review. Named subphases identify input loading, saved-primary
reconstruction and fixed-spectrum profiles. A fit-only ETA excludes later stages;
only quote a whole-request ETA when its field is available.
That request field covers AnalysisAgent execution through review; initial chat
setup and composing the final answer require additional time.
ETA must use only the current invocation. Never load old run reports, matching
catalog records, past timing files or reference speed/work counts to estimate it.
After the first completed evaluation, always quote the supplied numerical ETA
in chat as a rough fit-only estimate, even for a brand-new catalog. Do not
replace it with repeated "unknown" because optimizer stopping time is uncertain.
Explain that the workload begins with an uncalibrated reporting assumption:
24 calls for fitted Gamma or 12 for fixed Gamma. This assumption expands when
reached and never limits the optimizer. Current full-PDF and cached-call timings
remain separate; a cached burst cannot replace the full-PDF rate. An overdue
active call revises its assumed cost upward rather than suppressing ETA.
Before the first completed call, explain that the initial timing sample is
pending. Do not invent a historical reference, confidence interval, fixed review
allowance or whole-request ETA when only fit timing is measured.
Do not invent an interval: `remaining_seconds_range` remains absent. Completed
fits record forecasts made before completion and their actual errors for audit;
these errors never become reference inputs to later ETA forecasts.
Before a usable sample exists, state that a reliable estimate is pending. For
unbounded continuous scrambling, state that no end time is set; never add a
trial target or stop condition for reporting. Other work, including inspection,
code changes, plotting and verification, follows the same chat rule; give a
clearly labelled rough range based on completed work or explain why unknown.
In each final answer, include total elapsed wall-clock time only when it strictly
exceeds 60 seconds, including unsuccessful requests. Measure the whole current
request, not just its last command; exclude waiting for a later user reply.
The primary and user-authorized flux turns each report their own duration.

## Required first-turn result boundary

For single-source and joint stacking analyses with supported/requested flux
products, the first turn ends with a FINAL ANSWER containing the reviewed primary ns/Gamma, TS, p value and significance,
followed by a question asking whether to calculate flux products. Leave
AWAITING_FLUX pending. Do not run flux in this turn or replace this final answer
with commentary. Only a subsequent affirmative user reply authorizes stage 2;
pass the actual reply with --flux-user-reply and report flux/figures in that
later turn's final answer. This supersedes earlier automatic-continuation rules.

## Response language

- Follow the user's explicit language request. Otherwise, honor an explicitly
  established personal response-language preference.
- If neither applies, follow the language of the current request.
- If there is no preference or usable language cue, including a bare
  `$nusrcagent` invocation, respond in English.
- Do not infer a response-language preference from the language used to write
  `AGENTS.md`, skill instructions or other repository files.

## Clarification policy

Ask only about unresolved ambiguity that materially changes the spectrum,
relative weights, source/event membership, fit hypotheses or trial family.
Unsigned gamma 2.53 conventionally means E^-2.53; record that interpretation
and pass CLI `--gamma -2.53`. A bare explicit positive sign needs clarification;
preserve a power-law exponent explicitly defined by the user.
A unique column identifying requested flux/relative weights may be used with
recorded metadata. A common unknown multiplicative unit cancels in normalized
weights. Do not invent absolute units or drop invalid rows.
The example's radio_weight is an illustrative relative proxy, not a measured flux.

Record interpretations with repeatable
`--interpretation-note PARAMETER=EXPLANATION`; never pretend these are user
confirmations. Supplied spectral indices are fixed unless fitting is requested.

## Execution

1. Work from this checkout root with its pinned `.venv/bin/python`.
   Run `run_agent_wrap.py environment-check` for the selected sample/mode.
   Stop on failed preflight and explain missing inputs/dependencies.
2. Exactly one source selects single-source analysis. DR2 catalogs select
   `--catalog-operation stack|scan|scan_and_stack`; scan-only needs no weights.
   DR1 retains its existing scan+stack behavior.
3. Approved DR2 defaults: full14 spatial+energy, fitted ns and Gamma, seed
   CLI -3.0 / SkyLLH 3.0. Spatial-only fixes acceptance Gamma at CLI -2.5;
   it does not measure the source spectrum. Select DR1 only when requested.
4. Persist the request through `create-single` or `create-catalog`. Use
   `confirm` only for actual user answers. Run only tasks whose state is READY.

```bash
.venv/bin/python run_agent_wrap.py create-single --request "<request>" --name "<source>" --ra-deg <ra> --dec-deg <dec>
.venv/bin/python run_agent_wrap.py create-catalog --request "<request>" --catalog <catalog.csv> --catalog-operation scan_and_stack --weight-mode uniform
.venv/bin/python run_agent_wrap.py run --task <task_id>
```

Use explicit column options for a catalog. The three-row example uses
`--name-column name --ra-column ra_deg --dec-column dec_deg`.
For the distributed RFC 2019c radio-bright AGN sample, use
`create-catalog --catalog data_input/sources/radio_bright_agn_rfc2019c_xband_ge_0p15_dec_lt87_3386.csv`,
with `source_name`, `ra_deg`, `dec_deg` and, when requested, `xband_flux_jy`.
The selected CSV is bundled; the optional `--built-in-catalog` reader still
requires the separate original raw RFC input. Do not select that reader for
ordinary requests to use the bundled CSV.

5. Read the central task's `agent_review.json` and the run's `review.json` /
   `review.md`. Report every material warning. Never present failed-review
   numerical output as valid. If necessary, use `review-run`.
6. Inspect the expected tables, configuration, provenance and output artifacts.
   DR2 produces numeric reports and reviews; DR1 additionally has figures and
   optional workbook generation. Do not require unavailable DR2 workbook output.
7. Only dependency, transient I/O or output-generation failures may retry once
   with an unchanged request hash. Never repair scientific settings automatically.

## Follow-up analysis

`inspect-catalog` inspects inputs. `dominance` and `review-dominance` examine
source influence in a reviewed fitted-Gamma stack. Delta TS from deleting sources
is not source-detection significance.

`dr2-ra-scramble` is a fixed-Gamma smoke test, not empirical calibration.
`dr2-empirical-scramble` has the limited existing random-catalog stack scope
described in `docs/dr2_empirical_scrambling.md`; do not promise calibration for
arbitrary user catalogs or individual-source scans. Agree the trial family,
count, seeds and stopping strategy before any background trials. Negative-TS
discarding requires scientific review. Time-dependent trials are unsupported.

## Reporting

Report fitted quantities, TS, p-value and the corresponding significance together.
Use the one-sided Gaussian convention `Z = Phi^-1(1 - p)` in sigma and label
local/pre-trial versus post-trial and analytic versus empirical values. For ordinary local estimates, use half-chi-square dof=2 when Gamma is
free (`gamma_mode=fitted`) and dof=1 when Gamma is fixed. With `TS > 0`, use
`p = 0.5 exp(-TS/2)` for dof=2 or `p = 0.5 erfc(sqrt(TS/2))` for dof=1.
Always convert with `Z = Phi^-1(1-p)`; `Z = sqrt(TS)` applies only to dof=1.
At `TS=0`, retain the reporting convention `p=0.5`, `Z=0`.
Label both p-value and significance as estimates, record the dof and method,
and do not claim empirical calibration or a verified asymptotic distribution
for free Gamma. Do not apply these formulas to empirical or catalog-corrected
p-values or to a search across several fixed-Gamma hypotheses.
Unavailable post-trial quantities must remain unavailable.

Ordinary fits execute zero background trials. Record the requested and executed
counts and the analytic method as information, without creating a warning solely
for absent trials, analytic local calibration or unavailable empirical/post-trial
values. When all other checks pass, return `COMPLETED`. Actual fit-quality,
input or artifact warnings still produce `COMPLETED_WITH_WARNINGS`; `COMPLETED`
does not by itself establish a calibrated detection or publication readiness.

Use TS after likelihood maximization. Distinguish analytic local approximations
from empirically calibrated values and catalog-global quantities. Report the data
sample, likelihood mode, source count, weights, fitted/fixed Gamma, ns, TS, p-value and one-sided significance,
review status, artifacts and limitations. Include signed relative difference
before signed absolute difference in comparisons.

See [task interface](references/agent-task-interface.md) and
[scientific review policy](references/scientific-review-policy.md).

## Individual-source performance settings

New DR2 single-source tasks and individual catalog fits use a source-centered
declination window with minimum half-width 20 degrees, expanded until every
dataset retains at least 20% of its full sample. This is recorded at task
creation. Explicit event cuts keep their own rules; `--full-sky-events` requests
all events, and `--source-dec-window-deg` selects a larger minimum half-width.
The stack part of `scan_and_stack` retains its recorded event selection.
Scans reuse complete data and validated PDF tables; they never reuse another
source's event mask or fitted state. See `docs/single_source_performance.md`.
Do not change the event selection of historical tasks or background ensembles.

## Fixed-spectrum flux upper limits and reference-spectrum figures

New DR2 spatial+energy single-source tasks default to separate E^-2, E^-2.5 and E^-3 fits for preliminary one-sided 95% flux upper limits and a reference-spectrum figure. Record these defaults at task creation. The primary fit retains its requested Gamma mode. Use `--no-flux-upper-limits` if the user requests omission. Catalog scans require `--flux-upper-limits` to enable these extra fits and one figure per source; default scans omit them. For a request for a catalog flux-limit plot, enable this option and explain that large catalogs create many figures. Joint stacking has separate default flux outputs and two-stage intensity reporting, described below; DR1 and spatial-only results retain their existing procedures.

Read `docs/flux_upper_limits.md` for units, profile threshold, confidence qualifications and reference provenance. Plot the source limits, NGC 1068 and both diffuse benchmarks in one panel using common flux units, with diffuse multiplied by exactly 4*pi sr and published uncertainty bands. Do not add NGC 4151. Preserve the starting-track band CL qualification. Describe the limits as asymptotic profile-likelihood estimates; follow the default reporting policy below. A curve represents one complete fixed power-law hypothesis; do not call it a differential energy-bin limit. Review every fixed fit and its tables/figures. No background trials are performed by this feature.

## Catalog scan chat output

For completed DR2 scans, read `catalog_scan_summary` in the wrapper response
or read the compact table in `report.md`. Show its top five sources (all if fewer than five), sorted
by local significance. Copy `chat_table` into a text code block: compact
monospaced layout, grouped Local/Global headings, separate columns named
`p value` and `significance`, and `σ` in every significance cell. Do not
merge p value with significance or show only three sources. Include the
sqrt(TS) PNG inline and link the PDF and complete input-ordered CSV.

Global values are analytic estimates following arXiv:2103.12813 Sec. IV A:
`1-(1-p_local)^N_sources`, using the full selected source count. State the
independent-source approximation and absence of empirical calibration.
The table displays max(0, signed Gaussian Z), following paper Table I;
the CSV retains signed Z and the nonnegative excess display separately.
The Fig. 3-style histogram includes all selected sources and TS=0, uses
sqrt(TS), width-0.25 bins, log counts and sqrt(N) errors, and has no normal
fit. sqrt(TS) is not Gaussian significance for fitted Gamma. This source
correction does not calibrate the joint stack or extra search hypotheses.
Preserve every material fit warning; failed review blocks numerical reporting.

## Single-source TS > 9 flux measurement and default reporting

For newly created DR2 spatial+energy single-source tasks, the wrapper records
flux_measurement_ts_threshold=9 and the approved primary fit procedure.
Report the primary-spectrum flux measurement only for strict TS > 9; TS=9
and smaller do not trigger intervals or measurement figures. Retain existing
fixed-spectrum upper limits. Free-Gamma normalization intervals must profile
Gamma with its Gamma-dependent detector yield; do not freeze the best-fit
Gamma to rescale an ns error. Report 68.27% and 95% profile intervals, the
best-fit spectrum, its 68.27% joint-region envelope and flux-Gamma contours.
Fixed-Gamma primary fits provide normalization intervals at that fixed spectrum.
Use TS, local p-value and one-sided significance together; TS > 9 is the
reporting criterion, not a detection claim. Read docs/flux_measurements.md.

This measurement workflow applies to single sources, not catalog scans.
Preserve the current catalog fit procedure and the optional fixed-spectrum
upper-limit output. Historical task settings and artifacts retain their
recorded definitions. No background trials are started by this feature.

Owner-approved default reporting: do not proactively mention interpolation-
switch details, unvalidated coverage or excluded detector/PDF systematics in
answers, readable reports or figure captions. These three items alone do not
produce warnings or prevent COMPLETED; discuss them only if the user asks.
Retain truthful method flags and search diagnostics in numerical provenance.
This does not remove other fit-quality, bound-truncation, input or artifact
checks; actual failed reviews must still block valid-result reporting.

## Catalog optimizer default safeguard

For new DR2 catalog `scan` and individual fits in `scan_and_stack`, verify
`scan_fit_procedure=skyllh_lbfgs_v1` in the persistent task and analysis request.
This field is recorded by the CLI's separate catalog-default helper; it must
not depend on single-source flux-reporting or joint stacking defaults. The
backend must pass it explicitly and each source review must agree. Explain
a change of fit procedure before launching a large catalog; benchmark the
recorded procedure and worker configuration first. Do not infer runtime from
a previous scan with a different procedure. Preserve historical procedure
records, the flux-profile maximum-consistency guard and user-stopped tasks.

## Exact stacking cache workflow

DR2 multi-source spatial+energy fits automatically use exact observed-energy
interpolation lookups (16 MiB per dataset); fitted-Gamma stacks also share a
lossless spatial PDF cache (1 GiB compressed payload per fit). These are
per-process budgets plus bookkeeping/temporary arrays, not total machine limits.
They do not change scientific settings, fit procedures or CPU configuration.
Keep the existing create/READY/run/review workflow and the requested CPU budget.
New trials invalidate both caches; full budgets fall back to original formulas.
When diagnosing performance, inspect both cache records under
`working_set.datasets` in `report.yaml`, and compare PDF ratios, Gamma
derivatives and complete fit/optimizer results against the unchanged request.
Do not apply a scan's declination window to the joint stack or infer full-run
speedups from a warm-cache benchmark. See `docs/stacking_performance.md`.

## Original SkyLLH optimizer

For all newly created DR2 single-source, catalog-scan and joint stacking fits,
use `fit_procedure=skyllh_lbfgs_v1`; individual catalog fits also record
`scan_fit_procedure=skyllh_lbfgs_v1`. Do not add a Gamma-interval or
interpolation-switch maximum search. Preserve the likelihood, PDFs, bounds,
event selections and exact caches. Keep flux profiling and its maximum-consistency
guard: a profile above the recorded primary maximum fails review; do not change
the optimizer or silently replace the primary fit to repair it. Preserve historical
task records and results. Unsupported recorded procedures cannot be resumed by
substitution; create a new explicit request. Observed and corresponding trial
fits must use the same supported procedure.

## Joint-stack two-stage intensity reporting

For new DR2 time-integrated spatial+energy `stack` and joint `scan_and_stack`
tasks, the wrapper records separate `stacking_flux` defaults: 95% limits for
Gamma=2, 2.5, 3; primary measured intensity only for strict TS > 9; two-stage
reporting and catalog-total flux divided by exact 4*pi sr. Individual source
scan limits retain their separate opt-in setting. Preserve historical tasks.

1. Run the READY task normally. The primary stage performs likelihood
   maximization and review, then returns AWAITING_FLUX. Read
   `stacking_stages.primary` and its review. Before starting any joint-stack
   flux calculation, write a FINAL ANSWER chat bubble with weighting/source count, best-fit
   ns and Gamma, TS, local analytic p-value and one-sided significance, with
   estimate labels and every material warning. Failed primary review blocks
   reporting and continuation. Ask whether to continue with flux upper limits,
   applicable measurements and figures, then END THIS TURN at AWAITING_FLUX.
   A commentary progress message does not satisfy this first-stage output.
2. Only after the user replies to continue in a later turn, run the same task
   with `run --task <id> --stage flux --flux-user-reply "<actual user reply>"`.
   Preserve the actual reply; never infer it from the initial analysis request.
   If several pending tasks could match "continue", resolve them from this
   conversation; ask which task(s) only if the selection remains ambiguous. This stage
   validates the sealed primary result and unchanged request/code/inputs. It
   does not repeat primary maximization. Report the three catalog-total flux
   upper limits with their full-sky intensity equivalents. Regardless of primary
   TS, show the reviewed upper-limit PNG spectrum inline and link PDF and
   complete tables: the figure includes the three limits and two diffuse
   references even when TS <= 9. Only for primary TS > 9, also report measured
   intensity and 68.27%/95% profile intervals, add the measured spectrum and
   shading, and show fitted-Gamma intensity-Gamma contours when available.
   TS=9 does not enable measurements; it still requires upper-limit figures.

Use `I_catalog = sum_j Phi_j/(4*pi sr)` consistently for catalog curves and
bands. Keep the diffuse benchmarks in their original intensity units, with
published bands. Use one intensity axis and include only diffuse_tracks and
diffuse_starting_tracks; do not add NGC 1068. Report the pivots and per-sr units
explicitly. A boundary warning remains preliminary; a failed flux review blocks
valid flux reporting even though the earlier independently reviewed primary
result is preserved. Do not describe AWAITING_FLUX as a completed full task or
launch stage 2 before the user has replied to the first-stage final answer.
For multiple requested sources/weightings, the first turn may report all requested
primary fits together and ask which/all should continue; do not start any flux
stage in that first turn. The next turn reports the authorized flux products in
its own final answer, with figures regardless of TS and measurements only for
TS > 9. Re-entering the primary
stage or changing parameters while awaiting flux is rejected. See
`docs/stacking_flux.md` for definitions, artifacts and the two commands.

## Single-source calculation and chat output in two stages

For newly created single-source tasks, `run --task <task_id>` performs and
reviews the primary LLH maximization first. The wrapper returns
`single_source_llh_summary`: best-fit ns and Gamma, TS, local p value and
one-sided Gaussian significance, with Gamma convention and p-value method.
**Report these values in the final answer chat bubble, ask whether the user
wants flux upper limits/measurements and figures, and END THIS TURN.**
A commentary progress message does not satisfy this first-stage result output. Identify the analytic p value/significance as estimates,
and distinguish fixed Gamma (or spatial-only acceptance Gamma) from fitted Gamma.
Preserve any material review warnings. A failed primary review blocks reporting
its numbers as valid and blocks the flux stage.

If the wrapper returns `AWAITING_FLUX`, leave the task pending and wait for an
explicit user continuation reply in a later turn. Only after that reply run:

```bash
.venv/bin/python run_agent_wrap.py run --stage flux --task <task_id> --flux-user-reply "<actual user reply>"
```

Ask once in the first-stage final answer: "Would you like to continue with flux
upper limits, applicable measurements and figures?" Use the conversation's
language. A reply such as "继续" or "continue" authorizes the second stage;
a refusal leaves the reviewed primary result available without flux execution.
Do not treat the initial analysis request, a progress message or elapsed time as
this reply, and never invent a user reply. Record the actual reply with
`--flux-user-reply`. The CLI requires it and stores it on each flux attempt.
The flux stage reads the immutable, reviewed primary checkpoint, reconstructs
the same LLH and verifies its saved value without repeating primary maximization.
It then performs the requested fixed-spectrum limit fits and, for strict TS > 9,
the primary-spectrum measurement. After review, report the upper limits and/or
measurement with units and confidence levels, display the spectrum PNG inline,
and link the PDF and numerical tables. Display the contour PNG when produced.
Use `single_source_flux_summary` and its artifact paths. Do not proactively
include the three excluded reporting topics described above.

A flux-stage failure does not invalidate a successfully reviewed primary fit.
Keep the first chat bubble and its checkpoint, explain the failed second stage,
and do not report failed flux products as valid. After an interrupted flux
process is confirmed stopped, `resume` restores `AWAITING_FLUX`; continue only
under the user's existing explicit flux authorization, passing its actual reply
with `run --stage flux --flux-user-reply`, never repeat the primary fit. Changed requests, code, inputs,
packages or checkpoint bytes block continuation. Historical tasks retain their
recorded flow. Single-source modes with no supported/requested flux products
finish after their primary stage; do not invent a flux calculation. Catalog
individual-source scans retain their existing execution and optional flux switch.

## Single-source linear Gamma interpolation

For new standalone DR2 spatial+energy single-source tasks, verify that the
wrapper records signal_energy_gamma_interpolation=linear_v1. Primary LLH
maximization, flux profiling and fixed-spectrum upper-limit fits must all use
the same two-node linear interpolation on the existing Gamma grid. Verify the
result and per-dataset working-set metadata in both stages. A method mismatch
blocks continuation and valid reporting; create a new task when changing the
scientific definition. Do not relabel historical results or checkpoints.

Catalog scan fits also contain one source at a time: do not infer interpolation
from source count or change catalog/stack defaults. They retain the original
quadratic procedure. Preserve the original optimizer, bounds, tolerances and
maximum-consistency guard. Keep the existing first-final-answer/user-reply
boundary for interactive flux execution. Do not proactively add interpolation
switch diagnostics to normal results. See docs/single_source_linear_interpolation.md.

## Flux/intensity figure line styles

For single-source and joint stacking figures, use solid lines for results
computed by the current analysis (upper limits, measured spectra and contour
boundaries). Use dashed lines for all published reference spectra from IceCube
or other authors. Preserve colors, markers, uncertainty bands and units. This
is a rendering convention; do not rerun LLH fits or alter numerical results
only to change line styles.
