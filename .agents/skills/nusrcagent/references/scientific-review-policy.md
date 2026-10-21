# Scientific Review Policy

## Confirmation Boundaries

Use the skill's clarification policy to resolve conventional notation and approved input mappings, recording the interpretation before execution. Ask about unresolved alternatives that materially change the spectrum, relative weights, source/event membership, fit hypotheses or background-trial family. An unsigned spectral-index magnitude or an explicitly defined E^-Gamma convention can map to the negative wrapper exponent without a user answer; a bare explicit positive sign requires clarification. Preserve any explicit power-law exponent. An unknown common multiplicative weight unit does not require a user answer.

Do not select a column merely because it is numeric. Use relevant name/metadata and the user's weighting request; the example radio_weight is approved as a relative radio-weight proxy. Record unknown absolute units as unknown, inspect invalid/negative/zero/concentrated values, and ask when several scientifically distinct columns remain plausible.

## Deterministic Checks

Require these checks for catalog runs:

- Source count equals the normalized input count.
- `source_number` is one-based and preserves input order.
- Coordinates are finite and within RA `[0, 360)` and Dec `[-90, 90]` degrees.
- Normalized intrinsic weights sum to one.
- TS values are finite and non-negative.
- p-values remain in `[0, 1]`.
- Catalog post-trial p-values match the declared catalog-size correction.
- Excel, CSV, provenance, and expected PDF figures exist and are readable.

For DR2 spatial-only runs, additionally require `gamma_mode=fixed`, agreement between the normalized legacy-convention Gamma and `acceptance_gamma_legacy`, `energy_pdf=not_used`, and `working_set.signal_energy_tables_loaded=false`. Require only the background spatial-PDF provenance; do not require signal-energy-table provenance. Describe this Gamma as an acceptance Gamma, never as a fitted spectrum.

## Warning Interpretation

A fit at an optimizer boundary is a scientific warning, not an engineering repair. Do not widen bounds automatically.

Strong weight concentration can make a nominal stack behave like a few-source analysis. Report maximum normalized weight and effective source count.

The current backend uses an analytic local p-value approximation. The requested `background.n_trials` is not yet executed by Phase 1.1. Stacking post-trial significance therefore remains unavailable until the full weighting and spectral-index scan is included in empirical background trials.

Flux conversion is calibrated only for supported reference spectral indices. Do not extrapolate a conversion to an unsupported index.

Distinguish direct public-effective-area flux conversion from the DR1
paper-calibrated conversion. Report signed relative and absolute differences
for numerical comparisons. The specialized paper benchmark is not distributed.
Catalog-global significance remains unavailable without the appropriate trials.

## Recovery Policy

Automatically retry only deterministic output failures such as a missing workbook or failed PDF generation, without changing the request.

Never automatically change gamma, weights, catalog rows, coordinate columns, trial correction, optimizer bounds, or likelihood definitions. Ask the user and record the decision in the next request artifact.


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

## Publication Language

Use `TS`, defined after maximizing the likelihood, without an added maximization suffix.

Call results preliminary when any review warning remains. Call them publication-ready only after empirical background trials, validation against the reference implementation, stability checks, and all review findings are resolved.

## Analytic catalog scan reporting

New DR2 scan reports declare `catalog_scan_summary`. Verify its full source
count, top-five order, stable tie handling, input-ordered CSV, analytic
independent-source correction and both signed/display Gaussian significances.
Verify the complete sqrt(TS) histogram, including TS=0, and its PDF/PNG hashes.
Missing or inconsistent declared artifacts fail review. Historical scans
without this output schema retain their original requirements. This analytic
catalog correction does not imply empirical calibration or parameter coverage.


Owner reporting policy, 2026-10-19: the interpolation-switch detail and the two method-qualification flags remain in numerical metadata, not in default answers, readable reports or captions. They do not generate warnings or block COMPLETED. Explain them when requested. Other fit, bounds, input and artifact checks remain active. The TS > 9 measurement workflow is for single-source analysis only; catalog scans keep their current procedure.
