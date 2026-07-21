# HE-Neutrino Agent Wrapper Architecture

## Separation of responsibilities

```text
User language
    |
Codex Skill (language adapter)
    |
Persistent AgentTask + Planner
    |
Parameter confirmation gate
    |
Deterministic likelihood execution
    |
Run review + agent completion gate
    |
Audited user report
```

Codex interprets language but does not evaluate the likelihood. The deterministic pipeline does not interpret language. The persistent task between them records exactly what Codex understood and what the user confirmed.

## Components

- `.agents/skills/he-neutrino-analysis-cdx/SKILL.md`: natural-language workflow and reporting policy.
- `run_agent_wrap_cdx.py`: create, confirm, show, resume, and execute persistent tasks.
- `agent_core_cdx/task_state_cdx.py`: task schema, state transitions, parameter provenance, and persistence.
- `agent_core_cdx/planner_cdx.py`: source-count workflow selection, catalog inspection, and readiness checks.
- `agent_core_cdx/agent_orchestrator_cdx.py`: deterministic request construction, attempts, error classification, safe retry, and completion gate.
- `run_analysis_agent_cdx.py`: lower-level deterministic analysis entry point.
- `agent_core_cdx/review_cdx.py`: completed-run numerical and artifact review.

## Audit artifacts

Each task directory contains `task_cdx.json`, one immutable request per attempt, and final `agent_review_cdx.json`/`.md`. Each analysis run separately contains normalized configuration, provenance, tables, figures, workbook, and run review.

The request SHA-256 is stored for each attempt. An automatic retry is valid only when the hash is unchanged and `scientific_parameters_changed` is false.

## Interface boundary

The current adapter is repository-local Codex. A future ChatGPT Action, API CLI, or web application should create the same AgentTask schema and use the same state machine. Public adapters must expose only allow-listed task operations and must not provide source-code write access.

## Scientific boundary

The wrapper checks confirmations, finite ranges, artifacts, warnings, and declared completion. Validation of the likelihood model and cross-implementation scientific consistency is intentionally outside this wrapper release and must be reported separately.
