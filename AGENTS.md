# AGENTS.md

## What This File Is For

`AGENTS.md` is a local guide for AI coding agents working in this repository. It tells future agent sessions how to understand the project, which files matter, how to run or modify code safely, and what conventions to preserve.

Use it as project memory: when a new agent starts, it should read this file before making changes.

## Project Overview

This repository contains Python scripts and data products for radio-bright AGN / high-energy neutrino analysis, including IceCube public point-source data, source catalog handling, likelihood calculations, simulations, and flux conversion.

## Project Mission

- Build an agent/workflow for high-energy neutrino source searches that can eventually be useful to physicists and astronomers worldwide.
- Keep the analysis scientifically careful and reproducible enough that, at some point, it can support a publishable paper.
- Prefer choices that move the project toward publication-quality results, figures, checks, and documentation.

Important files and directories:

- `run_agent_wrap_cdx.py`: the sole public Python entry point. It provides task creation, confirmation, execution, recovery, catalog inspection, and completed-run review.

- `agent_core_cdx/task_state_cdx.py`: AgentTask persistence, parameter provenance, confirmation gate, and state transitions.
- `agent_core_cdx/planner_cdx.py`: source-count workflow selection and pre-execution catalog checks.
- `agent_core_cdx/agent_orchestrator_cdx.py`: attempt logging, safe retry, error classification, and machine completion gate.
- `agent_core_cdx/review_cdx.py`: scientific and artifact consistency checks that produce `review_cdx.json` and `review_cdx.md`.
- `analysis_backend_cdx/`: callable time-integrated single-source and catalog-stacking likelihood backends used by the agent runtime.
- `analysis_backend_cdx/skyllh_dr2_catalog_scan_cdx.py`: resumable, all-event DR2 spatial-only batch evaluator used for the 3386-source arXiv:2103.12813 benchmark; it preserves constrained and signed-fit outputs and accumulates the six paper-style stacks.
- `analysis_backend_cdx/dr2_flux_conversion_cdx.py`: direct DR2 effective-area/livetime implementation of the paper's diffuse-intensity event-count conversion. It does not reuse the legacy 10-year event-count constants.

- `.agents/skills/he-neutrino-analysis-cdx/SKILL.md`: repository-local Codex-native workflow for natural-language analysis requests, confirmation gates, execution, review, and safe retry behavior.
- `tests_cdx/`: deterministic wrapper tests and the multilingual natural-language evaluation corpus.
- `tools_cdx/`: internal evaluation and workbook-generation tools; these are not additional public entry points.
- `tools_cdx/run_2103_12813_dr2_spatial_only_cdx.py`: internal, checkpointed production runner for the owner-approved 3386-source comparison. Invoke it through the HE Neutrino Analysis Skill, not as a second public agent CLI.
- `docs/`: agent design, data/environment, testing/release, and scientific-status documentation.

- `legacy_codex_revised/`: legacy research code that has previously been modified by Codex. Keep it for scientific provenance and for tracing Codex-adapted legacy behavior.
- `legacy_code_dont_revise/`: owner-provided, unmodified legacy-code baseline. Treat this entire directory as read-only: agents may inspect, compare, and cite it, but must never edit, rename, format, path-rewrite, annotate, regenerate, overwrite, or delete any file inside it. If modified behavior is needed, copy the relevant material to an appropriate location outside this directory and make changes there.

- `legacy_codex_revised/likelihood_v4.py`: original likelihood / TS research script retained for scientific provenance.
- `legacy_codex_revised/likelihood_v5_Epdfs.py`: later research variant that adds reconstructed-energy PDFs and simulation-oriented switches; it is not the supported runtime backend.
- `legacy_codex_revised/likelihood_reproduce_1810.02823.py`, `legacy_codex_revised/likelihood_reproduce_1810.02823_ICformlsm.py`, `legacy_codex_revised/likelihood_reproduce_IC170922A.py`: historical attempts to reproduce published IceCube likelihood or event-significance results.
- `legacy_codex_revised/S_Epdf.py`, `legacy_codex_revised/S_Epdf_test.py`, `legacy_codex_revised/bkgd_pdf.py`: exploratory signal-energy and background-PDF construction/checking scripts.
- `legacy_codex_revised/source.py`: legacy source catalog definitions and selection logic.
- `legacy_codex_revised/neutrinos_data.py`: legacy IceCube event loading and event-array preparation.
- `legacy_codex_revised/ns2flux.py`: legacy flux-conversion utilities.
- `legacy_codex_revised/binomial_test.py`, `legacy_codex_revised/multiple_src_test.py`, `legacy_codex_revised/simu_to_postTrial.py`: historical multiple-source and post-trial significance calculations.
- `legacy_codex_revised/simu_Eproxy_Dec.py`: exploratory background event generation in reconstructed-energy/declination space.
- `legacy_codex_revised/p_value_map.py`, `legacy_codex_revised/plot.py`, `legacy_codex_revised/plot_skymap.py`: result visualization and sky-map scripts tied to historical output layouts.
- `legacy_codex_revised/use.py`, `legacy_codex_revised/use1.py`: legacy plotting/math/helper utilities.

- `data_input/`: input data, including the tracked IceCube public-data subset under `data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/` and source catalogs.
- `data_output/`: generated numeric outputs.
- `figures/`: generated plots.
- `Notes/`: project notes and supporting documents.

## Working Guidelines

- Read the relevant module before editing; legacy scripts still contain top-level flags and commented alternatives.
- Never modify anything under `legacy_code_dont_revise/`, even for seemingly mechanical maintenance such as path updates, comment markers, formatting, compatibility fixes, or repository-wide replacements. Exclude this directory explicitly from bulk-edit commands.
- Preserve scientific behavior unless the requested change explicitly asks for a model, catalog, or analysis change.
- Treat `data_input/` as source data. Do not overwrite input data unless explicitly requested.
- Put generated arrays, tables, and intermediate results in `data_output/`.
- Put generated plots in `figures/`.
- Avoid changing binary or generated files such as `.pyc`, `.DS_Store`, and existing PDFs unless the task requires it.
- Keep edits small and easy to audit. This is analysis code, so accidental behavioral changes can be expensive.
- Preserve established repository names, but do not create another root-level CLI; extend `run_agent_wrap_cdx.py` or the appropriate internal module.
- Keep detailed documentation under `docs/` rather than adding many overlapping files at the repository root.
- If any input (parameters, etc.) is uncertain, especially settings in an `Input` block, ask the user before editing or running the code.

## Python Notes

- The code uses NumPy/SciPy/Matplotlib style with many `from numpy import *` imports. Match the nearby style when making small edits.
- Keep new code close to the user's existing style when reasonable: compact, script-friendly, and direct, rather than over-engineered or overly verbose.
- Many quantities are stored in radians internally. Check `d2r = 180./pi` usage before changing coordinate logic.
- Data files are usually loaded with relative paths from the repository root. Run scripts from the repository root unless there is a clear reason not to.
- Some scripts print important configuration at import/runtime. Keep those messages if they help avoid scientific mistakes.
- Legacy copies of `use.py` and `use1.py`, plus `xsecs_nu.py`, may also exist as shared/global helpers in `/Users/beizhou/Library/CloudStorage/Dropbox/path_bei/`.
- The user's `~/.bash_profile` includes `export PYTHONPATH=/Users/beizhou/Library/CloudStorage/Dropbox/path_bei:$PYTHONPATH`. This can matter when reproducing results or resolving imports.

## Verification

The repository has deterministic wrapper tests, a multilingual language-case validator, and a data-manifest verifier. Run:

```bash
python3 verify_private_alpha_setup_cdx.py --hashes
python3 -m unittest discover -s tests_cdx -p 'test_*_cdx.py' -v
python3 tools_cdx/evaluate_agent_cases_cdx.py --validate-golden
```

Run these commands from the repository root in the supported Python environment:

- `verify_private_alpha_setup_cdx.py --hashes` checks the supported Python/NumPy environment and verifies every required data file against the SHA-256 value recorded in the data manifest. It detects missing, corrupted, or unintentionally modified data.
- The unittest command checks deterministic agent-wrapper behavior, including workflow planning, parameter confirmation, task persistence, recovery, completion states, and public CLI parsing. It does not validate the scientific correctness of the LLH implementation.
- `evaluate_agent_cases_cdx.py --validate-golden` validates the structure, unique IDs, prompts, and expected fields of the multilingual natural-language test corpus. It does not call Codex or measure live natural-language accuracy.

Passing these checks is required for engineering changes, but it is not sufficient to claim that the likelihood analysis is scientifically validated.

For nontrivial changes:

- Run the smallest relevant script or function path that exercises the edit.
- Check that expected output files still appear in `data_output/` or `figures/`.
- For plotting changes, inspect the generated figure when possible.
- For numerical changes, compare before/after values on a small input or short run.
- When reporting a numerical comparison or benchmark, report the signed relative difference first and the signed absolute difference second. Unless a task defines another convention, use `relative difference = (result - reference) / reference` and `absolute difference = result - reference`; label both clearly and include percentages for relative differences when useful.
- For release or interface changes, run one real single-source task and one small catalog scan plus stacking task through `run_agent_wrap_cdx.py`.
- Confirm that generated tables, workbook sheets, figures, provenance, and review artifacts are present and readable.

## Agent Behavior and Scientific Safety

- Exactly one source selects single-source analysis; multiple sources or a multi-row catalog select a source scan plus stacking.
- For LLH / likelihood analysis, use the user's existing code as the scientific baseline. Do not start from scratch unless the user explicitly asks for a new independent implementation.
- When creating derived LLH modules or wrappers, copy the relevant lines/blocks from the user's code where practical and preserve formatting/style as much as possible, then make only the minimal adaptations needed for callable runtime behavior.
- Keep legacy-to-runtime changes traceable: if behavior differs from `legacy_codex_revised/likelihood_v4.py` or related legacy files, document why and avoid silent scientific changes.
- Use `legacy_code_dont_revise/` as the untouched owner baseline when determining which changes were introduced in `legacy_codex_revised/` or the supported runtime.
- Do not invent gamma, coordinate interpretation, catalog cuts, weight definitions, weight meaning, or trial strategy.
- Ask the user when a scientific parameter is missing or ambiguous.
- Do not run a task until the confirmation gate reports `READY`.
- Only dependency, output-generation, and transient I/O failures may retry automatically, at most once, with an identical request hash.
- Never change scientific parameters, likelihood definitions, optimizer bounds, or catalog membership as an automatic repair.
- Treat warning-bearing results as preliminary and never present a failed review's numerical output as valid.
- Report the maximized-likelihood statistic as `TS`, not `TS_max`.
- Keep the current scientific limitations in `docs/scientific_status.md` visible when interpreting results.

## Caution Areas

- `legacy_codex_revised/source.py` contains many disabled catalog-selection blocks using `for ... in range(0)`. Be careful when enabling one path, because top-level definitions such as `RAs_src`, `Decs_src`, `N_src`, and `W_mdls_src` determine downstream behavior.
- `legacy_codex_revised/neutrinos_data.py` builds padded event arrays using `Nmax` and then truncates to `Nks.max()`. Preserve array shapes unless intentionally refactoring.
- `legacy_codex_revised/likelihood_v4.py` imports sibling legacy modules, so top-level code in those files runs during analysis.
- Most other files in `legacy_codex_revised/` are also top-level research scripts rather than import-safe modules. Several contain active `range(1)` blocks, early `exit()` calls, hard-coded parameters, historical output paths, or Python 2 syntax; inspect the complete active path before running them.
- Names such as `S_Epdf_test.py`, `multiple_src_test.py`, and `binomial_test.py` describe exploratory research checks, not deterministic tests collected by `tests_cdx/`.
- Some legacy scripts still refer to data products or neighboring projects that are not part of this repository. Preserve those references for provenance, but do not make them part of the supported runtime without confirming the inputs and scientific intent.
- `legacy_codex_revised/S_Epdf.py` contains dormant code capable of writing derived smearing data below `data_input/`; do not enable that path without explicit owner approval.
- `analysis_backend_cdx/` was derived from the legacy likelihood but is the implementation used by the supported agent runtime. Do not assume a change to one implementation automatically updates the other.
- File paths include project-local data and, in some commented blocks, absolute or neighboring-project paths. Do not make those paths active without checking availability.

## Owner Notes

- Preserve useful project memory in this file when repository paths or workflows change; update only stale details instead of replacing the document wholesale.
- This local `AGENTS.md` contains owner guidance and should not be overwritten automatically during repository synchronization.
