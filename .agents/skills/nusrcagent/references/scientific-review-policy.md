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
local/pre-trial versus post-trial and analytic versus empirical values. For the
existing analytic half-chi-square local approximation, `Z = sqrt(max(TS, 0))`.
Do not substitute sqrt(TS) for an empirical or catalog-corrected significance.
Unavailable post-trial quantities must remain unavailable.

Ordinary fits execute zero background trials. Record the requested and executed
counts and the analytic method as information, without creating a warning solely
for absent trials, analytic local calibration or unavailable empirical/post-trial
values. When all other checks pass, return `COMPLETED`. Actual fit-quality,
input or artifact warnings still produce `COMPLETED_WITH_WARNINGS`; `COMPLETED`
does not by itself establish a calibrated detection or publication readiness.

## Publication Language

Use `TS`, defined after maximizing the likelihood, without an added maximization suffix.

Call results preliminary when any review warning remains. Call them publication-ready only after empirical background trials, validation against the reference implementation, stability checks, and all review findings are resolved.
