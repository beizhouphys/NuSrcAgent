# Agent Wrapper Evaluation

## Scope

This evaluation covers the human-agent wrapper: workflow selection, parameter confirmation, task persistence, recovery policy, review propagation, and completion status. It does not claim validation of the underlying likelihood model.

## Deterministic suite

`tests_cdx/test_agent_wrap_cdx.py` verifies:

- one source selects single-source analysis;
- multiple sources select catalog scan plus stacking;
- missing gamma and weighting decisions block execution;
- column weights require a physical meaning;
- malformed coordinates and manual weights are blocked;
- confirmed tasks become ready and persist across reloads;
- terminal tasks cannot be mutated;
- pass, warning, and fail reviews map to distinct terminal states;
- safe failures retry once with an identical request hash;
- scientific/data failures do not receive automatic scientific changes.

## Language-adapter suite

`tests_cdx/natural_language_eval_cases_cdx.json` contains 16 Chinese, English, and mixed-language prompts, including ambiguous requests and safety challenges. `evaluate_agent_cases_cdx.py` validates the corpus and scores adapter predictions by exact match and safety-case pass rate.

The deterministic core can be tested offline. Repeated independent Codex runs are required before publishing a quantitative natural-language accuracy claim; a single development conversation is not an unbiased language-model evaluation.

## Development verification on 2026-07-21

- 21 deterministic wrapper tests passed on Python 3.8.15.
- The 16-case language corpus passed schema validation.
- The current development-session Codex trace in `tests_cdx/natural_language_predictions_codex_development_cdx.json` scored 16/16, including all safety cases. This is a conformance trace, not an independent accuracy estimate.
- Real-backend task `task_20260721T190853271003Z_cdx` completed the single-source path with warnings correctly propagated.
- Real-backend task `task_20260721T190853272429Z_cdx` completed the three-source scan plus stacking path with warnings correctly propagated, all 19 run checks resolved to pass or acknowledged warning, workbook QA contained no formula errors, and all three PDFs passed visual inspection.

## Release thresholds

- Zero execution attempts with unconfirmed required parameters.
- Zero automatic changes to gamma, weight meaning, catalog membership, coordinates, trial definitions, optimizer bounds, or likelihood definitions.
- Zero failed reviews reported as completed.
- 100% pass rate for safety-critical language cases.
- All deterministic tests pass on the supported Python interpreter.
- At least one real-backend single-source and one multi-source end-to-end task produce task and run review artifacts.

## Known boundaries

- Natural-language interpretation currently requires Codex and this repository Skill.
- ChatGPT, API, and web adapters are not included in this local release.
- Public hosting controls such as authentication, quotas, tenant isolation, and data-retention policy are not applicable to the local Skill and must precede a hosted service.
- LLH scientific consistency and empirical-trial validation remain a separate analysis workstream.
