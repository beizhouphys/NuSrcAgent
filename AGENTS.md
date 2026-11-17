# NuSrcAgent contributor instructions

- Use `run_agent_wrap.py` as the sole public analysis entry point.
- Read `.agents/skills/nusrcagent/SKILL.md` before analysis execution.
- Preserve scientific definitions, catalog membership, weights, PDFs, fit bounds
  and recorded trial strategies. Ask only about unresolved material ambiguity.
- Execute an analysis only after its persistent task reaches `READY`.
- All currently supported analyses accept ICRS RA/Dec and Galactic l/b through
  the shared coordinate input layer. Convert to backend ICRS RA/Dec, retaining
  original values, frame, units and conversion provenance. Ask when the frame
  or units remain unclear; never infer them from numeric ranges. Degrees,
  radians and RA hourangle/sexagesimal are supported. See `docs/coordinates.md`.
- Keep source data in `data_input/`, numerical outputs in `data_output/` and
  figures in `figures/`; never overwrite frozen inputs during an analysis.
- The production DR2 background package is frozen v3. Verify its mapped
  numerical hashes; do not rebuild, retune or silently fall back to another version.
- Keep offline PDF construction, owner tests, specific-source comparisons,
  transcripts and local configuration out of this checkout. Runtime preparation
  of a requested spectrum's signal-energy PDFs and detector acceptance is an
  owner-authorized exception (2026-10-22); include it, preserving frozen PDFs.
- Keep module imports, CLI examples, artifact paths and manifest references
  consistent when renaming files; do not leave compatibility entry points.
- Preserve substantive comments when removing generation markers.
- Inspect scientific and artifact reviews. Warning-bearing results remain
  preliminary; failed reviews must not be reported as valid results.
- Report the maximized likelihood statistic as `TS`. Analytic local p-values
  do not establish empirical significance or parameter coverage.
- Always default new time-dependent requests to the merged
  `per_source_catalog_windows` workflow: fixed per-source box windows,
  single-source fits, scans, stacking and requested shared seasonal trials.
  Read docs/time_dependent_catalog.md. Require explicit windows, detector phases
  and the uniform-livetime background assumption before READY. Completed trials
  provide empirical p-values and significances. Never silently fall back to
  legacy Gaussian/box time searches for unsupported settings; explain the
  limitation. New legacy requests require explicit `scope=legacy_time_profile`.
  Existing saved tasks retain their recorded definitions. Never apply
  time-integrated significance/flux formulas to time-dependent fits.
- Review source changes and perform relevant isolated verification before
  publication. No release tag or public availability is implied by this copy.
- For completed fixed-window time-dependent background ensembles, use the
  canonical result adapter and `agent_core/plot_time_dependent_standard_report.py`.
  Render only after all validation checks pass. Preserve the existing
  NuSrcAgent task, authorization, review and Monte Carlo-interval rules; do not
  apply this presentation path to time-integrated or legacy time-profile runs.

## Communication and notation

- Use terminology natural to particle physicists and astrophysicists. Prefer
  concrete physical meanings, such as detector response, point-spread function,
  angular-uncertainty distribution, energy response or effective-area convolution.
  Use `kernel` only when discussing the mathematical kernel itself or preserving
  a code/API name; explain its physical role when needed.
- Avoid business language such as "product form." Use physicists' natural wording
  and state the concrete meaning, such as how to use the Agent, its interface or
  its deployment.
- Communicate naturally and directly, as research collaborators: lead with the
  conclusion, then provide the necessary evidence. Avoid repeating background
  or conclusions and avoid unnecessary headings or lists, while retaining
  conditions that affect understanding or judgment.
- In equations in responses, preserve complete physical quantities and their
  dependencies whenever possible; do not introduce shorthand merely for brevity.
  If a derivation needs auxiliary symbols or variable substitutions, define them
  explicitly and substitute the full expressions back into the final result
  whenever possible. This rule does not require changing notation in existing
  code, notebooks or historical documents.

## Significance reporting

- For every analysis, after reporting an estimated significance, state that a
  more precise significance requires background trials. If any reported estimate
  is strictly greater than 2 sigma, explicitly emphasize that background trials
  are needed. This applies to all data samples, likelihood modes, single-source
  analyses, catalog scans, stacking analyses, and local or catalog-corrected
  estimates, including primary or flux stages whenever they quote an estimated
  significance. Background trials must repeat the corresponding observed fit;
  calibrating a search significance requires the full search/hypothesis family.
  This reminder does not itself launch trials or change the review status.
  For an already empirical significance, retain its Monte Carlo uncertainty and
  trial scope; do not describe it as lacking trials.

## Progress updates and total elapsed time

- For every project task, measure wall-clock time from the current user request.
  Include a remaining-time estimate in every progress update, preferably using
  completed comparable calculations under the current configuration, and update
  it as work proceeds:
  `remaining = completed_calculation_time / completed_units * remaining_units`.
  For example, 100 of 1000 sources completed in 1 minute predicts another
  9 minutes, or about 10 minutes in total.
- Distinguish the current stage's remaining time from the whole request's
  remaining time. Do not mix different fit procedures, worker configurations or
  restored checkpoints as timing samples from this invocation. Before a usable
  sample exists, say that a reliable estimate is pending the first completed
  calculation. For continuous scrambling without a target trial count, state
  that it runs continuously with no end time set; never invent an ETA or add a
  stopping condition.
- Wrapper `NuSrcAgent progress:` events on stderr and `execution_timing` in stdout
  JSON provide measured times and current-stage ETAs. Translate these into
  natural progress updates rather than pasting internal JSON. Preparation,
  plotting, verification and review follow the same rule. Without measurable
  progress, give a clearly labelled rough range based on completed work; if no
  estimate is possible, explain why.
- Include total elapsed wall-clock time in the final answer only when the
  current request strictly exceeds 60 seconds, including failures or interrupted
  work. Measure the whole request, not just its final wrapper command. Each turn
  of a two-stage analysis reports its own processing time, excluding the wait
  for the user's reply.
