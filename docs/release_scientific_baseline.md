# Default analysis definitions and fit settings

This page specifies the time-integrated analysis used by the examples. It is a
record of the model and numerical settings, not evidence that every scientific
systematic has been validated. Definitions of `ns`, `Gamma` and `TS` are in the
[README](../README.md#what-do-the-fitted-quantities-mean).

## Data and source model

The point-spread function (PSF) describes the reconstructed angular separation
of a signal event from a point source. A region-of-interest (ROI) cut would
discard events outside selected sky regions; no such cut is applied by default.
Calculations are divided into smaller blocks to limit memory, without dropping
source–event terms from the selected likelihood.

- Python 3.12 and hash-locked SkyLLH 26 environment.
- DR2 full14 with IC40, IC59, IC79 and pooled IC86 I–XI; 1,643,355 events.
- Point-source Rayleigh PSF; exact selected source–event terms, no default ROI.

## Spectrum, event count and PDFs

- Default spatial+energy: fitted ns and Gamma; ns bounds [0,10000], seed 10;
  SkyLLH Gamma bounds [1,6], seed 3. CLI spectral exponents use negative Gamma.
- Spatial-only: fixed acceptance Gamma, default SkyLLH 2.5 / CLI -2.5.
- Frozen background v3, current frozen signal-energy tables, unchanged hashes.

The default seeds are starting values for numerical maximization, not fixed
physical parameters. Bounds specify the allowed fit range. The negative CLI
exponent `-3` corresponds to a positive spectrum index `Gamma=3`. With a
spatial-only likelihood, the fixed acceptance Gamma enters the predicted
detector yield but is not determined from the event energies.

## Local p-value and significance estimates

Ordinary fits use the owner-approved half-chi-square estimate: dof=2 for free
Gamma, dof=1 for fixed Gamma. Convert the estimated p-value to one-sided Gaussian
significance with `Z = Phi^-1(1-p)`; only dof=1 gives `Z = sqrt(TS)`.
At TS=0, the reporting convention remains p=0.5 and Z=0. Reports and CSVs record
the method, dof and estimate flag. This changes the reported local estimate,
not the likelihood fit or any empirical calibration. Historical artifacts stay
as recorded.

## Selections, source weights and background trials

- Intrinsic weights and explicit cuts follow the scientific request. Event cuts
  condition and renormalize BSpdf; no silent source exclusion is allowed.
- Standard wrapper random seed 12345; empirical streams are separately recorded.
- DR1 definitions remain unchanged and do not use full14 v3 event tables.
- Conditional time-integrated event-RA scrambling preserves other event quantities;
  trial count and hypothesis family must be agreed for each actual calibration.
- Time-dependent scope is planned; its fit/search settings and scrambling require
  confirmation and implementation/validation before the final release.

BSpdf means background spatial probability density. If an event-declination
cut is requested, this density is normalized over the retained region rather
than over the original sky. Intrinsic source weights describe the assumed
source population; detector acceptance is applied separately.
The ordinary examples run no background trials. See
[scientific limitations](scientific_status.md) before interpreting fitted
parameters or a reported analytic p-value.

## Individual-source selection update, 2026-10-18

The all-event selections recorded above remain the historical reproducibility
baseline. New DR2 single-source and catalog-scan tasks instead default to the
[adaptive source-centered declination window](single_source_performance.md): minimum half-width
20 degrees and at least 20% of every dataset. Use `--full-sky-events` at task
creation to reproduce all-event references. Stacking selections, frozen PDFs,
Gamma conventions, fit bounds and historical task settings are unchanged.
