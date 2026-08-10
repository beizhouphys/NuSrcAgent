# Data, Environment, and Collaboration

## Environment

Both the default IceTracks-DR2 14-year SkyLLH backend and the selectable
legacy 10-year backend use one project-local Python 3.12 environment:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install --require-hashes -r requirements_skyllh_v26_lock_cdx.txt
.venv/bin/python run_agent_wrap_cdx.py environment-check
```

The pinned stack is SkyLLH 26.0.0, NumPy 2.5.1, SciPy 1.18.0, and Astropy
8.0.1, plus ReportLab 5.0.0 for legacy report artifacts. The hash-locked file
contains exact transitive dependencies; `requirements_skyllh_v26_cdx.txt` is
the shorter direct-dependency source used to regenerate it.

Run the selected sample's preflight before every analysis:

```bash
.venv/bin/python run_agent_wrap_cdx.py environment-check --data-sample icecube_public_ps_14yr_dr2
.venv/bin/python run_agent_wrap_cdx.py environment-check --data-sample icecube_public_ps_14yr_dr2 --likelihood-mode spatial_only
.venv/bin/python run_agent_wrap_cdx.py environment-check --data-sample icecube_public_ps_10yr
```

The Skill always invokes `.venv/bin/python`; it never depends on a temporary
environment or whichever `python3` happens to be active. SkyLLH source code and
the virtual environment are not copied into the repository: exact versions and
artifact hashes in the lock file make installation reproducible for each user.
The older Conda specification is retained only as historical private-alpha
provenance and is not the supported combined runtime.

## Included Data

The private Git checkout includes the audited subset required by the callable backend:

- five IceCube event samples;
- five uptime tables;
- five effective-area tables;
- five derived background PDF tables.

The local DR2 analysis additionally requires the IceTracks-DR2 release plus
the pre-calculated tables under `data_output/bkgd_pdfs_cdx/14yr_dr2_cdx/` and
`data_output/signal_energy_pdfs_cdx/14yr_dr2_cdx/`. Their provenance JSON files
record input/output SHA-256 values, package versions, axes, normalization
checks, and interpolation validation. These large products are not rebuilt by
an analysis run.

The preflight is likelihood-mode aware. DR2 spatial+energy requires both
background and signal-energy products. DR2 spatial-only requires the event,
uptime, IRF, and background spatial-PDF products but does not require or load
the signal-energy tables.

`data_manifest_private_alpha_cdx.json` records every required path and SHA-256 value. Verify the clone with:

```bash
.venv/bin/python verify_private_alpha_setup_cdx.py --hashes
```

Generated analysis products and unrelated local data are excluded from Git.

## Workbook Output

CSV and PDF outputs use the Python backend. Excel workbook generation additionally requires Node.js and `@oai/artifact-tool`; Codex may supply these through its bundled runtime. If unavailable, review reports the missing workbook rather than silently claiming full completion.

## Private Collaboration

Add collaborators by GitHub username. Each collaborator should authenticate with their own account; never share account passwords.

Keep `main` usable, use short-lived branches for development, and record scientific parameter changes explicitly in pull requests. Do not make the repository or included data public until data terms, provenance, software license, authorship, affiliation, and citation metadata are settled.

Problem reports should include the task ID, terminal state, `agent_review_cdx.json`, and the relevant run `review_cdx.json`, but not private or unpublished source catalogs.
