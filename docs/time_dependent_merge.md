# Time-dependent integration record

Integration branch: `time_dependent_merge`.

The donor is `Codex_time-dependent-stacking_SkyLLH` at
`5c70f58642a16363c777948f5ad170b5e43a1d41`. The integration preserves its
conditional likelihood, fixed per-source box or Gaussian time profiles, shared seasonal
fixed-count time/RA scrambles, and reference/cached fixed/free-Gamma engines.
The existing NuSrcAgent time-integrated and Gaussian/box temporal search
paths retain their scientific definitions.

## Integration order and boundary

1. Freeze donor configuration/output references and audit stock SkyLLH 26.0.0
   compatibility. Keep the existing NuSrcAgent numerical backends untouched.
2. Extract production likelihood, PDF/time/acceptance and cached/reference engine
   modules into `analysis_backend/time_dependent/`. A local SignalTimePDF subclass
   handles empty uptime overlap; stock SkyLLH is not globally patched or vendored.
3. Adapt normalized coordinates, weights, signed spectral exponents and frozen
   PDF paths to the donor contract. Route recorded
   `scope=per_source_catalog_windows` tasks to this engine. New time-dependent
   tasks now record this scope by default when it is omitted. New legacy
   requests must explicitly select `scope=legacy_time_profile`; existing saved
   tasks retain their recorded interpretation.
4. Integrate READY gating, observed artifacts/review and a separate fixed-count
   shared-trial workflow with immutable inputs, deterministic seeds, checkpoints,
   pause/resume and empirical reporting.
5. Update the skill, public documentation, dependency lock and recursive CI import
   checks. Keep owner tests, catalogs, results, benchmarks and donor CLI/reporting
   utilities outside this release checkout.

All changes are on `time_dependent_merge`. Existing time-integrated and original
legacy Gaussian/box numerical backend files are unchanged. Shared dispatch,
validation and reporting changes are scoped to the new mode. No changes have
been pushed and no release/publication is implied.

## Verification record, 2026-11-05

Verification used the requested `icecube_agent` environment (Python 3.11,
NumPy 2.4.6, Numba 0.68.0), with stock SkyLLH 26.0.0 loaded from its wheel instead
of the editable donor checkout. This is not the exact locked Python 3.12 runtime.

- 47 retained-module donor numerical tests pass against the extracted package.
  Unshipped donor scan helpers are used only as test references. An earlier
  58-test extraction check also included donor scan/trial utilities subsequently
  excluded from the production port.
- 13 adapter/workflow regressions pass: source order and weights, signed Gamma,
  invalid requests, legacy dispatch, artifact tampering, resumed deterministic
  trials and an independent scalar conditional-likelihood calculation.
- After making the merged workflow the default, all 18 routing/integration
  checks pass (the 13 above plus five public-wrapper regressions): omitted
  scope, confirmation, pending settings, explicit legacy selection, historical
  task preservation, default-engine stacking and unchanged time-integrated
  defaults. The numerical engines are unchanged by this routing update.
- For the real 694-source SN catalog, fixed Gamma=2 and fitted-Gamma observed
  source and stack TS/ns/Gamma exactly match the saved donor outputs: maximum
  absolute difference zero; relative difference zero where the reference is
  nonzero (undefined at zero). Both reference stack fits are at ns=TS=0; this
  comparison alone is not a nonzero-signal stacking validation.
- For both Gamma modes, four seeded cached trials are bitwise identical with
  one versus two threads; two seeded reference trials are bitwise identical
  with one versus two workers. Cached/reference TS/ns agree at rtol=1e-5,
  atol=1e-4 for these small ensembles. This checks reproducibility, not a
  full null-distribution calibration or a new speedup measurement.
- Real-input public-wrapper checks use an isolated repository root with
  read-only links to the identical frozen tables and DR2 events. Fixed/fitted
  Gamma scan-and-stack tasks and a fixed-Gamma single source reach READY and
  complete with passing artifact/scientific reviews. The trial checks use
  four-trial ensembles, pause after two, and resume with preserved seed indices.
  A deliberately code-changed continuation is rejected.
- The skill validator passes. The complete hash-locked package set resolves
  successfully for Python 3.12 with binary wheels. Existing package pins are
  retained; Numba 0.68.0, llvmlite 0.50.0 and PyYAML 6.0.3 are added.

Owner-only detailed parity evidence stays in the donor's
`run/time_dependent_merge_verification/`, not in the release checkout.
Reference SHA256 values:

| Reference | SHA256 |
| --- | --- |
| Fixed-Gamma observed NPZ | `746bea695b5b123a134eea4cfb414cde89dcfc38afae05c712791c0da6b320ae` |
| Fitted-Gamma observed NPZ | `02fa3d47416919e6c292e9cf422cb1a1b86154b2072b3b2488c54e242cb99a71` |
| Fixed-Gamma donor config | `9b129f16342e6adc7f5aa433289234ecf28d86fc39d5a6d57f4209803a183840` |
| Fitted-Gamma donor config | `b9581289214bdd3dc7df61b23d6cfc75f597892b514d8d6bc540ea8c7397e13a` |

## Remaining release gates and scientific limits

Run CI and real-data checks in the exact locked Python 3.12 environment before
declaring a tested release. A fresh full-bundle installation and real-data
regression of the original time-integrated paths were not repeated here:
NuSrcAgent lacks the full numerical bundle, and its hosted installer requires
GitHub authentication. Local matching inputs suffice for the new engine's
event-table path; no input hash was bypassed and no unavailable continuous
background model was fabricated.

The integration does not establish asymptotic calibration, coverage, sensitivity,
discovery potential, global time-search significance or physical systematics.
Only fixed per-source box or Gaussian profiles have shared trials. Flux/fluence, continuous trials
and automatic recovery of orphan checkpoint shards remain outside this scope.
The precomputed cached path received real-data wrapper verification; other
explicit backend/phase configurations need their corresponding release checks.

See [the public workflow](time_dependent_catalog.md) for schema and commands.
