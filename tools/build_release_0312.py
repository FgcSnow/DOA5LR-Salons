"""Build DOA5LR-Salons 0.3.12 = the PUBLISHED 0.3.11 pack + Replay Takeover 2.6 (lobby crash fix).

Input : the published 0.3.11 release folder (ZIP, installer and version.txt, SHA256 checked) and Replay Takeover 2.6
        in src/ReplayTakeover (the .asi is built from source/ReplayTakeover.cpp by source/build.cmd, SHA256 pinned below).
Changed: DOA5LR-ReplayTakeover.asi (2.6, signed), scripts/REPLAY-TAKEOVER-EN.txt, scripts/ReplayTakeover-Source
        (ReplayTakeover.cpp, build.cmd), the three guide copies (tools/pack_docs.py), VERSION and SHA256SUMS.
The installer is the published 1.3.2, byte-identical (re-uploaded with the release). Every other 0.3.11 file stays
byte-identical. Signing contacts the timestamp service. No publication, no game write.

  python tools/build_release_0312.py --base-dir <DOA5LR-Salons-0.3.11-Release> --out <folder>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_release_0311 import sha, sign, write_zip  # noqa: E402
from pack_docs import check_pack_guides, pack_guides  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
VERSION = "0.3.12"
GITHUB = "FgcSnow/DOA5LR-Salons"
REL_BASE = f"https://github.com/{GITHUB}/releases/download/v{VERSION}"
BASE_ZIP = "DOA5LR-Salons-0.3.11.zip"
BASE_ZIP_SHA256 = "0f43be109e04fdd84446853d9aa579b56feebf8864f350eb62d2f44c2c08d59a"
INSTALLER = "DOA5LR-Salons-Installer.exe"
INSTALLER_SHA256 = "eacd9d62da22997a7082b5f19e3a7217d9b9b577c3e2bbe2781ca4639643dfd6"   # published 1.3.2, unchanged
TAKEOVER = REPO / "src" / "ReplayTakeover"
TAKEOVER_ASI_SHA256 = "27f6d4d95a8cb3194ae305cb973ab4ff4285329fa794a22d23b0f9c8e790ab3d"   # 2.6, unsigned build
NOTES = [
    "notes=pack 0.3.12: fixes crashes in lobbies with Replay Takeover - version 2.6 sleeps completely while you are online",
    "note=0.3.12: after 0.3.11 some players crashed while browsing lobbies or creating a room. Replay Takeover 2.5 kept hooks "
    "in the game's memory and frame code active everywhere, lobbies included. Replay Takeover 2.6 goes fully to sleep while you "
    "are online (lobby list, rooms, online matches, spectating): the game runs untouched and F5/F6/F7 are left to other mods "
    "(F7 = copy the room link). Offline replays work exactly as before.",
    "note=0.3.12: every other file is byte-identical to 0.3.11 (installer 1.3.2 unchanged, your check box choices are kept).",
]


def manifest(base: str, zip_name: str, zip_data: bytes) -> str:
    drop = ("version=", "url=", "sha256=", "size=", "notes=", "installer=")
    lines = [l for l in base.splitlines() if not l.startswith(drop)]
    lines[1:1] = [f"version={VERSION}", f"url={REL_BASE}/{zip_name}", f"sha256={sha(zip_data)}", f"size={len(zip_data)}"] + NOTES
    k = next(i for i, l in enumerate(lines) if l.startswith("installer_version="))
    lines[k:k] = [f"installer={REL_BASE}/{INSTALLER}"]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    bz = (args.base_dir / BASE_ZIP).read_bytes()
    if sha(bz) != BASE_ZIP_SHA256:
        raise ValueError("base ZIP is not the published 0.3.11 archive")
    installer = (args.base_dir / INSTALLER).read_bytes()
    if sha(installer) != INSTALLER_SHA256:
        raise ValueError("base installer is not the published 1.3.2")
    base_manifest = (args.base_dir / "version.txt").read_text(encoding="utf-8-sig")
    if "version=0.3.11" not in base_manifest or f"sha256={BASE_ZIP_SHA256}" not in base_manifest \
            or f"installer_sha256={INSTALLER_SHA256}" not in base_manifest:
        raise ValueError("base version.txt is not the published 0.3.11 manifest")
    args.out.mkdir(parents=True, exist_ok=True)
    tmp_zip = args.out / "_base.zip"
    tmp_zip.write_bytes(bz)
    with ZipFile(tmp_zip) as z:
        payload = {n: z.read(n) for n in z.namelist()}
    tmp_zip.unlink()
    base = dict(payload)
    if payload[INSTALLER] != installer:
        raise AssertionError("the installer inside the 0.3.11 ZIP differs from the published one")

    asi = (TAKEOVER / "DOA5LR-ReplayTakeover.asi").read_bytes()
    if sha(asi) != TAKEOVER_ASI_SHA256:
        raise ValueError("src/ReplayTakeover/DOA5LR-ReplayTakeover.asi is not the Replay Takeover 2.6 build")
    cpp = (TAKEOVER / "source" / "ReplayTakeover.cpp").read_bytes()
    if b"Replay Takeover 2.6" not in cpp or b"Online()" not in cpp:
        raise AssertionError("ReplayTakeover.cpp is not the 2.6 source")

    print("signing DOA5LR-ReplayTakeover.asi")
    signed = sign({"DOA5LR-ReplayTakeover.asi": asi})
    changed = {
        "DOA5LR-ReplayTakeover.asi": signed["DOA5LR-ReplayTakeover.asi"],
        "scripts/REPLAY-TAKEOVER-EN.txt": (TAKEOVER / "REPLAY-TAKEOVER-EN.txt").read_bytes(),
        "scripts/ReplayTakeover-Source/ReplayTakeover.cpp": cpp,
        "scripts/ReplayTakeover-Source/build.cmd": (TAKEOVER / "source" / "build.cmd").read_bytes(),
        **pack_guides(VERSION),
        "DOA5LR-Salons-VERSION.txt": (VERSION + "\r\n").encode("ascii"),
    }
    for n in changed:
        if n not in payload:
            raise AssertionError(f"{n} is missing from 0.3.11")
        if payload[n] == changed[n]:
            raise AssertionError(f"{n} did not change")
    payload.update(changed)
    for n, src in (("DOA5LR-ReplayTakeover.ini", TAKEOVER / "DOA5LR-ReplayTakeover.ini"),
                   ("scripts/ReplayTakeover-Source/Checkpoint.h", TAKEOVER / "source" / "Checkpoint.h")):
        if payload[n] != src.read_bytes():
            raise AssertionError(f"{n} in 0.3.11 differs from src (unexpected)")
    payload["SHA256SUMS.txt"] = "".join(f"{sha(payload[n])} *{n}\n" for n in sorted(payload) if n != "SHA256SUMS.txt").encode("ascii")
    for n, b in base.items():
        if n not in changed and n != "SHA256SUMS.txt" and payload[n] != b:
            raise AssertionError(f"{n} changed although it should be byte-identical to 0.3.11")
    if set(payload) != set(base):
        raise AssertionError("file list differs from 0.3.11")
    check_pack_guides(payload, VERSION)

    zip_path = args.out / f"DOA5LR-Salons-{VERSION}.zip"
    write_zip(zip_path, payload)
    zip_data = zip_path.read_bytes()
    (args.out / INSTALLER).write_bytes(installer)
    (args.out / "version.txt").write_text(manifest(base_manifest, zip_path.name, zip_data), encoding="utf-8", newline="\n")
    assets = [zip_path, args.out / INSTALLER]
    (args.out / "SHA256SUMS.txt").write_text("".join(f"{sha(p.read_bytes())} *{p.name}\n" for p in assets), encoding="ascii", newline="\n")
    report = {
        "version": VERSION, "from": BASE_ZIP, "from_sha256": BASE_ZIP_SHA256,
        "zip": zip_path.name, "zip_sha256": sha(zip_data), "zip_bytes": len(zip_data), "zip_entries": len(payload),
        "installer_sha256": sha(installer), "installer_unchanged": True,
        "takeover_unsigned_sha256": TAKEOVER_ASI_SHA256, "takeover_signed_sha256": sha(changed["DOA5LR-ReplayTakeover.asi"]),
        "changed": sorted(list(changed) + ["SHA256SUMS.txt"]),
    }
    (args.out / "build-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
