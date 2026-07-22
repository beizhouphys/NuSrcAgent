# Data, Environment, and Collaboration

## Environment

The tested runtime is Python 3.8.15 with NumPy 1.24.4:

```bash
conda env create -f environment_private_alpha_cdx.yml
conda activate nusrcagent-cdx
```

An existing compatible environment can instead install `requirements_private_alpha_cdx.txt`.

## Included Data

The private Git checkout includes the audited subset required by the callable backend:

- five IceCube event samples;
- five uptime tables;
- five effective-area tables;
- five derived background PDF tables.

`data_manifest_private_alpha_cdx.json` records every required path and SHA-256 value. Verify the clone with:

```bash
python3 verify_private_alpha_setup_cdx.py --hashes
```

Generated analysis products and unrelated local data are excluded from Git.

## Workbook Output

CSV and PDF outputs use the Python backend. Excel workbook generation additionally requires Node.js and `@oai/artifact-tool`; Codex may supply these through its bundled runtime. If unavailable, review reports the missing workbook rather than silently claiming full completion.

## Private Collaboration

Add collaborators by GitHub username. Each collaborator should authenticate with their own account; never share account passwords.

Keep `main` usable, use short-lived branches for development, and record scientific parameter changes explicitly in pull requests. Do not make the repository or included data public until data terms, provenance, software license, authorship, affiliation, and citation metadata are settled.

Problem reports should include the task ID, terminal state, `agent_review_cdx.json`, and the relevant run `review_cdx.json`, but not private or unpublished source catalogs.
