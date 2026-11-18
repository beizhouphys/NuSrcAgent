# What the results do and do not establish

A successful calculation establishes that the requested fit ran and its output
checks passed. It does not by itself establish a neutrino detection, unbiased
source parameters or valid confidence intervals. This page separates the
implemented analysis from those further scientific questions.

## Implemented analyses

Current implementation: DR2 time-integrated point-source single fits, individual
catalog scans and stacking; DR1 time-integrated spatial-only analysis retained.
Both DR2 modes support single sources, scans and stacking. The DR1 path remains
spatial-only with its existing single-source and catalog scan+stack behavior;
it is not the DR2 model with a different event list. The selected radio-bright
AGN CSV is bundled in `data_input/sources/` for `--catalog` requests;
only the original raw RFC input for the optional built-in reader remains external.
The [README support table](../README.md#what-analyses-can-i-run) distinguishes
implemented paths from the approved first-release target.

New DR2 time-dependent requests default to the merged
[fixed per-source profile workflow](time_dependent_catalog.md), supporting
single-source fits, scans, stacking and fixed-count shared seasonal background
trials for fixed box or Gaussian signal-time PDFs. Completed trials provide empirical source-local, catalog-maximum and
stacking p-values and significances with Monte Carlo intervals. It does not
calibrate fitted time parameters or provide flux/fluence inference.
The [legacy Gaussian/box time-search workflow](time_dependent.md) requires
explicit selection for new requests and has no stacking or calibrated trials.
Existing saved tasks retain their recorded definitions.
This release copy does not establish publication readiness or implement extended
source modeling through its point-coordinate examples.

## Likelihood and detector assumptions

For new DR1 and DR2 single-source analyses and individual catalog fits, use a
source-centered declination window with a minimum half-width of 20 degrees.
Expand it until each dataset includes at least 20% of its sample. DR1 keeps
its abs(Dec) < 87 degree sample and background PDF normalization by the
selected-event fraction. DR2 keeps its background PDF integral normalization.
Joint stacks use all sample events unless the user supplies explicit cuts.
Historical DR1 requests without the new window setting keep their fixed
20-degree half-width. See [event selection](single_source_performance.md).

DR2 uses a point-source Rayleigh point-spread function (PSF) and retains every
selected source–event term, computing them in smaller blocks to limit memory
within the recorded event selection. New individual fits use the adaptive
source-centered declination window; this is a selection approximation to the
all-event fit, with its settings and retained fractions recorded. Spatial+energy includes the source's
signal-energy PDF inside the source-weighted sum. IC86 I–XI events are pooled.
Explicit event cuts condition and renormalize the background spatial PDF.

Full14 production background v3 is byte-identical to frozen v3-RC1. IC79
Dec–energy residuals remain; fitted ns, Gamma and flux may be biased. The
signal-energy tables and detector response require their own validation.
Naming a package v3 does not demonstrate significance or coverage calibration.
Coverage concerns how often an interval contains the true parameter in repeated
experiments; checking a file's hash cannot test this property or parameter bias.

## Requested spectra

Conventional PLs retain the frozen signal-energy PDFs. A requested exponent
outside the table's interpolation coverage, or a fixed non-PL spectrum from
modeling, triggers separate signal-energy PDF and detector-acceptance preparation.
The agent explains this step and reports a current measured preparation ETA
before interpolation and LLH fitting. This applies to single-source analyses,
catalog scans and stacking; spatial-only modes calculate acceptance without
using energy PDFs. See [requested spectra](requested_spectra.md) for the input
contract, support rules, response provenance and fixed-shape scope.

## Fitted spectra and boundaries

Spatial+energy fits ns and Gamma with the existing SkyLLH bounds/initial values;
fixed-Gamma spatial+energy is also selectable. At ns = 0 the spectrum is
unidentifiable: an optimizer's returned Gamma is not a spectral measurement.
The fixed acceptance Gamma used in spatial-only is not a measured spectrum.
Optimizer-boundary fits must be reported as warnings, not repaired by widening
bounds or selecting new PDFs. Source dominance and fixed-Gamma RA smoke tests
measure model influence or stability, not source-detection significance.

## Local p-values are not calibrated detection significances

Ordinary time-integrated fits execute zero background trials and use an analytic half-chi-square
local p-value approximation. A default `background.n_trials` in request metadata
does not mean those trials ran. Jointly fitting Gamma and optimizer boundaries
require appropriate null calibration; an analytic p-value is not a validated
detection significance or a coverage guarantee.
A source scan does not provide an empirical catalog-global p-value. DR1's
declared catalog-size correction is analytic and uncalibrated.
In particular, scanning many sources and quoting the smallest local p-value
does not account for the search over the catalog. Empirical calibration means
comparing the observed statistic with background realizations that repeat the
same fitted parameters and the same search.


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

## Scope of the existing background trials

Time-integrated empirical trials independently randomize each event RA and
preserve Dec, energy proxy, angular uncertainty, dataset membership and counts.
Observed and trial fits must use identical selected sources, intrinsic weights,
PDFs, event cuts and optimization; refit every observed free parameter in every
trial. Conditional randomization does not establish unbiased parameter estimates.
The empirical workflow follows a reviewed DR2 single-source analysis or stacking
analysis; it does not calibrate a catalog-scan maximum. Its negative-TS discard policy
can affect the sampled null distribution and requires explicit scientific review.

## Reproducing a calculation versus validating its science

Owner-only validation evidence is not shipped. Engineering/import checks and
small real release-copy examples do not replace scientific validation. Numerical
comparisons use signed relative difference `(result-reference)/reference` first,
then signed absolute difference `result-reference`; the relative difference is
undefined for a zero reference. See the [quickstart references](quickstart.md#observed-numerical-references)
and [installation verification](input_installation_verification.md) for the limited
reproducibility evidence actually available.

New DR2 single-source tasks and individual catalog fits default to a source-centered
declination window: minimum half-width 20 degrees and at least 20% of each
dataset. Use `--full-sky-events` at task creation for all events, or
`--source-dec-window-deg 30` for a larger minimum half-width. The stack part of
`scan_and_stack` retains its existing event selection. Scans reuse complete
loaded data and validated PDF tables. [Settings and limitations](single_source_performance.md).

## Fixed-spectrum point-source flux limits, 2026-10-19

New DR2 spatial+energy single-source tasks default to three separate fixed-spectrum fits (E^-2, E^-2.5, E^-3), preliminary one-sided 95% profile-likelihood upper limits, and a spectrum figure with published NGC 1068 and diffuse bands. Catalog scans keep these per-source outputs opt-in with `--flux-upper-limits`; stacking retains its existing definition. Coverage and detector/PDF systematics remain unvalidated/excluded. Historical tasks retain their recorded definitions. See [flux-limit definitions and plotting conventions](flux_upper_limits.md).

New DR2 source scans report an analytic independent-source catalog correction
`p_global = 1-(1-p_local)^N_sources`, alongside the local approximation.
This is not empirical calibration; correlated source hypotheses, additional
catalog selections and extra search hypotheses are not calibrated by it.
Signed Gaussian Z is retained; the top-five table displays max(0, Z) as in
arXiv:2103.12813 Table I. The sqrt(TS) figure is an observed source histogram,
not a background-trial distribution or a validation of the local approximation.

## Single-source measurement workflow, 2026-10-19

New single-source DR2 spatial+energy tasks use the owner-approved primary fit procedure and report flux measurements only for strict TS > 9. The calculation supplies correlated profile intervals and free-Gamma joint contours alongside the existing fixed-spectrum upper limits. Catalog scans retain their current procedure and omit the new measurement calculation. The owner-approved default reporting policy stores technical method details in numerical metadata, without warnings or unsolicited discussion of the three identified topics. Genuine fit, input and artifact checks remain active. See [single-source flux measurement definitions](flux_measurements.md).

New DR2 individual catalog fits explicitly record and review the owner-restored
`scan_fit_procedure=skyllh_lbfgs_v1`. Single-source and joint stacking defaults
are independent. Historical tasks retain their recorded procedure. An extra
Gamma-interval/stencil-switch search must not be silently inherited by new
source scans. This safeguard changes procedure provenance and checks; it does
not validate asymptotic significance, parameter bias or interval coverage.

## Original SkyLLH optimizer, 2026-10-19

Except for the explicit `per_source_catalog_windows` engine, new DR2 single-source, catalog-scan and joint stacking fits use
`skyllh_lbfgs_v1`. The owner requested removal of the additional Gamma-interval
and interpolation-switch maximum search. Likelihoods, PDFs, selections, bounds
and exact caches are retained. Flux profiling keeps its maximum-consistency
guard: a profile above the recorded primary optimum fails review. Historical
task records and results are not rewritten; unsupported procedures are rejected
before execution. Corresponding observed and background-trial fits must use the
same supported procedure.


New single-source tasks return a reviewed primary LLH result before flux
calculation. The flux stage uses its immutable best fit without repeating primary
maximization; stage separation changes execution/reporting order only. See
[single-source stages](single_source_stages.md).

## User-confirmed flux continuation, 2026-10-20

Single-source and joint stacking tasks with supported/requested flux products
stop at AWAITING_FLUX after primary review. The Agent reports the primary result in a final answer, asks whether to
continue, and ends the turn. Only a later affirmative user reply starts flux;
`--flux-user-reply` records the actual reply on the flux attempt. No primary
maximization, scientific setting, upper-limit definition or TS gate is changed.


## Single-source linear Gamma interpolation (2026-10-20)

New standalone DR2 spatial+energy single-source tasks use linear_v1 consistently
for the primary fit and all flux calculations. Catalog scans, joint stacks and
historical requests retain their recorded definitions. Frozen tables, optimizer,
tolerances and the profile maximum-consistency guard are unchanged. See
[single-source interpolation](single_source_linear_interpolation.md).

## CPU budget

Use `run --task <id> --workers N` (default 1) to select computing resources.
Single-source and joint stacking fits set numerical-library thread limits;
DR1 and DR2 catalog scans use N single-thread worker processes with separate input/PDF
caches and input-ordered results. Pass the option again for a user-authorized
flux stage. Scientific settings and current-run ETA observers are retained.
Dominance uses workers for independent delete-one refits and keeps cumulative
refits sequential with their original initial values. RA-scramble diagnostics
use workers for independent seeds; both accept `--workers N`.
See [CPU selection](cpu_execution.md).

## General background-trial follow-up

Use `prepare --baseline-task` to follow a reviewed DR2 single-source or stacking analysis with matched event-RA trials. Sources, weighting factors, event selection, fixed/fitted spectrum, PDFs, interpolation and fit procedure are inherited. The primary result is imported without another maximization. Reports include empirical p-value and significance, 68%/95% fixed-N and anytime-valid Monte Carlo intervals, PNG/PDF figures and checkpoints. Catalog-scan maxima, DR1 and time-dependent trials are not supported. Historical trials remain unchanged and do not calibrate another source/catalog hypothesis.
