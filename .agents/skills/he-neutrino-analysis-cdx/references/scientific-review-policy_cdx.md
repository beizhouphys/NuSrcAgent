# Scientific Review Policy

## Confirmation Boundaries

Ask the user before changing a scientific assumption. This includes spectral index, source cuts, coordinate interpretation, weight meaning, background-trial scope, and whether multiple hypotheses belong to one trial family.

Do not treat a column as a physical weight merely because it is numeric. Report its units or catalog meaning when known. Inspect missing, negative, zero, and highly concentrated values before use.

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

For the DR2 2103.12813 benchmark, distinguish direct public-effective-area
conversion from the paper's 10-year calibrated conversion. Require signed
relative and absolute differences for every numerical comparison. Treat the
signed-`ns` scan as a compatibility diagnostic and the constrained `ns >= 0`
scan as primary. Label the analytic catalog-size post-trial correction
uncalibrated until scrambled trials exist.

## Recovery Policy

Automatically retry only deterministic output failures such as a missing workbook or failed PDF generation, without changing the request.

Never automatically change gamma, weights, catalog rows, coordinate columns, trial correction, optimizer bounds, or likelihood definitions. Ask the user and record the decision in the next request artifact.

## Publication Language

Use `TS`, defined after maximizing the likelihood, without an added maximization suffix.

Call results preliminary when any review warning remains. Call them publication-ready only after empirical background trials, validation against the reference implementation, stability checks, and all review findings are resolved.
