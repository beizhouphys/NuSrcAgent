# NuSrcAgent

NuSrcAgent is a private-alpha agent for time-integrated high-energy neutrino single-source searches, catalog scans, and stacking analyses using the IceCube public point-source data.

```text
Natural-language request -> Codex Skill -> persistent task -> deterministic LLH backend -> scientific review
```

Version: `0.2.0-private-alpha.4`

This private repository is for the owner and invited collaborators. It is not yet a public or publication-ready scientific release.

## Capabilities

- One source selects a single-source analysis.
- Multiple sources or a catalog select a source-by-source scan plus stacking.
- Missing gamma or weighting choices block execution and trigger a question.
- Tasks preserve inputs, confirmations, attempts, request hashes, outputs, and completion status.
- Completed runs produce tables, figures, provenance, and machine-readable scientific reviews.
- Chinese, English, and mixed-language requests are supported through the repository Codex Skill.

## Install

```bash
git clone https://github.com/beizhouphys/NuSrcAgent.git
cd NuSrcAgent
conda env create -f environment_private_alpha_cdx.yml
conda activate nusrcagent-cdx
python3 verify_private_alpha_setup_cdx.py --hashes
```

The required IceCube/LLH data are included in the private repository. No separate data download is required.

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
python3 run_agent_wrap_cdx.py create-single \
  --request "Analyze TXS 0506+056" \
  --name "TXS 0506+056" --ra-deg 77.3582 --dec-deg 5.6931

python3 run_agent_wrap_cdx.py confirm --task <task_id> --gamma -2.53
python3 run_agent_wrap_cdx.py run --task <task_id>
```

Create a catalog task:

```bash
python3 run_agent_wrap_cdx.py create-catalog \
  --request "Scan and stack this catalog" \
  --catalog configs_cdx/examples_cdx/catalog_sources_rfc100_cdx.csv \
  --name-column source_name --ra-column ra_deg --dec-column dec_deg
```

Inspect a catalog or review an existing run:

```bash
python3 run_agent_wrap_cdx.py inspect-catalog --catalog <catalog.csv>
python3 run_agent_wrap_cdx.py review-run --run-directory <run_directory>
```

Use `python3 run_agent_wrap_cdx.py --help` to see all task, confirmation, execution, recovery, inspection, and review commands.

## Verify

```bash
python3 -m unittest discover -s tests_cdx -p 'test_*_cdx.py' -v
python3 tools_cdx/evaluate_agent_cases_cdx.py --validate-golden
```

## Repository Layout

- `run_agent_wrap_cdx.py`: sole public CLI.
- `agent_core_cdx/`: planning, state, execution, validation, reporting, and review.
- `analysis_backend_cdx/`: callable single-source and catalog likelihood backends.
- `.agents/skills/`: natural-language Codex Skill.
- `tests_cdx/`: deterministic and language-adapter tests.
- `tools_cdx/`: internal development and artifact-generation tools.
- `legacy_cdx/`: preserved research scripts not used by the agent runtime.
- `docs/`: design, data, validation, and scientific-status documentation.

## Documentation

- [Agent design and behavior](docs/agent_design.md)
- [Data, environment, and collaboration](docs/data_and_environment.md)
- [Testing and release criteria](docs/testing_and_release.md)
- [Scientific status and limitations](docs/scientific_status.md)

No open-source license has been granted for this private alpha.
