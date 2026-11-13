# Fixed-window time-dependent analysis

This is the default workflow for new time-dependent requests. It supports DR2
spatial+energy power-law single-source fits, independent catalog scans, joint
stacking and shared background trials with empirical p-values and significances.
The wrapper records `scope=per_source_catalog_windows` when scope is omitted,
including in later confirmations of these tasks. Windows, detector phases and
scientific assumptions still need explicit settings before READY.

Gaussian profiles and fitted time parameters remain unsupported here; such
requests do not automatically switch engines. The
[legacy Gaussian/box workflow](time_dependent.md) requires explicit
`scope=legacy_time_profile` in new requests. Existing saved tasks retain their
recorded workflow. Time-integrated analysis remains the default when no
time-dependent analysis is requested.

## Scientific request

Supply a temporal JSON file, for example for two catalog sources named a and b:

```json
{
  "scope": "per_source_catalog_windows",
  "profile": "box",
  "time_format": "mjd",
  "time_scale": "ut1",
  "background_time_model": "uniform_livetime",
  "datasets": ["IC86_I-XI"],
  "windows": [
    {"name": "a", "start_mjd": 58000, "stop_mjd": 58100},
    {"name": "b", "start_mjd": 58020, "stop_mjd": 58120}
  ]
}
```

Choose detector phases explicitly (`IC40`, `IC59`, `IC79`, `IC86_I-XI`, or
supported individual IC86 seasons). Do not include overlapping pooled and
individual seasons. Each selected phase must have active sources; windows
outside all selected uptime are rejected, not silently pruned. Windows must
match normalized catalog names and order exactly. Alternatively supply
`"window_columns": {"start": "start_mjd", "stop": "stop_mjd"}` instead of
`windows`, referencing preserved CSV metadata. Start/stop are fixed, not seeds.

Coordinates use the shared coordinate layer. Intrinsic source weights must be
strictly positive and are normalized by NuSrcAgent; detector acceptance is
applied separately by the likelihood. CLI `--gamma -2` means the positive
internal index Gamma=2 in E^(-Gamma); `--gamma-mode fitted` fits Gamma within the
recorded bounds. The numerical procedure is `catalog_continuous_profile_v1`.
Signal/background time densities are normalized over detector uptime. The
conditional likelihood, phase event counts, acceptance, source weights, angular
selection and linear-density Gamma interpolation retain the donor definitions.

Defaults are precomputed PDFs, `engine=auto`, `gamma_grid_step=0.1`,
`event_selection_angle_deg=10`, and `ns_max=1000`. Optional `engine` values are
`cached-fixed`, `cached-free`, or `reference`. Cached engines require precomputed
PDFs and the matching Gamma mode. Frozen event-indexed backgrounds and signal
tables are hash-verified; this engine does not use the time-integrated continuous
spatial background models. There is no silent PDF fallback. The explicit
`pdf_backend=skyllh` alternative uses the reference engine, not frozen tables.
Extra declination cuts, requested-spectrum models and fitted time parameters
are unsupported here.

## Observed fit

Use the sole public wrapper, in the installed runtime environment:

```bash
python run_agent_wrap.py create-catalog --request "fixed-window scan and stack" \
  --catalog sources.csv --name-column name --ra-column ra_deg --dec-column dec_deg \
  --catalog-operation scan_and_stack --weight-mode uniform --gamma -2 \
  --time-mode time_dependent --temporal-file windows.json
python run_agent_wrap.py run --task <READY_task_id> --workers 4
```

Use `create-single` with a one-source window for a single-source task, or select
`--catalog-operation scan|stack`. Review must pass before interpreting results.
Outputs include normalized settings, input hashes, source/stack TS, ns, Gamma,
fit diagnostics, CSV, PNG/PDF and independent review. Gamma at ns=0 is not a
measurement. Observed runs execute zero trials; significance remains unavailable
until a matched trial ensemble is complete. No time-integrated p-value formula,
flux limit or second flux stage is applied.

## Workers, threads and cached background trials

For cached engines, `--workers N` sets Numba threads (one process); reference
trials use N worker processes with one numerical-library thread each. Reference
observed fits remain serial. BLAS/OpenMP stay capped at one to avoid nested
oversubscription. Choose N within allocated CPU resources; no batch scheduler
allocation is implied. Cached fixed/free-Gamma engines reuse event quantities,
seasonal candidates and acceptance information as in the donor implementation.

```bash
python run_agent_wrap.py td-background-trials --action prepare \
  --baseline-task <reviewed_completed_task_id> --output-directory data_output/td_trials \
  --n-trials 10000 --seed 1 --workers 4 --batch-size 100
python run_agent_wrap.py td-background-trials --action run --output-directory data_output/td_trials
python run_agent_wrap.py td-background-trials --action status --output-directory data_output/td_trials
python run_agent_wrap.py td-background-trials --action stop --output-directory data_output/td_trials
python run_agent_wrap.py td-background-trials --action resume --output-directory data_output/td_trials
```

Preparation imports the reviewed observed result without fitting it again.
Trials preserve event counts per phase. They choose good runs with probabilities
proportional to their observed event counts, draw time uniformly inside the
selected run, and recompute RA from that time and the retained event azimuth.
RA is not an independent uniform draw. Declination, energy and angular error
are retained, and each realization is shared across all source/stack hypotheses.
This empirical seasonal scrambling distribution is distinct from the explicit
uniform-livetime background time density used in the fitted likelihood.
Seed equals base seed plus global trial index, independent of batches/resources.
Source-local TS, catalog maximum TS and stack TS are distinct null distributions.
Reports use `(exceedances + 1)/(N + 1)` and fixed-N binomial 68%/95% intervals;
finite Monte Carlo precision and inherited baseline warnings must be retained.
No calibration is claimed for additional catalogs, window searches or optional
stopping. No significance report is generated from an incomplete ensemble.

After a complete ensemble passes the baseline, fit, finite-value, requested
count, unique-seed and contiguous-index checks, NuSrcAgent creates a canonical
saved-result bundle below `<trial-output>/standard_results/` and renders it with
`scripts/plot_time_dependent_standard_report.py`. This output-only conversion
does not repeat likelihood maximization. It provides the local and shared-trial maximum-TS
catalog results, the stacking result when requested, machine-readable observed
and trial arrays, validation/provenance records, and applicable PNG/PDF figures.
For fitted-Gamma runs it reconstructs the immutable reviewed observed
likelihood, evaluates the full numerical `ns`-Gamma grid for the empirical
leading source and applicable stack, verifies the saved MLE and TS, and writes
the canonical likelihood-contour NPZ files before plotting. Surface evaluation
does not use the background trials and does not refit the parameters. A required
surface that is missing or fails this consistency check blocks the polished
standard result. Fixed-Gamma runs have no two-dimensional `ns`-Gamma surface.
The source-time display records a physical anchor when supplied and otherwise
uses the fixed-window midpoint. NuSrcAgent retains the scrambled distribution as
the time-dependent null calibration and does not add time-integrated asymptotic
significance formulas. Incomplete or failed ensembles retain diagnostics but do
not receive the polished standard presentation.

The task records immutable scientific settings, input/code/package identities,
hashed indexed NPZ shards and measured current-invocation timing. Stop takes
effect after a batch. `--max-batches` permits bounded execution; resume preserves
the original target and seed indices. A run lock prevents concurrent writers.
Changed inputs/code, failed fits, mismatched shards or an unreferenced shard
left by a crash block continuation; inspect such a shard before recovery rather
than overwriting it. Continuous trials and automatic orphan recovery are not
implemented. Trial tasks use their recorded worker count, not a resume override.

See [integration evidence and limitations](time_dependent_merge.md).
