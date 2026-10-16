# Data and environment

The combined environment uses Python 3.12, SkyLLH 26.0.0, NumPy 2.5.1,
SciPy 1.18.0, Astropy 8.0.1 and ReportLab 5.0.0. Install the exact dependency
set using `requirements_skyllh_v26_lock.txt` with pip `--require-hashes`.

All scientific paths are relative to the checkout root. `bash install.sh`
creates the environment and installs the selected project-provided raw data and
PDF bundles automatically. Users do not need to visit IceCube or choose files.
Public asset upload and the fixed download URL are pending; the complete local
route is `bash install.sh --bundle-dir /path/to/release_assets`.
See [installation details](input_installation.md) and [attribution](data_attribution.md).

## DR2 full14

Raw release directory:
`data_input/IceCube_data_released/2026_icecube_14_year_track_data_IceTracks_DR2/`.
It contains `DR2_readme.txt`, 14 event and uptime season files (IC40, IC59, IC79,
IC86 I–XI), and the IC40/59/79/86 effective-area and smearing CSV files.
The analysis pools IC86 I–XI and uses 1,643,355 events without default cuts.
The raw file hashes are recorded in `raw_input_manifest.json` in this directory.

Frozen v3 background products live in `data_output/bkgd_pdfs/14yr_dr2_v3/`:
four `background_model_<dataset>_DR2_v3.npz` files and four aligned
`bkgd_pdf_<dataset>_exp_DR2.txt` tables. The production datasets are IC40,
IC59, IC79 and IC86_I-XI. These are byte-identical copies of the approved
frozen numerical artifacts, not recalculated models.

Signal-energy tables live in `data_output/signal_energy_pdfs/14yr_dr2/`:
four `signal_energy_pdf_powerlaw_<dataset>_DR2.npz` files. The copied provenance
retains input IRF hashes, table axes and normalization/interpolation checks.
Original host paths and construction timings are omitted.

`pdf_release_manifest.json` maps original numerical paths to release paths and
retains their original SHA-256 values and original provenance identities.
The runtime pins the derived manifest, verifies v3 files before loading, verifies
signal table hashes before interpolation, and checks background event alignment.
Spatial-only does not load or require the signal-energy tables.

## DR1

Use `icecube_public_ps_10yr` explicitly. The directory is
`data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/`.
The required subset consists of five event files in `events/uncorrected_probably/`,
five uptime files, five effective-area files and five background tables under
`data_output/bkgd_pdfs/`. Exact paths and hashes are listed in
`../data_manifest_private_alpha.json`. These include the historical pooled
IC86 II–VII product; it must not be silently replaced with DR2 events.
DR2 v3 is never substituted for DR1 background inputs.

## Verification

```bash
.venv/bin/python run_agent_wrap.py environment-check --data-sample icecube_public_ps_14yr_dr2
.venv/bin/python verify_private_alpha_setup.py --hashes
.venv/bin/python verify_private_alpha_setup.py --data-sample icecube_public_ps_10yr --hashes
```

The optional DR1 workbook builder uses Node.js and `@oai/artifact-tool` installed
under this checkout's `node_modules/`. A public installation route for that
optional dependency remains pending. CSV and PDF outputs are independent of
the workbook; missing workbook support is reported as a warning.
