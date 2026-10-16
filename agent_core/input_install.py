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
import sys
import tarfile
from urllib.parse import urlparse
from urllib.request import urlopen

MANIFEST = "docs/input_bundles.json"
MANIFEST_SHA256 = "fb2b36c2ad3f6b4336b0a9115958ce3a9fcb3ab90ba9de91aafe203ac64e8e54"
SAMPLES = ("icecube_public_ps_14yr_dr2", "icecube_public_ps_10yr")


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
                with urlopen(base.rstrip("/") + "/" + bundle["filename"], timeout=120) as response, partial.open("wb") as output:
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
