# DR2 empirical event-RA calibration

A background-trial calculation estimates how often background alone gives a
TS at least as large as the observed fit. It is distinct from fitting the
observed data: ordinary single-source/scan/stack commands do not perform these
trials. Event RA means right ascension. The procedure below randomizes it under
the time-integrated uniform-RA background assumption, while keeping other event
quantities and the chosen analysis fixed.

The public `dr2-empirical-scramble` workflow follows a reviewed DR2
single-source analysis or stacking analysis. It imports the observed primary
result without another maximization and freezes its source list, weighting
factors, event selection, spectrum, PDFs, interpolation, fit bounds, initial
values and optimizer random seed. Fixed/fitted Gamma, spatial+energy and
spatial-only modes retain their original settings. A fixed supplied spectrum
retains its shape without fitting a fictitious PL Gamma.

```bash
.venv/bin/python run_agent_wrap.py dr2-empirical-scramble \
  --action prepare --baseline-task <analysis_task_id_or_path> \
  --output-directory <new_directory> --n-trials 100 --workers 2 \
  --seed 20261023 --request "Calibrate this specified analysis with 100 background trials"
.venv/bin/python run_agent_wrap.py dr2-empirical-scramble \
  --action run --output-directory <new_directory>
```

`prepare` checks primary scientific/artifact review, sealed primary artifacts,
scientific code/input hashes and package versions, and creates a `READY` task.
It does not run trials or modify the original analysis. A primary result at
`AWAITING_FLUX` can be used; flux calculation is independent and still requires
the user's separate continuation reply. The trial seed controls event RA;
the optimizer keeps the original analysis random seed. Existing source
coordinates and weighting factors are never replaced by random sources.

For continuous trials, replace `--n-trials 100` with `--continuous` during
preparation, then use `--action launch`. No ending time is set. `status` and
`snapshot` export completed-trial statistics, `stop` is graceful, and `resume`
continues with unused deterministic trial indices. Fixed-N runs also support
`--max-fits` for an operational pilot and later `resume`; a pilot is not a
precision significance measurement. Choose the trial budget or stopping rule
before production. Changing inputs/code blocks continuation rather than
rewriting existing checkpoints.

Outputs include `background_trials.csv`, `results_snapshot.md`,
`ts_background_snapshot.png` and `.pdf`, plus machine-readable snapshots,
per-fit reviews and provenance. Both p-value and one-sided significance include
68%/95% fixed-N Clopper-Pearson intervals and anytime-valid confidence sequences.
Primary warnings remain visible. Ordinary fits do not launch trials automatically.
The selected hypothesis is one specified single-source analysis or stacking
analysis; a stacking component of `scan_and_stack` calibrates only that stack.
This does not calibrate the largest TS from a catalog scan, choices among
weighting schemes/cuts, DR1, or time-dependent searches.

## What is randomized?

Each event RA is randomized independently and uniformly in [0,2π); all non-RA
event quantities and catalog positions remain fixed. Background alignment is
verified before RA is changed, and source–event spatial quantities are recomputed.
Declination, reconstructed energy, angular uncertainty, observation-period
membership and event counts are preserved. Every background trial repeats the
same fitted parameters and analysis choices as the observed fit. This tests a
conditional background hypothesis; it does not establish unbiased ns/Gamma.

Original source–event spatial geometry cannot be reused after changing RA.
Caching unchanged energy/declination quantities requires an equivalence check.
The fixed-Gamma `dr2-ra-scramble` smoke test cannot replace free-Gamma trials,
and an observed TS from a different maximizer or scientific configuration
cannot serve as the reference for the current ensemble.

## Running and retaining the trial ensemble

Fixed-N actions include `prepare`, `run`, `resume` and `report`; continuous and
host-shard actions preserve deterministic trial identities and checkpoint hashes.
Never start the same task directory on multiple computers. Stop is graceful:
running fits checkpoint before the task pauses. A code/input hash change requires
a separately reviewed successor rather than silently modifying a historical task.
Here a checkpoint is a saved completed trial that allows a long calculation to
continue without repeating it. A host shard is a separate group of trials run
on one computer; it must not have two computers writing into the same directory.

## Interpreting the reported probability

The reported tail counts use TS_trial ≥ TS_observed and the documented
(K+1)/(N+1) estimator. K=0 is not p=0. Report one-sided Gaussian significance,
fixed-N intervals and anytime-valid confidence sequences when repeated inspection
or data-dependent stopping is possible. These Monte Carlo intervals do not
correct invalid trial sampling or hidden hypothesis selection.
Here N is the number of retained background trials and K is the number with
TS at least as large as the observed TS. The quoted Gaussian significance is
the one-sided Gaussian tail equivalent of that probability. Monte Carlo
intervals describe uncertainty from the finite number of trials, not detector
or PDF systematics. An anytime-valid confidence sequence is the interval used
when progress can be checked repeatedly or the run can be stopped after looking
at it; an ordinary fixed-N interval alone does not cover that stopping procedure.

New tasks follow the owner-approved discard-without-record rule for negative-TS
background fits. Its possible bias must be reviewed before interpreting the
retained ensemble as a calibrated null distribution. Historical random-catalog trials do not calibrate a different source/catalog hypothesis.

Report observed TS, fitted ns/Gamma, the trial TS distribution, K/N, p-value
and intervals, one-sided significance, fit boundaries, failures, runtime and
the input/fit/review records. Disclose any choices informed by observed results:
freezing them afterwards does not remove selection bias. Several catalog,
weight or cut choices require trials covering that selection; this specified-analysis workflow does not provide that general correction. PDF tuning,
signal injections and time-dependent trials require separately defined work.
