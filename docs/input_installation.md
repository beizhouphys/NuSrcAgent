# One-command installation

The installation script works with Python 3.12 on macOS/Linux. Python must
already be installed with its `venv` and pip tools, used to create a separate
Python environment and install libraries. Run the command from the project
folder containing `install.sh`. Inputs are hosted on GitHub, not fetched manually
from IceCube. The repository is private: collaborators need repository read
access and an existing GitHub HTTPS login (`gh auth login`, Git credential
helper, or `GH_TOKEN`/`GITHUB_TOKEN`). An SSH key alone cannot authenticate an
HTTPS asset download; SSH-only users must log in with `gh auth login` once.
No maintainer credentials are included in the checkout or written by installation.

```bash
bash install.sh
```

The script creates `.venv/`, a Python environment inside the project folder,
installs the specified versions of all required libraries, downloads the input
archives and checks that they contain the expected data and PDF tables.
It installs no PDF construction tools and starts no scientific analysis or trials.
Python itself is a prerequisite; automatic operating-system Python installation
and a native Windows installation script are not implemented.
Set `NUSRC_PYTHON` to an existing Python 3.12 executable if it is not named
`python3.12`. The script does not install the optional DR1 Excel-workbook
dependency; numerical analysis and CSV/PDF outputs are separate from that feature.

When the command finishes successfully, you can run the
[worked examples](quickstart.md) with `.venv/bin/python`. There is no need to
activate an environment or change your system-wide Python installation.

## What data are downloaded?

A bundle is simply an archive of related input files, unpacked by the script.
PDF below means probability density function, not a PDF document.

Default DR2 spatial+energy installs six assets: one raw-data archive (events,
uptime, effective areas, smearing matrices, original README), one frozen v3
background archive, and four already-compressed SEpdf table archives with
provenance. The optional DR1 supported-input archive is separate.

Events describe the reconstructed tracks; uptime specifies the observation
intervals. Effective areas describe the detector's signal acceptance, while
smearing matrices describe the response from true neutrino quantities to
reconstructed quantities. The precomputed PDFs are the numerical probability
densities used by the likelihood. Installing them does not recalculate or tune
their definitions.

Numerical archives are distributed separately, not committed to Git. The raw
archive is our fixed copy of the public IceCube inputs, not a request for users
to navigate the official download website; attribution is retained in
[data attribution](data_attribution.md).

For reproducibility, a manifest is a file listing the inputs and their
identities. A SHA-256 checksum is a fingerprint of a file's bytes: it checks
that you received exactly the intended file, not that its model is correct.
`input_bundles.json` records filenames, sizes, archive SHA-256 values, snapshot
identities and every extracted file's path/size/hash. The installer pins this
manifest and rejects other snapshots. `raw_input_manifest.json`,
`pdf_release_manifest.json` and the separate DR1 manifest retain their numerical
identity checks. Frozen bytes are never rebuilt or silently replaced.

## GitHub login and alternative download locations

No token needs to be pasted into the installation command. The script first
uses an existing `GH_TOKEN`/`GITHUB_TOKEN` environment variable if supplied,
then your GitHub command-line login, then saved Git HTTPS credentials. These
are alternative ways to use your own account, not additional requirements.
If authentication fails, check that your account has repository access and,
if you use GitHub's `gh` tool, run `gh auth login` before retrying installation.

All seven assets are hosted in the existing `v0.2.0-private-alpha.4` Release.
That tag is only an input-storage location, not the installed code version
(currently 0.2.0); no existing tag was moved and no new tag/Release was created.
For maintainers: the shipped manifest fixes the HTTPS location, numeric GitHub
asset IDs, and archive/member hashes. Private assets are downloaded through the GitHub API
using your own credentials; authorization is removed before cross-host redirects.
An explicit mirror can be supplied through `--base-url`; it must serve the same
hash-pinned files. A maintainer-provided local directory is also supported with
`--bundle-dir /absolute/path/to/release_assets`.
No mutable latest-input selection or automatic upstream data substitution occurs.

## Optional data selections and checking an installation

The default command installs full14 DR2 spatial+energy inputs. To install the
separate DR1 inputs, or omit DR2 signal energy tables for a spatial-only fit,
use the first or second command below. The final two commands install/check
inputs in an existing environment. You do not need them for a normal first
installation, because `install.sh` already performs these steps.

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

## If installation is interrupted

Run the same installation command again. Already verified files are reused;
an incomplete archive may need downloading again. Keep the printed error if
you need help, but do not send passwords, tokens or an unpublished source catalog.

Archive and extracted-file hashes are checked before inputs are accepted.
Unexpected members, path traversal, links and altered existing inputs are
rejected. Existing verified inputs are reused. Downloads and verified extraction
staging remain in `.input_downloads/` for recovery and are Git-ignored; repeated
installation skips completed valid bundles/files. A failed partial download may
need to restart that archive. Differing existing inputs are preserved and reported
so the user can move them aside explicitly. No destructive repair is performed.

## Download size and disk space

The default install downloads six archives totaling 1,522,756,289 bytes (about
1.52 GB) and extracts 4,051,798,595 bytes (about 3.8 GiB). Keep additional free
space for the environment, retained downloads/staging, outputs and trial
checkpoints. Bundle contents and exact sizes are in [input_bundles.json](input_bundles.json).

After a successful installation, follow the [minimal examples](quickstart.md).
Installation/hash checks confirm environment and input identity, not scientific
validity; see the [verification record](input_installation_verification.md).
