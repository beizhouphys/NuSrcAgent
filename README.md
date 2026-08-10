# NuSrcAgent

NuSrcAgent is a private-alpha agent for time-integrated high-energy neutrino single-source and stacking searches using IceCube public point-source data. The default backend is IceTracks-DR2 14-year spatial+energy SkyLLH v26; the existing 10-year backend remains selectable.

```text
Natural-language request -> Codex Skill -> persistent task -> deterministic LLH backend -> scientific review
```

Version: `0.2.0-private-alpha.4`

This private repository is for the owner and invited collaborators. It is not yet a public or publication-ready scientific release.

## Capabilities

- One source selects a single-source analysis.
- Multiple sources or a catalog select stacking; the legacy 10-year path retains its existing source scan.
- DR2 spatial+energy fits Gamma by default (seed `-3.0` in the user-facing legacy convention). DR2 spatial-only is selectable and uses fixed acceptance Gamma `-2.5` by default; stacking weights remain an explicit scientific choice.
- Tasks preserve inputs, confirmations, attempts, request hashes, outputs, and completion status.
- Completed runs produce tables, figures, provenance, and machine-readable scientific reviews.
- Chinese, English, and mixed-language requests are supported through the repository Codex Skill.

## Install

```bash
git clone https://github.com/beizhouphys/NuSrcAgent.git
cd NuSrcAgent
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install --require-hashes -r requirements_skyllh_v26_lock_cdx.txt
.venv/bin/python run_agent_wrap_cdx.py environment-check
.venv/bin/python verify_private_alpha_setup_cdx.py --hashes
```

Both supported data samples use this project-local pinned environment; see `docs/data_and_environment.md`. Large DR2 data and pre-calculated PDF products must be present locally.

## Use With Codex

Open the repository in Codex and ask naturally:

```text
Analyze TXS 0506+056 at RA 77.3582 deg and Dec 5.6931 deg.
Ask me before choosing any unspecified scientific parameter.
```

Codex discovers `$he-neutrino-analysis-cdx`, creates a persistent task, asks for missing parameters, runs the deterministic backend, and reviews the result.

## Command Line

`run_agent_wrap_cdx.py` is the only public Python entry point.

Create and run a single-source task:

```bash
.venv/bin/python run_agent_wrap_cdx.py create-single \
  --request "Analyze TXS 0506+056" \
  --name "TXS 0506+056" --ra-deg 77.3582 --dec-deg 5.6931

.venv/bin/python run_agent_wrap_cdx.py run --task <task_id>
```

Create a catalog task:

```bash
.venv/bin/python run_agent_wrap_cdx.py create-catalog \
  --request "Scan and stack this catalog" \
  --catalog configs_cdx/examples_cdx/catalog_sources_rfc100_cdx.csv \
  --name-column source_name --ra-column ra_deg --dec-column dec_deg \
  --weight-mode uniform
```

Add `--gamma-mode fixed --gamma -2.53` for a fixed spectrum. Add
`--likelihood-mode spatial_only` for the 14-year spatial-only likelihood; it
uses fixed acceptance Gamma `-2.5` unless `--gamma` is supplied. Add
`--data-sample icecube_public_ps_10yr --gamma -2.53` to select the legacy
10-year analysis explicitly.

Inspect a catalog or review an existing run:

```bash
.venv/bin/python run_agent_wrap_cdx.py inspect-catalog --catalog <catalog.csv>
.venv/bin/python run_agent_wrap_cdx.py review-run --run-directory <run_directory>
```

Use `.venv/bin/python run_agent_wrap_cdx.py --help` to see all environment, task, confirmation, execution, recovery, inspection, and review commands.

## Verify

```bash
.venv/bin/python -m unittest discover -s tests_cdx -p 'test_*_cdx.py' -v
.venv/bin/python tools_cdx/evaluate_agent_cases_cdx.py --validate-golden
```

## 2103.12813 DR2 Benchmark

The repository also contains an owner-approved, resumable internal workflow
for comparing the 3386 RFC 2019c radio-bright AGN against arXiv:2103.12813
with the 14-year DR2 spatial-only likelihood. It produces a catalog scan, six
paper-style stacks, direct DR2 effective-area flux conversions, paper-reference
tables with digitization provenance, comparison PDFs, a workbook, and a
scientific review. Invoke this workflow through the HE Neutrino Analysis Skill;
`run_agent_wrap_cdx.py` remains the sole public CLI.

## Repository Layout

- `run_agent_wrap_cdx.py`: sole public CLI.
- `agent_core_cdx/`: planning, state, execution, validation, reporting, and review.
- `analysis_backend_cdx/`: callable single-source and catalog likelihood backends.
- `.agents/skills/`: natural-language Codex Skill.
- `tests_cdx/`: deterministic and language-adapter tests.
- `tools_cdx/`: internal development and artifact-generation tools.
- `legacy_codex_revised/`: preserved research scripts not used by the agent runtime.
- `docs/`: design, data, validation, and scientific-status documentation.

## Documentation

- [Agent design and behavior](docs/agent_design.md)
- [Data, environment, and collaboration](docs/data_and_environment.md)
- [Testing and release criteria](docs/testing_and_release.md)
- [Scientific status and limitations](docs/scientific_status.md)

No open-source license has been granted for this private alpha.
