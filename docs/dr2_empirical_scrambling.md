# Estimating significance with event-RA background trials

A fitted TS is not a probability. Background trials estimate how often a
background-only data realization gives a TS at least as large as the observed
one. Here the realizations are made by randomizing each event's right ascension
(RA), under the time-integrated uniform-RA background assumption.

## Current scope

The existing `dr2-empirical-scramble` interface prepares a prespecified random
catalog stack with uniform intrinsic weights, full14 data and frozen v3. It fits
ns and Gamma for observed data and every trial, preserving the same LLH/PDFs.
It is not a general user-catalog or source-scan post-trial calibration interface.
Choose the trial count, seeds, hypotheses and stopping strategy before running.

This is a separate calculation, not a step automatically performed by the
ordinary `run` command. The worked single-source and three-source examples do
not run these trials, and this specialized interface does not calibrate them.

## Preparing a new background-trial calculation

Read the [scientific status](scientific_status.md) and
[frozen v3 definition](dr2_v3_release.md), then check the selected catalog,
weights, event cuts and hypothesis family against the current request. Record
input fingerprints and the approved fit settings. Ask about unresolved choices
that materially change the calculation; historical examples do not authorize
a new run. Use `.venv/bin/python run_agent_wrap.py`; the environment check must
pass and the persistent task must reach `READY` before execution.

For the supported random-catalog stack, a separately authorized small timing
pilot can assess runtime and memory on the actual catalog and worker setup.
It does not precisely measure a tail probability. Choose the production trial
count or stopping strategy and Monte Carlo precision in advance; do not stop
solely because a target significance has been reached. Do not choose among PDF
versions using their resulting p-values. These preparation requirements do not
extend the interface to arbitrary user catalogs or source scans.

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
retained ensemble as a calibrated null distribution. No significance claim for
an arbitrary catalog is justified by this implementation's historical runs.

Report observed TS, fitted ns/Gamma, the trial TS distribution, K/N, p-value
and intervals, one-sided significance, fit boundaries, failures, runtime and
the input/fit/review records. Disclose any choices informed by observed results:
freezing them afterwards does not remove selection bias. Several catalog,
weight or cut choices require trials covering that selection; the current
fixed-stack interface does not provide that general correction. PDF tuning,
signal injections and time-dependent trials require separately defined work.
