from __future__ import annotations

import argparse
import json
import tarfile
from pathlib import Path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the private NuSrcAgent LLH data bundle from the audited manifest.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--manifest", default="data_manifest_private_alpha_cdx.json")
    parser.add_argument("--output", default="data_output/private_release_cdx/NuSrcAgent_data_v0.2.0_cdx.tar.gz")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).expanduser().resolve()
    manifest_path = root / args.manifest
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output = root / args.output
    missing = [item["path"] for item in manifest["files"] if not (root / item["path"]).exists()]
    if missing:
        raise ValueError("cannot build bundle; missing: %s" % ", ".join(missing))
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(str(output), "w:gz") as archive:
        archive.add(str(manifest_path), arcname=manifest_path.name)
        for item in manifest["files"]:
            archive.add(str(root / item["path"]), arcname=item["path"])
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
