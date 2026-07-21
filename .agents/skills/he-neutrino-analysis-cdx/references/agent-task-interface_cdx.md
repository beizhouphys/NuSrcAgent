# Agent Task Interface

Use `run_agent_wrap_cdx.py` for every new analysis request. The wrapper stores tasks under `data_output/agent_tasks_cdx/<task_id>/task_cdx.json`.

## State meanings

- `AWAITING_CONFIRMATION`: show the persisted questions and wait for the user.
- `READY`: execute with `run --task`.
- `RUNNING` or `REVIEWING`: do not create a duplicate; inspect the task and explicitly resume only after confirming the earlier process stopped.
- `COMPLETED`: report results normally.
- `COMPLETED_WITH_WARNINGS`: report results together with every material warning.
- `FAILED`: report the failure and recommended action; do not present numerical output as valid.

## Parameter provenance

Each parameter stores `value`, `source`, and `confirmed`. `user` means explicitly supplied or confirmed by the user. `agent_inferred` is limited to unambiguous structural catalog columns. `system` and `system_default` values must not be used to hide a scientific choice.

Column weighting requires both a column name and a user-confirmed physical meaning or units. Uniform weighting requires no weight meaning. A new scientific choice after completion creates a new task.

## Recovery

The wrapper records one attempt per execution and hashes the deterministic request. Only dependency, output-generation, and transient I/O failures may retry automatically, at most once, using the identical request hash. Use `resume` only for a task left in `RUNNING` or `REVIEWING` after an interrupted process.
