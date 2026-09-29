"""Build DOA5LR-Salons 0.3.13 = the PUBLISHED 0.3.12 pack + the Danger Zone / The Crimson 1-2 stages + DOA5LR-Diagnostic.

Input : the published 0.3.12 release folder (ZIP, installer and version.txt, SHA256 checked), the stage files of the
        tested pre-release (dz-crimson-test-r5, folder Runtime; every file pinned in src/Maps/maps-files.json) and
        src/Diagnostic (log tool; its webhook file envoi-logs.txt is local only, never committed).
Added  : 69 stage files (unchanged tested binaries, not re-signed), scripts/MAPS-DZ-CRIMSON-EN.txt, DOA5LR-Diagnostic/*
        (probe exe signed).
Changed: installer 1.3.3 (Maps check box, manifest key optional_v4 that 1.3.2 ignores before its self-update; JoinFix and
        the main maps modules added to the missing-file check), its source copy, the three guide copies, VERSION, SHA256SUMS.
Every other 0.3.12 file stays byte-identical. Signing contacts the timestamp service. No publication, no game write.

  python tools/build_release_0313.py --base-dir <DOA5LR-Salons-0.3.12-Release> --maps-dir <r5 Runtime> --out <folder>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_release_0311 import sha, sign, write_zip  # noqa: E402
from pack_docs import check_pack_guides, pack_guides  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
VERSION = "0.3.13"
GITHUB = "FgcSnow/DOA5LR-Salons"
REL_BASE = f"https://github.com/{GITHUB}/releases/download/v{VERSION}"
BASE_ZIP = "DOA5LR-Salons-0.3.12.zip"
BASE_ZIP_SHA256 = "b41efba380e26c22eeaff03a8177db3c4452799fc9edfa97fb9c4eb433bb9be8"
BASE_INSTALLER_SHA256 = "eacd9d62da22997a7082b5f19e3a7217d9b9b577c3e2bbe2781ca4639643dfd6"
INSTALLER = "DOA5LR-Salons-Installer.exe"
INSTALLER_VERSION = "1.3.3"
MAPS_LIST = REPO / "src" / "Maps" / "maps-files.json"
DIAG = REPO / "src" / "Diagnostic"
PROBE_SHA256 = "5d6ff581d2ce164a63e93a9ca19e188415b8bb810c48afeb200423b0ea661cd9"   # observer 1.0 / collector 1.1 of the pre-release (unsigned)
MAPS_GLOBS = ("DOA5LR-Crimson.asi;DOA5LR-Crimson-Audio.asi;DOA5LR-Crimson-Audio.ini;DOA5LR-Crimson-BackendProbe.asi;"
              "DOA5LR-Crimson-EventLog.asi;DOA5LR-Crimson-VFX.asi;DOA5LR-Crimson-VFX.ini;DOA5LR-DangerZone.asi;DOA5LR-DangerZone.ini;"
              "DOA5LR-DebugArchive.asi;DOA5LR-DNZ-Complete.asi;DOA5LR-DNZ-Complete.ini;DOA5LR-DNZ-Name.asi;DOA5LR-DNZ-Preview.asi;"
              "DOA5LR-DNZ-SharedAudio.asi;DOA5LR-DNZ-SharedAudio.ini;DOA5LR-DNZ-Thumbnail.asi;DOA5LR-ExtraStages.asi;"
              "DOA5LR-ExtraStages.ini;DOA5LR-RandomStages.asi;DOA5LR-RandomStages.ini;CodexCrimson\\*;CodexDangerZone\\*;"
              "PS4Stages\\*;scripts\\MAPS-DZ-CRIMSON-EN.txt")
MAPS_LABEL = "Maps: Danger Zone + The Crimson 1 and 2 (PS4 stages, Random included; everyone in a room needs them)"
OPTIONAL_V4 = f"optional_v4=maps|{MAPS_LABEL}|{MAPS_GLOBS}"
NOTES = [
    "notes=pack 0.3.13: new stages Danger Zone + The Crimson 1 & 2 (PS4), offline and online, Random included - "
    "installer check box on by default; everyone in a room needs them",
    "note=0.3.13: Danger Zone, The Crimson 1 and The Crimson 2 (PS4 versions): pick them by hand with proper thumbnails or tick "
    "them in the game's Random filter (three new check boxes). Offline and online; the original stages stay.",
    "note=0.3.13: ONLINE, EVERYONE IN THE ROOM (players and spectators) NEEDS THE MAPS: update before joining rooms that use them. "
    "Installer 1.3.3 adds a Maps check box, on by default (untick it to leave them out; your .ini settings are kept).",
    "note=0.3.13: AutoLink costumes work with the maps, but only put character folders inside AutoLink (+ _Movie, _Texture, "
    "_Sound, _Stages): modding tools stored in AutoLink\\_Modding made a tester crash after the first fight.",
    "note=0.3.13: new DOA5LR-Diagnostic tool (DOA5LR-Diagnostic\\DOA5LR Diagnostic.cmd): checks maps, lobby modules and AutoLink, "
    "plays with a read-only probe, and 'Send my logs' sends a ZIP to FGCsnow's Discord ONLY after you confirm (no IP, SteamID, "
    "chat or inputs). The maps modules write local logs next to the game for crash reports.",
    "note=0.3.13: the installer now also checks JoinFix and the main maps modules; if an antivirus removed one, it offers the "
    "repair when you close the game. The download is bigger (about 270 MB) because it contains the stages.",
    "note=0.3.13: pre-release testers (dz-crimson-test-r4/r5): do not use its 'Remove the maps' button any more, untick Maps in "
    "the installer instead. Every other file is byte-identical to 0.3.12.",
]


def manifest(base: str, zip_name: str, zip_data: bytes, installer: bytes) -> str:
    drop = ("version=", "url=", "sha256=", "size=", "notes=", "installer=", "installer_version=", "installer_sha256=", "optional_v4=")
    lines = [l for l in base.splitlines() if not l.startswith(drop)]
    lines[1:1] = [f"version={VERSION}", f"url={REL_BASE}/{zip_name}", f"sha256={sha(zip_data)}", f"size={len(zip_data)}"] + NOTES
    k = next(i for i, l in enumerate(lines) if l.startswith("keep="))
    lines[k:k] = [f"installer={REL_BASE}/{INSTALLER}", f"installer_version={INSTALLER_VERSION}", f"installer_sha256={sha(installer)}"]
    k = next(i for i, l in enumerate(lines) if l.startswith("optional_v3=")) + 1
    lines[k:k] = [OPTIONAL_V4]   # 1.3.2 ignores this key, parses the rest and offers 1.3.3 first
    if "delete=DOA5LR-DNZ-Menu.asi" not in lines:
        k = next(i for i, l in enumerate(lines) if l.startswith("delete="))
        lines[k:k] = ["delete=DOA5LR-DNZ-Menu.asi"]   # old stage-menu test module, incompatible with the maps
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-dir", type=Path, required=True)
    ap.add_argument("--maps-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    bz = (args.base_dir / BASE_ZIP).read_bytes()
    if sha(bz) != BASE_ZIP_SHA256:
        raise ValueError("base ZIP is not the published 0.3.12 archive")
    if sha((args.base_dir / INSTALLER).read_bytes()) != BASE_INSTALLER_SHA256:
        raise ValueError("base installer is not the published 1.3.2")
    base_manifest = (args.base_dir / "version.txt").read_text(encoding="utf-8-sig")
    if "version=0.3.12" not in base_manifest or f"sha256={BASE_ZIP_SHA256}" not in base_manifest:
        raise ValueError("base version.txt is not the published 0.3.12 manifest")
    args.out.mkdir(parents=True, exist_ok=True)
    tmp_zip = args.out / "_base.zip"
    tmp_zip.write_bytes(bz)
    with ZipFile(tmp_zip) as z:
        payload = {n: z.read(n) for n in z.namelist()}
    tmp_zip.unlink()
    base = dict(payload)

    # stage files: exactly the tested pre-release binaries
    maps = json.loads(MAPS_LIST.read_text(encoding="utf-8-sig"))
    added: dict[str, bytes] = {}
    for e in maps:
        data = (args.maps_dir / e["path"]).read_bytes()
        if sha(data) != e["sha256"] or len(data) != int(e["size"]):
            raise ValueError(f"stage file differs from the tested pre-release: {e['path']}")
        added[e["path"]] = data
    if len(added) != 69:
        raise AssertionError("69 stage files expected")
    added["scripts/MAPS-DZ-CRIMSON-EN.txt"] = (REPO / "src" / "Maps" / "MAPS-DZ-CRIMSON-EN.txt").read_bytes()
    globs = [g.replace("\\", "/") for g in MAPS_GLOBS.split(";")]
    import fnmatch
    for n in added:
        if not any(fnmatch.fnmatchcase(n.lower(), g.lower()) for g in globs):
            raise AssertionError(f"{n} is not covered by the Maps component globs (it would stay when the box is unticked)")

    # diagnostic tool
    hook = (DIAG / "envoi-logs.txt").read_bytes()
    if b"discord.com/api/webhooks/" not in hook:
        raise ValueError("src/Diagnostic/envoi-logs.txt has no webhook")
    probe = (DIAG / "Sonde" / "DOA5LR-TestEnLigne.exe").read_bytes()
    if sha(probe) != PROBE_SHA256:
        raise ValueError("src/Diagnostic/Sonde/DOA5LR-TestEnLigne.exe is not the tested probe")
    print("building installer from repository source")
    src = REPO / "src" / "Installer"
    subprocess.run(["cmd", "/c", str(src / "build.cmd")], cwd=src, check=True)
    installer_source = (src / "Installer.cs").read_bytes()
    if f'AppVersion = "{INSTALLER_VERSION}"'.encode() not in installer_source or b'case "optional_v4"' not in installer_source \
            or MAPS_LABEL.encode() not in installer_source:
        raise AssertionError("installer source is not 1.3.3 with the Maps component")
    for g in MAPS_GLOBS.split(";"):
        if ('@"' + g + '"').encode() not in installer_source:
            raise AssertionError(f"installer Maps globs differ from the manifest: {g}")

    print("signing the installer and the probe")
    signed = sign({INSTALLER: (src / INSTALLER).read_bytes(), "DOA5LR-TestEnLigne.exe": probe})
    installer = signed[INSTALLER]
    diag = {
        "DOA5LR-Diagnostic/DOA5LR Diagnostic.cmd": (DIAG / "DOA5LR Diagnostic.cmd").read_bytes(),
        "DOA5LR-Diagnostic/DOA5LR-Diagnostic.ps1": (DIAG / "DOA5LR-Diagnostic.ps1").read_bytes(),
        "DOA5LR-Diagnostic/maps-files.json": (DIAG / "maps-files.json").read_bytes(),
        "DOA5LR-Diagnostic/salons-modules.json": (DIAG / "salons-modules.json").read_bytes(),
        "DOA5LR-Diagnostic/envoi-logs.txt": hook,
        "DOA5LR-Diagnostic/Sonde/DOA5LR-TestEnLigne.exe": signed["DOA5LR-TestEnLigne.exe"],
        "DOA5LR-Diagnostic/Sonde/CrashEventParser.ps1": (DIAG / "Sonde" / "CrashEventParser.ps1").read_bytes(),
        "DOA5LR-Diagnostic/Sonde/Exporter-plantage-Windows.ps1": (DIAG / "Sonde" / "Exporter-plantage-Windows.ps1").read_bytes(),
        "DOA5LR-Diagnostic/Sonde/VERSION.json": (DIAG / "Sonde" / "VERSION.json").read_bytes(),
        "DOA5LR-Diagnostic/Sonde-Source/OnlineTestObserver.cpp": (DIAG / "Sonde-Source" / "OnlineTestObserver.cpp").read_bytes(),
    }
    if (DIAG / "maps-files.json").read_bytes() != MAPS_LIST.read_bytes():
        raise AssertionError("src/Diagnostic/maps-files.json differs from src/Maps/maps-files.json")
    salons = json.loads((DIAG / "salons-modules.json").read_text(encoding="utf-8-sig"))
    for e in salons:
        if sha(payload[e["path"]]) != e["sha256"]:
            raise AssertionError(f"salons-modules.json does not match the 0.3.12 file {e['path']}")
    added.update(diag)
    for n in added:
        if n in payload:
            raise AssertionError(f"{n} already exists in 0.3.12")
    payload.update(added)
    changed = {INSTALLER: installer, "scripts/Installer-Source/Installer.cs": installer_source, **pack_guides(VERSION),
               "DOA5LR-Salons-VERSION.txt": (VERSION + "\r\n").encode("ascii")}
    for n in changed:
        if n not in payload:
            raise AssertionError(f"{n} is missing from 0.3.12")
        if payload[n] == changed[n]:
            raise AssertionError(f"{n} did not change")
    payload.update(changed)
    payload.pop("SHA256SUMS.txt", None)
    payload["SHA256SUMS.txt"] = "".join(f"{sha(payload[n])} *{n}\n" for n in sorted(payload)).encode("ascii")
    for n, b in base.items():
        if n not in changed and n != "SHA256SUMS.txt" and payload[n] != b:
            raise AssertionError(f"{n} changed although it should be byte-identical to 0.3.12")
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
        "added": len(added), "changed": sorted(list(changed) + ["SHA256SUMS.txt"]),
    }
    (args.out / "build-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
