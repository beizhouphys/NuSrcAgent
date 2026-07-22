# Private-Alpha Data Setup

## Policy

The private repository includes the audited LLH input subset required by the current callable backend. Generated analysis products and unrelated local data remain excluded from Git.

Repository access is for explicitly invited collaborators. Do not make the repository public or redistribute its data without confirming the applicable IceCube data terms and the provenance of the corrected combined event sample.

## Included data

The Git checkout contains only the files required by the current callable time-integrated backend:

- five event samples under `data_input/.../events/uncorrected_probably/`;
- five uptime tables under `data_input/.../uptime/`;
- five effective-area tables under `data_input/.../irfs/`;
- five derived background PDF tables under `data_output/bkgd_pdfs_cdx/`.

No separate download or extraction is required. Verify presence and hashes from the repository root:

```bash
python3 verify_private_alpha_setup_cdx.py --hashes
```

The verifier does not upload or modify any data. `data_manifest_private_alpha_cdx.json` defines the tracked data set and expected SHA-256 values; the bundle builder remains available only for archival compatibility.

## Workbook output

CSV and PDF outputs use the Python backend. Excel workbook generation additionally requires Node.js and `@oai/artifact-tool`; Codex installations may supply these through the bundled runtime. If unavailable, the run review reports the missing workbook rather than silently claiming full completion.
