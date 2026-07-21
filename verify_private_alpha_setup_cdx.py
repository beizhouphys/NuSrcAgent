from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Verify the NuSrcAgent private-alpha environment and data bundle.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--manifest", default="data_manifest_private_alpha_cdx.json")
    parser.add_argument("--hashes", action="store_true", help="Compute SHA-256 for every required data file.")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).expanduser().resolve()
    manifest_path = root / args.manifest
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks = []
    checks.append(check_python())
    checks.append(check_numpy())
    for item in manifest["files"]:
        path = root / item["path"]
        if not path.exists():
            checks.append({"id": item["path"], "status": "fail", "message": "missing"})
        elif args.hashes:
            actual = sha256_file(path)
            checks.append({"id": item["path"], "status": "pass" if actual == item["sha256"] else "fail", "message": "sha256 verified" if actual == item["sha256"] else "sha256 mismatch"})
        else:
            checks.append({"id": item["path"], "status": "pass", "message": "present"})
    statuses = [item["status"] for item in checks]
    status = "fail" if "fail" in statuses else ("warning" if "warning" in statuses else "pass")
    result = {"status": status, "python": platform.python_version(), "hashes_checked": bool(args.hashes), "checks": checks}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if status == "fail" else 0


def check_python():
    supported = sys.version_info[:2] == (3, 8)
    return {"id": "python", "status": "pass" if supported else "warning", "message": "Python 3.8 is the private-alpha supported runtime"}


def check_numpy():
    try:
        import numpy
    except ImportError:
        return {"id": "numpy", "status": "fail", "message": "NumPy is not installed"}
    supported = numpy.__version__ == "1.24.4"
    return {"id": "numpy", "status": "pass" if supported else "warning", "message": "installed version %s; tested version 1.24.4" % numpy.__version__}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
