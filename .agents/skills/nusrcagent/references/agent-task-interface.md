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

## Recovery

The wrapper records one attempt per execution and hashes the deterministic request. Only dependency, output-generation, and transient I/O failures may retry automatically, at most once, using the identical request hash. Use `resume` only for a task left in `RUNNING` or `REVIEWING` after an interrupted process.
