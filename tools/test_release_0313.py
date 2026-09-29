"""End-to-end test of the built 0.3.13 release on fake game folders (no Steam, no real game, no network).

  PYTHONUTF8=1 python tools/test_release_0313.py --rel <DOA5LR-Salons-0.3.13-Release> --base <DOA5LR-Salons-0.3.12-Release>

1. published installer 1.3.2 + 0.3.12, then the new 1.3.3 updates to 0.3.13: maps + Diagnostic installed, 0.3.12 files kept
2. Maps unticked -> the 69 stage files and the guide are removed, everything else stays; ticked again -> back, identical
3. the published 1.3.2 reads the 0.3.13 manifest (unknown key optional_v4 ignored) and installs it (maps always then)
4. version.txt keeps 0.3.12's components, adds optional_v4 with the installer's exact globs, points to v0.3.13
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
from zipfile import ZipFile

def sha(p: Path) -> str: return hashlib.sha256(p.read_bytes()).hexdigest()
def ok(c, m):
    print(("  OK   " if c else "  FAIL ") + m)
    if not c: sys.exit(1)

ap = argparse.ArgumentParser(); ap.add_argument("--rel", type=Path, required=True); ap.add_argument("--base", type=Path, required=True)
a = ap.parse_args()
T = Path(tempfile.mkdtemp(prefix="doa5lr-0313-"))
NEW = a.rel / "DOA5LR-Salons-Installer.exe"; OLD = a.base / "DOA5LR-Salons-Installer.exe"

def local_manifest(rel: Path, zipname: str, name: str) -> Path:
    d = T / name; d.mkdir()
    shutil.copy(rel / zipname, d / zipname)
    lines = []
    for l in (rel / "version.txt").read_text(encoding="utf-8").splitlines():
        if l.startswith("url="): l = "url=" + zipname          # sibling ZIP (local manifest rule)
        if l.startswith(("installer=", "installer_version=", "installer_sha256=")): continue   # no self-update in the test
        lines.append(l)
    (d / "version.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return d / "version.txt"

M12 = local_manifest(a.base, "DOA5LR-Salons-0.3.12.zip", "m12")
M13 = local_manifest(a.rel, "DOA5LR-Salons-0.3.13.zip", "m13")
maps = json.loads((Path(__file__).resolve().parents[1] / "src/Maps/maps-files.json").read_text(encoding="utf-8-sig"))
with ZipFile(a.rel / "DOA5LR-Salons-0.3.13.zip") as z: zip13 = set(z.namelist())
with ZipFile(a.base / "DOA5LR-Salons-0.3.12.zip") as z: zip12 = {n: z.read(n) for n in z.namelist()}

def new_game(name):
    g = T / name; g.mkdir(); (g / "game.exe").write_bytes(b"fake game"); return g
def run(exe, g, man):
    r = subprocess.run([str(exe), "--auto", "--game", str(g), "--manifest", str(man)])
    return r.returncode
def log(g): p = g / "DOA5LR-Salons-Installer.log"; return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
def maps_ok(g): return all((g / e["path"]).is_file() and sha(g / e["path"]) == e["sha256"] for e in maps)
def maps_gone(g): return not any((g / e["path"]).exists() for e in maps) and not (g / "scripts/MAPS-DZ-CRIMSON-EN.txt").exists()
def comp(g, k, v):
    p = g / "DOA5LR-Salons-Components.txt"
    lines = [l for l in p.read_text().splitlines() if not l.startswith(k + "=")] if p.exists() else []
    p.write_text("\n".join(lines + [f"{k}={v}"]) + "\n")

print("1. 0.3.12 by the published 1.3.2, then 0.3.13 by 1.3.3")
g = new_game("g1")
ok(run(OLD, g, M12) == 0, "1.3.2 installs 0.3.12")
ok((g / "DOA5LR-Salons-VERSION.txt").read_text().strip() == "0.3.12", "version 0.3.12")
(g / "scripts/DOA5LR-JoinFix.ini").write_bytes(b"[JoinFix]\r\nKeyFix=1\r\nCopyLinkKey=0\r\n")   # a personal setting
ok(run(NEW, g, M13) == 0, "1.3.3 updates to 0.3.13")
ok((g / "DOA5LR-Salons-VERSION.txt").read_text().strip() == "0.3.13", "version 0.3.13")
ok(maps_ok(g), "69 stage files installed, identical to the tested ones")
ok((g / "DOA5LR-Diagnostic/DOA5LR-Diagnostic.ps1").is_file() and (g / "DOA5LR-Diagnostic/Sonde/DOA5LR-TestEnLigne.exe").is_file(), "Diagnostic tool installed")
ok(b"CopyLinkKey=0" in (g / "scripts/DOA5LR-JoinFix.ini").read_bytes(), "personal JoinFix.ini kept")
for n in ("scripts/DOA5LR-Lobby.asi", "scripts/DOA5LR-JoinFix.asi", "scripts/DOA5LR-InviteFix.asi", "scripts/DOA5LR-WiFi-Wired-Detector.asi", "DOA5LR-ReplayTakeover.asi"):
    ok(hashlib.sha256((g / n).read_bytes()).hexdigest() == hashlib.sha256(zip12[n]).hexdigest(), f"{n} identical to 0.3.12")
ok("maps=1" in (g / "DOA5LR-Salons-Components.txt").read_text(), "Maps recorded as ticked (default on)")

print("2. Maps unticked, then ticked again")
comp(g, "maps", 0)
ok(run(NEW, g, M13) == 0, "reinstall with Maps unticked")
left = [e["path"] for e in maps if (g / e["path"]).exists()] + (["guide"] if (g / "scripts/MAPS-DZ-CRIMSON-EN.txt").exists() else [])
print("     restent :", left)
ok(all(x.endswith(".ini") for x in left), "stage files and guide removed (only the .ini settings kept, like every component)")
ok((g / "scripts/DOA5LR-Lobby.asi").is_file() and (g / "DOA5LR-Diagnostic/DOA5LR-Diagnostic.ps1").is_file(), "lobby modules and Diagnostic still there")
comp(g, "maps", 1)
ok(run(NEW, g, M13) == 0, "reinstall with Maps ticked")
ok(maps_ok(g), "stage files back, identical")

print("3. the published 1.3.2 reads the 0.3.13 manifest")
g2 = new_game("g2")
ok(run(OLD, g2, M13) == 0, "1.3.2 installs 0.3.13 (optional_v4 ignored, no refusal)")
ok(maps_ok(g2), "stages installed by 1.3.2 too")
ok("Refused" not in log(g2), "no 'Refused' in the 1.3.2 log")

print("4. version.txt")
v = (a.rel / "version.txt").read_text(encoding="utf-8")
ok("version=0.3.13" in v and "/v0.3.13/DOA5LR-Salons-0.3.13.zip" in v and "installer_version=1.3.3" in v, "version, url, installer")
for k in ("optional=borderless|", "optional=60fps|", "optional_v2=inputlab|", "optional_v3=replaytakeover|", "optional_v4=maps|"):
    ok(k in v, f"component line {k}")
ok(sha(a.rel / "DOA5LR-Salons-0.3.13.zip") in v and sha(NEW) in v, "hashes of the ZIP and of the installer")
src = (Path(__file__).resolve().parents[1] / "src/Installer/Installer.cs").read_text(encoding="utf-8-sig")
globs = next(l for l in v.splitlines() if l.startswith("optional_v4=")).split("|")[2].split(";")
ok(all(('@"' + g_ + '"') in src for g_ in globs), "manifest globs = installer globs")
ok("DOA5LR-Diagnostic/envoi-logs.txt" in zip13 and not any("rollback" in n.lower() or n.lower().endswith(".log") for n in zip13), "ZIP content (webhook file, no log, no rollback)")
print("ALL 0.3.13 RELEASE TESTS PASSED")
print(T)
