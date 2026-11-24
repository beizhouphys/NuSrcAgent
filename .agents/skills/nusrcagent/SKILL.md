---
name: nusrcagent
description: Coordinate supported IceCube single-source searches, catalog scans and stacking through persistent tasks and scientific review, including DR2 Gaussian/box searches and fixed-window time-dependent stacking with shared background trials.
---

# NuSrcAgent

Use the repository wrapper for every analysis. Read `AGENTS.md` and
`docs/scientific_status.md`; numerical success does not establish scientific validity.

## Source coordinates: all analyses

Under the default analysis settings, the minimum information required from
the researcher is the sky coordinates or a resolvable name of each source.
Accept ICRS RA/Dec or Galactic l/b. Resolve the frame and angular units from
the request, explicit notation, column headers or catalog metadata, never
from a numeric range alone. Ask only when the frame or units remain unclear;
record the clarification before running. Do not label an unspecified
equatorial equinox as ICRS. For name-only input, look up the coordinates,
record the source and resolve any ambiguous object identification.

Use the shared converter, not a hand-written numerical transformation:
`create-single --longitude ... --latitude ... --coordinate-frame galactic
--longitude-unit deg --latitude-unit deg`. For ICRS RA hourangle, use
`--coordinate-frame icrs --longitude-unit hourangle --latitude-unit deg`;
sexagesimal strings are supported. Radians are also supported. The original
`--ra-deg/--dec-deg` interface and degree-only inline sources retain their
explicit degree convention. Never combine these with generic coordinates.
For catalogs use `--longitude-column/--latitude-column`, frame and units,
or unambiguous headers such as `l_deg,b_deg` or `ra_deg,dec_deg`. Bare
`l,b` or `ra,dec` headers alone do not specify units. Use `confirm` with
the same options for a task awaiting coordinate clarification.

All supported single-source, catalog-wide single-source and stacking
analyses share this input layer, including DR1 and DR2, spatial-only and
spatial+energy modes. Backends receive only canonical ICRS RA/Dec; retain
original coordinates, units, frame and conversion provenance. Do not change
weights, source membership or scientific settings during conversion. This
does not enable a planned but unimplemented analysis mode.
See `docs/coordinates.md` for CLI and structured-request examples.


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
24 calls for fitted spectral index or 12 for fixed spectral index. This assumption expands when
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


Single-source primary fits now expose the same evaluation ETA, labelled
`single-source fit` / `single_source_fit_only`. Flux measurement ETA is split
into normalization intervals, spectral-index intervals, contour spectral-index bounds and each
confidence contour. Read `completed_units`, `total_units` and
`estimate_scope=current_profile_group_only`: quote the numerical ETA for that
group, and identify later groups/fits/output/review as unestimated. Do not
keep saying unknown once an evaluation sample supplies a rough estimate.
Before the first completed endpoint, the estimate uses current evaluation
costs with an explicit uncalibrated call assumption (96 for free-index
normalization crossings, 12 for scalar crossings, 32 for contour slices).
After a unit completes, the same group's measured unit durations replace
that assumption. Never combine different group costs. Initial loading and
saved-primary reconstruction have no comparable completed sample; say why
those ETAs are pending. Read profile timing and the stage timing file for
actual forecast errors; never use those completed-run errors as future ETA
inputs. See `docs/task_timing.md`.

## Required first-turn result boundary

For single-source and joint stacking analyses with supported/requested flux
products, the first turn ends with a FINAL ANSWER containing the reviewed primary n and s, TS, p value and significance,
followed by a question asking whether to calculate flux products. Leave
AWAITING_FLUX pending. Do not run flux in this turn or replace this final answer
with commentary. Only a subsequent affirmative user reply authorizes stage 2;
pass the actual reply with --flux-user-reply and report flux/figures in that
later turn's final answer. This supersedes earlier automatic-continuation rules.

For fixed-window time-dependent single-source, scan and joint-stack analyses,
the first turn likewise ends with a FINAL ANSWER containing the reviewed
observed ns/s and TS, the required observed-TS source ranking, the
unavailable-calibration statement, material warnings and the default observed-
stage contour figures defined below. Show those figures before asking whether
to run a fixed-count matched background ensemble. Only a subsequent explicit
reply with an agreed trial count authorizes that second stage. Follow the
analysis-specific contracts below; time-dependent tasks do not enter
`AWAITING_FLUX`.

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
For a power law, `--s` takes the spectral index in E^(-s). Use `--s 2.5`
for E^(-2.5) and `--s -2.5` for E^(+2.5). Record the interpretation.
Clarify a signed value in a natural-language request when the exponent
convention is ambiguous. The legacy option `--gamma` takes the signed exponent -s.
Prepare the detector response when the requested spectrum needs it.
A unique column identifying requested flux/relative weights may be used with
recorded metadata. A common unknown multiplicative unit cancels in normalized
weights. Do not invent absolute units or drop invalid rows.
The example's radio_weight is an illustrative relative proxy, not a measured flux.

Record interpretations with repeatable
`--interpretation-note PARAMETER=EXPLANATION`; never pretend these are user
confirmations. Supplied spectral indices are fixed unless fitting is requested.

## Requested spectra and detector response

This interface applies to every supported single-source analysis, catalog-wide
single-source analysis and stacking analysis, including spatial-only acceptance
and follow-ups using the recorded model. Read
[requested-spectra.md](references/requested-spectra.md) when the spectrum
needs preparation or the user supplies a non-power-law model.

Conventional PLs with all required interpolation nodes in the frozen tables
continue to use those tables. For other PLs or a supplied spectrum, first tell
the user that signal-energy PDFs and detector acceptance must be calculated
for that spectrum before interpolation and LLH fitting. Spatial-only fits
calculate acceptance and do not construct/use energy PDFs. Do not reject a
spectrum merely for its PL exponent or reverse its sign.

After creating a READY task, run `prepare-spectrum --task <id> --estimate-only`
to measure a preparation unit in this invocation. Report its numerical ETA
with the returned scope and exclusions before continuing `prepare-spectrum`
or `run`. A cache hit needs no new construction. Do not invent a whole-run ETA
from one dataset's pilot. Preparation does not maximize the LLH or start trials.
A supplied non-PL shape is fixed; fit its normalization through n, without
reporting a fictitious PL spectral index. Preserve all existing primary/flux-stage gates.

## Time-dependent DR2 workflow selection

Always use the newly merged workflow by default for time-dependent requests.
Treat any request for a `spatial+energy+time` likelihood or analysis as a
time-dependent request even when it does not separately say "time-dependent"
or provide a scope; do not route it to the time-integrated spatial+energy
workflow. Read `docs/time_dependent_catalog.md` first. New tasks default to
`scope=per_source_catalog_windows`, including when the input omits scope.
Use this workflow for single sources, scans, stacks or
scan_and_stack. Preserve explicit catalog order, positive intrinsic weights,
fixed box or Gaussian time profiles, user-requested detector phases and background-time model, frozen PDFs
and fitted/fixed s. When the request does not specify detector phases,
default to the supported IceCube phases whose detector uptime has a non-empty
overlap with at least one source profile's finite support in the catalog; record the derived phase
set and its overlap provenance. When the request does not specify a background-
time model, default to `background_time_model=uniform_livetime`. An explicit
user request overrides either default when supported; if it is unsupported,
explain the limitation rather than substituting another setting. This scope
uses `catalog_continuous_profile_v1`, not the optimizer defaults below.
`--workers` sets cached-engine Numba threads or reference-engine trial processes;
keep BLAS/OpenMP at one thread. Do not silently substitute engines or time
searches. Only execute observed tasks after READY. Inspect artifact/scientific
reviews. Use the time-dependent reporting stages under the joint-stack and
single-source sections below; observed fits run zero trials and no flux stage.

Missing fixed time-profile parameters must be resolved before READY. Omitted detector phases or
background-time model do not require clarification once these defaults have
been recorded. Fixed Gaussian profiles are supported by this engine with one
center MJD and positive sigma in days per source; fixed boxes retain start/stop
MJD. Fitted time parameters remain unsupported here. Explain that limitation
rather than silently selecting the legacy workflow. Only an explicit request
for a fitted-time legacy search should select `scope=legacy_time_profile`.
Keep existing saved tasks on their recorded workflow.

For `scope=per_source_catalog_windows`, also read
[time-dependent-result-standard.md](references/time-dependent-result-standard.md).

Use the same spectral-index notation in every workflow and every
human-facing report and figure: plain text `s` and the symbol
`s`, defined by `dN/dE proportional to E^{-s}`. Keep `gamma`,
`gamma_min`, `gamma_max` and related names unchanged in CLI options, Python
interfaces and machine-readable artifacts; those fields store the positive
s value after the existing signed-exponent conversion. Time-integrated
reports use `n` for the signal count;
`--s S` and `--gamma -S` specify the same spectrum in both workflows.

Every observed-only time-dependent result must include a compact source-fit
table ranked by descending observed TS. Report exactly
`min(10, N_sources)` rows, so a catalog with fewer than ten sources reports
every source. Break equal-TS ties by the preserved input catalog order. Each row
must identify the rank and source and give its best-fit ns and observed TS. For
a fitted-s analysis, also give the best-fit s in every row; write
`unidentified` when ns=0 rather than quoting an arbitrary optimizer value. For
a fixed-s analysis, state the common fixed s once and omit a misleading
best-fit-s column. Apply this rule to scan, stack, `scan_and_stack` and
standalone requests, including stack-only tasks for which the per-source fits
are supporting diagnostics. Do not rank this observed-stage table by p-value,
trial TS or post-trial significance.

Use these default chat presentation rules for fixed-profile time-dependent
analyses unless the user asks for different artifacts:

- Retain `time_dependent_ts.pdf` as an artifact, but do not display or link it
  in chat by default.
- Before asking whether to run background trials, display the validated
  observed-likelihood contour PNG for the `min(3, N_sources)` sources with the
  largest observed TS, ordered by observed TS with input order as the tie-break,
  and the stacking contour PNG when a stack was fitted. These contours apply to
  fitted-s analyses; for fixed s, state that a two-dimensional ns-s
  contour is not applicable. Constructing these output-only surfaces does not
  authorize or require background trials and does not calibrate significance.
- After a complete validated background ensemble, show a source summary table
  for exactly the `min(3, N_sources)` sources with the largest empirical local
  significance, ranked by increasing add-one local p-value with observed TS and
  then input order as tie-breaks. Include the observed best fit, local p-value,
  one-sided significance and Monte Carlo interval. Show a separate stacking
  summary table when a stack was fitted. Always generate and embed in the final
  answer the all-source pre-trial/post-trial p-value-versus-year PNG with IceCube
  phase labels after completed, validated background trials, without waiting for
  a separate plot request. This applies to single-source, scan, stack and
  scan_and_stack tasks, including supporting source fits saved by stack-only
  ensembles. Link the PDF and complete source table. Follow the timeline and
  output-only recovery contract in
  [time-dependent-result-standard.md](references/time-dependent-result-standard.md);
  do not infer missing source calibration from the catalog-operation label.
  Also display the applicable background-trial TS histogram;
  show both source and stacking histograms when both hypotheses were fitted.
  Do not substitute the observed-TS ranking for this post-trial local-
  significance ranking.

The following subsection applies only to explicitly requested legacy analyses.

## Legacy Gaussian/box single-source searches and catalog scans

Use the same public wrapper with `--time-mode time_dependent` and a complete
`--temporal-file` JSON specification with `scope=legacy_time_profile`.
Read `docs/time_dependent.md` first.
Single sources and independent catalog scans are supported in this scope;
stacking and scan_and_stack must use the fixed-profile scope above instead.
For multiple sources select `--catalog-operation scan`; do not request stacking
weights. Coordinates and spectrum use the existing shared input layers.

Require an explicit Gaussian or box profile, MJD/UT1 convention and
`background_time_model=uniform_livetime`; do not choose this rate assumption
silently. A supplied t0 or width is fixed unless explicitly requested as a fit
seed. Omitted t0/width defaults to fitted, but execution requires each fitted
parameter's finite bounds and explicit seeds plus the time-search method,
maxiter, xtol and ftol. Ask only about remaining material settings. Record these
values as user inputs, not invented confirmations. A task with missing/invalid
temporal settings stays AWAITING_CONFIRMATION; complete it through
`confirm --task <id> --temporal-file <complete.json>`. Run only after READY.

The likelihood includes good-run interval normalization and time-dependent
acceptance across all four DR2 datasets, keeping the original SkyLLH n and s
maximization. Inspect `time_dependent_summary`, settings, search convergence,
boundaries, detector fractions, input order, CSV/PNG/PDF and artifact reviews.
Report n, fitted or fixed s, TS, t0 and Gaussian sigma_t or full box duration
with units and modes. At n=0 temporal parameters/spectral index are not measurements.
P-values, significances and catalog-corrected quantities remain unavailable:
never apply the time-integrated half-chi-square estimate, catalog-size correction
or sqrt(TS) as a significance. No trials for this legacy time-search scope are
implemented; future calibration must
repeat the complete observed temporal/spectral/catalog search. These tasks
execute zero trials and no time-integrated flux products; they finish after
the primary result and review, without a flux-continuation question. Match any
validation claim to the deterministic and real-wrapper evidence, separately
from time-search calibration, coverage or proof of a global maximum.

## Execution

1. Work from this checkout root with its pinned `.venv/bin/python`.
   Run `run_agent_wrap.py environment-check` for the selected sample/mode.
   Stop on failed preflight and explain missing inputs/dependencies.
2. Exactly one source selects single-source analysis. DR2 catalogs select
   `--catalog-operation stack|scan|scan_and_stack`; scan-only needs no weights.
   DR1 retains its existing scan+stack behavior.
3. Approved DR2 defaults: full14 spatial+energy, fitted n and s, seed
   CLI -3.0 / SkyLLH 3.0. DR1 and DR2 spatial-only analyses use the fixed
   acceptance exponent -2.5 unless the user supplies another spectrum.
   Historical tasks keep their recorded spectra. Select DR1 only when requested.
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
source influence in a reviewed stack with fitted s. Delta TS from deleting sources
is not source-detection significance.

`dr2-ra-scramble` is a fixed-index smoke test, not empirical calibration.
For requested background trials following a reviewed DR2 time-integrated
single-source analysis or stacking analysis, use the recorded primary task:

```bash
.venv/bin/python run_agent_wrap.py dr2-empirical-scramble \
  --action prepare --baseline-task <task_id_or_path> \
  --output-directory <new_directory> --n-trials <agreed_count> \
  --workers <N> --request "<user request>"
.venv/bin/python run_agent_wrap.py dr2-empirical-scramble \
  --action run --output-directory <new_directory>
```

Agree trial count or continuous stopping rule and hypothesis scope first;
use `--continuous` instead of a fixed count when explicitly requested, then
`--action launch`. Do not launch trials merely because significance reporting
reminds the user about them. The primary may be at `AWAITING_FLUX`; do not
execute flux or alter its continuation gate. Preparation inherits source
coordinates, weighting factors, event selection, fixed/fitted spectrum,
interpolation, PDFs, fit bounds, initial values and optimizer seed. It imports
the reviewed primary result without maximizing it again. Every trial repeats
the corresponding fit, changing only event RA. Never replace the user's source
or catalog with random sources. Catalog-scan maxima, DR1 and time-dependent
trials are outside this workflow; a `scan_and_stack` follow-up calibrates only
its stacking component. Report primary warnings and the actual hypothesis scope.

Use `status|snapshot|stop|resume` to monitor or continue saved work. Report
empirical p-value and one-sided significance, 68%/95% uncertainty intervals,
and display the PNG trial-distribution figure with links to its PDF and tables.
Follow the task's recorded negative-TS policy and preserve all historical
trials/checkpoints. See `docs/dr2_empirical_scrambling.md`.
When status may be inspected repeatedly or stopping is data-dependent, report
the anytime-valid confidence sequence as the primary Monte Carlo uncertainty,
alongside the fixed-N interval as a descriptive snapshot.


Honor a requested CPU budget with `--workers N` (positive integer; default 1),
including user-authorized flux commands. Single-source and joint stacking fits
set numerical-library thread limits before analysis imports. DR1 and DR2 scans use N
spawned workers with one numerical thread and a separate input/PDF cache each;
`scan_and_stack` applies these rules to its respective phases. Preserve current-run
ETA observers and keep CPU settings in execution provenance, outside the scientific
request hash. Dominance accepts `--workers N` for independent delete-one refits;
its cumulative refits retain their previous-result seeds and sequential order.
RA-scramble diagnostics accept the same option for independent seeds. Checkpoints
are written by the parent only. See `docs/cpu_execution.md`; empirical scrambling
retains its recorded `--workers` scheduler setting and default.

## Reporting

Report fitted quantities, TS, p-value and the corresponding significance together.
Use the one-sided Gaussian convention `Z = Phi^-1(1 - p)` in sigma and label
local/pre-trial versus post-trial and analytic versus empirical values. For ordinary local estimates, use half-chi-square dof=2 when spectral index is
free (`gamma_mode=fitted`) and dof=1 when spectral index is fixed. With `TS > 0`, use
`p = 0.5 exp(-TS/2)` for dof=2 or `p = 0.5 erfc(sqrt(TS/2))` for dof=1.
Always convert with `Z = Phi^-1(1-p)`; `Z = sqrt(TS)` applies only to dof=1.
At `TS=0`, retain the reporting convention `p=0.5`, `Z=0`.
Label both p-value and significance as estimates, record the dof and method,
and do not claim empirical calibration or a verified asymptotic distribution
for free spectral index. Do not apply these formulas to empirical or catalog-corrected
p-values or to a search across several fixed-index hypotheses.
Unavailable post-trial quantities must remain unavailable.

For every analysis, immediately after reporting an estimated significance in
chat or a readable report, state that a more precise significance requires
background trials. If any reported estimated significance is strictly greater
than 2 sigma, explicitly emphasize that background trials are needed to
calibrate that result. This applies to all data samples, likelihood modes,
single-source fits, catalog scans, joint stacks and estimated local or
catalog-corrected values, including primary and flux-stage summaries when
they quote significance. Trials must repeat the corresponding observed fit
and the full search/hypothesis family for the significance being calibrated.
This reporting reminder does not authorize launching trials, change the
analytic estimate or review status, or describe an already empirical result
as lacking trials; retain its Monte Carlo uncertainty and trial scope.

Ordinary fits execute zero background trials. Record the requested and executed
counts and the analytic method as information, without creating a warning solely
for absent trials, analytic local calibration or unavailable empirical/post-trial
values. When all other checks pass, return `COMPLETED`. Actual fit-quality,
input or artifact warnings still produce `COMPLETED_WITH_WARNINGS`; `COMPLETED`
does not by itself establish a calibrated detection or publication readiness.

Use TS after likelihood maximization. Distinguish analytic local approximations
from empirically calibrated values and catalog-global quantities. Report the data
sample, likelihood mode, source count, weights, fitted or fixed s, n, TS, p-value and one-sided significance,
review status, artifacts and limitations. Include signed relative difference
before signed absolute difference in comparisons.

See [task interface](references/agent-task-interface.md) and
[scientific review policy](references/scientific-review-policy.md).

## Individual-source performance settings

New DR1 and DR2 single-source tasks and individual catalog fits use a source-centered
declination window with minimum half-width 20 degrees, expanded until every
dataset includes at least 20% of its full sample. This is recorded at task
creation. Explicit event cuts keep their own rules; `--full-sky-events` requests
all events, and `--source-dec-window-deg` selects a larger minimum half-width.
The stack part of `scan_and_stack` retains its recorded event selection.
Scans reuse complete data and validated PDF tables; they never reuse another
source's event mask or fitted state. See `docs/single_source_performance.md`.
Do not change the event selection of historical tasks or background ensembles.
For DR1, use its existing abs(Dec) < 87 degree sample and original background
PDF normalization by the selected-event fraction. New `--full-sky-events`
requests record [-90, 90] bounds. Historical DR1 requests without a window
or explicit bounds keep their fixed 20-degree half-width.

## Fixed-spectrum flux upper limits and reference-spectrum figures

New DR2 spatial+energy single-source tasks default to separate E^-2, E^-2.5 and E^-3 fits for preliminary one-sided 95% flux upper limits and a reference-spectrum figure. Record these defaults at task creation. The primary fit keeps its requested spectral-index mode. Use `--no-flux-upper-limits` if the user requests omission. Catalog scans require `--flux-upper-limits` to enable these extra fits and one figure per source; default scans omit them. For a request for a catalog flux-limit plot, enable this option and explain that large catalogs create many figures. Joint stacking has separate default flux outputs and two-stage intensity reporting, described below; DR1 and spatial-only results keep their existing procedures.

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
fit. sqrt(TS) is not Gaussian significance for fitted spectral index. This source
correction does not calibrate the joint stack or extra search hypotheses.
Preserve every material fit warning; failed review blocks numerical reporting.

## Single-source TS > 9 flux measurement and default reporting

For newly created DR2 spatial+energy single-source tasks, the wrapper records
flux_measurement_ts_threshold=9 and the approved primary fit procedure.
Report the primary-spectrum flux measurement only for strict TS > 9; TS=9
and smaller do not trigger intervals or measurement figures. Retain existing
fixed-spectrum upper limits. Free-spectral index normalization intervals must profile
spectral index with its spectral index-dependent detector yield; do not freeze the best-fit
spectral index to rescale an uncertainty on n. Report 68.27% and 95% profile intervals, the
best-fit spectrum, its 68.27% joint-region envelope and flux-spectral index contours.
Fixed-spectral index primary fits provide normalization intervals at that fixed spectrum.
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

Except for `per_source_catalog_windows`, for new DR2 catalog `scan` and individual fits in `scan_and_stack`, verify
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
interpolation lookups (16 MiB per dataset); stack with fitted ss also share a
lossless spatial PDF cache (1 GiB compressed payload per fit). These are
per-process budgets plus bookkeeping/temporary arrays, not total machine limits.
They do not change scientific settings, fit procedures or CPU configuration.
Keep the existing create/READY/run/review workflow and the requested CPU budget.
New trials invalidate both caches; full budgets fall back to original formulas.
When diagnosing performance, inspect both cache records under
`working_set.datasets` in `report.yaml`, and compare PDF ratios, spectral index
derivatives and complete fit/optimizer results against the unchanged request.
Do not apply a scan's declination window to the joint stack or infer full-run
speedups from a warm-cache benchmark. See `docs/stacking_performance.md`.

## Original SkyLLH optimizer

Except for `per_source_catalog_windows`, for all newly created DR2 single-source, catalog-scan and joint stacking fits,
use `fit_procedure=skyllh_lbfgs_v1`; individual catalog fits also record
`scan_fit_procedure=skyllh_lbfgs_v1`. Do not add a spectral index-interval or
interpolation-switch maximum search. Preserve the likelihood, PDFs, bounds,
event selections and exact caches. Keep flux profiling and its maximum-consistency
guard: a profile above the recorded primary maximum fails review; do not change
the optimizer or silently replace the primary fit to repair it. Preserve historical
task records and results. Unsupported recorded procedures cannot be resumed by
substitution; create a new explicit request. Observed and corresponding trial
fits must use the same supported procedure.

## Joint-stack two-stage intensity reporting

### Time-integrated analysis

For new DR2 time-integrated spatial+energy `stack` and joint `scan_and_stack`
tasks, the wrapper records separate `stacking_flux` defaults: 95% limits for
s=2, 2.5, 3; primary measured intensity only for strict TS > 9; two-stage
reporting and catalog-total flux divided by exact 4*pi sr. Individual source
scan limits retain their separate opt-in setting. Preserve historical tasks.

1. Run the READY task normally. The primary stage performs likelihood
   maximization and review, then returns AWAITING_FLUX. Read
   `stacking_stages.primary` and its review. Before starting any joint-stack
   flux calculation, write a FINAL ANSWER chat bubble with weighting/source count, best-fit
   n, s, TS, local analytic p-value and one-sided significance, with
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
   shading, and show fitted-index intensity-spectral index contours when available.
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

### Time-dependent analysis

For new DR2 `spatial+energy+time` `stack` and `scan_and_stack` tasks, use the
fixed-profile `per_source_catalog_windows` workflow. The two reporting stages are
the reviewed observed fit and, only after separate authorization, its matched
fixed-count shared background ensemble. Time-dependent tasks have no flux stage.

1. Run the READY observed task normally. It performs the requested source fits
   and/or joint stack with zero background trials, then completes review. Read
   the observed source and stack results and both artifact/scientific reviews.
   Write a FINAL ANSWER chat bubble with the weighting prescription and source
   count, the required top-observed-TS source table defined above, the leading
   observed source when a scan is present, and the applicable stack best-fit ns,
   s and TS. State that local, catalog post-trial and stacking
   p-values/significances are unavailable from the observed-only fit. Preserve
   every material warning and identify s as unidentified when ns=0. Display
   the default top-observed-TS source contours and stacking contour defined
   above, then ask whether to continue with matched shared seasonal background
   trials and request an agreed fixed trial count if none has been supplied.
   END THIS TURN after the question. A significance reminder or the initial
   analysis request does not itself authorize trials.
2. Only after the user explicitly authorizes the background stage with a fixed
   count in a later turn, run `td-background-trials` from the reviewed baseline.
   Import the observed fit without maximizing it again; repeat the recorded
   source and stack hypotheses on each shared seasonal scramble and preserve the
   index-to-seed mapping through pause/resume. Do not report a completed result
   from an incomplete ensemble. After the requested count and all validation
   checks pass, present the canonical table with the leading source, best fit,
   add-one local p-value, default response-phase Sidak result, empirical shared-trial maximum-TS result,
   and weighted-stack empirical result when applicable. Show the top-local-
   significance source and stacking summary tables defined above, rather than
   repeating the observed-TS ranking as the post-trial summary. Report Monte
   Carlo intervals and distinguish local, catalog-maximum and stacking
   probabilities. These trials do not calibrate fitted time parameters.

Use the canonical saved-result bundle and
`agent_core/plot_time_dependent_standard_report.py`; do not substitute an ad hoc
plotter. After trials, display the phase-labelled source p-values-over-time
figure and the applicable source and stacking background-TS histograms as
defined above. A missing, nonfinite or MLE/TS-mismatched required observed-stage
contour surface fails the result validation gate.
Use the matched scrambled distribution as the null calibration and do not add a
time-integrated asymptotic overlay. Include NuSrcAgent review status, requested
and produced trial counts, seed uniqueness, index contiguity, material warnings,
and links to the PNG/PDF figures and numerical artifacts. Apply the shared
time-integrated/time-dependent visual-style contract below to every generated
figure.

## Single-source calculation and chat output in two stages

### Time-integrated analysis

For newly created single-source tasks, `run --task <task_id>` performs and
reviews the primary LLH maximization first. The wrapper returns
`single_source_llh_summary`: best-fit n, s, TS, local p value and
one-sided Gaussian significance, with spectral index convention and p-value method.
**Report these values in the final answer chat bubble, ask whether the user
wants flux upper limits/measurements and figures, and END THIS TURN.**
A commentary progress message does not satisfy this first-stage result output. Identify the analytic p value/significance as estimates,
and distinguish fixed spectral index (or spatial-only acceptance spectral index) from fitted spectral index.
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

### Time-dependent analysis

For a new DR2 `spatial+energy+time` single-source or scan-only request, use the
fixed-profile `per_source_catalog_windows` workflow. The two reporting stages are
the reviewed observed fit and the separately authorized fixed-count background
ensemble; there is no time-dependent flux continuation.

1. Run the READY observed task and review its artifacts. In the first FINAL
   ANSWER, report the required top-observed-TS source table (one row for a
   standalone source), the leading observed source for a catalog scan,
   fixed/fitted s treatment, detector phases and time-window definition,
   review status and every material warning. State that p-values and
   significances are unavailable because the observed fit ran zero trials; at
   ns=0, report s as unidentified. Display the default top-observed-TS
   source contours defined above, then ask whether to continue with matched
   shared seasonal background trials and request the fixed trial count if it is
   not yet agreed. END THIS TURN after the question. Do not launch trials merely
   because the answer explains that empirical calibration is required.
2. In a later turn, only after explicit user authorization with the fixed count,
   run `td-background-trials` from the reviewed observed baseline. For one source,
   report the add-one empirical local p-value, exceedances/trials, one-sided
   significance when finite, Monte Carlo intervals and the minimum resolvable
   p-value. For a scan, additionally report the empirical shared-trial maximum-TS
   post-trial result as the calibration of the full catalog scan. Display the
   response-phase Sidak approximation by default for each source, using the
   source's box stop or Gaussian center to assign a detector-response phase
   and counting all selected IC86 I–XI seasons as one phase. State
   validation, requested/produced counts, seed uniqueness and index contiguity,
   preserve all inherited warnings, and show the top-local-significance source
   summary table defined above, with best-fit s included only when s was
   fitted.

After validation passes, use the canonical result bundle and standard renderer.
Display the phase-labelled p-values-over-time figure and the applicable source
background-trial TS histogram. Link the displayed figures and the machine-
readable tables and NPZ files. Do not call likelihood-drop contours calibrated
confidence regions, and do not use a time-integrated analytic significance
formula for these fits. Apply the shared time-integrated/time-dependent visual-
style contract below to every generated figure.

## Single-source linear spectral-index interpolation

For new standalone DR2 spatial+energy single-source tasks, verify that the
wrapper records signal_energy_gamma_interpolation=linear_v1. Primary LLH
maximization, flux profiling and fixed-spectrum upper-limit fits must all use
the same two-node linear interpolation on the existing spectral-index grid. Verify the
result and per-dataset working-set metadata in both stages. A method mismatch
blocks continuation and valid reporting; create a new task when changing the
scientific definition. Do not relabel historical results or checkpoints.

Catalog scan fits also contain one source at a time: do not infer interpolation
from source count or change catalog/stack defaults. They retain the original
quadratic procedure. Preserve the original optimizer, bounds, tolerances and
maximum-consistency guard. Keep the existing first-final-answer/user-reply
boundary for interactive flux execution. Do not proactively add interpolation
switch diagnostics to normal results. See docs/single_source_linear_interpolation.md.

## Analysis figure line styles

Use the time-integrated upper-limit and likelihood-contour figures as the visual
style source for both time-integrated and time-dependent single-source and joint
stacking figures. Reuse their white background, serif/STIX typography and math
text, spectral-index $s$ labels, inward major/minor ticks on all sides, restrained
axes and grid, clear stroke hierarchy, uncluttered frame-free legends and
publication-scale spacing. Use solid lines for results computed by the current
analysis and dashed lines for published reference spectra from IceCube or other
authors.

In particular, render time-dependent likelihood surfaces with the same
time-integrated contour language: solid purple (`#7752a5`) and orange
(`#d17c12`) contour boundaries where multiple contour families need
distinguishing, low-alpha fills, and a black star for an identifiable best fit.
At ns=0, show the full s-independent ridge and label s as unidentified
instead of drawing an arbitrary star. Keep the time-dependent likelihood-drop
statistic and requested numerical contour levels unchanged; matching the style
does not turn them into calibrated confidence regions.

For time-dependent p-value and background-TS figures, inherit the same
typography, axes, tick, linewidth and current-analysis solid-series conventions
from the upper-limit figure while retaining the plot-specific phase shading,
significance guides, histogram encoding, observed-TS marker, uncertainty bands
and units required by the standard time-dependent renderer. Extend
`agent_core/plot_time_dependent_standard_report.py` to enforce this shared style
rather than introducing an ad hoc plotter. This is a rendering convention; do
not rerun likelihood fits, change statistical definitions or alter numerical
results only to change figure styling.
