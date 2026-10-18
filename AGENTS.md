# NuSrcAgent contributor instructions

- Use `run_agent_wrap.py` as the sole public analysis entry point.
- Read `.agents/skills/nusrcagent/SKILL.md` before analysis execution.
- Preserve scientific definitions, catalog membership, weights, PDFs, fit bounds
  and recorded trial strategies. Ask only about unresolved material ambiguity.
- Execute an analysis only after its persistent task reaches `READY`.
- Keep source data in `data_input/`, numerical outputs in `data_output/` and
  figures in `figures/`; never overwrite frozen inputs during an analysis.
- The production DR2 background package is frozen v3. Verify its mapped
  numerical hashes; do not rebuild, retune or silently fall back to another version.
- Keep PDF construction, owner tests, specific-source comparisons, transcripts
  and local configuration out of this checkout.
- Keep module imports, CLI examples, artifact paths and manifest references
  consistent when renaming files; do not leave compatibility entry points.
- Preserve substantive comments when removing generation markers.
- Inspect scientific and artifact reviews. Warning-bearing results remain
  preliminary; failed reviews must not be reported as valid results.
- Report the maximized likelihood statistic as `TS`. Analytic local p-values
  do not establish empirical significance or parameter coverage.
- Time-dependent analysis is planned but not implemented in this copy. Do not
  claim support or run time-dependent background trials.
- Review source changes and perform relevant isolated verification before
  publication. No release tag or public availability is implied by this copy.
