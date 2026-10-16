#!/usr/bin/env bash
set -euo pipefail

# Bootstrap the pinned environment and the matching project-provided inputs.
project_root="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_root"
python_command="${NUSRC_PYTHON:-python3.12}"
sample="icecube_public_ps_14yr_dr2"
mode=""
bundle_directory=""
base_url=""
while (($#)); do
    case "$1" in
        --bundle-dir) bundle_directory="$2"; shift 2 ;;
        --base-url) base_url="$2"; shift 2 ;;
        --data-sample) sample="$2"; shift 2 ;;
        --likelihood-mode) mode="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: bash install.sh [--bundle-dir PATH | --base-url HTTPS_URL] [--data-sample icecube_public_ps_14yr_dr2|icecube_public_ps_10yr] [--likelihood-mode spatial_energy|spatial_only]"
            exit 0 ;;
        *) echo "Unknown installation option: $1" >&2; exit 2 ;;
    esac
done
if [[ -z "$mode" ]]; then
    if [[ "$sample" == "icecube_public_ps_10yr" ]]; then mode="spatial_only"; else mode="spatial_energy"; fi
fi
if ! command -v "$python_command" >/dev/null; then
    echo "Python 3.12 is required. Install it, then rerun bash install.sh." >&2
    exit 2
fi
"$python_command" -c 'import sys; assert sys.version_info[:2] == (3, 12), "Python 3.12 is required"'
# Fail early if this unpublished checkout has no asset endpoint configured.
"$python_command" -c '
from agent_core.input_install import preflight_source
import sys
try:
    preflight_source(".", sys.argv[1], sys.argv[2], sys.argv[3] or None, sys.argv[4] or None)
except (ValueError, OSError) as exc:
    raise SystemExit(str(exc))
' "$sample" "$mode" "$bundle_directory" "$base_url"
if [[ ! -x .venv/bin/python ]]; then
    "$python_command" -m venv .venv
fi
.venv/bin/python -m pip install --disable-pip-version-check --require-hashes -r requirements_skyllh_v26_lock.txt
install_options=(--data-sample "$sample" --likelihood-mode "$mode")
if [[ -n "$bundle_directory" ]]; then install_options+=(--bundle-dir "$bundle_directory"); fi
if [[ -n "$base_url" ]]; then install_options+=(--base-url "$base_url"); fi
.venv/bin/python run_agent_wrap.py install-inputs "${install_options[@]}"
.venv/bin/python verify_private_alpha_setup.py --data-sample "$sample" --likelihood-mode "$mode" --hashes
echo "Installation and input verification complete."
