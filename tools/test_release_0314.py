"""End-to-end test of the built 0.3.14 release on fake game folders (no Steam, no real game, no network).

  PYTHONUTF8=1 python tools/test_release_0314.py --rel <DOA5LR-Salons-0.3.14-Release> --base <DOA5LR-Salons-0.3.13-Release> --uimod <old d3d9.dll>

1. published 1.3.3 installs 0.3.13, then 1.3.4 updates to 0.3.14: diagnostics removed, rebuilt modules in, foreign d3d9.dll
   kept, ResolutionMod lowered to 0 (Borderless off), 0.3.13 files byte-identical, personal .ini kept
2. the published 1.3.3 (self-update declined) installs 0.3.14: no d3d9.dll deleted any more, pack identical
3. 1.3.4 removes the exact old ui_mod d3d9.dll (backed up)
4. Maps unticked -> removed, ticked -> back
5. version.txt: delete_if replaces delete=d3d9.dll, optional_v4 globs identical to the installer's table, points to v0.3.14
"""
from __future__ import annotations
import argparse, hashlib, json, re, shutil, subprocess, sys, tempfile
from pathlib import Path
from zipfile import ZipFile

REPO = Path(__file__).resolve().parents[1]
def sha(p: Path) -> str: return hashlib.sha256(p.read_bytes()).hexdigest()
def ok(c, m):
    print(("  OK   " if c else "  FAIL ") + m)
    if not c: sys.exit(1)

ap = argparse.ArgumentParser(); ap.add_argument("--rel", type=Path, required=True); ap.add_argument("--base", type=Path, required=True)
ap.add_argument("--uimod", type=Path, required=True)
a = ap.parse_args()
T = Path(tempfile.mkdtemp(prefix="doa5lr-0314-"))
NEW = a.rel / "DOA5LR-Salons-Installer.exe"; OLD = a.base / "DOA5LR-Salons-Installer.exe"
UIMOD = a.uimod.read_bytes()
ok(hashlib.sha256(UIMOD).hexdigest() == "badac2aa7b4ca2d355cecdf36afad246f5e27891c86f7fa23dc42c1998ba4ee8", "old ui_mod d3d9.dll fixture")

def local_manifest(rel: Path, zipname: str, name: str) -> Path:
    d = T / name; d.mkdir()
    shutil.copy(rel / zipname, d / zipname)
    lines = []
    for l in (rel / "version.txt").read_text(encoding="utf-8").splitlines():
        if l.startswith("url="): l = "url=" + zipname
        if l.startswith(("installer=", "installer_version=", "installer_sha256=")): continue   # self-update declined / not tested here
        lines.append(l)
    (d / "version.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return d / "version.txt"

M13 = local_manifest(a.base, "DOA5LR-Salons-0.3.13.zip", "m13")
M14 = local_manifest(a.rel, "DOA5LR-Salons-0.3.14.zip", "m14")
with ZipFile(a.base / "DOA5LR-Salons-0.3.13.zip") as z: zip13 = {n: z.read(n) for n in z.namelist()}
with ZipFile(a.rel / "DOA5LR-Salons-0.3.14.zip") as z: zip14 = {n: z.read(n) for n in z.namelist()}
maps = json.loads((REPO / "src/Maps/maps-files.json").read_text(encoding="utf-8-sig"))
REMOVED = ["DOA5LR-Crimson-EventLog.asi", "DOA5LR-Crimson-BackendProbe.asi"]

def new_game(name):
    g = T / name; g.mkdir(); (g / "game.exe").write_bytes(b"fake game"); return g
def run(exe, g, man, *extra): return subprocess.run([str(exe), "--auto", "--game", str(g), "--manifest", str(man), *extra]).returncode
def resmod(g):
    t = (g / "DInput8.ini").read_bytes(); s = t[2:].decode("utf-16-le"); i = s.index("[PATCH]")
    return s[s.index("ResolutionMod=", i) + len("ResolutionMod=")]
def maps_ok(g): return all((g / e["path"]).is_file() and sha(g / e["path"]) == e["sha256"] for e in maps)
def comp(g, k, v):
    p = g / "DOA5LR-Salons-Components.txt"
    lines = [l for l in p.read_text().splitlines() if not l.startswith(k + "=")] if p.exists() else []
    p.write_text("\n".join(lines + [f"{k}={v}"]) + "\n")

print("1. 0.3.13 by the published 1.3.3, then 0.3.14 by 1.3.4")
g = new_game("g1")
ok(run(OLD, g, M13) == 0, "1.3.3 installs 0.3.13")
ok(resmod(g) == "1" and all((g / n).is_file() for n in REMOVED), "0.3.13 state: ResolutionMod=1, diagnostics present")
(g / "d3d9.dll").write_bytes(b"ReShade d3d9.dll")
(g / "DOA5LR-Crimson-EventLog.log").write_bytes(b"x" * 1000)
(g / "scripts/DOA5LR-JoinFix.ini").write_bytes(b"[JoinFix]\r\nKeyFix=1\r\nCopyLinkKey=0\r\n")
ok(run(NEW, g, M14) == 0, "1.3.4 updates to 0.3.14")
ok((g / "DOA5LR-Salons-VERSION.txt").read_text().strip() == "0.3.14", "version 0.3.14")
ok(not any((g / n).exists() for n in REMOVED + ["DOA5LR-Crimson-EventLog.log"]), "EventLog / BackendProbe and the EventLog log removed")
ok((g / "d3d9.dll").read_bytes() == b"ReShade d3d9.dll", "foreign d3d9.dll kept")
ok(resmod(g) == "0", "ResolutionMod lowered to 0 (Borderless off)")
ok(maps_ok(g), "67 stage files match the new list (rebuilt RandomStages / VFX)")
ok(b"CopyLinkKey=0" in (g / "scripts/DOA5LR-JoinFix.ini").read_bytes(), "personal JoinFix.ini kept")
same = [n for n in zip14 if n in zip13 and zip14[n] == zip13[n]]
OPTIONAL_OFF = {"DOA5LR-Companion.exe", "DOA5LR-InputBridge-Xidi.dll", "DOA5LR-InputBridge.ini", "DOA5LR-ControllerProfiles.ini"}   # InputLab runtime, off
BORDERLESS_OFF = ("scripts/DOA5LR-Borderless.asi", "scripts/BORDERLESS-EN.txt", "scripts/Borderless-Source/")   # unticked by default
check = [n for n in same if not n.endswith(".ini") and n not in OPTIONAL_OFF and not n.startswith(BORDERLESS_OFF) and n != "DOA5LR-Salons-Installer.exe"]
ok(len(check) >= 140 and all((g / n).read_bytes() == zip13[n] for n in check), f"{len(check)} unchanged files identical to 0.3.13 on disk")

print("2. the published 1.3.3 installs 0.3.14 (self-update declined)")
g2 = new_game("g2")
ok(run(OLD, g2, M13) == 0, "1.3.3 installs 0.3.13")
(g2 / "d3d9.dll").write_bytes(b"ReShade d3d9.dll")
ok(run(OLD, g2, M14) == 0, "1.3.3 installs 0.3.14")
ok((g2 / "DOA5LR-Salons-VERSION.txt").read_text().strip() == "0.3.14" and maps_ok(g2), "0.3.14 installed, maps OK")
ok((g2 / "d3d9.dll").read_bytes() == b"ReShade d3d9.dll", "1.3.3 no longer deletes d3d9.dll (delete_if ignored, delete= gone)")
ok(not any((g2 / n).exists() for n in REMOVED), "diagnostics removed by 1.3.3 too (delete=)")

print("3. 1.3.4 removes only the exact old ui_mod d3d9.dll")
(g / "d3d9.dll").write_bytes(UIMOD)
ok(run(NEW, g, M14) == 0 and not (g / "d3d9.dll").exists(), "old ui_mod d3d9.dll removed")
ok(any(p.read_bytes() == UIMOD for p in (g / "DOA5LR-Salons-Backups").rglob("d3d9.dll")), "and kept in the backup")

print("4. Maps unticked, then ticked again")
comp(g, "maps", 0)
ok(run(NEW, g, M14) == 0, "reinstall with Maps unticked")
left = [e["path"] for e in maps if (g / e["path"]).exists()]
ok(all(x.endswith(".ini") for x in left), "stage files removed (only .ini settings kept)")
comp(g, "maps", 1)
ok(run(NEW, g, M14) == 0 and maps_ok(g), "stage files back, identical")

print("5. version.txt")
v = (a.rel / "version.txt").read_text(encoding="utf-8").splitlines()
ok("version=0.3.14" in v and "delete=d3d9.dll" not in v, "version 0.3.14, no unconditional d3d9.dll delete")
ok("delete_if=d3d9.dll|badac2aa7b4ca2d355cecdf36afad246f5e27891c86f7fa23dc42c1998ba4ee8" in v, "delete_if for the old ui_mod only")
ok(all(f"delete={n}" in v for n in REMOVED + ["DOA5LR-Crimson-EventLog.log"]), "diagnostics in the delete list")
ok(any(l.startswith("url=https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.14/DOA5LR-Salons-0.3.14.zip") for l in v), "ZIP url on v0.3.14")
ok(f"installer_sha256={sha(NEW)}" in v and "installer_version=1.3.4" in v, "installer 1.3.4 pinned")
src = (REPO / "src/Installer/Installer.cs").read_text(encoding="utf-8-sig")
opt4 = next(l for l in v if l.startswith("optional_v4="))
globs = opt4.split("|")[2].split(";")
ok(all(('@"' + g_ + '"') in src for g_ in globs), "optional_v4 globs identical to the installer's Maps table (1.3.3 accepts them)")
old4 = next(l for l in (a.base / "version.txt").read_text(encoding="utf-8").splitlines() if l.startswith("optional_v4="))
ok(old4.split("|")[2] == opt4.split("|")[2], "optional_v4 globs unchanged since 0.3.13")
for l in (a.base / "version.txt").read_text(encoding="utf-8").splitlines():
    if l.startswith(("optional", "move=", "keep=")): ok(l in v or l.startswith("optional_v4="), f"kept: {l[:60]}")
print("ALL 0.3.14 RELEASE TESTS PASSED")
