# Agent Design and Behavior

## Architecture

NuSrcAgent separates natural-language interpretation from deterministic execution:

```text
Codex Skill
  -> task planner and confirmation gate
  -> persistent AgentTask
  -> deterministic likelihood backend
  -> artifact and scientific review
  -> completion gate
```

Codex interprets Chinese, English, or mixed-language requests. The Python layer receives structured coordinates, catalog paths, gamma values, and weighting choices; it does not call an LLM API.

## Workflow Selection

- Exactly one source selects `single_source`.
- Multiple sources or a multi-row catalog select the catalog workflow. For the default DR2 backend this runs the requested stack; the explicitly selected legacy 10-year backend retains its source scan plus stacking outputs.
- Inspection-only requests use `inspect-catalog`.
- Existing results use `review-run`.
- Unclear source count or intent requires a user question.

## Parameter Gate

Execution is blocked until required scientific choices are explicit. The owner-approved default is the 14-year DR2 spatial+energy sample with fitted Gamma and a legacy-convention seed of `-3.0`. Explicit DR2 spatial-only requests use `gamma_mode=fixed` and default acceptance Gamma `-2.5`; this Gamma controls detector-acceptance weights and is not a fitted spectrum.

The default DR2 fit uses SkyLLH Gamma bounds `[1.0, 6.0]` (legacy convention
`[-6.0, -1.0]`) and `ns` bounds `[0, 10000]`; each run records these bounds and
the Gamma/`ns` seeds in its result provenance.

User confirmation remains required for:

- a finite negative spectral index gamma for fixed-Gamma analyses (or a non-default fit seed/range);
- for stacking, uniform, catalog-column, or manual weighting;
- the physical meaning or units of a selected weight column;
- coordinate-column interpretation when it cannot be inferred safely.

Each parameter records its value, provenance, and confirmation state.

## Task States

`DRAFT`, `AWAITING_CONFIRMATION`, `READY`, `RUNNING`, `REVIEWING`, `COMPLETED`, `COMPLETED_WITH_WARNINGS`, and `FAILED` are persisted under `data_output/agent_tasks_cdx/`.

A terminal task is immutable. A changed scientific choice creates a new task.

## Recovery and Completion

Only dependency, output-generation, or transient I/O failures may retry automatically, at most once, with an identical request hash. Gamma, weights, catalog membership, coordinates, trial definitions, optimizer bounds, and likelihood definitions are never changed automatically.

Completion requires confirmed parameters, a recorded run directory, and a completed-run review. Warning reviews produce `COMPLETED_WITH_WARNINGS`; failed reviews produce `FAILED`, whose numerical results must not be presented as valid.

## Interfaces

`run_agent_wrap_cdx.py` is the sole public Python CLI. It exposes task creation, confirmation, execution, resume, display, catalog inspection, and run review as subcommands. Internal modules may be imported directly by tests and development tools but are not separate user interfaces.
