---
name: he-neutrino-analysis-cdx
description: Orchestrate, execute, and scientifically review time-integrated high-energy neutrino single-source searches, catalog-wide source scans, and catalog stacking analyses in the NuSrcAgent repository. Use when a user asks in natural language to inspect a source catalog, analyze one or more sky coordinates, choose or apply catalog weights, run the IceCube public-data likelihood, reproduce 2103.12813-style outputs, diagnose a run, or assess whether analysis outputs are trustworthy.
---

# HE Neutrino Analysis

Use Codex as the natural-language adapter and reviewer. Persist every analysis through the task wrapper; keep likelihood evaluation deterministic in the repository tools.

## Workflow

1. Read the repository `AGENTS.md` and preserve its scientific and naming constraints.
2. Select the workflow and data sample before execution:
   - exactly one source: single-source analysis;
   - more than one source or a multi-row catalog: catalog stacking (the legacy 10-year path also produces its existing catalog-wide source scan);
   - inspection only: `inspect-catalog`;
   - existing run assessment: `review-run`;
   - unclear source count or intent: ask the user.

3. Before reading or running an analysis backend, check the project-local pinned environment and the selected sample's required files:

```bash
.venv/bin/python run_agent_wrap_cdx.py environment-check --data-sample icecube_public_ps_14yr_dr2 [--likelihood-mode spatial_energy|spatial_only]
```

Use `icecube_public_ps_10yr` only when the user selected the 10-year sample. If `.venv/bin/python` is absent, stop and give the installation commands from `docs/data_and_environment.md`; do not silently use system Python, another virtual environment, or a temporary environment. If the check returns `status=fail`, report its failed checks and do not execute an LLH task.

4. For an analysis, create a persistent task from the user's original words and the parameters Codex extracted. The agreed default is IceTracks-DR2 14-year spatial+energy data with fitted Gamma, seeded at legacy gamma `-3.0` (SkyLLH Gamma `3.0`). The DR2 spatial-only mode instead fixes the acceptance Gamma at legacy `-2.5` (SkyLLH `2.5`) unless the user explicitly supplies another value; it never fits Gamma. Other fixed-Gamma spatial+energy requests require an explicit value. Select the 10-year backend only when the user asks for it.

Single source:

```bash
.venv/bin/python run_agent_wrap_cdx.py create-single --request "<original request>" --name <name> --ra-deg <ra> --dec-deg <dec> [--likelihood-mode spatial_energy|spatial_only] [--gamma-mode fitted|fixed] [--gamma <negative_gamma>] [--data-sample icecube_public_ps_14yr_dr2|icecube_public_ps_10yr]
```

Catalog or inline sources:

```bash
.venv/bin/python run_agent_wrap_cdx.py create-catalog --request "<original request>" --catalog <file> [--likelihood-mode spatial_energy|spatial_only] [--gamma-mode fitted|fixed] [--gamma <negative_gamma>] [--weight-mode uniform|column|manual] [--data-sample icecube_public_ps_14yr_dr2|icecube_public_ps_10yr]
```

For inline input, repeat `--source name,ra_deg,dec_deg`. Add `--weight-column` and `--weight-meaning` for column weighting, or `--weights` for manual weighting. The planner inspects catalog files automatically.

5. Read the returned task status. For `AWAITING_CONFIRMATION`, ask only the listed `questions`. Record the user's answer:

```bash
.venv/bin/python run_agent_wrap_cdx.py confirm --task <task_id> [--gamma <gamma>] [--weight-mode <mode>] [--weight-column <column>] [--weight-meaning <meaning>] [--weights <values>]
```

Do not run until the task reports `READY`. If the user changes a parameter after a terminal result, create a new task rather than mutating the old audit record.

6. Run a ready task through the wrapper:

```bash
.venv/bin/python run_agent_wrap_cdx.py run --task <task_id>
```

The wrapper writes attempt hashes, classifies failures, permits at most one safe retry with unchanged scientific parameters, and enforces `COMPLETED`, `COMPLETED_WITH_WARNINGS`, or `FAILED` from the review.

7. For an inspection-only request, use:

```bash
.venv/bin/python run_agent_wrap_cdx.py inspect-catalog --catalog <catalog>
```

For an existing-run review, use:

```bash
.venv/bin/python run_agent_wrap_cdx.py --repo-root . review-run --run-directory <run_directory>
```

Treat `status=fail` as blocking and present unresolved questions to the user.

8. Confirm scientific assumptions before execution. The fitted-Gamma DR2 default above is pre-approved. Do not silently invent:
   - a fixed source spectral index or non-default fit bounds;
   - intrinsic stacking scheme: uniform, catalog column, or manual values;
   - interpretation of a candidate weight column;
   - catalog cuts or source exclusions;
   - any request for empirical post-trial significance.

The default sample is IceCube IceTracks-DR2 14-year data. It uses SkyLLH v26, point sources, spatial+energy PDFs from the project-local pre-calculated tables, and all events. When the user explicitly asks for spatial-only, it uses only signal and background spatial PDFs; no signal or background energy term/table enters the event PDF. Gamma is then a fixed acceptance-weight parameter, not a fitted source-spectrum result. Exact source-event terms are reduced in memory-bounded adaptive event/source chunks; no ROI cut is introduced. Inspect the recorded `working_set` provenance and remember that runtime still scales with catalog size. The 10-year backend remains selectable for reproduction work. Both supported paths are currently time-integrated; source extension and time-dependent analyses remain future work.

9. Read `<task_directory>/agent_review_cdx.json` and `<run_directory>/review_cdx.json` after every run. If the run review is absent, run:

```bash
.venv/bin/python run_agent_wrap_cdx.py --repo-root . review-run --run-directory <run_directory>
```

10. Apply the review policy:
   - `pass`: report results and artifacts.
   - `warning`: report results with every scientifically material warning; do not describe the run as publication-ready.
   - `fail`: do not present numerical results as valid.
   - Retry once only for a failed check with `auto_fix_allowed=true`, and only when the repair does not alter scientific inputs.
   - Stop and ask the user for checks involving scientific assumptions, catalog content, fit behavior, or trial definitions.

11. Render and visually inspect generated PDFs and workbook sheets when the selected backend produces them. The first DR2 SkyLLH stacking backend writes the numeric report, provenance, and review artifacts but does not yet produce the legacy 10-year figures/workbook.

For the owner-approved 3386-source arXiv:2103.12813 DR2 benchmark, use the
repository's dedicated resumable internal workflow only after confirming the
catalog cut, acceptance Gamma, the three stacking Gammas, both weighting
schemes, and the `Delta TS=-3.84` upper-limit definition. Its implementation
is `tools_cdx/run_2103_12813_dr2_spatial_only_cdx.py`; do not present that
internal tool as another public CLI. Resume from its recorded checkpoint
rather than deleting partial output. Require the paper-reference provenance,
constrained and signed-fit labels, DR2 effective-area flux provenance,
comparison tables, rendered figures, and scientific cautions before reporting
it.

12. Report the statistic as `TS` after likelihood maximization; do not append a maximization suffix. Distinguish pre-trial and post-trial quantities. Do not infer stacking post-trial significance when the run leaves it blank.

## Completion Gate

Finish only when the wrapper reaches `COMPLETED` or `COMPLETED_WITH_WARNINGS` and all artifacts expected for the selected backend exist. Never present a `FAILED` task's numerical output as valid. Summarize the data sample, likelihood mode, fitted Gamma or fixed acceptance Gamma as applicable, weighting scheme, number of sources, `TS`, fitted `ns`, review status, and limitations.

Read [scientific-review-policy_cdx.md](references/scientific-review-policy_cdx.md) when interpreting checks, deciding whether to retry, or preparing a publication-oriented summary.
Read [agent-task-interface_cdx.md](references/agent-task-interface_cdx.md) when creating, confirming, resuming, or diagnosing persistent tasks.
