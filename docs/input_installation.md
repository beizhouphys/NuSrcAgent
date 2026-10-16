# One-command installation

The bootstrap targets macOS/Linux and requires Python 3.12, `venv` and pip.
Run from the checkout root. Inputs are hosted on GitHub, not fetched manually
from IceCube. The repository is private: collaborators need repository read
access and an existing GitHub HTTPS login (`gh auth login`, Git credential
helper, or `GH_TOKEN`/`GITHUB_TOKEN`). An SSH key alone cannot authenticate an
HTTPS asset download; SSH-only users must log in with `gh auth login` once.
No maintainer credentials are included in the checkout or written by installation.

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

## Download location and authentication

All seven assets are hosted in the existing `v0.2.0-private-alpha.4` Release.
That tag is only an input-storage location, not the installed code version
(currently 0.2.0); no existing tag was moved and no new tag/Release was created.
The shipped manifest pins the HTTPS location, numeric GitHub asset IDs, and
archive/member hashes. Private assets are downloaded through the GitHub API
using your own credentials; authorization is removed before cross-host redirects.
An explicit mirror can be supplied through `--base-url`; it must serve the same
hash-pinned files. A maintainer-provided local directory is also supported with
`--bundle-dir /absolute/path/to/release_assets`.
No mutable latest-input selection or automatic upstream data substitution occurs.

## Options and repeated installation

```bash
bash install.sh --data-sample icecube_public_ps_10yr
bash install.sh --likelihood-mode spatial_only
.venv/bin/python run_agent_wrap.py install-inputs
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
validity; see the [verification record](input_installation_verification.md).
