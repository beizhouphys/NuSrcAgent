# One-command installation

The bootstrap targets macOS/Linux and requires Python 3.12, `venv` and pip.
It has been verified on macOS using local bundles; a public HTTPS installation
and other platforms have not yet been validated. Run from the checkout root.

**Current preparation copy:** the public download endpoint is unset. Obtain
the prepared bundles from the maintainer and use their absolute directory:

```bash
bash install.sh --bundle-dir /absolute/path/to/release_assets
```

**After the bundles are published and their URL is pinned:**

```bash
bash install.sh
```

The bootstrap creates a checkout-local environment, installs the exact locked
dependencies, installs our fixed input bundles and verifies the selected sample.
It installs no PDF construction tools and starts no scientific analysis or trials.
Python itself is a prerequisite; automatic operating-system Python installation
and a native Windows bootstrap are not implemented.
Set `NUSRC_PYTHON` to an existing Python 3.12 executable if it is not named
`python3.12`. The script does not install the optional DR1 Excel-workbook
dependency; numerical analysis and CSV/PDF outputs are separate from that feature.

## Bundle contents

Default DR2 spatial+energy installs six assets: one raw-data archive (events,
uptime, effective areas, smearing matrices, original README), one frozen v3
background archive, and four already-compressed SEpdf table archives with
provenance. The optional DR1 supported-input archive is separate.
Numerical archives are distributed separately, not committed to Git. The raw
archive is our fixed copy of the public IceCube inputs, not a request for users
to navigate the official download website; attribution is retained in
[data attribution](data_attribution.md).

`input_bundles.json` records filenames, sizes, archive SHA-256 values, snapshot
identities and every extracted file's path/size/hash. The installer pins this
manifest and rejects other snapshots. `raw_input_manifest.json`,
`pdf_release_manifest.json` and the separate DR1 manifest retain their numerical
identity checks. Frozen bytes are never rebuilt or silently replaced.

## During release preparation

After publishing the approved assets, the maintainer sets the fixed HTTPS
`download_base_url` in the bundled manifest and updates the code's pinned
manifest hash. Users then need only the default command. An explicit mirror can
be supplied through `--base-url`; it must serve the same hash-pinned files.
No mutable latest-input selection or automatic upstream data substitution occurs.

## Options and repeated installation

```bash
# Current local-bundle route; omit --bundle-dir only after URL publication.
bash install.sh --bundle-dir /absolute/path/to/release_assets --data-sample icecube_public_ps_10yr
bash install.sh --bundle-dir /absolute/path/to/release_assets --likelihood-mode spatial_only
.venv/bin/python run_agent_wrap.py install-inputs --bundle-dir /absolute/path/to/release_assets
.venv/bin/python verify_private_alpha_setup.py --hashes
```

The verifier command above checks default DR2 spatial+energy. Match an optional
installation with `--data-sample icecube_public_ps_10yr` or
`--likelihood-mode spatial_only`. `install.sh` runs the matching verification
automatically and finishes with `Installation and input verification complete.`
If dependencies need downloading, even the local-bundle route needs network
access to the Python package index unless the required packages are cached.

Archive and extracted-file hashes are checked before inputs are accepted.
Unexpected members, path traversal, links and altered existing inputs are
rejected. Existing verified inputs are reused. Downloads and verified extraction
staging remain in `.input_downloads/` for recovery and are Git-ignored; repeated
installation skips completed valid bundles/files. A failed partial download may
need to restart that archive. Differing existing inputs are preserved and reported
so the user can move them aside explicitly. No destructive repair is performed.

The default install downloads six archives totaling 1,522,756,289 bytes (about
1.52 GB) and extracts 4,051,798,595 bytes (about 3.8 GiB). Keep additional free
space for the environment, retained downloads/staging, outputs and trial
checkpoints. Bundle contents and exact sizes are in [input_bundles.json](input_bundles.json).

After a successful installation, follow the [minimal examples](quickstart.md).
Installation/hash checks confirm environment and input identity, not scientific
validity; the [verification record](input_installation_verification.md) separates
completed local checks from the pending public download-path check.
