# Single-Source and Stacking Analysis Agent

The repository now has a persistent Codex-native agent wrapper. In Codex App or Codex CLI, ask for a single-source or catalog analysis in natural language. The repository Skill creates an auditable task through `run_agent_wrap_cdx.py`, confirms unresolved scientific assumptions, runs deterministic tools, reviews outputs, and retries only safe engineering failures with an unchanged request hash.

`run_agent_wrap_cdx.py` is the preferred human-agent entry point. It records the original request, selected workflow, parameter provenance, confirmations, attempts, artifacts, and completion state under `data_output/agent_tasks_cdx/`.

`run_analysis_agent_cdx.py` remains the lower-level structured execution tool. It creates a YAML request, validates and normalizes inputs, runs the requested analysis, writes outputs, and automatically creates `review_cdx.json` and `review_cdx.md`.

Inspect a catalog before running:

```bash
python3 run_codex_analysis_tool_cdx.py inspect-catalog --catalog <catalog.csv>
```

Review an existing run:

```bash
python3 run_codex_analysis_tool_cdx.py review-run --run-directory <run_directory> --repo-root .
```

## Single Source

```bash
python3 run_analysis_agent_cdx.py single \
  --name "TXS 0506+056" \
  --ra-deg 77.3582 \
  --dec-deg 5.6931 \
  --gamma -2.53
```

## Catalog File and Catalog Weight

```bash
python3 run_analysis_agent_cdx.py catalog \
  --catalog configs_cdx/examples_cdx/catalog_sources_rfc100_cdx.csv \
  --name-column source_name \
  --ra-column ra_deg \
  --dec-column dec_deg \
  --weight-column xband_flux_jy \
  --gamma -2.53
```

## Inline Coordinates and Manual Weights

```bash
python3 run_analysis_agent_cdx.py catalog \
  --source "TXS 0506+056,77.3582,5.6931" \
  --source "PKS 1502+106,226.1041,10.4942" \
  --source "3C 279,194.0465,-5.7893" \
  --weights "1.0,0.8,0.6" \
  --gamma -2.53
```

Use `--prepare-only` before the subcommand to generate and validate the request without running the likelihood. Repeat `--gamma` to scan more than one spectral index. All spectral indices use the negative power-law convention.

The 100-source smoke-test catalog is derived reproducibly from `data_input/VLBI_rfc_2019c_cat_BZ.dat`. It selects sources with X-band flux at least 0.15 Jy and declination between -87 and +87 degrees, then samples 100 entries evenly across the eligible catalog order for broad sky coverage. It is a software test subset, not the formal full-catalog science sample.
