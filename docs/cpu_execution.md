# Choosing the CPU budget

Use the same execution option for single-source, catalog scan and joint stacking:

```bash
.venv/bin/python run_agent_wrap.py run --task <task_id> --workers 2
```

`--workers` must be a positive integer and defaults to 1. It controls computing
resources; it does not change the catalog, event selection, weights, likelihood,
Gamma convention, optimizer, bounds, seeds or scientific request hash.

For a single-source or joint stacking fit, the CLI sets numerical-library thread
limits before importing NumPy, SciPy or the analysis modules. This includes
spatial-only fits and the retained DR1 path. The limit is a budget: a calculation
that does not use threaded library operations may use fewer CPU cores.

For a DR1 or DR2 individual-source scan, N spawned processes run the existing independent
source fits. Each process inherits one numerical thread, so N workers do not each
start N threads. Source results retain input order and the same fit seeds; each
process keeps its own complete input/PDF cache. Memory use can grow with N.
`scan_and_stack` performs the joint fit with N numerical threads, then uses N
single-thread workers for its individual-source fits. The DR1 source scan also uses N single-thread processes, with the same input order
and per-process data cache; its joint stacking stage uses numerical thread limits.

Primary/flux reporting still takes two user turns. If flux continuation is
authorized, pass the CPU option again:

```bash
.venv/bin/python run_agent_wrap.py run --task <task_id> --stage flux \
  --flux-user-reply "<actual user reply>" --workers 2
```

Each attempt records `cpu_budget`; each report records `execution`, including the
requested budget, scan-worker count and numerical-library environment. DR2 per-source
execution records contain the worker PID and inherited thread limits. Historical
records remain unchanged. CPU selection is implemented at the public CLI; callers
embedding Python must establish numerical-library limits before numerical imports.

The current-run ETA observers are retained. Scan ETA uses elapsed scheduler wall
time divided by the number of returned source fits, including this invocation's
worker startup. It does not add worker CPU times or use old run speeds. Joint
stacking retains separate full-PDF and cached-call timings, the cold-call cache
cost adjustment and current-invocation-only estimates. No ETA changes optimizer
stopping conditions. Empirical scrambling retains its separate `--workers`
scheduler and one numerical thread per worker.

## Fixed-window time-dependent engine

The default time-dependent `per_source_catalog_windows` scope interprets `--workers N` as
Numba threads for cached fixed/free-Gamma engines, or process workers for
reference background trials. Reference observed fitting is serial. The public
wrapper caps BLAS/OpenMP at one before numerical imports for these tasks;
Numba parallelism supplies the cached-engine CPU budget. Trials retain their
recorded budget on resume. This does not change the existing time-integrated
CPU rules above. See [workflow and checkpoint details](time_dependent_catalog.md).

## Dominance and RA-scramble diagnostics

```bash
.venv/bin/python run_agent_wrap.py dominance --request "<request>" \
  --baseline-run-directory <run_directory> --output-directory <output_directory> \
  --candidate-count 15 --top-n 10 --workers 2
.venv/bin/python run_agent_wrap.py dr2-ra-scramble \
  --baseline-run-directory <run_directory> --output-directory <output_directory> \
  --seeds 104729,130363,155921 --workers 2
```

Dominance runs independent delete-one refits in N single-thread processes.
Screening and cumulative removals retain their original sequence and use the
numerical-library thread budget. Each cumulative fit keeps the preceding fit's
Gamma and ns seeds; parallelizing that sequence would change the fit procedure.
RA-scramble diagnostics run independent seeds in N single-thread processes within
each original mode. Source/event random streams, seed order and Gamma settings
remain unchanged. Only the parent writes checkpoints, after each returned fit;
resumption skips completed jobs, and changing the worker budget does not change
the scientific trial definition. Diagnostic checkpoints record the worker budget.

The same option name is used for empirical scrambling: `--workers N` at task
preparation records its scheduler size; execution/resumption uses that recorded
value. Its existing default of 2 is retained; `run`, `dominance` and
`dr2-ra-scramble` default to 1. No deprecated CPU-option alias is provided.
