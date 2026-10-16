"""Install the fixed project-provided input bundles; never construct PDFs.

Standard-library-only so the shell bootstrap can check its download source
before creating a virtual environment or installing dependencies.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile
from functools import lru_cache
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

MANIFEST = "docs/input_bundles.json"
MANIFEST_SHA256 = "9a9a9590a9e0d65ec922051028f3ad9829920cb9a20b579290cf4765524b6412"
SAMPLES = ("icecube_public_ps_14yr_dr2", "icecube_public_ps_10yr")


@lru_cache(maxsize=1)
def _github_token():
    """Reuse local GitHub authentication; never print or persist credentials."""
    for name in ("GH_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(name):
            return os.environ[name]
    if shutil.which("gh"):
        result = subprocess.run(["gh", "auth", "token", "--hostname", "github.com"],
                                capture_output=True, text=True, timeout=20)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    result = subprocess.run(["git", "credential", "fill"],
                            input="protocol=https\nhost=github.com\n\n",
                            env=dict(os.environ, GIT_TERMINAL_PROMPT="0"),
                            capture_output=True, text=True, timeout=20)
    if result.returncode == 0:
        credentials = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        if credentials.get("password"):
            return credentials["password"]
    raise ValueError("Private input downloads require GitHub repository access. Log in with gh auth login, or use Git HTTPS credentials / GH_TOKEN, then rerun bash install.sh. SSH-only clone authentication cannot authenticate HTTPS asset downloads.")


class _AssetRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        if urlparse(newurl).scheme != "https":
            raise ValueError("Input download redirected to a non-HTTPS URL")
        redirected = super().redirect_request(request, response, code, message, headers, newurl)
        if redirected is not None and urlparse(newurl).hostname != urlparse(request.full_url).hostname:
            redirected.remove_header("Authorization")
        return redirected


def _open_download(manifest, bundle, base):
    github = manifest.get("github_release")
    if github and base == manifest.get("download_base_url"):
        asset_id = int(bundle["github_asset_id"])
        url = f"https://api.github.com/repos/{github['repository']}/releases/assets/{asset_id}"
        headers = {"Accept": "application/octet-stream", "User-Agent": "NuSrcAgent-input-installer",
                   "Cache-Control": "no-cache"}
        if github.get("private"):
            headers["Authorization"] = "Bearer " + _github_token()
        request = Request(url, headers=headers)
        return build_opener(_AssetRedirectHandler()).open(request, timeout=120)
    return urlopen(base.rstrip("/") + "/" + bundle["filename"], timeout=120)


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_manifest(root):
    path = Path(root) / MANIFEST
    if sha256(path) != MANIFEST_SHA256:
        raise ValueError("Input-bundle manifest hash mismatch; use the matching source checkout")
    value = json.loads(path.read_text())
    if value.get("schema_version") != 1:
        raise ValueError("Unsupported input-bundle schema")
    return value


def selected_bundles(manifest, sample, mode):
    if sample not in SAMPLES or mode not in (None, "spatial_energy", "spatial_only"):
        raise ValueError("Unsupported input sample or likelihood mode")
    if sample == SAMPLES[1] and mode not in (None, "spatial_only"):
        raise ValueError("DR1 supports spatial_only")
    return [r for r in manifest["bundles"] if sample in r["samples"]
            and not (mode == "spatial_only" and r["kind"] == "signal_energy")]


def preflight_source(root, sample=SAMPLES[0], mode=None, bundle_directory=None, base_url=None):
    manifest = load_manifest(root)
    bundles = selected_bundles(manifest, sample, mode)
    base = base_url or manifest.get("download_base_url")
    if bundle_directory:
        directory = Path(bundle_directory).expanduser().resolve()
        missing = [r["filename"] for r in bundles if not (directory / r["filename"]).is_file()]
        if missing:
            raise ValueError("Local input bundle files are missing: " + ", ".join(missing))
    elif not base:
        raise ValueError("Input bundles are prepared locally but not published yet. For local verification, use --bundle-dir PATH; a published checkout will contain the fixed download URL.")
    elif urlparse(base).scheme != "https":
        raise ValueError("The input-bundle download base URL must use HTTPS")
    elif base == manifest.get("download_base_url") and manifest.get("github_release", {}).get("private"):
        _github_token()
    return manifest, bundles, base


def _safe_target(root, relative):
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] not in ("data_input", "data_output"):
        raise ValueError(f"Invalid input-bundle destination: {relative}")
    target = root.joinpath(*path.parts)
    if not target.resolve().is_relative_to(root):
        raise ValueError(f"Input path escapes checkout through a symlink: {relative}")
    return target


def _matching_file(target, record):
    return (target.is_file() and target.stat().st_size == record["bytes"]
            and sha256(target) == record["sha256"])


def _extract_checked(root, archive, bundle):
    expected = {r["path"]: r for r in bundle["files"]}
    seen = set()
    installed = 0
    with tarfile.open(archive, "r:*") as stream:
        for member in stream:
            if member.name not in expected or member.name in seen or not member.isfile():
                raise ValueError(f"Unexpected, duplicate or non-regular archive member: {member.name}")
            seen.add(member.name)
            record = expected[member.name]
            if member.size != record["bytes"]:
                raise ValueError(f"Archive member size mismatch: {member.name}")
            target = _safe_target(root, member.name)
            if target.exists():
                if not _matching_file(target, record):
                    raise ValueError(f"Existing input differs from the frozen snapshot: {target}. Move it aside before reinstalling; it was not overwritten.")
                continue
            staging = root / ".input_downloads/staging" / bundle["id"] / member.name
            staging.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            source = stream.extractfile(member)
            if source is None:
                raise ValueError(f"Unreadable archive member: {member.name}")
            with source, staging.open("wb") as output:
                while block := source.read(1024 * 1024):
                    digest.update(block)
                    output.write(block)
            if digest.hexdigest() != record["sha256"]:
                raise ValueError(f"Extracted input hash mismatch: {member.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            # Atomic, exclusive placement; staging lives on this same filesystem.
            # Retain the staging link for recovery rather than permanently deleting it.
            os.link(staging, target)
            installed += 1
    if seen != set(expected):
        raise ValueError("Archive is missing declared input files")
    return installed


def install_inputs(root, sample=SAMPLES[0], mode=None, bundle_directory=None, base_url=None):
    root = Path(root).resolve()
    manifest = load_manifest(root)
    bundles = selected_bundles(manifest, sample, mode)
    results = []
    for bundle in bundles:
        records = bundle["files"]
        targets = [_safe_target(root, r["path"]) for r in records]
        if all(_matching_file(p, r) for p, r in zip(targets, records, strict=True)):
            results.append({"id": bundle["id"], "status": "already_verified", "files": len(records)})
            continue
        _, _, base = preflight_source(root, sample, mode, bundle_directory, base_url)
        if bundle_directory:
            archive = Path(bundle_directory).expanduser().resolve() / bundle["filename"]
        else:
            archive = root / ".input_downloads" / bundle["filename"]
            archive.parent.mkdir(parents=True, exist_ok=True)
            if not _matching_file(archive, bundle):
                partial = archive.with_suffix(archive.suffix + ".part")
                print(f"Downloading {bundle['filename']} ({bundle['bytes'] / 1e6:.1f} MB)", file=sys.stderr, flush=True)
                with _open_download(manifest, bundle, base) as response, partial.open("wb") as output:
                    shutil.copyfileobj(response, output, 1024 * 1024)
                if not _matching_file(partial, bundle):
                    raise ValueError(f"Downloaded archive hash mismatch: {bundle['filename']}")
                partial.replace(archive)
        if not _matching_file(archive, bundle):
            raise ValueError(f"Input archive hash mismatch: {bundle['filename']}")
        installed = _extract_checked(root, archive, bundle)
        if not all(_matching_file(p, r) for p, r in zip(targets, records, strict=True)):
            raise ValueError(f"Post-install hash mismatch in {bundle['id']}")
        results.append({"id": bundle["id"], "status": "installed", "files": len(records), "new_files": installed})
    return {"status": "pass", "data_sample": sample, "likelihood_mode": mode,
            "input_manifest_sha256": MANIFEST_SHA256, "bundles": results}
