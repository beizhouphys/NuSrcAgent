# Agent Task Interface

Use `run_agent_wrap.py` for every new analysis request. The wrapper stores tasks under `data_output/agent_tasks/<task_id>/task.json`.

## State meanings

- `AWAITING_CONFIRMATION`: show the persisted questions and wait for the user.
- `READY`: execute with `run --task`.
- `RUNNING` or `REVIEWING`: do not create a duplicate; inspect the task and explicitly resume only after confirming the earlier process stopped.
- `COMPLETED`: report results normally.
- `COMPLETED_WITH_WARNINGS`: report results together with every material warning.
- `FAILED`: report the failure and recommended action; do not present numerical output as valid.

## Parameter provenance

Each parameter stores `value`, `source`, and `confirmed`. `user` means explicitly supplied or confirmed by the user. `agent_inferred` covers unambiguous structural catalog columns. `agent_interpreted` identifies an approved interpretation under the skill's clarification policy, with its rationale stored in `interpretation`. Use repeatable creation options `--interpretation-note PARAMETER=EXPLANATION` for gamma, gamma_mode, weight_column or weight_meaning. This marks provenance only: it neither supplies missing values nor changes readiness or scientific validation. `system` and `system_default` values must not hide a scientific choice.

Column weighting requires a column name and a recorded meaning, supplied by the user, catalog metadata or an approved relative-weight interpretation. Unknown common absolute units do not block normalized weighting; identify a proxy honestly and do not invent physical units. Multiple scientifically distinct candidate columns still require clarification. Uniform weighting requires no weight meaning. A new scientific choice after completion creates a new task.

## Built-in catalogs

Use `create-catalog --built-in-catalog radio_bright_agn_rfc2019c_3386` for the owner-defined RFC 2019c radio-bright AGN catalog. The task records `inputs.kind=built_in_catalog`; the analysis request records `catalog.builtin`; validation and normalization load the source rows directly from `analysis_backend/sources.py`. Do not materialize an intermediate CSV or add another runner. Coordinate columns are `source_name`, `ra_deg`, and `dec_deg`; the available model-weight column is `xband_flux_jy`, representing X-band flux density in Jy. Use that catalog metadata to resolve radio-flux weighting without asking the user to repeat it.

For a GitHub installation, prefer the bundled full-precision CSV at
`data_input/sources/radio_bright_agn_rfc2019c_xband_ge_0p15_dec_lt87_3386.csv`
through `create-catalog --catalog <path>`, with `source_name`, `ra_deg`,
`dec_deg` and optional `xband_flux_jy` weighting. The built-in reader above
instead needs the original raw RFC file, which is not bundled. Do not rebuild
or materialize another catalog when the supplied CSV already matches the request.

## Coordinate inputs

All supported analyses use the shared coordinate conversion before backend
evaluation. ICRS RA/Dec and Galactic l/b accept explicit degree/radian units;
ICRS RA also accepts hourangle and sexagesimal strings. Generic single-source
options are `--longitude`, `--latitude`, `--coordinate-frame`,
`--longitude-unit` and `--latitude-unit`. Catalogs additionally accept
`--longitude-column` and `--latitude-column`; repeated `--source` values use
the declared frame/units. Existing degree-only options retain their contract.
Missing frame or units block readiness; use `confirm` with the actual user
clarification. Preserve `coordinate_input` provenance through the request and
normalized sources. See `docs/coordinates.md`.

## Recovery

The wrapper records one attempt per execution and hashes the deterministic request. Only dependency, output-generation, and transient I/O failures may retry automatically, at most once, using the identical request hash. Use `resume` only for a task left in `RUNNING` or `REVIEWING` after an interrupted process.

## Single-source stage state

New single-source tasks record `execution_flow=single_source_two_stage_v1`.
`run --task` executes the primary fit and its review; chat output must show
`single_source_llh_summary` in the first-stage final answer, ask whether to
continue with flux products, and end the turn before any flux command. `AWAITING_FLUX` means
that the primary result is valid and the requested flux products remain pending;
it is not a final task completion. Wait for the user's continuation reply, then
run `run --stage flux --task <id> --flux-user-reply "<actual user reply>"` in the
later turn. The CLI rejects a missing/blank reply and records it on each flux
attempt. This is user authorization, not a change to scientific parameters. Parameters are frozen after the primary result.
The final run and original LLH run have separate artifact directories and
reviews. `artifacts.llh_run_directory` and `artifacts.llh_checkpoint` preserve
the first result even if the second stage fails. `show` returns these states
and summaries. An interrupted flux stage resumes to `AWAITING_FLUX` after
`resume`; historical tasks keep their recorded one-call behavior. Modes without
supported/requested flux products finish after the primary stage.

## Stacking continuation after primary output

At AWAITING_FLUX, report `stacking_stages.primary` in a final answer, ask whether
to continue, and end the turn. After the user replies, use the same task with
`run --task <id> --stage flux --flux-user-reply "<actual user reply>"`.
Do not launch flux from the first turn or fabricate the reply. Report reviewed
flux quantities and figures in the next final answer. Multiple pending tasks
must be selected from conversation context; ask only if the selection is unclear.

## Background-trial continuation

A reviewed DR2 single-source or stacking primary can be followed by
`dr2-empirical-scramble --action prepare --baseline-task <task_id_or_path>`.
Choose a new output directory and the agreed trial budget or `--continuous`.
Preparation creates a separate READY task, imports the primary result without
rerunning its maximization, and inherits its scientific settings. It leaves
the original analysis and its flux gate unchanged. Run fixed-N trials with
`--action run`; launch a continuous task with `--action launch`. Snapshot,
graceful stop and resume preserve completed checkpoints and deterministic
seed allocation. Statistics cover only the specified source or stack, not a
catalog-scan maximum. See the background-trial guide for interval conventions.

## Time-dependent primary results

New DR2 time-dependent tasks default to `per_source_catalog_windows`, including
when scope is omitted from `--temporal-file`. Require fixed per-source box or Gaussian profiles before READY. Omitted detector
phases are derived from detector-uptime overlap; the background-time model defaults
to uniform_livetime. Explicit supported settings take precedence. Choose
`scan`, `stack` or `scan_and_stack` for the requested catalog operation; the
default catalog operation remains `scan`. `run` and `show` return
`time_dependent_summary` with ns/s/TS and artifact paths. Observed fits run
zero trials and have unavailable significance, with no flux continuation.
Requested `td-background-trials` follow-ups provide empirical local,
catalog-maximum and stacking p-values/significances after a complete ensemble.
See `docs/time_dependent_catalog.md` for commands and fixed-window calibration.
The legacy Gaussian/box time-search workflow requires explicit
`scope=legacy_time_profile` for new tasks; existing saved tasks retain their
recorded interpretation. See `docs/time_dependent.md` only for legacy requests.
