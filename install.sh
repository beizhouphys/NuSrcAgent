#!/usr/bin/env bash
set -euo pipefail

# Bootstrap the pinned environment and the matching project-provided inputs.
project_root="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_root"

platform="$(uname -s)"
host_arch="$(uname -m)"
required_arch=""
if [[ "$platform" == Darwin ]] && { [[ "$host_arch" == arm64 ]] ||
    /usr/bin/arch -arm64 /usr/bin/true 2>/dev/null; }; then
    host_arch=arm64
    required_arch=arm64
fi

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
run_native() {
    if [[ -n "$required_arch" ]]; then
        /usr/bin/arch "-$required_arch" "$@"
    else
        "$@"
    fi
}

compatible_python() {
    run_native "$1" -c '
import platform
import sys
required_arch = sys.argv[1]
sys.exit(0 if sys.version_info[:2] == (3, 12)
         and (not required_arch or platform.machine() == required_arch) else 1)
' "$required_arch" >/dev/null 2>&1
}

venv_builder() {
    compatible_python "$1" && run_native "$1" -c 'import ensurepip, venv' >/dev/null 2>&1
}

find_python() {
    local candidate conda_base
    while IFS= read -r candidate; do
        if [[ "$platform" == Darwin && "$candidate" == /usr/bin/python3 ]]; then
            continue
        fi
        if venv_builder "$candidate"; then
            printf '%s\n' "$candidate"
            return
        fi
    done < <(type -aP python3.12 python3 || true)

    if [[ "$platform" == Darwin ]]; then
        for candidate in /opt/homebrew/bin/python3.12 \
                         /opt/homebrew/opt/python@3.12/bin/python3.12 \
                         /Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12; do
            if venv_builder "$candidate"; then
                printf '%s\n' "$candidate"
                return
            fi
        done
    fi

    if conda_base="$(conda info --base 2>/dev/null)" && [[ -n "$conda_base" ]]; then
        for candidate in "$conda_base/bin/python3.12" "$conda_base"/envs/*/bin/python3.12; do
            if venv_builder "$candidate"; then
                printf '%s\n' "$candidate"
                return
            fi
        done
    fi
    return 1
}

bootstrap_uv() {
    local bootstrap_dir="$1" target expected_hash actual_hash staging archive uv_executable
    local uv_version=0.13.10
    case "$platform:$host_arch" in
        Darwin:arm64)
            target=uv-aarch64-apple-darwin
            expected_hash=e419bf07533bdbf48795fc793601c834dd79db57a8c49ce8e25cfe3a8639958d ;;
        Darwin:x86_64)
            target=uv-x86_64-apple-darwin
            expected_hash=153e03197588204c04fc4c81cc4bafbfa4280222a385e4ee36a87aeec0ae63b4 ;;
        Linux:aarch64|Linux:arm64)
            target=uv-aarch64-unknown-linux-musl
            expected_hash=68174084fe40b6300361c5b2038066120dc62c92920c22a0f31f6fc74b066b57 ;;
        Linux:x86_64)
            target=uv-x86_64-unknown-linux-musl
            expected_hash=5597970380083a340b7983af05a84824b4db1c62b7059c796935b7fd6dc95fd2 ;;
        *)
            printf 'Automatic Python setup is unavailable on %s %s.\n' "$platform" "$host_arch" >&2
            return 1 ;;
    esac
    uv_executable="$bootstrap_dir/$uv_version/$target/uv"
    if [[ ! -x "$uv_executable" ]]; then
        printf 'Downloading uv %s to set up Python 3.12.\n' "$uv_version" >&2
        mkdir -p "${uv_executable%/*}" || return 1
        staging="$(mktemp -d "$bootstrap_dir/download.XXXXXXXX")" || return 1
        archive="$staging/$target.tar.gz"
        curl --fail --silent --show-error --location --retry 2 --connect-timeout 15 --max-time 120 \
            "https://releases.astral.sh/github/uv/releases/download/$uv_version/$target.tar.gz" \
            --output "$archive" || return 1
        if command -v sha256sum >/dev/null; then
            actual_hash="$(sha256sum < "$archive")" || return 1
        else
            actual_hash="$(shasum -a 256 < "$archive")" || return 1
        fi
        if [[ "${actual_hash%% *}" != "$expected_hash" ]]; then
            printf 'SHA-256 mismatch for %s.\n' "$target.tar.gz" >&2
            return 1
        fi
        tar -xzf "$archive" -C "$staging" "$target/uv" || return 1
        mv "$staging/$target/uv" "$uv_executable" || return 1
    fi
    printf '%s\n' "$uv_executable"
}

bootstrap_python() {
    local bootstrap_dir="$project_root/.bootstrap" uv_executable
    uv_executable="$(bootstrap_uv "$bootstrap_dir")" || return 1
    export UV_PYTHON_INSTALL_DIR="$bootstrap_dir/python"
    export UV_CACHE_DIR="$bootstrap_dir/cache"
    run_native "$uv_executable" --no-config python install --no-bin 3.12 >&2 || return 1
    run_native "$uv_executable" --no-config python find --managed-python 3.12
}

python_requirement="${required_arch:+$required_arch }Python 3.12 with venv and ensurepip"
reuse_venv=false
if [[ -f .venv/pyvenv.cfg ]] && compatible_python .venv/bin/python; then
    reuse_venv=true
fi

if [[ -n "${NUSRC_PYTHON:-}" ]]; then
    python_command="$NUSRC_PYTHON"
    if ! venv_builder "$python_command"; then
        printf 'NUSRC_PYTHON=%s must point to %s.\n' "$python_command" "$python_requirement" >&2
        exit 2
    fi
elif "$reuse_venv"; then
    python_command=.venv/bin/python
elif ! python_command="$(find_python)"; then
    if ! python_command="$(bootstrap_python)" ||
       ! venv_builder "$python_command"; then
        printf 'Could not set up %s. Set NUSRC_PYTHON and rerun bash install.sh.\n' "$python_requirement" >&2
        exit 2
    fi
fi
# Check the fixed download source and private-repository authentication early.
run_native "$python_command" -c '
from agent_core.input_install import preflight_source
import sys
try:
    preflight_source(".", sys.argv[1], sys.argv[2], sys.argv[3] or None, sys.argv[4] or None)
except (ValueError, OSError) as exc:
    raise SystemExit(str(exc))
' "$sample" "$mode" "$bundle_directory" "$base_url"
if ! "$reuse_venv"; then
    if [[ -e .venv || -L .venv ]]; then
        backup_dir="$(mktemp -d "$project_root/.venv-backup.XXXXXXXX")"
        mv .venv "$backup_dir/"
        printf 'Saved previous environment in %s/.venv\n' "$backup_dir"
    fi
    run_native "$python_command" -m venv .venv
fi
if ! run_native .venv/bin/python -m pip --version >/dev/null 2>&1; then
    run_native .venv/bin/python -m ensurepip
fi
run_native .venv/bin/python -c 'import platform, sys; print(f"Project Python {platform.python_version()} ({platform.machine()}) at {sys.executable}")'
run_native .venv/bin/python -m pip install --disable-pip-version-check --require-hashes -r requirements_skyllh_v26_lock.txt
install_options=(--data-sample "$sample" --likelihood-mode "$mode")
if [[ -n "$bundle_directory" ]]; then install_options+=(--bundle-dir "$bundle_directory"); fi
if [[ -n "$base_url" ]]; then install_options+=(--base-url "$base_url"); fi
run_native .venv/bin/python run_agent_wrap.py install-inputs "${install_options[@]}"
run_native .venv/bin/python verify_private_alpha_setup.py --data-sample "$sample" --likelihood-mode "$mode" --hashes
echo "Installation and input verification complete."
