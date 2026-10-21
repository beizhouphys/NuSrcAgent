# Individual-source event selection and input reuse

New DR2 single-source tasks and catalog scans use a source-centered declination
window. Its half-width starts at 20 degrees and expands until IC40, IC59, IC79
and IC86 I–XI each retain at least 20% of their own full event sample. A single
half-width is used for all four datasets; boundaries are clipped at the poles.
The background spatial PDF is conditioned using the frozen model's integral
over the selected interval. No event-count normalization is substituted.

For an individual-source task or scan, add `--source-dec-window-deg 30` at
creation to start with a larger minimum half-width. Values below 20 degrees
are rejected. Add `--full-sky-events` at creation for the original all-event
fit. Explicit `--event-dec-min-deg`, `--event-dec-max-deg` or
`--event-abs-dec-max-deg` instead retain their existing selection rules and
cannot be combined with the adaptive source window. The default is recorded
in the persistent task before execution; the task must still reach `READY`.
Historical tasks without the new setting keep their recorded all-event or
explicit-cut behavior. DR1 and the stack part of `scan_and_stack` are unchanged.

Every individual result records `source_dec_window`, the actual declination
bounds, `event_counts_before_selection`, selected `event_counts`, retained
fractions and `background_spatial_conditional_normalization`. Scientific review
checks the requested minimum half-width, source-centered boundaries and the
20% requirement separately for each dataset. A windowed fit can differ from
an all-event fit: retaining 20% does not prove parameter bias or significance
coverage. Any background trials for a windowed fit must repeat the same event
selection and fit procedure; historical ensembles must not be relabeled.

During a scan the runtime loads each dataset once and keeps immutable complete
data templates. Each source receives fresh mutable data and its own selected
events. The PDF store keeps validated background PDF tables and compact signal
energy PDF grids, keyed by dataset and the complete Gamma grid. It does not
keep one source's fitted state or selected event sample for another source.
The cache is released when the scan ends. Independent CLI processes have
independent caches; no cross-process memory cache or persisted hash trust is
introduced.

SHA-256 values are cached in memory by resolved path, device, inode, size,
mtime and ctime. Unchanged files are hashed once per process; a changed file
requires a fresh hash. Reusing loaded neutrino data or PDF tables also checks
file identities and fails if a loaded input changed. Frozen hashes and table
bytes are unchanged. The first load still performs the complete required PDF
verification. Per-source `execution.cache_stats` records data loads, cache hits,
PDF table loads and signal-file verifications.

Use `run --task <id> --workers N` to select a positive CPU budget (default 1).
Single-source and joint stacking fits set numerical-library thread limits before
loading the analysis modules. DR1 and DR2 catalog scans use N independent processes,
each limited to one numerical thread and keeping its own complete input cache.
See [CPU selection](cpu_execution.md) for primary/flux commands and provenance.
