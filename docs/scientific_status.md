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
it is not the DR2 model with a different event list. The optional RFC input is
not bundled. The [README support table](../README.md#what-analyses-can-i-run) distinguishes
implemented paths from the approved first-release target.

Time-dependent analysis is not implemented in this copy. Planned single-source
and catalog-scan integration uses SkyLLH; time-dependent stacking awaits
collaborator code and validation. No time-dependent scrambling is approved here.
This release copy does not establish publication readiness or implement extended
source modeling through its point-coordinate examples.

## Likelihood and detector assumptions

DR2 uses a point-source Rayleigh point-spread function (PSF) and retains every
selected source–event term, computing them in smaller blocks to limit memory
without making a sky-region approximation. Spatial+energy includes the source's
signal-energy PDF inside the source-weighted sum. IC86 I–XI events are pooled.
Explicit event cuts condition and renormalize the background spatial PDF.

Full14 production background v3 is byte-identical to frozen v3-RC1. IC79
Dec–energy residuals remain; fitted ns, Gamma and flux may be biased. The
signal-energy tables and detector response require their own validation.
Naming a package v3 does not demonstrate significance or coverage calibration.
Coverage concerns how often an interval contains the true parameter in repeated
experiments; checking a file's hash cannot test this property or parameter bias.

## Fitted spectra and boundaries

Spatial+energy fits ns and Gamma with the existing SkyLLH bounds/initial values;
fixed-Gamma spatial+energy is also selectable. At ns = 0 the spectrum is
unidentifiable: an optimizer's returned Gamma is not a spectral measurement.
The fixed acceptance Gamma used in spatial-only is not a measured spectrum.
Optimizer-boundary fits must be reported as warnings, not repaired by widening
bounds or selecting new PDFs. Source dominance and fixed-Gamma RA smoke tests
measure model influence or stability, not source-detection significance.

## Local p-values are not calibrated detection significances

Ordinary fits execute zero background trials and use an analytic half-chi-square
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

## Scope of the existing background trials

Time-integrated empirical trials independently randomize each event RA and
preserve Dec, energy proxy, angular uncertainty, dataset membership and counts.
Observed and trial fits must use identical selected sources, intrinsic weights,
PDFs, event cuts and optimization; refit every observed free parameter in every
trial. Conditional randomization does not establish unbiased parameter estimates.
The existing empirical workflow prepares one fixed random-catalog stack, not
arbitrary user-catalog or source-scan calibration. Its negative-TS discard policy
can affect the sampled null distribution and requires explicit scientific review.

## Reproducing a calculation versus validating its science

Owner-only validation evidence is not shipped. Engineering/import checks and
small real release-copy examples do not replace scientific validation. Numerical
comparisons use signed relative difference `(result-reference)/reference` first,
then signed absolute difference `result-reference`; the relative difference is
undefined for a zero reference. See the [quickstart references](quickstart.md#observed-numerical-references)
and [installation verification](input_installation_verification.md) for the limited
reproducibility evidence actually available.
