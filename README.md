# NuSrcAgent

Private-alpha agent wrapper for time-integrated high-energy neutrino single-source searches, catalog scans, and stacking analyses.

NuSrcAgent separates natural-language interaction from deterministic likelihood execution:

```text
User request -> Codex Skill -> persistent AgentTask -> LLH tools -> review -> completion gate
```

## Private-alpha status

Version: `0.2.0-private-alpha`

This repository is currently intended only for the owner and explicitly invited collaborators. It is not a public scientific release, and results must not be described as publication-ready while review warnings remain. No redistribution or public deployment is authorized at this stage.

## Capabilities

- One source automatically selects single-source analysis.
- Multiple sources or a catalog select a catalog-wide single-source scan plus stacking.
- Missing gamma or weighting definitions block execution and trigger a user question.
- Tasks persist confirmations, attempts, request hashes, artifacts, and terminal status.
- Safe engineering failures may retry once without changing scientific parameters.
- Completed runs produce machine-readable reviews and pass/warning/fail completion states.
- Chinese, English, and mixed-language requests are supported through the repository Codex Skill.

## Setup

Create the tested Conda environment:

```bash
conda env create -f environment_private_alpha_cdx.yml
conda activate nusrcagent-cdx
```

Or install the minimal Python dependency into an existing Python 3.8 environment:

```bash
python3 -m pip install -r requirements_private_alpha_cdx.txt
```

The LLH data are distributed separately from Git. Place the private data bundle at the repository root, extract it, and verify it:

```bash
tar -xzf NuSrcAgent_data_v0.2.0_cdx.tar.gz
python3 verify_private_alpha_setup_cdx.py --hashes
```

See [DATA_SETUP_cdx.md](DATA_SETUP_cdx.md) for the data policy and expected paths.

## Use with Codex

Open this repository in Codex and ask naturally, or explicitly invoke:

```text
$he-neutrino-analysis-cdx
Analyze TXS 0506+056 at RA 77.3582 deg and Dec 5.6931 deg with gamma -2.53.
```

The Skill creates a persistent task and calls the deterministic wrapper only after required parameters are confirmed.

## Direct CLI

```bash
python3 run_agent_wrap_cdx.py create-single \
  --request "Analyze TXS 0506+056" \
  --name "TXS 0506+056" --ra-deg 77.3582 --dec-deg 5.6931

python3 run_agent_wrap_cdx.py confirm --task <task_id> --gamma -2.53
python3 run_agent_wrap_cdx.py run --task <task_id>
```

## Verify

The deterministic wrapper tests do not require the private LLH data:

```bash
python3 -m unittest discover -s tests_cdx -p 'test_*_cdx.py' -v
python3 evaluate_agent_cases_cdx.py --validate-golden
```

After installing the data, run the setup verifier and a single-source smoke test. Current scientific limitations and warnings are documented in [project_audit_cdx.md](project_audit_cdx.md) and [AGENT_EVALUATION_cdx.md](AGENT_EVALUATION_cdx.md).

## Documentation

- [Agent usage](README_AGENT_cdx.md)
- [Behavior contract](AGENT_BEHAVIOR_SPEC_cdx.md)
- [Architecture](AGENT_ARCHITECTURE_cdx.md)
- [Evaluation](AGENT_EVALUATION_cdx.md)
- [Private collaboration](PRIVATE_ALPHA_GUIDE_cdx.md)
- [Release checklist](RELEASE_CHECKLIST_cdx.md)

## License and citation

No open-source license has been granted for this private alpha. Author, affiliation, citation, and public-release licensing metadata will be added before any public release.
