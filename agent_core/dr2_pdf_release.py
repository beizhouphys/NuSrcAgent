"""Frozen v3 PDF verification using an explicit release path mapping.

Numerical file bytes and their original SHA-256 values are unchanged.
The derived manifest intentionally replaces private construction paths.
"""
import hashlib
from agent_core.file_cache import sha256_file
import json
from pathlib import Path

BACKGROUND_PDF_VERSION = "v3"
BACKGROUND_PDF_DIRECTORY = "data_output/bkgd_pdfs/14yr_dr2_v3"
BACKGROUND_PDF_PROVENANCE = BACKGROUND_PDF_DIRECTORY + "/background_pdf_provenance_DR2_v3.json"
RC1_MANIFEST = "docs/pdf_release_manifest.json"
RC1_SHA256 = "8be466d6ab508fe215b78708b5bdb97f53d3e2c3f1de0946a7352c186eab6df4"
ORIGINAL_RC1_SHA256 = "65ef8d7b84ae634f6ee58f046d7ccfac62a54616d2be7d14219de9fa2f88c6e3"
DATASET_NAMES = ("IC40", "IC59", "IC79", "IC86_I-XI")


def background_spec(version="v3"):
    if version != "v3":
        raise ValueError("This release distributes frozen DR2 background v3 only")
    return (BACKGROUND_PDF_DIRECTORY, "background_model_{name}_DR2_v3.npz", BACKGROUND_PDF_PROVENANCE)


def sha256(path):
    return sha256_file(path)


def _manifest(root):
    root = Path(root)
    if sha256(root / RC1_MANIFEST) != RC1_SHA256:
        raise ValueError("Release PDF path-mapping manifest hash mismatch")
    value = json.loads((root / RC1_MANIFEST).read_text())
    if value["original_frozen_manifest_sha256"] != ORIGINAL_RC1_SHA256:
        raise ValueError("Original frozen v3-RC1 identity mismatch")
    return value


def verify_v3_release(root):
    root = Path(root)
    manifest = _manifest(root)
    release = json.loads((root / BACKGROUND_PDF_PROVENANCE).read_text())
    if release["artifact_label"] != "v3" or release["parent_sha256"] != ORIGINAL_RC1_SHA256:
        raise ValueError("Invalid DR2 v3 release provenance")
    directory, pattern, _ = background_spec()
    paths = {f"{directory}/{filename}" for name in DATASET_NAMES for filename in
             (pattern.format(name=name), f"bkgd_pdf_{name}_exp_DR2.txt")}
    expected = {row["path"]: row["sha256"] for row in manifest["files"]
                if row["kind"] == "background_v3"}
    if set(expected) != paths or release["files"] != expected:
        raise ValueError("Unexpected DR2 v3 artifact set or provenance hashes")
    for path, value in expected.items():
        if sha256(root / path) != value:
            raise ValueError(f"DR2 v3 numerical artifact hash mismatch: {path}")
    return release


def verify_signal_file(root, path):
    root = Path(root)
    relative = str(Path(path).relative_to(root))
    expected = {row["path"]: row["sha256"] for row in _manifest(root)["files"]
                if row["kind"] == "signal_powerlaw"}
    if relative not in expected or sha256(path) != expected[relative]:
        raise ValueError(f"Signal energy PDF hash mismatch: {relative}")


def verify_background_release(root, version):
    background_spec(version)
    return verify_v3_release(root)
