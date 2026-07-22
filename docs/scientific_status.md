# Scientific Status and Limitations

This document records the boundary between the working agent interface and the still-developing likelihood analysis.

## Current Scope

The callable backend supports time-integrated single-source searches, catalog-wide source scans, and catalog stacking with the included IceCube public 10-year point-source data subset.

The current implementation reports local p-values using an analytic half-chi-square approximation. It does not yet execute empirical right-ascension scrambling trials. Catalog source-scan post-trial values use the declared catalog-size correction; stacking post-trial significance remains unavailable.

Flux conversion is calibrated only for supported reference spectral indices.

## Known Scientific Risks

The preserved legacy likelihood contains invalid-region and empty-ROI behaviors that require controlled numerical study before scientific publication. Historical research scripts also contain neighboring-project dependencies and older SciPy interfaces.

The callable backend is separated from those legacy scripts, but it was derived from the same analysis and still requires systematic validation against a trusted reference implementation, optimizer-boundary checks, input-order and weight-normalization invariance tests, and empirical trial calibration.

## Interpretation

- Use `TS` for the statistic after likelihood maximization.
- Distinguish pre-trial and post-trial quantities.
- Treat optimizer-boundary fits and strongly concentrated weights as scientific warnings.
- Do not infer a value where the output intentionally leaves stacking post-trial significance blank.
- Do not describe warning-bearing results as publication-ready.

## Legacy Code

`legacy_cdx/` preserves the original research scripts for provenance and future LLH development. They are not imported by the supported agent runtime and may require additional scientific dependencies or external files. Moving them into the legacy directory does not certify or alter their numerical behavior.
