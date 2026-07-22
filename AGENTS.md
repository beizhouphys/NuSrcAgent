# NuSrcAgent Agent Guide

## Purpose

NuSrcAgent provides a Codex-native interface to deterministic time-integrated high-energy neutrino single-source, catalog-scan, and stacking analyses.

## Supported Interface

Use `run_agent_wrap_cdx.py` for every public CLI operation. Do not recreate removed legacy entry scripts.

The runtime is divided into:

- `agent_core_cdx/`: planning, task state, execution, validation, output, and review;
- `analysis_backend_cdx/`: callable likelihood implementations;
- `.agents/skills/he-neutrino-analysis-cdx/`: natural-language workflow;
- `legacy_cdx/`: historical research scripts outside the supported agent runtime.

## Scientific Safety

- Never invent gamma, catalog cuts, coordinates, weight definitions, or trial strategy.
- Ask the user when a scientific parameter is missing or ambiguous.
- Do not silently modify LLH definitions or optimizer behavior.
- Treat warning-bearing results as preliminary.
- Report the maximized-likelihood statistic as `TS`, not `TS_max`.
- Keep `data_input/` immutable and keep generated runs under `data_output/`.

## Development

- Keep the public CLI thin; place behavior in the relevant internal module.
- Avoid adding another root-level entry point.
- Add tests for planner, confirmation, recovery, completion, or CLI changes.
- Preserve repository-relative paths.
- Do not commit generated runs, figures, caches, credentials, or unrelated local data.

## Verification

Run:

```bash
python3 verify_private_alpha_setup_cdx.py --hashes
python3 -m unittest discover -s tests_cdx -p 'test_*_cdx.py' -v
python3 tools_cdx/evaluate_agent_cases_cdx.py --validate-golden
```

For release changes, also run one real single-source task and one small catalog scan plus stacking task.
