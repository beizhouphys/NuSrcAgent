# HE-Neutrino Analysis Agent Wrapper

This repository-local Codex Skill turns Chinese, English, or mixed-language requests into persistent, reviewed single-source or catalog analysis tasks. Exactly one source selects single-source analysis. Multiple sources select a catalog-wide single-source scan plus stacking.

## Codex usage

Start a prompt with `$he-neutrino-analysis-cdx` or ask naturally for an HE-neutrino source analysis in this repository. Codex creates a task, asks only unresolved scientific questions, runs the deterministic pipeline after confirmation, and reports the review status and artifacts.

## Direct task interface

Create a task without silently defaulting gamma:

```bash
python3 run_agent_wrap_cdx.py create-single \
  --request "Analyze TXS 0506+056" \
  --name "TXS 0506+056" --ra-deg 77.3582 --dec-deg 5.6931
```

Confirm the question and execute:

```bash
python3 run_agent_wrap_cdx.py confirm --task <task_id> --gamma -2.53
python3 run_agent_wrap_cdx.py run --task <task_id>
```

For a catalog:

```bash
python3 run_agent_wrap_cdx.py create-catalog \
  --request "Analyze this catalog with uniform weights and gamma -2.53" \
  --catalog configs_cdx/examples_cdx/catalog_sources_rfc100_cdx.csv \
  --gamma -2.53 --weight-mode uniform
```

Task records are written under `data_output/agent_tasks_cdx/`. Numeric run outputs remain under `data_output/runs_cdx/`, and figures remain under `figures/runs_cdx/`.

## Status contract

- `AWAITING_CONFIRMATION`: answer the persisted questions; the LLH has not run.
- `READY`: all required parameters are confirmed.
- `COMPLETED`: execution and review passed.
- `COMPLETED_WITH_WARNINGS`: results exist but every warning must be reported.
- `FAILED`: do not present numerical output as valid.

## Verification

```bash
python3 -m unittest discover -s tests_cdx -p 'test_*_cdx.py' -v
python3 evaluate_agent_cases_cdx.py --validate-golden
python3 evaluate_agent_cases_cdx.py \
  --predictions tests_cdx/natural_language_predictions_codex_development_cdx.json
```

See `AGENT_BEHAVIOR_SPEC_cdx.md` for behavioral rules, `AGENT_ARCHITECTURE_cdx.md` for component boundaries, and `AGENT_EVALUATION_cdx.md` for current evidence and remaining release claims.
