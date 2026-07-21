# HE-Neutrino Agent Behavior Specification

## Scope

The agent wrapper interprets analysis requests, selects a supported deterministic workflow, confirms required scientific parameters, executes the existing likelihood pipeline, reviews artifacts, and reports completion. It does not modify likelihood source code or silently choose scientific assumptions.

## Tool Selection

| Input | Selected workflow |
|---|---|
| Exactly one source | Single-source analysis |
| More than one source or a multi-row catalog | Catalog-wide single-source scan plus stacking |
| Existing run directory | Completed-run review |
| Catalog-inspection request only | Catalog inspection |
| Ambiguous source count or analysis request | Ask the user |

The selected workflow and reason are persisted in `task_cdx.json` before execution.

## Parameter Gate

Every analysis requires a user-confirmed negative spectral index. Multi-source stacking also requires a confirmed weighting mode. Column weighting additionally requires a confirmed column and its physical meaning or units. Manual weighting requires one confirmed non-negative value per source.

An inferred coordinate column may be accepted when catalog inspection identifies one unambiguous alias. The inference and its source remain visible in the task record. Scientific parameters are never inferred merely because a numeric column exists.

## States

`DRAFT -> AWAITING_CONFIRMATION -> READY -> RUNNING -> REVIEWING -> COMPLETED | COMPLETED_WITH_WARNINGS | FAILED`

Only `READY` tasks can execute. An interrupted `RUNNING` or `REVIEWING` task requires an explicit resume operation.

## Recovery

The wrapper may retry an identical request once for dependency, output-generation, or transient I/O failures. It records the error category, repair action, request hash, and that scientific parameters were unchanged. Data-validation, scientific-ambiguity, fit-behavior, and unknown internal failures do not trigger automatic scientific changes.

## Completion

`COMPLETED` requires all parameters confirmed, a recorded run directory, and a passing completed-run review. A review warning produces `COMPLETED_WITH_WARNINGS`. Any review failure produces `FAILED`; numerical results from that task must not be presented as valid.

## Current Boundary

Natural-language interpretation is supplied by Codex through the repository Skill. The persisted task is interface-independent and can later be created by a ChatGPT, API, CLI, or web adapter. This specification covers agent behavior and artifacts, not validation of the underlying likelihood model.
