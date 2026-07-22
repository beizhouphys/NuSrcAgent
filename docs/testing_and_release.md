# Testing and Release

## Deterministic Tests

`tests_cdx/test_agent_wrap_cdx.py` covers workflow selection, parameter confirmation, task persistence, invalid inputs, recovery policy, review propagation, completion status, and the public CLI.

Run:

```bash
python3 -m unittest discover -s tests_cdx -p 'test_*_cdx.py' -v
```

## Language Cases

`tests_cdx/natural_language_eval_cases_cdx.json` contains Chinese, English, and mixed-language prompts, including ambiguous and safety-critical requests.

```bash
python3 tools_cdx/evaluate_agent_cases_cdx.py --validate-golden
```

A development-session conformance trace is not an unbiased quantitative estimate of language-model accuracy. Independent fresh Codex sessions are required before publishing an accuracy claim.

## Release Gate

A collaborator release requires:

- no execution with unconfirmed scientific parameters;
- no automatic scientific parameter changes;
- no failed review reported as completed;
- all deterministic and safety-critical language cases passing;
- setup and data hashes passing;
- one real single-source run;
- one real multi-source scan plus stacking run;
- clean-clone verification and passing GitHub Actions.

A future public release additionally requires a software license, authorship and affiliation, preferred citation, data redistribution decisions, external usability testing, and completion of the separate LLH scientific-validation work.

Hosted ChatGPT or web deployment would also require authentication, user isolation, upload limits, quotas, cancellation, privacy and retention policies, a worker queue, and safe operational logging.
