"""Build DOA5LR-Salons 0.3.10 = the PUBLISHED 0.3.9 pack + DOA5LR-JoinFix 0.2 (room join fix).

Input : the published 0.3.9 release folder (ZIP, installer and version.txt, SHA256 checked). Every 0.3.9
        file stays byte-identical except DOA5LR-Salons-VERSION.txt and SHA256SUMS.txt.
Added : scripts/DOA5LR-JoinFix.asi (release build -DNO_LOG, signed with src/tools/sign.ps1),
        scripts/DOA5LR-JoinFix.ini, scripts/JOINFIX-EN.txt, scripts/JoinFix-Source/*.
Installer 1.3.1 is unchanged (same signed bytes); the manifest points to the v0.3.10 release assets.
Signing contacts the timestamp service. No publication or game-folder write. Output: --out folder.

  python tools/build_release_0310.py --base-dir <DOA5LR-Salons-0.3.9-Release> --out <folder>
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
from build_release_039 import executable_bytes  # noqa: E402  (same Authenticode-neutral comparison as 0.3.9)

REPO = Path(__file__).resolve().parents[1]
VERSION = "0.3.10"
BASE_VERSION = "0.3.9"
GITHUB = "FgcSnow/DOA5LR-Salons"
REL_BASE = f"https://github.com/{GITHUB}/releases/download/v{VERSION}"
BASE_ZIP = "DOA5LR-Salons-0.3.9.zip"
BASE_ZIP_SHA256 = "d8d9ca313709c15063fc635b2716e5f292d40f5f5a34219c9f8a891fe1610f3b"
INSTALLER = "DOA5LR-Salons-Installer.exe"
INSTALLER_SHA256 = "c6e4e36c630bb5bfb0aab80e1571872e7e9d4eda483835ecbe8166d773ef4ee3"
INSTALLER_VERSION = "1.3.1"
JOINFIX = REPO / "src" / "JoinFix"
NOTES = [
    "notes=pack 0.3.10: fixes rooms that nobody can join (players enter, then leave after 30 s) - new DOA5LR-JoinFix",
    "note=0.3.10: the game publishes each room's network encryption key as text; when a random byte is 0, Steam cuts it and "
    "nobody can join that room (about 1 room in 11, and it stays broken for everyone until it is created again). "
    "DOA5LR-JoinFix repairs the key before your room is published. It works on the HOST side: everyone who creates rooms needs 0.3.10.",
    "note=0.3.10: JoinFix also always accepts the network link of players in your room and asks Steam again for the room data "
    "after an invite if it is missing. Settings in scripts\\DOA5LR-JoinFix.ini; no log file, nothing is sent anywhere.",
    "note=0.3.10: in a room, press F7 to copy its steam://joinlobby link to the clipboard (private rooms have no Join game "
    "button in Steam); paste it on Discord, a click joins your room while the game is running.",
    "note=0.3.10: every other file is byte-identical to 0.3.9 (installer 1.3.1 unchanged).",
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sign_dll(blob: bytes) -> bytes:
    tool = REPO / "src" / "tools" / "sign.ps1"
    with tempfile.TemporaryDirectory(prefix="doa5lr-sign-") as tmp:
        p = Path(tmp) / "DOA5LR-JoinFix.dll"     # signed under a .dll name, stored back as .asi
        p.write_bytes(blob)
        r = subprocess.run(["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(tool), str(p)],
                           capture_output=True, text=True, errors="replace")
        print("  " + r.stdout.strip().replace("\n", "\n  "))
        if r.returncode != 0 or "SIGNED" not in r.stdout:
            raise RuntimeError("signature failed:\n" + r.stdout + r.stderr)
        signed = p.read_bytes()
    if executable_bytes(signed) != executable_bytes(blob):
        raise AssertionError("signing changed executable content")
    return signed


def write_zip(path: Path, payload: dict[str, bytes]) -> None:
    with ZipFile(path, "w", compression=ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted(payload):
            zi = ZipInfo(name, date_time=(2026, 9, 25, 0, 0, 0))
            zi.compress_type = ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, payload[name], compress_type=ZIP_DEFLATED, compresslevel=9)
    with ZipFile(path) as z:
        if z.testzip() is not None or {n: z.read(n) for n in z.namelist()} != payload:
            raise AssertionError(f"ZIP verification failed: {path.name}")


def manifest(base: str, zip_name: str, zip_data: bytes) -> str:
    drop = ("version=", "url=", "sha256=", "size=", "notes=", "installer=")
    lines = [l for l in base.splitlines() if not l.startswith(drop)]
    # the 0.3.9 notes stay below the new ones (older installers show every note= line)
    head = [f"version={VERSION}", f"url={REL_BASE}/{zip_name}", f"sha256={sha(zip_data)}", f"size={len(zip_data)}"] + NOTES
    lines[1:1] = head
    k = next(i for i, l in enumerate(lines) if l.startswith("installer_version="))
    lines[k:k] = [f"installer={REL_BASE}/{INSTALLER}"]
    text = "\n".join(lines) + "\n"
    if f"installer_version={INSTALLER_VERSION}" not in text or f"installer_sha256={INSTALLER_SHA256}" not in text:
        raise AssertionError("installer lines of the 0.3.9 manifest changed")
    return text


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    bz = (args.base_dir / BASE_ZIP).read_bytes()
    if sha(bz) != BASE_ZIP_SHA256:
        raise ValueError("base ZIP is not the published 0.3.9 archive")
    installer = (args.base_dir / INSTALLER).read_bytes()
    if sha(installer) != INSTALLER_SHA256:
        raise ValueError("installer is not the published 1.3.1")
    base_manifest = (args.base_dir / "version.txt").read_text(encoding="utf-8-sig")
    if "version=0.3.9" not in base_manifest:
        raise ValueError("base version.txt is not the 0.3.9 manifest")
    tmp_zip = args.out / "_base.zip"
    args.out.mkdir(parents=True, exist_ok=True)
    tmp_zip.write_bytes(bz)
    with ZipFile(tmp_zip) as z:
        payload = {n: z.read(n) for n in z.namelist()}
    tmp_zip.unlink()
    base = dict(payload)

    print("building DOA5LR-JoinFix from repository source")
    subprocess.run(["cmd", "/c", str(JOINFIX / "build.cmd")], cwd=JOINFIX, check=True)
    release = (JOINFIX / "DOA5LR-JoinFix.asi").read_bytes()
    for bad in (b"DOA5LR-JoinFix.log", b"KeyTest"):
        if bad in release:
            raise AssertionError(f"release JoinFix contains debug-only code: {bad!r}")
    print("signing DOA5LR-JoinFix.asi")
    signed = sign_dll(release)

    added = {
        "scripts/DOA5LR-JoinFix.asi": signed,
        "scripts/DOA5LR-JoinFix.ini": (JOINFIX / "DOA5LR-JoinFix.ini").read_bytes(),
        "scripts/JOINFIX-EN.txt": (JOINFIX / "JOINFIX-EN.txt").read_bytes(),
        "scripts/JoinFix-Source/joinfix.c": (JOINFIX / "joinfix.c").read_bytes(),
        "scripts/JoinFix-Source/build.cmd": (JOINFIX / "build.cmd").read_bytes(),
        "scripts/JoinFix-Source/version.rc": (JOINFIX / "version.rc").read_bytes(),
    }
    for n in added:
        if n in payload:
            raise AssertionError(f"{n} already exists in 0.3.9")
    payload.update(added)
    payload["DOA5LR-Salons-VERSION.txt"] = (VERSION + "\r\n").encode("ascii")
    payload.pop("SHA256SUMS.txt", None)
    payload["SHA256SUMS.txt"] = "".join(f"{sha(payload[n])} *{n}\n" for n in sorted(payload)).encode("ascii")
    for n, b in base.items():
        if n not in ("DOA5LR-Salons-VERSION.txt", "SHA256SUMS.txt") and payload[n] != b:
            raise AssertionError(f"{n} changed although it should be byte-identical to 0.3.9")
    if payload[INSTALLER] != installer:
        raise AssertionError("installer inside the ZIP differs from the downloadable one")

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
        "installer_version": INSTALLER_VERSION, "installer_sha256": INSTALLER_SHA256,
        "joinfix_unsigned_sha256": sha(release), "joinfix_signed_sha256": sha(signed),
        "added": sorted(added), "changed": ["DOA5LR-Salons-VERSION.txt", "SHA256SUMS.txt"],
    }
    (args.out / "build-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
