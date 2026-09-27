"""Build DOA5LR-Salons 0.3.11 = the PUBLISHED 0.3.10 pack (r2) + Replay Takeover 2.5 + installer 1.3.2.

Input : the published 0.3.10 r2 release folder (ZIP, installer and version.txt, SHA256 checked) and the Replay
        Takeover 2.5 files in src/ReplayTakeover (the .asi is the released binary, SHA256 pinned below).
Added : DOA5LR-ReplayTakeover.asi (signed) + DOA5LR-ReplayTakeover.ini next to game.exe (where the plugin reads its
        .ini and where its own installer puts it, so a copy installed by hand is replaced, never loaded twice),
        scripts/REPLAY-TAKEOVER-EN.txt, scripts/ReplayTakeover-Source/*.
Changed: installer 1.3.2 (Replay Takeover check box, manifest key optional_v3 that 1.3.1 ignores before its
        self-update), its source copy, the three guide copies (tools/pack_docs.py), VERSION and SHA256SUMS.
Every other 0.3.10 file stays byte-identical. Signing contacts the timestamp service. No publication, no game write.

  python tools/build_release_0311.py --base-dir <DOA5LR-Salons-0.3.10-r2-Release> --out <folder>
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import sys
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_release_039 import executable_bytes  # noqa: E402  (Authenticode-neutral comparison)
from pack_docs import check_pack_guides, pack_guides  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
VERSION = "0.3.11"
GITHUB = "FgcSnow/DOA5LR-Salons"
REL_BASE = f"https://github.com/{GITHUB}/releases/download/v{VERSION}"
BASE_ZIP = "DOA5LR-Salons-0.3.10.zip"
BASE_ZIP_SHA256 = "2a441cb3125962910106341ae75b5b3d34805406df1af1c168e744d0d39ab272"
BASE_INSTALLER_SHA256 = "c6e4e36c630bb5bfb0aab80e1571872e7e9d4eda483835ecbe8166d773ef4ee3"
INSTALLER = "DOA5LR-Salons-Installer.exe"
INSTALLER_VERSION = "1.3.2"
TAKEOVER = REPO / "src" / "ReplayTakeover"
TAKEOVER_ASI_SHA256 = "4fc96588962edfd4b7e778a77981701212287ae51a1fbb3149934c9232db6c3a"   # DOA5LR-ReplayTakeover-2.5.zip
OPTIONAL_V3 = (r"optional_v3=replaytakeover|Replay Takeover: take control of P1/P2 in a replay and rewind (replays only)|"
               r"DOA5LR-ReplayTakeover.asi;DOA5LR-ReplayTakeover.ini;scripts\REPLAY-TAKEOVER-EN.txt;scripts\ReplayTakeover-Source\*")
NOTES = [
    "notes=pack 0.3.11: Replay Takeover 2.5 (by BonuStage & FGCsnow) - take control of P1/P2 in any replay and rewind; installer check box, on by default",
    "note=0.3.11: Replay Takeover 2.5: while a replay plays, L2 (or F5) takes control of P1 or P2; Select jumps back instantly "
    "to that moment and keeps control, Start jumps back and gives control back, L3 (or F7) jumps back with the stage rebuilt. "
    "Broken walls, tables and benches come back. Guide: scripts\\REPLAY-TAKEOVER-EN.txt.",
    "note=0.3.11: installer 1.3.2 adds a Replay Takeover check box (on by default; untick it to leave the mod out, your .ini is kept). "
    "It installs next to game.exe like its own installer: a copy installed by hand is updated to 2.5 and its settings are kept. "
    "It writes a local DOA5LR-ReplayTakeover.log next to the game and sends nothing.",
    "note=0.3.11: every other file is byte-identical to 0.3.10.",
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sign(blobs: dict[str, bytes]) -> dict[str, bytes]:
    tool = REPO / "src" / "tools" / "sign.ps1"
    out = {}
    with tempfile.TemporaryDirectory(prefix="doa5lr-sign-") as tmp:
        paths = {}
        for i, name in enumerate(blobs):
            ext = ".exe" if name.endswith(".exe") else ".dll"     # an .asi is signed under a .dll name, stored back as .asi
            paths[name] = Path(tmp) / f"{i:02d}-{Path(name).stem}{ext}"
            paths[name].write_bytes(blobs[name])
        r = subprocess.run(["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(tool)] + [str(p) for p in paths.values()],
                           capture_output=True, text=True, errors="replace")
        print("  " + r.stdout.strip().replace("\n", "\n  "))
        if r.returncode != 0 or r.stdout.count("SIGNED") != len(paths):
            raise RuntimeError("signature failed:\n" + r.stdout + r.stderr)
        for name, p in paths.items():
            out[name] = p.read_bytes()
            if executable_bytes(out[name]) != executable_bytes(blobs[name]):
                raise AssertionError(f"signing changed executable content: {name}")
    return out


def write_zip(path: Path, payload: dict[str, bytes]) -> None:
    with ZipFile(path, "w", compression=ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted(payload):
            zi = ZipInfo(name, date_time=(2026, 9, 27, 0, 0, 0))
            zi.compress_type = ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, payload[name], compress_type=ZIP_DEFLATED, compresslevel=9)
    with ZipFile(path) as z:
        if z.testzip() is not None or {n: z.read(n) for n in z.namelist()} != payload:
            raise AssertionError(f"ZIP verification failed: {path.name}")


def manifest(base: str, zip_name: str, zip_data: bytes, installer: bytes) -> str:
    drop = ("version=", "url=", "sha256=", "size=", "notes=", "installer=", "installer_version=", "installer_sha256=", "optional_v3=")
    lines = [l for l in base.splitlines() if not l.startswith(drop)]
    # the older notes stay below the new ones (older installers show every note= line)
    lines[1:1] = [f"version={VERSION}", f"url={REL_BASE}/{zip_name}", f"sha256={sha(zip_data)}", f"size={len(zip_data)}"] + NOTES
    k = next(i for i, l in enumerate(lines) if l.startswith("keep="))
    lines[k:k] = [f"installer={REL_BASE}/{INSTALLER}", f"installer_version={INSTALLER_VERSION}", f"installer_sha256={sha(installer)}"]
    k = next(i for i, l in enumerate(lines) if l.startswith("optional_v2=")) + 1
    lines[k:k] = [OPTIONAL_V3]   # 1.3.1 ignores this key, so it still parses the manifest and offers 1.3.2 first
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    bz = (args.base_dir / BASE_ZIP).read_bytes()
    if sha(bz) != BASE_ZIP_SHA256:
        raise ValueError("base ZIP is not the published 0.3.10 (r2) archive")
    if sha((args.base_dir / INSTALLER).read_bytes()) != BASE_INSTALLER_SHA256:
        raise ValueError("base installer is not the published 1.3.1")
    base_manifest = (args.base_dir / "version.txt").read_text(encoding="utf-8-sig")
    if "version=0.3.10" not in base_manifest or f"sha256={BASE_ZIP_SHA256}" not in base_manifest:
        raise ValueError("base version.txt is not the published 0.3.10 manifest")
    args.out.mkdir(parents=True, exist_ok=True)
    tmp_zip = args.out / "_base.zip"
    tmp_zip.write_bytes(bz)
    with ZipFile(tmp_zip) as z:
        payload = {n: z.read(n) for n in z.namelist()}
    tmp_zip.unlink()
    base = dict(payload)

    asi = (TAKEOVER / "DOA5LR-ReplayTakeover.asi").read_bytes()
    if sha(asi) != TAKEOVER_ASI_SHA256:
        raise ValueError("src/ReplayTakeover/DOA5LR-ReplayTakeover.asi is not the released 2.5 binary")

    print("building installer from repository source")
    src = REPO / "src" / "Installer"
    subprocess.run(["cmd", "/c", str(src / "build.cmd")], cwd=src, check=True)
    installer_source = (src / "Installer.cs").read_bytes()
    if f'AppVersion = "{INSTALLER_VERSION}"'.encode() not in installer_source or OPTIONAL_V3.split("|", 1)[0].split("=")[1].encode() not in installer_source:
        raise AssertionError("installer source is not 1.3.2 with the Replay Takeover component")

    print("signing DOA5LR-ReplayTakeover.asi and the installer")
    signed = sign({"DOA5LR-ReplayTakeover.asi": asi, INSTALLER: (src / INSTALLER).read_bytes()})
    installer = signed[INSTALLER]

    added = {
        "DOA5LR-ReplayTakeover.asi": signed["DOA5LR-ReplayTakeover.asi"],
        "DOA5LR-ReplayTakeover.ini": (TAKEOVER / "DOA5LR-ReplayTakeover.ini").read_bytes(),
        "scripts/REPLAY-TAKEOVER-EN.txt": (TAKEOVER / "REPLAY-TAKEOVER-EN.txt").read_bytes(),
        "scripts/ReplayTakeover-Source/ReplayTakeover.cpp": (TAKEOVER / "source" / "ReplayTakeover.cpp").read_bytes(),
        "scripts/ReplayTakeover-Source/Checkpoint.h": (TAKEOVER / "source" / "Checkpoint.h").read_bytes(),
        "scripts/ReplayTakeover-Source/build.cmd": (TAKEOVER / "source" / "build.cmd").read_bytes(),
        "scripts/ReplayTakeover-Source/tests/test.cmd": (TAKEOVER / "source" / "tests" / "test.cmd").read_bytes(),
        "scripts/ReplayTakeover-Source/tests/TestEngine.cpp": (TAKEOVER / "source" / "tests" / "TestEngine.cpp").read_bytes(),
    }
    for n in added:
        if n in payload:
            raise AssertionError(f"{n} already exists in 0.3.10")
    payload.update(added)
    changed = {INSTALLER: installer, "scripts/Installer-Source/Installer.cs": installer_source, **pack_guides(VERSION),
               "DOA5LR-Salons-VERSION.txt": (VERSION + "\r\n").encode("ascii")}
    for n in changed:
        if n not in payload:
            raise AssertionError(f"{n} is missing from 0.3.10")
    payload.update(changed)
    payload.pop("SHA256SUMS.txt", None)
    payload["SHA256SUMS.txt"] = "".join(f"{sha(payload[n])} *{n}\n" for n in sorted(payload)).encode("ascii")
    for n, b in base.items():
        if n not in changed and n != "SHA256SUMS.txt" and payload[n] != b:
            raise AssertionError(f"{n} changed although it should be byte-identical to 0.3.10")
    check_pack_guides(payload, VERSION)

    zip_path = args.out / f"DOA5LR-Salons-{VERSION}.zip"
    write_zip(zip_path, payload)
    zip_data = zip_path.read_bytes()
    (args.out / INSTALLER).write_bytes(installer)
    (args.out / "version.txt").write_text(manifest(base_manifest, zip_path.name, zip_data, installer), encoding="utf-8", newline="\n")
    assets = [zip_path, args.out / INSTALLER]
    (args.out / "SHA256SUMS.txt").write_text("".join(f"{sha(p.read_bytes())} *{p.name}\n" for p in assets), encoding="ascii", newline="\n")
    report = {
        "version": VERSION, "from": BASE_ZIP, "from_sha256": BASE_ZIP_SHA256,
        "zip": zip_path.name, "zip_sha256": sha(zip_data), "zip_bytes": len(zip_data), "zip_entries": len(payload),
        "installer_version": INSTALLER_VERSION, "installer_sha256": sha(installer),
        "takeover_unsigned_sha256": TAKEOVER_ASI_SHA256, "takeover_signed_sha256": sha(added["DOA5LR-ReplayTakeover.asi"]),
        "added": sorted(added), "changed": sorted(list(changed) + ["SHA256SUMS.txt"]),
    }
    (args.out / "build-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
