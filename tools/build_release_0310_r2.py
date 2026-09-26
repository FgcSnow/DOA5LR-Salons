"""Rebuild the PUBLISHED 0.3.10 archive with the 0.3.10 guide (r2): same pack version, only the README changes.

The published 0.3.10 ZIP shipped READ-ME-FIRST-EN.txt, START-HERE.md and InputLab/START-HERE-EN.md titled 0.3.9.
r2 replaces those three copies with docs/INPUT-SETTINGS.md (tools/pack_docs.py) and recomputes SHA256SUMS.txt.
Every other entry stays byte-identical, including DOA5LR-Salons-VERSION.txt (installed 0.3.10 packs are not
asked to update). Output: the ZIP under its final name and under a temporary asset name, version.txt (final)
and version-phase1.txt (points to the temporary asset while the raw version.txt cache expires).

  python tools/build_release_0310_r2.py --release-dir <DOA5LR-Salons-0.3.10-Release> --out <folder>
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_release_0310 import write_zip, INSTALLER, INSTALLER_SHA256, REL_BASE  # noqa: E402
from pack_docs import GUIDE_COPIES, check_pack_guides, pack_guides  # noqa: E402

VERSION = "0.3.10"
ZIP_NAME = f"DOA5LR-Salons-{VERSION}.zip"
TEMP_NAME = f"DOA5LR-Salons-{VERSION}-r2.zip"
PUBLISHED_SHA256 = "0e3e8e135bff271107bef269843e5d3e8c31905fa9c9cdcb370d058fb52ddd31"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def manifest(base: str, name: str, data: bytes) -> str:
    out = []
    for line in base.splitlines():
        if line.startswith("url="):
            line = f"url={REL_BASE}/{name}"
        elif line.startswith("sha256="):
            line = f"sha256={sha(data)}"
        elif line.startswith("size="):
            line = f"size={len(data)}"
        out.append(line)
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--release-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    published = (args.release_dir / ZIP_NAME).read_bytes()
    if sha(published) != PUBLISHED_SHA256:
        raise ValueError("not the published 0.3.10 archive")
    installer = (args.release_dir / INSTALLER).read_bytes()
    if sha(installer) != INSTALLER_SHA256:
        raise ValueError("installer is not the published 1.3.1")
    base_manifest = (args.release_dir / "version.txt").read_text(encoding="utf-8")
    if f"sha256={PUBLISHED_SHA256}" not in base_manifest:
        raise ValueError("version.txt is not the published 0.3.10 manifest")
    with ZipFile(args.release_dir / ZIP_NAME) as z:
        base = {n: z.read(n) for n in z.namelist()}

    payload = dict(base)
    payload.update(pack_guides(VERSION))
    payload["SHA256SUMS.txt"] = "".join(f"{sha(payload[n])} *{n}\n" for n in sorted(payload) if n != "SHA256SUMS.txt").encode("ascii")
    check_pack_guides(payload, VERSION)
    changed = sorted(n for n in payload if payload[n] != base.get(n))
    if set(payload) != set(base) or set(changed) != set(GUIDE_COPIES) | {"SHA256SUMS.txt"}:
        raise AssertionError(f"unexpected changes: {changed}")
    if payload["DOA5LR-Salons-VERSION.txt"] != b"0.3.10\r\n" or payload[INSTALLER] != installer:
        raise AssertionError("version file or installer changed")

    args.out.mkdir(parents=True, exist_ok=True)
    zip_path = args.out / ZIP_NAME
    write_zip(zip_path, payload)
    data = zip_path.read_bytes()
    (args.out / TEMP_NAME).write_bytes(data)
    (args.out / INSTALLER).write_bytes(installer)
    (args.out / "version.txt").write_text(manifest(base_manifest, ZIP_NAME, data), encoding="utf-8", newline="\n")
    (args.out / "version-phase1.txt").write_text(manifest(base_manifest, TEMP_NAME, data), encoding="utf-8", newline="\n")
    (args.out / "SHA256SUMS.txt").write_text(f"{sha(data)} *{ZIP_NAME}\n{sha(data)} *{TEMP_NAME}\n{sha(installer)} *{INSTALLER}\n",
                                             encoding="ascii", newline="\n")
    report = {"version": VERSION, "revision": "r2", "from_sha256": PUBLISHED_SHA256, "zip": ZIP_NAME, "temp_asset": TEMP_NAME,
              "zip_sha256": sha(data), "zip_bytes": len(data), "zip_entries": len(payload), "changed": changed}
    (args.out / "build-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
