# Private-Alpha Data Setup

## Policy

LLH input data and generated analysis products are intentionally excluded from Git. The source repository contains code, tests, small example catalogs, and a cryptographic manifest only.

The private data bundle is for explicitly invited collaborators. Do not upload it to a public repository or redistribute it without confirming the applicable IceCube data terms and the provenance of the corrected combined event sample.

## Bundle

Expected bundle name:

```text
NuSrcAgent_data_v0.2.0_cdx.tar.gz
```

Extract it from the repository root:

```bash
tar -xzf NuSrcAgent_data_v0.2.0_cdx.tar.gz
```

It restores only the files required by the current callable time-integrated backend:

- five event samples under `data_input/.../events/uncorrected_probably/`;
- five uptime tables under `data_input/.../uptime/`;
- five effective-area tables under `data_input/.../irfs/`;
- five derived background PDF tables under `data_output/bkgd_pdfs_cdx/`.

Verify presence and hashes:

```bash
python3 verify_private_alpha_setup_cdx.py --hashes
```

The verifier does not upload or modify any data.

## Workbook output

CSV and PDF outputs use the Python backend. Excel workbook generation additionally requires Node.js and `@oai/artifact-tool`; Codex installations may supply these through the bundled runtime. If unavailable, the run review reports the missing workbook rather than silently claiming full completion.
