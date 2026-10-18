---
name: nusrcagent
description: Coordinate supported IceCube time-integrated single-source searches, catalog scans and stacking through persistent tasks and scientific review.
---

# NuSrcAgent

Use the repository wrapper for every analysis. Read `AGENTS.md` and
`docs/scientific_status.md`; numerical success does not establish scientific validity.

## Response language

- Follow the user's explicit language request. Otherwise, honor an explicitly
  established personal response-language preference.
- If neither applies, follow the language of the current request.
- If there is no preference or usable language cue, including a bare
  `$nusrcagent` invocation, respond in English.
- Do not infer a response-language preference from the language used to write
  `AGENTS.md`, skill instructions or other repository files.

## Clarification policy

Ask only about unresolved ambiguity that materially changes the spectrum,
relative weights, source/event membership, fit hypotheses or trial family.
Unsigned gamma 2.53 conventionally means E^-2.53; record that interpretation
and pass CLI `--gamma -2.53`. A bare explicit positive sign needs clarification;
preserve a power-law exponent explicitly defined by the user.
A unique column identifying requested flux/relative weights may be used with
recorded metadata. A common unknown multiplicative unit cancels in normalized
weights. Do not invent absolute units or drop invalid rows.
The example's radio_weight is an illustrative relative proxy, not a measured flux.

Record interpretations with repeatable
`--interpretation-note PARAMETER=EXPLANATION`; never pretend these are user
confirmations. Supplied spectral indices are fixed unless fitting is requested.

## Execution

1. Work from this checkout root with its pinned `.venv/bin/python`.
   Run `run_agent_wrap.py environment-check` for the selected sample/mode.
   Stop on failed preflight and explain missing inputs/dependencies.
2. Exactly one source selects single-source analysis. DR2 catalogs select
   `--catalog-operation stack|scan|scan_and_stack`; scan-only needs no weights.
   DR1 retains its existing scan+stack behavior.
3. Approved DR2 defaults: full14 spatial+energy, fitted ns and Gamma, seed
   CLI -3.0 / SkyLLH 3.0. Spatial-only fixes acceptance Gamma at CLI -2.5;
   it does not measure the source spectrum. Select DR1 only when requested.
4. Persist the request through `create-single` or `create-catalog`. Use
   `confirm` only for actual user answers. Run only tasks whose state is READY.

```bash
.venv/bin/python run_agent_wrap.py create-single --request "<request>" --name "<source>" --ra-deg <ra> --dec-deg <dec>
.venv/bin/python run_agent_wrap.py create-catalog --request "<request>" --catalog <catalog.csv> --catalog-operation scan_and_stack --weight-mode uniform
.venv/bin/python run_agent_wrap.py run --task <task_id>
```

Use explicit column options for a catalog. The three-row example uses
`--name-column name --ra-column ra_deg --dec-column dec_deg`.
The optional built-in RFC catalog requires a separately obtained external input;
do not assume it is bundled.

5. Read the central task's `agent_review.json` and the run's `review.json` /
   `review.md`. Report every material warning. Never present failed-review
   numerical output as valid. If necessary, use `review-run`.
6. Inspect the expected tables, configuration, provenance and output artifacts.
   DR2 produces numeric reports and reviews; DR1 additionally has figures and
   optional workbook generation. Do not require unavailable DR2 workbook output.
7. Only dependency, transient I/O or output-generation failures may retry once
   with an unchanged request hash. Never repair scientific settings automatically.

## Follow-up analysis

`inspect-catalog` inspects inputs. `dominance` and `review-dominance` examine
source influence in a reviewed fitted-Gamma stack. Delta TS from deleting sources
is not source-detection significance.

`dr2-ra-scramble` is a fixed-Gamma smoke test, not empirical calibration.
`dr2-empirical-scramble` has the limited existing random-catalog stack scope
described in `docs/dr2_empirical_scrambling.md`; do not promise calibration for
arbitrary user catalogs or individual-source scans. Agree the trial family,
count, seeds and stopping strategy before any background trials. Negative-TS
discarding requires scientific review. Time-dependent trials are unsupported.

## Reporting

Report fitted quantities, TS, p-value and the corresponding significance together.
Use the one-sided Gaussian convention `Z = Phi^-1(1 - p)` in sigma and label
local/pre-trial versus post-trial and analytic versus empirical values. For ordinary local estimates, use half-chi-square dof=2 when Gamma is
free (`gamma_mode=fitted`) and dof=1 when Gamma is fixed. With `TS > 0`, use
`p = 0.5 exp(-TS/2)` for dof=2 or `p = 0.5 erfc(sqrt(TS/2))` for dof=1.
Always convert with `Z = Phi^-1(1-p)`; `Z = sqrt(TS)` applies only to dof=1.
At `TS=0`, retain the reporting convention `p=0.5`, `Z=0`.
Label both p-value and significance as estimates, record the dof and method,
and do not claim empirical calibration or a verified asymptotic distribution
for free Gamma. Do not apply these formulas to empirical or catalog-corrected
p-values or to a search across several fixed-Gamma hypotheses.
Unavailable post-trial quantities must remain unavailable.

Ordinary fits execute zero background trials. Record the requested and executed
counts and the analytic method as information, without creating a warning solely
for absent trials, analytic local calibration or unavailable empirical/post-trial
values. When all other checks pass, return `COMPLETED`. Actual fit-quality,
input or artifact warnings still produce `COMPLETED_WITH_WARNINGS`; `COMPLETED`
does not by itself establish a calibrated detection or publication readiness.

Use TS after likelihood maximization. Distinguish analytic local approximations
from empirically calibrated values and catalog-global quantities. Report the data
sample, likelihood mode, source count, weights, fitted/fixed Gamma, ns, TS, p-value and one-sided significance,
review status, artifacts and limitations. Include signed relative difference
before signed absolute difference in comparisons.

See [task interface](references/agent-task-interface.md) and
[scientific review policy](references/scientific-review-policy.md).
