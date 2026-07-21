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

- `likelihood_v4.py`: main likelihood / TS analysis script.
- `source.py`: source catalog definitions and selection logic.
- `neutrinos_data.py`: IceCube event loading and event-array preparation.
- `inject_nus.py`: neutrino injection / simulation-related code.
- `ns2flux.py`: conversion utilities from fitted signal counts to flux-like quantities.
- `use.py`, `use1.py`: shared plotting/math/helper utilities.
- `run_analysis_agent_cdx.py`: deterministic single-source and catalog-stacking execution entry point; every completed run is automatically reviewed.
- `run_codex_analysis_tool_cdx.py`: machine-readable catalog inspection and completed-run review tools for Codex.
- `run_agent_wrap_cdx.py`: persistent human-agent task interface with planning, confirmation, execution, recovery, and completion states.
- `agent_core_cdx/task_state_cdx.py`: AgentTask persistence, parameter provenance, confirmation gate, and state transitions.
- `agent_core_cdx/planner_cdx.py`: source-count workflow selection and pre-execution catalog checks.
- `agent_core_cdx/agent_orchestrator_cdx.py`: attempt logging, safe retry, error classification, and machine completion gate.
- `agent_core_cdx/review_cdx.py`: scientific and artifact consistency checks that produce `review_cdx.json` and `review_cdx.md`.
- `.agents/skills/he-neutrino-analysis-cdx/SKILL.md`: repository-local Codex-native workflow for natural-language analysis requests, confirmation gates, execution, review, and safe retry behavior.
- `data_input/`: All input data, including input catalogs, public IceCube data, and more.
- `data_output/`: generated numeric outputs.
- `figures/`: generated plots.
- `Notes/`: project notes and supporting documents.

## Working Guidelines

- Read the relevant script before editing; many parameters are controlled by top-level flags and commented alternatives.
- Preserve scientific behavior unless the requested change explicitly asks for a model, catalog, or analysis change.
- Treat `data_input/` as source data. Do not overwrite input data unless explicitly requested.
- Put generated arrays, tables, and intermediate results in `data_output/`.
- Put generated plots in `figures/`.
- Avoid changing binary or generated files such as `.pyc`, `.DS_Store`, and existing PDFs unless the task requires it.
- Keep edits small and easy to audit. This is analysis code, so accidental behavioral changes can be expensive.
- Name every Codex-generated file with `_cdx` before the extension, for example `analysis_cdx.py`, `notes_cdx.md`, or `table_cdx.csv`. If there is no extension, append `_cdx` at the end.
- Name every Codex-generated directory with `_cdx` at the end.
- GitHub-required repository metadata are an owner-approved exception: `.gitignore`, `README.md`, and files under `.github/` may use their standard names so GitHub recognizes them.
- When modifying an existing code file, append the language-appropriate comment marker plus `cdx` at the end of every line added or changed by Codex. For Python, use `# cdx`.
- If any input (parameters, etc.) is uncertain, especially settings in an `Input` block, ask the user before editing or running the code.

## Python Notes

- The code uses NumPy/SciPy/Matplotlib style with many `from numpy import *` imports. Match the nearby style when making small edits.
- Keep new code close to the user's existing style when reasonable: compact, script-friendly, and direct, rather than over-engineered or overly verbose.
- Many quantities are stored in radians internally. Check `d2r = 180./pi` usage before changing coordinate logic.
- Data files are usually loaded with relative paths from the repository root. Run scripts from the repository root unless there is a clear reason not to.
- Some scripts print important configuration at import/runtime. Keep those messages if they help avoid scientific mistakes.
- `use.py`, `use1.py`, and `xsecs_nu.py` are also maintained as shared/global helper files in `/Users/beizhou/Library/CloudStorage/Dropbox/path_bei/`.
- The user's `~/.bash_profile` includes `export PYTHONPATH=/Users/beizhou/Library/CloudStorage/Dropbox/path_bei:$PYTHONPATH`. This can matter when reproducing results or resolving imports.

## Verification

There is no formal test suite in this repository at the moment. For nontrivial changes:

- Run the smallest relevant script or function path that exercises the edit.
- Check that expected output files still appear in `data_output/` or `figures/`.
- For plotting changes, inspect the generated figure when possible.
- For numerical changes, compare before/after values on a small input or short run.

## Caution Areas

- `source.py` contains many disabled catalog-selection blocks using `for ... in range(0)`. Be careful when enabling one path, because top-level definitions such as `RAs_src`, `Decs_src`, `N_src`, and `W_mdls_src` determine downstream behavior.
- `neutrinos_data.py` builds padded event arrays using `Nmax` and then truncates to `Nks.max()`. Preserve array shapes unless intentionally refactoring.
- `likelihood_v4.py` imports `source.py` and `neutrinos_data.py`, so top-level code in those files runs during analysis.
- File paths include project-local data and, in some commented blocks, absolute or neighboring-project paths. Do not make those paths active without checking availability.
