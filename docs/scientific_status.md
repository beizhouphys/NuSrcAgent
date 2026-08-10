# Scientific Status and Limitations

This document records the boundary between the working agent interface and the still-developing likelihood analysis.

## Current Scope

The callable backend has two time-integrated data paths. The default IceTracks-DR2 14-year SkyLLH v26 path supports point-like single-source and multi-source stacking with either spatial+energy or spatial-only likelihoods, using all experimental events. Spatial+energy fits Gamma by default and optionally fixes it; it reads the project-local pre-calculated background spatial+energy PDFs and signal-energy tables. Spatial-only uses only the spatial components and never loads or evaluates signal/background energy PDFs. The existing IceCube public 10-year path remains available without scientific changes for reproduction and comparison work.

The DR2 stacking weights use the project notation: source model weight `w_{j,model}`, SkyLLH detector yield `w_{j,acc}^k`, and SkyLLH dataset signal fraction `f_k`. Signal energy remains inside the source-weighted sum and is evaluated at each source declination. The code structure keeps time dependence separable, but no time PDF is enabled yet.

For spatial-only, the per-dataset signal PDF is
`S_i^k = sum_j[w_{j,model} w_{j,acc}^k S_{ij,spatial}^k] / sum_j[w_{j,model} w_{j,acc}^k]`, and the event ratio is `S_i^k / B_{i,spatial}^k`. The fixed owner-approved acceptance Gamma is `-2.5` in the legacy convention (SkyLLH `2.5`). It changes `w_{j,acc}^k`; it is not fitted from event energies and must not be interpreted as a measured source spectrum.

The owner-approved default fitted-Gamma bounds are SkyLLH Gamma `[1.0, 6.0]`
(legacy convention `[-6.0, -1.0]`) and `ns` `[0, 10000]`, with seeds Gamma
`3.0` and `ns=10`. The pre-calculated signal-energy tables span
SkyLLH Gamma `[0.9, 6.1]`; the extra 0.1 on each side is retained as the
interpolation margin. Fixed-Gamma analyses do not apply fitted-Gamma bounds.

The current implementation reports local p-values using an analytic half-chi-square approximation. It does not yet execute empirical right-ascension scrambling trials. Catalog source-scan post-trial values on the 10-year path use the declared catalog-size correction; stacking post-trial significance remains unavailable.

For the dedicated DR2 reproduction of arXiv:2103.12813, flux conversion is
available at legacy Gamma `-2.0`, `-2.53`, and `-3.0`. It directly integrates
the public DR2 muon-neutrino effective areas and measured livetimes using Eq.
(10) of that paper, then applies the stated three-flavor factor. It does not
reuse the legacy 10-year paper-calibrated event-count constants. This
distinction must be retained when comparing limits.

## Known Scientific Risks

The preserved legacy likelihood contains invalid-region and empty-ROI behaviors that require controlled numerical study before scientific publication. Historical research scripts also contain neighboring-project dependencies and older SciPy interfaces.

The callable backend is separated from those legacy scripts, but it was derived from the same analysis and still requires systematic validation against a trusted reference implementation, optimizer-boundary checks, input-order and weight-normalization invariance tests, and empirical trial calibration.

The DR2 single-source all-event NGC 1068 regression is close to, but intentionally not identical to, the official SkyLLH benchmark that uses a 10-degree event-selection optimization. The signed differences observed in the initial all-event check are +1.38% (+0.402) for TS, +1.01% (+0.810) for fitted ns, and -0.0887% (-0.00285) for Gamma. This difference must be understood before publication claims.

The DR2 implementation includes every event and every source-event term, but
reduces the exact source-weighted sum in adaptive event and source chunks. It
does not materialize SkyLLH's full Cartesian source-event arrays and does not
substitute an ROI cut. The default working-pair budget is `2**20`, with event
and source chunks capped at 2048 each; the actual chunk sizes are recorded in
each result. This bounds working memory, but total arithmetic still scales as
the number of sources times 1,643,355 events. Catalogs with hundreds or
thousands of sources therefore still require runtime benchmarking before a
production launch.

The 3386-source RFC 2019c benchmark has a separate resumable batch evaluator
in `analysis_backend_cdx/skyllh_dr2_catalog_scan_cdx.py`. It uses the same
all-event Rayleigh spatial PDF as the supported DR2 backend, evaluates source
blocks without an ROI, checkpoints the accumulated stack, and preserves both
the primary constrained `ns >= 0` fit and a signed-`ns` paper-compatibility
diagnostic. Its catalog-size post-trial correction is analytic and explicitly
uncalibrated; it is not a substitute for right-ascension-scrambled trials.
Numerically zero spatial ratios are aggregated exactly during one-dimensional
fits, so repeated background-only terms are evaluated once; a dense-versus-
compressed regression agrees at relative/absolute tolerance `1e-11`. The first
full 3386-source dense production run completed in 733.98 seconds on the
development machine. This is a performance observation, not a portable
runtime guarantee.

## Interpretation

- Use `TS` for the statistic after likelihood maximization.
- Distinguish pre-trial and post-trial quantities.
- Treat optimizer-boundary fits and strongly concentrated weights as scientific warnings.
- Do not infer a value where the output intentionally leaves stacking post-trial significance blank.
- Do not describe warning-bearing results as publication-ready.

## Legacy Code

`legacy_codex_revised/` preserves the original research scripts for provenance and future LLH development. They are not imported by the supported agent runtime and may require additional scientific dependencies or external files. Moving them into the legacy directory does not certify or alter their numerical behavior.
