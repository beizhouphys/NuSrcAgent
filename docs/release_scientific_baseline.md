# First-release scientific baseline

- Python 3.12 and hash-locked SkyLLH 26 environment.
- DR2 full14 with IC40, IC59, IC79 and pooled IC86 I–XI; 1,643,355 events.
- Point-source Rayleigh PSF; exact selected source–event terms, no default ROI.
- Default spatial+energy: fitted ns and Gamma; ns bounds [0,10000], seed 10;
  SkyLLH Gamma bounds [1,6], seed 3. CLI spectral exponents use negative Gamma.
- Spatial-only: fixed acceptance Gamma, default SkyLLH 2.5 / CLI -2.5.
- Frozen background v3, current frozen signal-energy tables, unchanged hashes.
- Intrinsic weights and explicit cuts follow the scientific request. Event cuts
  condition and renormalize BSpdf; no silent source exclusion is allowed.
- Standard wrapper random seed 12345; empirical streams are separately recorded.
- DR1 definitions remain unchanged and do not use full14 v3 event tables.
- Conditional time-integrated event-RA scrambling preserves other event quantities;
  trial count and hypothesis family must be agreed for each actual calibration.
- Time-dependent scope is planned; its fit/search settings and scrambling require
  confirmation and implementation/validation before the final release.
