# Radio-Bright AGN Project Audit

Date: 2026-07-20

## Scope and handling rules

This audit covers the current repository inventory, Python source, configuration files, text and numerical outputs, NPZ products, PDFs, and rendered figures. Existing files were not renamed. Existing scientific code and input data were not modified.

For subsequent Codex work in this repository:

- New files created by Codex will use `_cdx` immediately before the extension.
- New directories created by Codex will end in `_cdx`.
- Only lines actually added or changed in an existing code file will end with the language-appropriate `cdx` comment, such as `# cdx` for Python.

## Inventory

- Repository size: approximately 1.3 GB.
- Files: 164.
- Directories below the repository root: 22.
- Python source: 19 files, 3,608 lines.
- Main file types: 38 CSV, 31 TXT, 22 YAML, 19 Python, 18 PDF, 8 DAT, 7 Markdown, 6 NPZ, 3 PNG, and 2 PYC files.
- No zero-byte files or symbolic links were found.
- The largest products are six stacking PDF tables, each approximately 108 MB and 1,133,444 lines.

## Project structure

- `likelihood_v4.py` is the legacy, top-level scientific workflow. Its active settings currently select gamma `-2.53`, equal weighting, stacking-result calculation, and Figure 4 reproduction.
- `source.py` activates the 2019c radio-quasar catalog with an X-band flux threshold of 0.15 Jy and produces 3,386 selected sources.
- `neutrinos_data.py` loads five combined IceCube samples and filters reconstructed declination to `(-87, 87)` degrees.
- `likelihood_backend_single_source_cdx.py` is a callable NumPy-only single-source backend derived from the legacy workflow.
- `agent_core_cdx/` provides configuration parsing, validation, normalization, mock execution, report generation, and the callable likelihood entry point.
- `run_agent_analysis_cdx.py` is the config-driven CLI. Its default backend is explicitly a non-scientific mock.
- `data_input/` contains the catalog, atmospheric flux tables, corrected and uncorrected IceCube events, uptime tables, and response functions.
- `data_output/` contains background PDFs, source tables, stacking products, and five recorded config-driven runs.

## Verification performed

- All 19 Python files passed Python source compilation/AST parsing.
- Both example YAML configurations passed `--validate-only`.
- Both example configurations normalized successfully; catalog weights sum to 1.0.
- The mock backend executed in memory for both example configurations without writing run products.
- All active relative paths used by the callable single-source backend were found.
- All six NPZ files opened successfully with object-array support. Their `S_ki`, `B_ki`, `fks`, and `Nks` arrays contain finite values.
- All five background-PDF tables contain finite, strictly positive PDF values.
- All 12 stacking TS curve files contain finite numerical values.
- All 18 PDFs opened successfully. First pages were rendered and visually reviewed; plots and text were legible with no obvious clipping or overlap.
- Numeric input/output row counts were collected. Corrected combined IC86-II--VII data contain 761,143 data rows, 18 fewer than the `uncorrected_probably` combined file, consistent with merging 19 duplicated pairs into 19 events.

## Findings

### Critical: invalid likelihood points can become artificial maxima

`likelihood_v4.py:403-405` and `likelihood_backend_single_source_cdx.py:184-185` return a **positive** `1e99` log-likelihood when a likelihood factor is negative. Because the code maximizes log likelihood, this invalid point is treated as an extremely good fit. The resulting TS becomes approximately `2e99`.

This is visible in existing products:

- `data_output/TableI_all_sources_cdx.txt` contains 13 affected sources at the end of the table.
- `data_output/TableI_reproduction_five_sources_cdx.txt` ranks those invalid fits first.
- `data_output/TableI_reproduction_top5_cdx.txt` therefore contains only invalid fits.
- These rows report zero p-values and infinite significances and must not be used as scientific results.

The invalid-region return should be a rejected/very low likelihood rather than a large positive likelihood. This change should be made only together with a controlled before/after numerical check because it changes fitted source results.

### High: two scripts depend on a file outside the repository

`inject_nus.py:30` and `ns2flux.py:25` actively load:

`../20180725_Tridents_HE/data_input/IceCube_6yr_atm.dat`

That neighboring path is not part of this repository, so these scripts are not self-contained. The input should either be added under `data_input/` with provenance or exposed as an explicit configuration parameter.

### High: the current scientific environment is incomplete

The active `python3` environment has NumPy but does not have SciPy, Astropy, lmfit, or Matplotlib. The legacy scripts therefore cannot run in this environment even though their source parses successfully. In addition, several scripts call `scipy.integrate.simps`, which is absent from newer SciPy releases and should be migrated carefully to `scipy.integrate.simpson` with compatible argument handling.

### High: callable likelihood can divide by zero for an empty ROI sample

`likelihood_backend_single_source_cdx.py:169-173` divides by `Njk` before checking whether a sample has zero events in the source ROI. The current 20-degree ROI and data make this unlikely, but arbitrary future inputs can trigger division by zero. The legacy implementation has the same pattern at `likelihood_v4.py:387-392`.

### Medium: config validation and executable backend support differ

The config layer accepts and normalizes `catalog_stacking`, but `agent_core_cdx/likelihood_backend_cdx.py:10-15` rejects every likelihood request except a single, time-integrated source. Catalog configurations therefore work only with the mock backend at present. This is acceptable for a scaffold but should remain prominent in user-facing documentation.

### Medium: trial configuration is recorded but not performed

The callable likelihood backend reports a local p-value using a half-chi-square approximation. It does not run the configured right-ascension scrambling trials, and `post_trial_p` remains null. Existing likelihood reports correctly warn about this in the newer runs.

### Medium: large generated tables duplicate NPZ content

The six 108 MB stacking text tables occupy most of the repository size. Six corresponding NPZ products total roughly 103 MB and are much faster to load. If the text tables are retained for auditability, their provenance and regeneration command should be documented; otherwise they are candidates for external artifact storage.

### Low: no formal tests or version-control metadata are available

No test suite was found, and the directory is not currently recognized as a Git repository. Reproducing scientific changes therefore depends on manual small-run comparisons and stored run provenance.

## Output and figure assessment

- Background PDFs are finite and positive for all five IceCube samples.
- The six current RQ stacking TS curves are finite and cross the plotted 95% threshold.
- Figure 2, Figure 3, Figure 4, effective-area PDFs, the paper, and the likelihood notes render successfully.
- The current Figure 4 panels are visually clean and consistent with the stored curve products.
- Recorded `mock_phase0` results are diagnostic only and are explicitly labeled non-scientific.
- Recorded `likelihood_single_source_v1` results have no post-trial correction and should not be interpreted as final catalog-search significances.

## Recommended order of work

1. Correct the invalid-likelihood penalty in both likelihood implementations and reproduce the 13 affected source fits on a controlled subset.
2. Regenerate `TableI_all_sources_cdx.txt` and the reproduction tables, confirming that no `2e99`, `nan`, or `inf` values remain.
3. Make the atmospheric-flux dependency repository-local or configurable.
4. Establish a pinned scientific Python environment and replace deprecated SciPy integration calls with verified equivalents.
5. Add small regression tests for config validation, ROI-empty behavior, likelihood-domain rejection, Table I finite outputs, and Figure 4 threshold crossings.
6. Document how the large stacking TXT and NPZ products are generated and which format is authoritative.

## Changes made by this audit

- Added this report: `project_audit_cdx.md`.
- No existing source code, configuration, input data, numerical output, or figure was modified.
