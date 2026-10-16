# Conditional event-RA calibration

The existing `dr2-empirical-scramble` interface prepares a prespecified random
catalog stack with uniform intrinsic weights, full14 data and frozen v3. It fits
ns and Gamma for observed data and every trial, preserving the same LLH/PDFs.
It is not a general user-catalog or source-scan post-trial calibration interface.
Choose the trial count, seeds, hypotheses and stopping strategy before running.

Each event RA is randomized independently and uniformly in [0,2π); all non-RA
event quantities and catalog positions remain fixed. Background alignment is
verified before RA is changed, and source–event spatial quantities are recomputed.

Fixed-N actions include `prepare`, `run`, `resume` and `report`; continuous and
host-shard actions preserve deterministic trial identities and checkpoint hashes.
Never start the same task directory on multiple computers. Stop is graceful:
running fits checkpoint before the task pauses. A code/input hash change requires
a separately reviewed successor rather than silently modifying a historical task.

The reported tail counts use TS_trial ≥ TS_observed and the documented
(K+1)/(N+1) estimator. K=0 is not p=0. Report one-sided Gaussian significance,
fixed-N intervals and anytime-valid confidence sequences when repeated inspection
or data-dependent stopping is possible. These Monte Carlo intervals do not
correct invalid trial sampling or hidden hypothesis selection.

New tasks follow the owner-approved discard-without-record rule for negative-TS
background fits. Its possible bias must be reviewed before interpreting the
retained ensemble as a calibrated null distribution. No significance claim for
an arbitrary catalog is justified by this implementation's historical runs.
