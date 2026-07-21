---
name: he-neutrino-analysis-cdx
description: Orchestrate, execute, and scientifically review time-integrated high-energy neutrino single-source searches, catalog-wide source scans, and catalog stacking analyses in the Radio_Bright_AGN repository. Use when a user asks in natural language to inspect a source catalog, analyze one or more sky coordinates, choose or apply catalog weights, run the IceCube public-data likelihood, reproduce 2103.12813-style outputs, diagnose a run, or assess whether analysis outputs are trustworthy.
---

# HE Neutrino Analysis

Use Codex as the natural-language adapter and reviewer. Persist every analysis through the task wrapper; keep likelihood evaluation deterministic in the repository tools.

## Workflow

1. Read the repository `AGENTS.md` and preserve its scientific and naming constraints.
2. Select the workflow before execution:
   - exactly one source: single-source analysis;
   - more than one source or a multi-row catalog: catalog-wide single-source scan plus stacking;
   - inspection only: `inspect-catalog`;
   - existing run assessment: `review-run`;
   - unclear source count or intent: ask the user.

3. For an analysis, create a persistent task from the user's original words and the parameters Codex extracted. Omit any parameter the user did not provide; never insert a scientific default.

Single source:

```bash
python3 run_agent_wrap_cdx.py create-single --request "<original request>" --name <name> --ra-deg <ra> --dec-deg <dec> [--gamma <negative_gamma>]
```

Catalog or inline sources:

```bash
python3 run_agent_wrap_cdx.py create-catalog --request "<original request>" --catalog <file> [--gamma <negative_gamma>] [--weight-mode uniform|column|manual]
```

For inline input, repeat `--source name,ra_deg,dec_deg`. Add `--weight-column` and `--weight-meaning` for column weighting, or `--weights` for manual weighting. The planner inspects catalog files automatically.

4. Read the returned task status. For `AWAITING_CONFIRMATION`, ask only the listed `questions`. Record the user's answer:

```bash
python3 run_agent_wrap_cdx.py confirm --task <task_id> [--gamma <gamma>] [--weight-mode <mode>] [--weight-column <column>] [--weight-meaning <meaning>] [--weights <values>]
```

Do not run until the task reports `READY`. If the user changes a parameter after a terminal result, create a new task rather than mutating the old audit record.

5. Run a ready task through the wrapper:

```bash
python3 run_agent_wrap_cdx.py run --task <task_id>
```

The wrapper writes attempt hashes, classifies failures, permits at most one safe retry with unchanged scientific parameters, and enforces `COMPLETED`, `COMPLETED_WITH_WARNINGS`, or `FAILED` from the review.

6. For an inspection-only request, use:

```bash
python3 run_codex_analysis_tool_cdx.py inspect-catalog --catalog <catalog>
```

For an existing-run review, use:

```bash
python3 run_codex_analysis_tool_cdx.py review-run --run-directory <run_directory> --repo-root .
```

Treat `status=fail` as blocking and present unresolved questions to the user.

7. Confirm scientific assumptions before execution. Do not silently invent:
   - source spectral index or indices;
   - intrinsic stacking scheme: uniform, catalog column, or manual values;
   - interpretation of a candidate weight column;
   - catalog cuts or source exclusions;
   - any request for empirical post-trial significance.

The current sample is fixed to the IceCube public 10-year point-source data and the current implementation is time-integrated. State those constraints when material.

8. Read `<task_directory>/agent_review_cdx.json` and `<run_directory>/review_cdx.json` after every run. If the run review is absent, run:

```bash
python3 run_codex_analysis_tool_cdx.py review-run --run-directory <run_directory> --repo-root .
```

9. Apply the review policy:
   - `pass`: report results and artifacts.
   - `warning`: report results with every scientifically material warning; do not describe the run as publication-ready.
   - `fail`: do not present numerical results as valid.
   - Retry once only for a failed check with `auto_fix_allowed=true`, and only when the repair does not alter scientific inputs.
   - Stop and ask the user for checks involving scientific assumptions, catalog content, fit behavior, or trial definitions.

10. Render and visually inspect every generated PDF and every workbook sheet. Treat overlaps, clipping, blank plots, and unreadable columns as auto-fixable output failures; rerun review after repairing them.

11. Report the statistic as `TS` after likelihood maximization; do not append a maximization suffix. Distinguish pre-trial and post-trial quantities. Do not infer stacking post-trial significance when the run leaves it blank.

## Completion Gate

Finish only when the wrapper reaches `COMPLETED` or `COMPLETED_WITH_WARNINGS` and the request file, task audit, numeric tables, review artifacts, provenance, and expected figures/workbook exist. Never present a `FAILED` task's numerical output as valid. Summarize the selected gamma, weighting scheme, number of sources, highest-TS source for catalog scans, stacking results, review status, and limitations.

Read [scientific-review-policy_cdx.md](references/scientific-review-policy_cdx.md) when interpreting checks, deciding whether to retry, or preparing a publication-oriented summary.
Read [agent-task-interface_cdx.md](references/agent-task-interface_cdx.md) when creating, confirming, resuming, or diagnosing persistent tasks.
