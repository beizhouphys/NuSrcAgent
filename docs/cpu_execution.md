# Choosing the CPU budget

Use the same execution option for single-source, catalog scan and joint stacking:

```bash
.venv/bin/python run_agent_wrap.py run --task <task_id> --cpus 2
```

`--cpus` must be a positive integer and defaults to 1. It controls computing
resources; it does not change the catalog, event selection, weights, likelihood,
Gamma convention, optimizer, bounds, seeds or scientific request hash.

For a single-source or joint stacking fit, the CLI sets numerical-library thread
limits before importing NumPy, SciPy or the analysis modules. This includes
spatial-only fits and the retained DR1 path. The limit is a budget: a calculation
that does not use threaded library operations may use fewer CPU cores.

For a DR2 individual-source scan, N spawned processes run the existing independent
source fits. Each process inherits one numerical thread, so N workers do not each
start N threads. Source results retain input order and the same fit seeds; each
process keeps its own complete input/PDF cache. Memory use can grow with N.
`scan_and_stack` performs the joint fit with N numerical threads, then uses N
single-thread workers for its individual-source fits. The DR1 scan retains its
existing sequential source loop and uses the numerical thread limit.

Primary/flux reporting still takes two user turns. If flux continuation is
authorized, pass the CPU option again:

```bash
.venv/bin/python run_agent_wrap.py run --task <task_id> --stage flux \
  --flux-user-reply "<actual user reply>" --cpus 2
```

Each attempt records `cpu_budget`; each report records `execution`, including the
requested budget, scan-worker count and numerical-library environment. Per-source
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
