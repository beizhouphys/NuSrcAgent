"""Verify the selected runtime inputs and frozen numerical release hashes."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from agent_core.environment import check_environment, _required_paths
from agent_core.dr2_pdf_release import verify_v3_release, verify_signal_file


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--data-sample", choices=["icecube_public_ps_14yr_dr2", "icecube_public_ps_10yr"], default="icecube_public_ps_14yr_dr2")
    parser.add_argument("--likelihood-mode", choices=["spatial_energy", "spatial_only"])
    parser.add_argument("--manifest", help="Explicit alternative input manifest")
    parser.add_argument("--hashes", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve()
    environment = check_environment(root, args.data_sample, args.likelihood_mode)
    checks = []
    if args.data_sample == "icecube_public_ps_10yr":
        manifest_path = root / (args.manifest or "data_manifest_private_alpha.json")
    else:
        manifest_path = root / (args.manifest or "docs/raw_input_manifest.json")
    manifest = json.loads(manifest_path.read_text())
    required = {str(p) for p in _required_paths(args.data_sample, args.likelihood_mode)}
    declared = [r["path"] for r in manifest["files"]]
    covered = required if args.data_sample == "icecube_public_ps_10yr" else {p for p in required if p.startswith("data_input/")}
    checks.append({"id": "manifest_coverage", "status": "pass" if covered <= set(declared) and len(declared) == len(set(declared)) else "fail"})
    for row in manifest["files"]:
        path = root / row["path"]
        if row["path"] not in required:
            continue
        status = "pass" if path.is_file() else "fail"
        if args.hashes and status == "pass":
            with path.open("rb") as stream:
                status = "pass" if hashlib.file_digest(stream, "sha256").hexdigest() == row["sha256"] else "fail"
        checks.append({"path": row["path"], "status": status})
    if args.hashes and args.data_sample == "icecube_public_ps_14yr_dr2":
        try:
            release = verify_v3_release(root)
            checks.append({"id": "frozen_v3_hashes", "status": "pass", "files": len(release["files"])})
            if (args.likelihood_mode or "spatial_energy") == "spatial_energy":
                mapping = json.loads((root / "docs/pdf_release_manifest.json").read_text())
                for row in mapping["files"]:
                    if row["kind"] == "signal_powerlaw":
                        verify_signal_file(root, root / row["path"])
                        checks.append({"path": row["path"], "status": "pass"})
        except (ValueError, OSError) as exc:
            checks.append({"id": "frozen_pdf_hashes", "status": "fail", "message": str(exc)})
    failed = environment["status"] == "fail" or any(c["status"] == "fail" for c in checks)
    print(json.dumps({"status": "fail" if failed else "pass", "environment": environment, "hashes_checked": args.hashes, "checks": checks}, indent=2))
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
