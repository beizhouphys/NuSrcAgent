# Observation data, detector response and Python libraries

The likelihood uses reconstructed IceCube tracks, detector observation periods,
effective areas, response matrices and precomputed probability densities.
The installation script supplies the matching inputs; this page explains what
they contain and where to find them. PDF means probability density function.

The combined environment uses Python 3.12, SkyLLH 26.0.0, NumPy 2.5.1,
SciPy 1.18.0, Astropy 8.0.1 and ReportLab 5.0.0. Install the exact dependency
set using `requirements_skyllh_v26_lock.txt` with pip `--require-hashes`.
These exact versions are installed by `bash install.sh`; users do not need to
choose or install each library separately. SkyLLH performs likelihood fitting;
NumPy/SciPy and Astropy provide numerical and astronomy utilities.

All scientific paths are relative to the checkout root. `bash install.sh`
creates the environment and installs the selected project-provided raw data and
PDF bundles automatically. Users do not need to visit IceCube or choose files.
All seven bundles are hosted on the existing GitHub Release and their URLs,
asset IDs and hashes are pinned. Private downloads reuse the collaborator's
GitHub login; `bash install.sh` needs no local bundle directory.
See [installation details](input_installation.md) and [attribution](data_attribution.md).

## Source catalogs

The versioned radio-bright AGN CSVs are in `data_input/sources/`; see the
[catalog notes](../data_input/sources/README.md) for the 3386-source selection,
columns, radio-flux weights and attribution. They are included in the code
checkout, not in the large IceCube/PDF input bundles. Other private catalogs
are not distributed. Use `--catalog` to analyze a supplied CSV.

## DR2: the 14-year sample

Raw release directory:
`data_input/IceCube_data_released/2026_icecube_14_year_track_data_IceTracks_DR2/`.
It contains `DR2_readme.txt`, 14 event and uptime season files (IC40, IC59, IC79,
IC86 I–XI), and the IC40/59/79/86 effective-area and smearing CSV files.
The analysis pools IC86 I–XI and uses 1,643,355 events without default cuts.
The raw file hashes are recorded in `raw_input_manifest.json` in this directory.
An event's reconstructed energy proxy is not its true neutrino energy.
Effective areas and smearing matrices describe detector acceptance and energy/
direction response; uptime files specify when the detector was taking data.

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
Spatial-only does not load or require the signal-energy tables. File checksums
and manifests ensure the same numerical inputs are used on different computers;
they do not establish that a PDF is an unbiased description of the data.

## DR1

Use `icecube_public_ps_10yr` explicitly. The directory is
`data_input/IceCube_data_released/2021_icecube_10_year_track_data_point_source/`.
The required subset consists of five event files in `events/uncorrected_probably/`,
five uptime files, five effective-area files and five background tables under
`data_output/bkgd_pdfs/`. Exact paths and hashes are listed in
`../data_manifest_private_alpha.json`. These include the historical pooled
IC86 II–VII product; it must not be silently replaced with DR2 events.
DR2 v3 is never substituted for DR1 background inputs.

## Check the installed sample

The normal installer checks the selected sample automatically. `environment-check`
checks the Python environment and presence of required files. The separate
verifier with `--hashes` also checks file contents against the recorded
checksums. Use the DR1 command only after installing its optional inputs.

```bash
.venv/bin/python run_agent_wrap.py environment-check --data-sample icecube_public_ps_14yr_dr2
.venv/bin/python verify_private_alpha_setup.py --hashes
.venv/bin/python verify_private_alpha_setup.py --data-sample icecube_public_ps_10yr --hashes
```

The optional DR1 workbook builder uses Node.js and `@oai/artifact-tool` installed
under this checkout's `node_modules/`. A public installation route for that
optional dependency remains pending. CSV and PDF outputs are independent of
the workbook; missing workbook support is reported as a warning.
