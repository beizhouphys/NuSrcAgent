# Stacking performance and exact PDF caching

A fitted-Gamma stack evaluates all selected sources against every selected
event at each new spectral hypothesis. A source scan instead fits one source
at a time, defaults to its recorded adaptive declination window and can run
two independent single-thread workers with `run --task <id> --cpus 2`.
These workloads are different even when they contain the same catalog.

The same `--cpus N` option sets numerical-library thread limits for single-source
and joint stacking fits, including their user-authorized flux stages. It is a
thread budget, not a promise of N-fold acceleration. In `scan_and_stack`, the
joint fit uses the thread budget and the scan uses N single-thread processes.
The [CPU execution guide](cpu_execution.md) describes the shared interface.

The stacking spatial PDF depends on the source coordinates, event coordinates
and angular uncertainties, but not on Gamma or ns. Recomputing it on every
Gamma update repeats expensive trigonometric and exponential calculations.

## Lossless fit-local spatial cache

Fitted-Gamma DR2 spatial+energy stacks with multiple sources share one spatial
block cache across their datasets. Each block is first evaluated with the
original float64 formula, compressed using standard-library zlib and restored
bit for bit for later Gamma updates. Source weights, signal-energy PDFs and
their derivatives are still evaluated at the current Gamma. Event/source
block sizes, source ordering and weighted reductions are unchanged.

The shared compressed-payload budget is 1 GiB per fit, plus small bookkeeping
and the existing temporary block arrays. If the budget fills, uncached blocks
use the original formula. This limit is independent of catalog size. No full
uncompressed Cartesian array is allocated and no disk cache is written.

Each dataset has an independent namespace. Initializing a new trial discards
its previous spatial blocks, so event-RA scrambles, selected events and event
uncertainties cannot inherit stale geometry. No cache crosses analysis objects
or processes. Single-source, fixed-Gamma, spatial-only and DR1 fits do not
enable this cache.

The per-dataset `working_set.datasets.<dataset>.spatial_cache` in `report.yaml`
records the shared payload limit and current size, dataset block count,
compressed size, hits/misses and accumulated geometry, compression and
decompression seconds. The shared size appears in each dataset's record;
do not add those repeated shared-size values together.

## Exact observed-energy interpolation lookup

Multi-source DR2 spatial+energy fits also use an independent signal-energy
interpolation lookup for each dataset. A trial's exact valid observed
`log_energy` values are identified with `np.unique`; no rounding or new energy
bins are introduced. The existing `np.interp` evaluates each distinct energy
once for each requested signal-table declination/Gamma node. An inverse index
restores the value for every original event, including repeated energies and
the original zero for events outside the valid energy range.

The Gamma nodes remain the original table indices. The three-node Gamma
interpolation, its derivative, source weights and all weighted reductions
retain their original arithmetic and order. Only repeated energy-axis
interpolations are replaced by indexing their previously evaluated values.

Each dataset has a 16 MiB payload budget, including the inverse index, distinct
energies and cached float64 PDF values: at most 64 MiB across four datasets,
plus small bookkeeping and temporary initialization arrays. If the inverse
index and three lookup vectors cannot fit, the lookup is disabled. Once a
prepared lookup fills, uncached table nodes use the original interpolation.
Thus high-cardinality input energies cannot create an unbounded PDF cache.

Initializing a new trial clears all lookup vectors and rebuilds the energy
index. There is no sharing across datasets, analysis objects or processes.
Single-source, spatial-only and DR1 fits retain their existing path. Fixed-
Gamma multi-source spatial+energy fits may also use the lookup.

`working_set.datasets.<dataset>.energy_interpolation_cache` records whether
the lookup was enabled, its reason, payload budget/size, number of distinct
valid energies, cached PDF nodes, hits/misses, lookup-construction `np.interp`
call count/time, and whether the payload budget was saturated. Those call/time
counters exclude fallback interpolations; misses include prepared-lookup
requests that could not be cached. A disabled lookup has no construction calls.
The spatial cache's
1 GiB budget is separate from these four 16 MiB energy-lookup budgets.

## Verification and interpretation

Isolated kernel checks compare both the PDF ratio and its Gamma derivative
bit for bit, including changed weights, spectral endpoints, exhausted cache
budgets and new-trial invalidation. End-to-end fit checks must also compare
TS, ns, Gamma, convergence status and optimizer evaluation counts against
the unchanged scientific request through `run_agent_wrap.py`.

Energy-lookup checks additionally cover exact energy knots, valid-range
endpoints, out-of-range and nonfinite energies, repeated values, both source-
and event-declination signal PDFs, and multiple source blocks. Existing
diagnostic callers of `_gamma_slices` and `_interpolate_energy` retain their
original interfaces and interpolation behavior.

A warm-cache kernel benchmark does not include initial loading, hash checks,
cache construction, optimization or report generation. Historical elapsed
times also depend on machine load and suspension. Report kernel and complete
run measurements separately, with signed relative numerical differences
before signed absolute differences. A performance check does not establish
significance calibration, parameter coverage or publication readiness.

## Workflow and resource accounting

The cache is selected automatically by the existing public wrapper; it does not
add a scientific parameter or change a recorded fit procedure. Create the task,
require READY, then run it and inspect the scientific/artifact reviews as usual.
For `scan_and_stack`, the individual fits keep their adaptive event selection and
scan procedure; only the multi-source stack enables the applicable caches.
Historical results and existing background ensembles are not rewritten.

Cache budgets apply per analysis process, not to the entire machine. Multiple
simultaneous stacks each have their own budgets. The caches do not launch
workers or change CPU/thread settings. Preserve the task's CPU budget when
comparing timings. Report the two cache records in `working_set.datasets`
alongside the event/source block sizes when investigating performance.

Use an unchanged scientific request for before/after checks. Compare the event
selection, catalog/weights, numerical input hashes, TS, ns, Gamma, optimizer
status, calls and iterations; compare PDF ratios and Gamma derivatives bit for
bit before interpreting any timing change. Repeated-energy lookup is indexing
at the original values, not an approximation to nearby energies.

## Fit-time progress

The timing observer distinguishes first-call setup, full source-weighted PDF
recomputation and reuse of the existing PDF ratio, using unchanged cache keys.
Only current-run measurements and an explicitly uncalibrated initial workload
assumption predict remaining fit time; no old reports or historical matches
are read. Preparation, analysis, files/figures and review are timed separately.
After the first measured call, a new catalog gets a labelled rough ETA. Its
first-call cost excludes measured cache construction and includes a small
current-payload read probe, so startup is not multiplied by remaining calls. No
optimizer settings or scientific inputs change. See
[progress and elapsed time](task_timing.md) for the assumptions and measured
prediction errors.
