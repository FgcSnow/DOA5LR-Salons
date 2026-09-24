"""Build the PUBLIC DOA5LR-Salons 0.3.9 release from the tested 0.3.9 preview.

Input : the preview ZIP (v0.3.9-preview.1, SHA256 checked) -> its binaries are the exact tested bytes.
Changes: version 0.3.9, final documentation, new PE files signed (self-signed cert, src/tools/sign.ps1),
         installer rebuilt from repository source and shipped separately and inside the ZIP,
         manifest with the official GitHub release URLs + installer= lines.
Signing contacts the timestamp service. No publication or game-folder write. Output: --out folder.

  python tools/build_release_039.py --preview-dir <DOA5LR-Salons-0.3.9-Preview> --out <folder>
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

REPO = Path(__file__).resolve().parents[1]
VERSION = "0.3.9"
INSTALLER_VERSION = "1.3.1"
GITHUB = "FgcSnow/DOA5LR-Salons"
REL_BASE = f"https://github.com/{GITHUB}/releases/download/v{VERSION}"
PREVIEW_ZIP = "DOA5LR-Salons-0.3.9-inputlab-draft.zip"
PREVIEW_SHA256 = "3fc4f9fc3348a3954080d24a3999d3e0532c8558ed90da858438449e72afd3f2"
PREVIEW_MANIFEST = "version-0.3.9-inputlab-draft.txt"
XIDI_SHA256 = "7f2a1c7616515153d899b726c8ecf72d5fa81c27a9d14b5c394cdd2e09f325c5"
INSTALLER_IN_ZIP = "DOA5LR-Salons-Installer.exe"
# new binaries of 0.3.9 that were unsigned in the preview (0.3.8 components and UpdateCheck 1.1 are already signed)
TO_SIGN = {
    "DOA5LR-Companion.exe": ".exe",
    "InputLab/DOA5LR-Companion.exe": ".exe",
    "InputLab/DOA5LR-Commandes.exe": ".exe",
    "InputLab/DOA5LR-Detecteur.exe": ".exe",
    "InputLab/DOA5LR-Peripheriques.exe": ".exe",
    "InputLab/payload/dinput8ex.bin": ".dll",      # InputLab bridge (a DLL); signed under a .dll name, stored back as .bin
    INSTALLER_IN_ZIP: ".exe",
}
GUIDE = REPO / "docs" / "INPUT-SETTINGS.md"
CHANGES = REPO / "docs" / "RELEASE-NOTES-0.3.9.md"
NOTES = [
    "notes=pack 0.3.9: Keyboard / controller settings app (keyboard remapping, Controller Finder), launch from the installer through Steam, in-game update banner (UpdateCheck 1.1), diagnostics export",
    "note=0.3.9: new Keyboard / controller app, always installed: remap keyboard keys, choose Keyboard or Controller before launch, search connected controllers by name or VID/PID. In-game keyboard remapping is an optional component, OFF by default; new installs use the usual Controller path and your existing choices are kept.",
    "note=0.3.9: the installer (1.3.1) can launch the game through Steam (it opens Steam first if needed) and create a DOA5LR (Lobby Mods) desktop shortcut that opens the configuration first. Idea by Inyo, thanks!",
    "note=0.3.9: UpdateCheck 1.1 shows an 8-second banner in game when a newer pack exists (borderless/window mode only; Banner=0 in scripts\\DOA5LR-UpdateCheck.ini turns it off). The installer still opens only after you close the game, and installing stays your choice.",
    "note=0.3.9: Logs > Export diagnostics ZIP gathers the existing local logs and a small report for you to review and share manually. Nothing is uploaded.",
    "note=Known limits: only DualSense Edge was tested on real hardware; detection is not automatic support. For keyboard play, disconnect controllers before starting the game (a pad connected at startup can block the keyboard). No PS5 controller emulation.",
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_pe(blob: bytes) -> bool:
    return blob[:2] == b"MZ"


def release_doc(path: Path) -> bytes:
    """Bundled docs live outside repo/docs, so use permanent release-tag links."""
    text = path.read_text(encoding="utf-8-sig")
    def replace(match):
        target = match.group(1)
        if ":" in target or target.startswith("#"):
            return match.group(0)
        dest = (path.parent / target.split("#", 1)[0]).resolve()
        if not dest.is_file():
            raise AssertionError(f"missing documentation link in {path.name}: {target}")
        rel = dest.relative_to(REPO).as_posix()
        anchor = "#" + target.split("#", 1)[1] if "#" in target else ""
        return f"](https://github.com/{GITHUB}/blob/v{VERSION}/{rel}{anchor})"
    return re.sub(r"\]\(([^)]+)\)", replace, text).encode("utf-8")


def executable_bytes(blob: bytes) -> bytes:
    """Remove only Authenticode fields/data so signing cannot hide a code change."""
    pe = struct.unpack_from("<I", blob, 0x3C)[0]
    optional = pe + 24
    magic = struct.unpack_from("<H", blob, optional)[0]
    security = optional + (128 if magic == 0x10B else 144)
    cert_offset, cert_size = struct.unpack_from("<II", blob, security)
    if cert_size and cert_offset + cert_size != len(blob):
        raise AssertionError("certificate table is not at the end of the PE")
    data = bytearray(blob[:cert_offset] if cert_size else blob)
    data[optional + 64:optional + 68] = b"\0" * 4
    data[security:security + 8] = b"\0" * 8
    # Signing pads the unsigned file to an 8-byte certificate-table boundary.
    return bytes(data) + b"\0" * (-len(data) % 8)


def sign(blobs: dict[str, bytes]) -> dict[str, bytes]:
    """Sign copies with src/tools/sign.ps1 (same cert as every pack binary). Returns the signed bytes."""
    tool = REPO / "src" / "tools" / "sign.ps1"
    if not tool.is_file():
        raise FileNotFoundError(tool)
    out = {}
    with tempfile.TemporaryDirectory(prefix="doa5lr-sign-") as tmp:
        paths = {}
        unique = {}
        for i, (name, blob) in enumerate(blobs.items()):
            digest = sha(blob)
            if digest in unique:
                paths[name] = unique[digest]
                continue
            p = Path(tmp) / f"{i:02d}-{Path(name).stem}{TO_SIGN[name]}"
            p.write_bytes(blob); paths[name] = p; unique[digest] = p
        r = subprocess.run(["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(tool)] + [str(p) for p in unique.values()],
                           capture_output=True, text=True, errors="replace")
        print("  " + r.stdout.strip().replace("\n", "\n  "))
        if r.returncode != 0 or r.stdout.count("SIGNED") != len(unique):
            raise RuntimeError("signature failed:\n" + r.stdout + r.stderr)
        for name, p in paths.items():
            out[name] = p.read_bytes()
            if executable_bytes(out[name]) != executable_bytes(blobs[name]):
                raise AssertionError(f"signing changed executable content: {name}")
    return out


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


def readme_test(old: bytes) -> bytes:
    t = old.decode("utf-8-sig")
    t = t.replace("DOA5LR InputLab — LOCAL TEST DRAFT", "DOA5LR InputLab — Keyboard / controller app (pack 0.3.9)")
    t = t.replace("verified DOA5LR-Salons 0.3.8 pack already installed", "verified DOA5LR-Salons 0.3.8 or 0.3.9 pack already installed")
    t = t.replace("This is an unpublished local draft.\r\nIts new executables and DLLs are unsigned.\r\n",
                  "Its executables and DLLs are signed with the self-signed DOA5LR-Salons certificate\r\n"
                  "(not a publicly trusted publisher certificate or a security guarantee).\r\n")
    for bad in ("DRAFT", "unpublished", "unsigned"):
        if bad in t:
            raise AssertionError(f"README-TEST-EN.txt still says {bad!r}")
    return ("﻿" + t).encode("utf-8")


def manifest(preview: str, zip_name: str, zip_data: bytes, installer: bytes) -> str:
    drop = ("version=", "url=", "sha256=", "size=", "notes=", "installer=", "installer_version=", "installer_sha256=")
    keep_notes = ("note=0.3.8:", "note=Source/signature scope:", "note=Support the project:")
    lines = [l for l in preview.splitlines()
             if not l.startswith(drop) and (not l.startswith("note=") or l.startswith(keep_notes))]
    # Older installers strictly reject unknown optional IDs before self-update.
    # They ignore this new key and can offer the 1.3.1 installer first.
    lines = [l.replace("optional=inputlab|", "optional_v2=inputlab|", 1)
             if l.startswith("optional=inputlab|") else l for l in lines]
    head = [f"version={VERSION}", f"url={REL_BASE}/{zip_name}", f"sha256={sha(zip_data)}", f"size={len(zip_data)}"] + NOTES
    lines[1:1] = head
    k = lines.index("keep=*.ini")
    lines[k:k] = [f"installer={REL_BASE}/DOA5LR-Salons-Installer.exe", f"installer_version={INSTALLER_VERSION}", f"installer_sha256={sha(installer)}"]
    text = "\n".join(lines) + "\n"
    for bad in ("draft", "candidate", "preview"):
        if bad in text.lower():
            raise AssertionError(f"manifest still mentions {bad!r}")
    return text


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--preview-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    pz = args.preview_dir / PREVIEW_ZIP
    if sha(pz.read_bytes()) != PREVIEW_SHA256:
        raise ValueError("preview ZIP is not the tested v0.3.9-preview.1 archive")
    with ZipFile(pz) as z:
        payload = {n: z.read(n) for n in z.namelist()}
    tested = {n: sha(b) for n, b in payload.items() if is_pe(b)}

    print("building installer from repository source")
    source = REPO / "src" / "Installer"
    subprocess.run(["cmd", "/c", "build.cmd"], cwd=source, check=True)
    installer_source = (source / "Installer.cs").read_bytes()
    if f'"{INSTALLER_VERSION}"'.encode() not in installer_source:
        raise AssertionError("installer source version differs from release metadata")
    payload[INSTALLER_IN_ZIP] = (source / INSTALLER_IN_ZIP).read_bytes()
    payload["scripts/Installer-Source/Installer.cs"] = installer_source
    unsigned_installer_sha = sha(payload[INSTALLER_IN_ZIP])

    print("signing the new 0.3.9 binaries")
    signed = sign({n: payload[n] for n in TO_SIGN})
    installer = signed[INSTALLER_IN_ZIP]
    payload.update(signed)
    payload.pop("SHA256SUMS.txt", None)

    guide = release_doc(GUIDE)
    for n in ("READ-ME-FIRST-EN.txt", "START-HERE.md", "InputLab/START-HERE-EN.md"):
        payload[n] = guide
    payload["InputLab/CHANGELOG-EN.md"] = release_doc(CHANGES)
    payload["InputLab/README-TEST-EN.txt"] = readme_test(payload["InputLab/README-TEST-EN.txt"])
    payload["DOA5LR-Salons-VERSION.txt"] = (VERSION + "\r\n").encode("ascii")
    for n, b in payload.items():
        if n.lower().endswith((".txt", ".md")) and any(w in b.lower() for w in (b"inputlab-draft", b"local test build", b"unpublished")):
            raise AssertionError(f"draft wording left in {n}")
    if sha(payload["dinput8ex.bin"]) != XIDI_SHA256 or sha(payload["DOA5LR-InputBridge-Xidi.dll"]) != XIDI_SHA256:
        raise AssertionError("mandatory original Xidi changed")
    payload["SHA256SUMS.txt"] = "".join(f"{sha(payload[n])} *{n}\n" for n in sorted(payload)).encode("ascii")

    args.out.mkdir(parents=True, exist_ok=True)
    zip_path = args.out / f"DOA5LR-Salons-{VERSION}.zip"
    write_zip(zip_path, payload)
    zip_data = zip_path.read_bytes()
    (args.out / "DOA5LR-Salons-Installer.exe").write_bytes(installer)

    portable = {n: b for n, b in payload.items() if n.startswith("InputLab/")}
    portable["SHA256SUMS.txt"] = "".join(f"{sha(portable[n])} *{n}\n" for n in sorted(portable)).encode("ascii")
    port_path = args.out / f"DOA5LR-Commandes-portable-{VERSION}.zip"
    write_zip(port_path, portable)

    preview_manifest = (args.preview_dir / PREVIEW_MANIFEST).read_text(encoding="utf-8-sig")
    (args.out / "version.txt").write_text(manifest(preview_manifest, zip_path.name, zip_data, installer), encoding="utf-8", newline="\n")
    (args.out / "START-HERE.md").write_bytes(guide)
    assets = [zip_path, args.out / "DOA5LR-Salons-Installer.exe", port_path]
    (args.out / "SHA256SUMS.txt").write_text("".join(f"{sha(p.read_bytes())} *{p.name}\n" for p in assets), encoding="ascii", newline="\n")

    # Runtime executable content is unchanged; the installer alone is rebuilt
    # with the manifest compatibility fix. Signing content equality is enforced.
    report = {
        "version": VERSION, "installer_version": INSTALLER_VERSION, "from_preview": PREVIEW_ZIP, "preview_sha256": PREVIEW_SHA256,
        "zip": zip_path.name, "zip_sha256": sha(zip_data), "zip_bytes": len(zip_data), "zip_entries": len(payload),
        "installer_sha256": sha(installer), "portable": port_path.name, "portable_sha256": sha(port_path.read_bytes()),
        "signed": {n: {"unsigned": unsigned_installer_sha if n == INSTALLER_IN_ZIP else tested[n], "signed": sha(payload[n])} for n in TO_SIGN},
        "installer_source_sha256": sha(installer_source),
        "unchanged_binaries": sorted(n for n in tested if n not in TO_SIGN),
    }
    for n in report["unchanged_binaries"]:
        if sha(payload[n]) != tested[n]:
            raise AssertionError(f"{n} changed although it should be byte-identical to the preview")
    (args.out / "build-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("signed", "unchanged_binaries")}, indent=2))


if __name__ == "__main__":
    main()
