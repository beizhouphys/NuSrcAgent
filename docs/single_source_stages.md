# Single-source results in two stages

The primary LLH fit can finish well before flux confidence intervals and figures.
New wrapper-created single-source tasks return the reviewed primary fit first,
so the Agent can report it immediately and continue the flux calculation.

1. Create and confirm the task as usual. Once READY, run
   `.venv/bin/python run_agent_wrap.py run --task <task_id>`.
   This step maximizes LLH and reviews the fit and its saved artifacts. Read
   `single_source_llh_summary`, then send best-fit ns, Gamma, TS, local p value
   and one-sided significance in a chat bubble. The summary states the spectral
   exponent convention and whether Gamma was fitted or fixed; p value and
   significance retain the approved analytic estimate and its recorded method.
2. If status is AWAITING_FLUX, automatically run
   `.venv/bin/python run_agent_wrap.py run --stage flux --task <task_id>`.
   Read `single_source_flux_summary`, report the reviewed flux quantities with
   units and confidence levels, show the spectrum PNG (and contours when
   available), and link the PDF and numerical tables. This is part of the same
   user request and requires no extra confirmation.

The first-stage request contains no flux calculation. The complete scientific
request is separately hashed in the task and primary checkpoint. The flux stage
reconstructs the same LLH at the recorded primary best fit, checks that its value
reproduces TS, and performs the original requested flux calculations. It does
not repeat primary maximization or replace its best-fit ns, Gamma, TS, optimizer
status, bounds or procedure. Fixed-spectrum upper-limit hypotheses still require
their own ns fits; those belong to the second stage.

The existing strict TS > 9 measurement rule, 95% limits for exponents -2, -2.5,
-3, reference spectra and figure style are unchanged. See
[measurements](flux_measurements.md) and [upper limits](flux_upper_limits.md).

Each stage writes a separate run directory and review. The immutable first-stage
artifacts remain under `artifacts.llh_run_directory`; the JSON checkpoint is
`artifacts.llh_checkpoint`. AWAITING_FLUX means the first stage passed review
and the full task remains unfinished. COMPLETED is reached after both requested
stages pass. Scientific warnings retain COMPLETED_WITH_WARNINGS. A failed primary
review blocks flux execution and valid numerical reporting. A failed flux stage
retains the reviewed first-stage result but no failed flux result is reported as
valid. Only dependency, output-generation and transient I/O errors may retry
once with the identical stage request; a flux retry never reruns the primary fit.

An interrupted RUNNING/REVIEWING flux process must first be confirmed stopped.
Use `resume --task <task_id>`, then `run --stage flux --task <task_id>`.
The continuation checks checkpoint and artifact hashes, code, inputs and package
versions; changes block it and require a new explicit request. A per-task process
lock rejects simultaneous stage execution. Parameters cannot change while flux
is pending. Repeated primary execution is rejected.

One-row catalogs selected as single-source tasks follow the same workflow.
Catalog individual-source scans retain their existing execution and optional
flux switch. Historical records are not migrated. DR1 and spatial-only modes
do not gain new flux capabilities; modes with no supported/requested flux
products complete after the primary fit and report that stage alone.

## Verification of the execution change

Fixed-Gamma NGC 1068 completed both stages, including three fixed-spectrum
limits, primary normalization intervals and the spectrum figure. A default
fitted-Gamma low-TS source produced limits without a reported measurement, and
a small catalog scan plus stack retained its existing reviewed behavior.
Comparing the one-call and two-stage fixed-Gamma results gave signed relative
difference 0 and signed absolute difference 0 for all 22 checked fit, limit and
interval quantities. These comparisons verify the execution change without
changing the scientific definitions.
