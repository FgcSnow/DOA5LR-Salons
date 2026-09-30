"""Build DOA5LR-Salons 0.3.14 = the PUBLISHED 0.3.13 pack + the fixes from the 0.3.13 reports.

Input  : the published 0.3.13 release folder (ZIP, installer and version.txt, SHA256 checked).
Changed: installer 1.3.4 (ResolutionMod follows Borderless, delete_if=, PLAY / Set controls) and its source copy,
         DOA5LR-RandomStages.asi 2.1 + .ini (new stages in offline Random only), DOA5LR-Crimson-VFX.asi v26 (bounded log) + .ini,
         scripts/MAPS-DZ-CRIMSON-EN.txt, DOA5LR-Diagnostic/maps-files.json + DOA5LR-Diagnostic.ps1 (.ini checked for presence only), the three guide copies, VERSION, SHA256SUMS.
         DOA5LR-DangerZone.asi rebuilt without its crash handler (the 0.3.13 file is a Defender ML false positive,
         Wacatac.C!ml, quarantined on players' PCs; crash dumps come from Windows WER / DOA5LR-Diagnostic instead) and
         DOA5LR-ExtraStages.asi 2.0.4 (log can be turned off): both built outside this repository by the maps work,
         seen applied in a real game, pinned by SHA-256 below and passed with --dz / --extrastages.
Removed: DOA5LR-Crimson-EventLog.asi and DOA5LR-Crimson-BackendProbe.asi (porting diagnostics), also deleted on disk.
Manifest: delete=d3d9.dll becomes delete_if=d3d9.dll|<old ui_mod sha256> (1.3.3 ignores the key: nothing deleted).
The two modules are rebuilt from src/Maps (build.cmd runs their self-tests) and signed with the installer.
Split download (installer 1.3.4): besides the full ZIP (url=, what older installers use) the release gets
DOA5LR-Salons-core-0.3.14.zip (the full pack minus the stage data) and DOA5LR-Salons-maps-data-1.zip (CodexCrimson,
CodexDangerZone, PS4Stages), announced by core= / data= in version.txt. core + data == full, entry for entry.
Every other 0.3.13 file stays byte-identical. Signing contacts the timestamp service. No publication, no game write.

  python tools/build_release_0314.py --base-dir <DOA5LR-Salons-0.3.13-Release> --dz <DOA5LR-DangerZone.asi>
         --extrastages <DOA5LR-ExtraStages 2.0.4 .asi> --out <folder>
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
VERSION = "0.3.14"
GITHUB = "FgcSnow/DOA5LR-Salons"
REL_BASE = f"https://github.com/{GITHUB}/releases/download/v{VERSION}"
BASE_ZIP = "DOA5LR-Salons-0.3.13.zip"
BASE_ZIP_SHA256 = "33e58048085a6da515c599545742be2192aea7fd99f50fb75fa738f6e5dd3875"
BASE_INSTALLER_SHA256 = "485b34afda6ec85f07227b8f9b956852c7246dab4216192eb25316e7b04f0b2c"
BASE_MANIFEST_SHA256 = "ca30d3732a68e05c53298e0f0935909934c58d2b864173c2ced555678b1ee21c"
INSTALLER = "DOA5LR-Salons-Installer.exe"
INSTALLER_VERSION = "1.3.5"
UIMOD_D3D9_SHA256 = "badac2aa7b4ca2d355cecdf36afad246f5e27891c86f7fa23dc42c1998ba4ee8"   # 0.2.3-0.3.3 ui_mod d3d9.dll
# 0.3.13 binaries the rebuilt modules replace (their sources in src/Maps rebuild to these, PE timestamp aside)
OLD_RANDOM_SHA256 = "0bfee24fedeb17a2cf90a7dcb27705d9d0b4ab6ebc3c3f22c0f0b88c38cb522a"
OLD_VFX_SHA256 = "b6a651486e022205d5c3623c6f12f13ff39ad42e7ae7fd6c56c31037b55cef32"
DZ_SHA256 = "4b2a37adb9339b940527f89880ebc227d3758eaf57dd32701ed5a5bb0256f0f8"            # MSVC, no crash handler
EXTRASTAGES_SHA256 = "bdfc58709d44386753189575b964c9a95b8a0b0400ef9bc06eefa3161721dffa"   # 2.0.4
DATA_PREFIXES = ("CodexCrimson/", "CodexDangerZone/", "PS4Stages/")
DATA_ZIP = "DOA5LR-Salons-maps-data-1.zip"   # data set 1 = the stage data of 0.3.13/0.3.14; a later release may reuse this asset
REMOVED = ["DOA5LR-Crimson-EventLog.asi", "DOA5LR-Crimson-BackendProbe.asi"]
REMOVED_LOGS = ["DOA5LR-Crimson-EventLog.log"]
# 1.3.5 (WAZAAAAA): the maps modules go to scripts\ like every other module; they find their .ini, logs and stage data
# from game.exe's folder (checked in game 30/09: all 11 applied from scripts\, logs still next to game.exe).
# DebugArchive stays next to game.exe (it builds its paths from its own location).
MOVED = ["DOA5LR-Crimson.asi", "DOA5LR-Crimson-Audio.asi", "DOA5LR-Crimson-VFX.asi", "DOA5LR-DangerZone.asi",
         "DOA5LR-DNZ-Complete.asi", "DOA5LR-DNZ-Name.asi", "DOA5LR-DNZ-Preview.asi", "DOA5LR-DNZ-SharedAudio.asi",
         "DOA5LR-DNZ-Thumbnail.asi", "DOA5LR-ExtraStages.asi", "DOA5LR-RandomStages.asi"]
OLD_MAPS_LABEL = "Maps: Danger Zone + The Crimson 1 and 2 (PS4 stages, Random included; everyone in a room needs them)"
MAPS_LABEL = "Maps: Danger Zone + The Crimson 1 and 2 (PS4 stages, offline Random; everyone in a room needs them)"
NOTES = [
    "notes=pack 0.3.14: your own resolution/window again without Borderless, your d3d9.dll kept, PLAY starts the game, "
    "new stages in offline Random only, smaller Crimson log, maps modules tidied into scripts",
    "note=0.3.14: the pack's AutoLink setting (DInput8.ini ResolutionMod=1) forced the desktop resolution for everyone. It is only "
    "needed by Borderless: Installer 1.3.5 sets ResolutionMod=0 when Borderless is unticked, so the resolution and window mode of "
    "the game's launcher apply again. A value you changed by hand is not turned back on.",
    "note=0.3.14: older installers deleted any d3d9.dll (meant for one old file of the 0.3.3 pack). Now only that exact old file is "
    "removed; ReShade or another d3d9 mod stays. A removed file is in DOA5LR-Salons-Backups.",
    "note=0.3.14: PLAY starts the game directly; Set controls opens the controls app (idea from Inyo). With keyboard remapping on "
    "in Keyboard mode, PLAY still opens the controls app first (it checks that no controller is connected).",
    "note=0.3.14: Danger Zone / Crimson are drawn by OFFLINE Random only: online Random (ranked, lobbies) is the game's own again, "
    "so a player without the maps never gets them. Pick them by hand in rooms (everyone in the room needs the maps).",
    "note=0.3.14: the Crimson effects log keeps startup and errors only (512 KB max); two porting diagnostics (Crimson-EventLog, Crimson-BackendProbe) "
    "are removed. Windows 11 error 4551 on a .asi = Smart App Control (not Defender): see the guide.",
    "note=0.3.14: DOA5LR-DangerZone.asi of 0.3.13 is flagged by Windows Defender (false positive): it is rebuilt without its crash "
    "handler. If Defender removed it, updating puts the new one back and the maps work again.",
    "note=0.3.14: the maps modules (DangerZone, DNZ-*, Crimson*, ExtraStages, RandomStages .asi) moved to the scripts folder like "
    "every other module of the pack (thanks WAZAAAAA); the update removes the old copies next to game.exe. Their .ini files and "
    "the stage data stay next to game.exe.",
    "note=0.3.14: accept Installer 1.3.5 when it is offered: the resolution and d3d9.dll fixes are done by the new installer, and "
    "later updates only download what changed (about 7 MB instead of 270 MB when your stage files are intact). If an older "
    "installer stops with 'the file contains a virus', run the update again: Defender has then removed the old DangerZone.asi.",
]


def manifest(base: str, zip_name: str, zip_data: bytes, installer: bytes, core_name: str, core: bytes, data: bytes) -> str:
    drop = ("version=", "url=", "sha256=", "size=", "notes=", "installer=", "installer_version=", "installer_sha256=")
    if "delete=d3d9.dll" not in base.splitlines():
        raise AssertionError("base manifest has no delete=d3d9.dll line")
    lines = [l for l in base.splitlines() if not l.startswith(drop) and l != "delete=d3d9.dll"]
    lines[1:1] = [f"version={VERSION}", f"url={REL_BASE}/{zip_name}", f"sha256={sha(zip_data)}", f"size={len(zip_data)}",
                  f"core={REL_BASE}/{core_name}|{sha(core)}|{len(core)}", f"data=maps|{REL_BASE}/{DATA_ZIP}|{sha(data)}|{len(data)}"] + NOTES
    k = next(i for i, l in enumerate(lines) if l.startswith("keep="))
    lines[k:k] = [f"installer={REL_BASE}/{INSTALLER}", f"installer_version={INSTALLER_VERSION}", f"installer_sha256={sha(installer)}"]
    k = next(i for i, l in enumerate(lines) if l.startswith("optional_v4="))
    if OLD_MAPS_LABEL not in lines[k]:
        raise AssertionError("optional_v4 label differs from 0.3.13")
    # 1.3.5: optional_v5 only (1.3.3/1.3.4 ignore it: no Maps box, no 'required maps files' check on the old root paths;
    # the root copies go through the delete= lines below, so no installer ever loads the modules twice)
    lines[k] = f"optional_v5=maps|{MAPS_LABEL}|{';'.join(maps_globs())}"
    k = next(i for i, l in enumerate(lines) if l.startswith("delete="))
    lines[k:k] = [f"delete={n}" for n in REMOVED + REMOVED_LOGS + MOVED]
    k = max(i for i, l in enumerate(lines) if l.startswith("delete=")) + 1
    lines[k:k] = [f"delete_if=d3d9.dll|{UIMOD_D3D9_SHA256}"]   # 1.3.4: only the old ui_mod file; 1.3.3 ignores the key
    return "\n".join(lines) + "\n"


def maps_globs() -> list[str]:
    import re
    src = (REPO / "src/Installer/Installer.cs").read_text(encoding="utf-8-sig")
    m = re.search(r'public static readonly Component Maps = new Component \{ Id = "maps", Label = "(.*?)", Globs = new\[\] \{ (.*?) \} \};', src)
    if not m or m.group(1) != MAPS_LABEL:
        raise AssertionError("Maps component not found in the installer source")
    return [g.strip()[2:-1] for g in m.group(2).split(",")]


def build(cmd: Path, product: Path) -> bytes:
    print(f"building {product.name}")
    r = subprocess.run(["cmd", "/c", str(cmd)], cwd=cmd.parent, capture_output=True, text=True, errors="replace")
    print("  " + r.stdout.strip().replace("\n", "\n  "))
    if r.returncode != 0 or "FAILED" in r.stdout:
        raise RuntimeError(f"{cmd} failed:\n{r.stdout}{r.stderr}")
    return product.read_bytes()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-dir", type=Path, required=True)
    ap.add_argument("--dz", type=Path, required=True)
    ap.add_argument("--extrastages", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    bz = (args.base_dir / BASE_ZIP).read_bytes()
    if sha(bz) != BASE_ZIP_SHA256:
        raise ValueError("base ZIP is not the published 0.3.13 archive")
    if sha((args.base_dir / INSTALLER).read_bytes()) != BASE_INSTALLER_SHA256:
        raise ValueError("base installer is not the published 1.3.3")
    base_manifest_bytes = (args.base_dir / "version.txt").read_bytes()
    if sha(base_manifest_bytes) != BASE_MANIFEST_SHA256:
        raise ValueError("base version.txt is not the published 0.3.13 manifest")
    base_manifest = base_manifest_bytes.decode("utf-8-sig")
    args.out.mkdir(parents=True, exist_ok=True)
    tmp_zip = args.out / "_base.zip"
    tmp_zip.write_bytes(bz)
    with ZipFile(tmp_zip) as z:
        payload = {n: z.read(n) for n in z.namelist()}
    tmp_zip.unlink()
    base = dict(payload)
    if sha(base["DOA5LR-RandomStages.asi"]) != OLD_RANDOM_SHA256 or sha(base["DOA5LR-Crimson-VFX.asi"]) != OLD_VFX_SHA256:
        raise AssertionError("0.3.13 RandomStages / Crimson-VFX are not the expected binaries")

    dz_asi, es_asi = args.dz.read_bytes(), args.extrastages.read_bytes()
    if sha(dz_asi) != DZ_SHA256 or sha(es_asi) != EXTRASTAGES_SHA256:
        raise ValueError("--dz / --extrastages are not the pinned binaries")
    if b"Startup v2.0.4" not in es_asi or b"DOA5LR-DangerZone-crash.txt" in dz_asi:
        raise AssertionError("unexpected ExtraStages / DangerZone build")
    random_asi = build(REPO / "src/Maps/RandomStages/build.cmd", REPO / "src/Maps/RandomStages/DOA5LR-RandomStages.asi")
    vfx_asi = build(REPO / "src/Maps/CrimsonVFX/build.cmd", REPO / "src/Maps/CrimsonVFX/DOA5LR-Crimson-VFX.asi")
    print("building installer from repository source")
    src = REPO / "src" / "Installer"
    subprocess.run(["cmd", "/c", str(src / "build.cmd")], cwd=src, check=True)
    installer_source = (src / "Installer.cs").read_bytes()
    for needle in (f'AppVersion = "{INSTALLER_VERSION}"', 'case "optional_v5"', 'case "delete_if"', 'case "core"', 'case "data"', "SyncResolutionMod", "RequiresChooser", MAPS_LABEL):
        if needle.encode() not in installer_source:
            raise AssertionError(f"installer source is not 1.3.4 ({needle} missing)")

    print("signing the installer and the two rebuilt modules")
    signed = sign({INSTALLER: (src / INSTALLER).read_bytes(), "DOA5LR-RandomStages.asi": random_asi, "DOA5LR-Crimson-VFX.asi": vfx_asi,
                   "DOA5LR-DangerZone.asi": dz_asi, "DOA5LR-ExtraStages.asi": es_asi})
    installer = signed[INSTALLER]

    # Diagnostic: same list minus the removed modules, new hashes for the rebuilt ones (both repo copies stay identical)
    maps = json.loads((REPO / "src/Maps/maps-files.json").read_text(encoding="utf-8-sig"))
    # every listed file takes the hash of the file this pack ships (asi AND ini: a fresh install gets the new defaults)
    maps_files = {n: signed[n] for n in ("DOA5LR-RandomStages.asi", "DOA5LR-Crimson-VFX.asi", "DOA5LR-DangerZone.asi", "DOA5LR-ExtraStages.asi")}
    maps_files["DOA5LR-RandomStages.ini"] = (REPO / "src/Maps/RandomStages/DOA5LR-RandomStages.ini").read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    maps_files["DOA5LR-Crimson-VFX.ini"] = (REPO / "src/Maps/CrimsonVFX/DOA5LR-Crimson-VFX.ini").read_bytes()
    new_maps = []
    for e in maps:
        if e["path"].startswith("scripts/") and e["path"][8:] in MOVED:   # list already rewritten by an earlier run
            e = {**e, "path": e["path"][8:]}
        if e["path"] in REMOVED:
            continue
        data = maps_files.get(e["path"], base.get(e["path"]))
        if data is None:
            raise AssertionError(f"listed stage file missing from the pack: {e['path']}")
        new_maps.append({**e, "sha256": sha(data), "size": len(data)})
    if len(new_maps) != 67:
        raise AssertionError("67 stage files expected after removing the two diagnostics")
    maps_json = (json.dumps(new_maps, indent=2) + "\n").encode("utf-8")
    for copy in (REPO / "src/Maps/maps-files.json", REPO / "src/Diagnostic/maps-files.json"):
        copy.write_bytes(maps_json)

    changed = {
        INSTALLER: installer,
        "scripts/Installer-Source/Installer.cs": installer_source,
        "DOA5LR-RandomStages.asi": signed["DOA5LR-RandomStages.asi"],
        "DOA5LR-RandomStages.ini": maps_files["DOA5LR-RandomStages.ini"],
        "DOA5LR-Crimson-VFX.asi": signed["DOA5LR-Crimson-VFX.asi"],
        "DOA5LR-DangerZone.asi": signed["DOA5LR-DangerZone.asi"],
        "DOA5LR-ExtraStages.asi": signed["DOA5LR-ExtraStages.asi"],
        "DOA5LR-Crimson-VFX.ini": maps_files["DOA5LR-Crimson-VFX.ini"],
        "scripts/MAPS-DZ-CRIMSON-EN.txt": (REPO / "src/Maps/MAPS-DZ-CRIMSON-EN.txt").read_bytes(),
        "DOA5LR-Diagnostic/maps-files.json": maps_json,
        "DOA5LR-Diagnostic/DOA5LR-Diagnostic.ps1": (REPO / "src/Diagnostic/DOA5LR-Diagnostic.ps1").read_bytes(),   # .ini: presence only
        **pack_guides(VERSION),
        "DOA5LR-Salons-VERSION.txt": (VERSION + "\r\n").encode("ascii"),
    }
    for n in changed:
        if n not in payload:
            raise AssertionError(f"{n} is missing from 0.3.13")
        if payload[n] == changed[n]:
            raise AssertionError(f"{n} did not change")
    payload.update(changed)
    for n in REMOVED:
        if n not in payload:
            raise AssertionError(f"{n} is not in 0.3.13")
        del payload[n]
    payload.pop("SHA256SUMS.txt", None)
    payload["SHA256SUMS.txt"] = "".join(f"{sha(payload[n])} *{n}\n" for n in sorted(payload)).encode("ascii")
    for n, b in base.items():
        if n in REMOVED or n in changed or n == "SHA256SUMS.txt":
            continue
        if payload[n] != b:
            raise AssertionError(f"{n} changed although it should be byte-identical to 0.3.13")
    if set(payload) != (set(base) - set(REMOVED)):
        raise AssertionError("unexpected file added or missing")
    for n in MOVED:
        payload["scripts/" + n] = payload.pop(n)
    for e in new_maps:
        if e["path"] in MOVED:
            e["path"] = "scripts/" + e["path"]
    maps_json = (json.dumps(new_maps, indent=2) + "\n").encode("utf-8")
    for copy in (REPO / "src/Maps/maps-files.json", REPO / "src/Diagnostic/maps-files.json"):
        copy.write_bytes(maps_json)
    payload["DOA5LR-Diagnostic/maps-files.json"] = maps_json
    payload.pop("SHA256SUMS.txt", None)
    payload["SHA256SUMS.txt"] = "".join(f"{sha(payload[n])} *{n}\n" for n in sorted(payload)).encode("ascii")
    globs = maps_globs()
    stray = [n for n in MOVED if "scripts\\" + n not in globs or n not in globs]
    if stray:
        raise AssertionError(f"installer Maps globs do not own both paths of {stray}")
    listed = json.loads(maps_json)
    bad = [e["path"] for e in listed if e["path"] not in payload or sha(payload[e["path"]]) != e["sha256"]]
    if bad:
        raise AssertionError(f"maps-files.json does not match the pack: {bad}")
    check_pack_guides(payload, VERSION)

    zip_path = args.out / f"DOA5LR-Salons-{VERSION}.zip"
    write_zip(zip_path, payload)
    zip_data = zip_path.read_bytes()
    # split download: the stage data = every maps-list entry under DATA_PREFIXES (the installer derives it the same way:
    # entries of DOA5LR-Diagnostic/maps-files.json absent from the core)
    data_files = {n: b for n, b in payload.items() if n.startswith(DATA_PREFIXES)}
    listed = {e["path"] for e in new_maps}
    if not data_files or set(data_files) != {n for n in listed if n.startswith(DATA_PREFIXES)}:
        raise AssertionError("stage data files and maps-files.json disagree")
    core_files = {n: b for n, b in payload.items() if n not in data_files}
    if {**core_files, **data_files} != payload or set(core_files) & set(data_files):
        raise AssertionError("core + data != full pack")
    if {n for n in listed if n not in core_files} != set(data_files):
        raise AssertionError("the installer would derive another data list")
    core_path, data_path = args.out / f"DOA5LR-Salons-core-{VERSION}.zip", args.out / DATA_ZIP
    write_zip(core_path, core_files)
    write_zip(data_path, data_files)
    core_data, data_data = core_path.read_bytes(), data_path.read_bytes()
    (args.out / INSTALLER).write_bytes(installer)
    (args.out / "version.txt").write_text(manifest(base_manifest, zip_path.name, zip_data, installer, core_path.name, core_data, data_data),
                                          encoding="utf-8", newline="\n")
    assets = [zip_path, core_path, data_path, args.out / INSTALLER]
    (args.out / "SHA256SUMS.txt").write_text("".join(f"{sha(p.read_bytes())} *{p.name}\n" for p in assets), encoding="ascii", newline="\n")
    report = {
        "version": VERSION, "from": BASE_ZIP, "from_sha256": BASE_ZIP_SHA256,
        "zip": zip_path.name, "zip_sha256": sha(zip_data), "zip_bytes": len(zip_data), "zip_entries": len(payload),
        "core_zip": core_path.name, "core_sha256": sha(core_data), "core_bytes": len(core_data),
        "data_zip": DATA_ZIP, "data_sha256": sha(data_data), "data_bytes": len(data_data), "data_entries": len(data_files),
        "installer_version": INSTALLER_VERSION, "installer_sha256": sha(installer),
        "random_stages_sha256": sha(signed["DOA5LR-RandomStages.asi"]), "crimson_vfx_v26_sha256": sha(signed["DOA5LR-Crimson-VFX.asi"]),
        "dangerzone_sha256": sha(signed["DOA5LR-DangerZone.asi"]), "extrastages_sha256": sha(signed["DOA5LR-ExtraStages.asi"]),
        "removed": REMOVED, "changed": sorted(list(changed) + ["SHA256SUMS.txt"]),
    }
    (args.out / "build-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
