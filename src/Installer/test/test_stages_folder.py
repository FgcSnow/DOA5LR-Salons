# Installer 1.3.11: maps modules move from scripts\ to scripts\DOA5LR-Stages\ (fake game, fake pack, local manifest).
# Checks: 0.3.15 layout upgraded, old copies removed and backed up, no module left in two places (the ASI loader also
# loads sub-folders, so a duplicate would be loaded twice), 4a safety net without delete= lines, maps left out removes
# every copy, player .ini kept.   python test_stages_folder.py
import os, sys, zipfile, hashlib, subprocess, tempfile, glob
EXE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "DOA5LR-Salons-Installer.exe")
T = tempfile.mkdtemp(prefix="doa5lr-stages-test-")
GAME = os.path.join(T, "game"); os.makedirs(GAME)
LOG = os.path.join(GAME, "DOA5LR-Salons-Installer.log")
MAPS = ["Crimson", "Crimson-Audio", "Crimson-VFX", "DangerZone", "DNZ-Complete", "DNZ-Name", "DNZ-Preview", "DNZ-SharedAudio",
        "DNZ-Thumbnail", "ExtraStages", "RandomStages"]
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def ok(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        if os.path.exists(LOG): print(open(LOG, encoding="utf-8", errors="replace").read()[-3000:])
        sys.exit(1)
def ex(rel): return os.path.exists(os.path.join(GAME, rel))
def put(rel, data):
    p = os.path.join(GAME, rel); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(data)

CORE = {"dinput8.dll": b"loader", "dinput8Hooked.dll": b"autolink", "DInput8.ini": b"[PATCH]\r\n", "dinput8ex.bin": b"xidi", "Xidi.32.dll": b"xidi32",
        "DOA5LR-Salons-VERSION.txt": b"0.3.16\n", "scripts/DOA5LR-Lobby.asi": b"lobby", "scripts/DOA5LR-InviteFix.asi": b"inv",
        "scripts/DOA5LR-WiFi-Wired-Detector.asi": b"wifi", "scripts/DOA5LR-UpdateCheck.asi": b"upd", "scripts/DOA5LR-JoinFix.asi": b"join",
        "scripts/DOA5LR-Borderless.asi": b"border", "scripts/DOA5LR-60fps-menus.asi": b"fps",
        "DOA5LR-DebugArchive.asi": b"debug-new", "DOA5LR-ExtraStages.ini": b"[Stages]\r\nFIREWORKS=0\r\n",
        "CodexCrimson/CRIMSON1.TMC": b"model", "scripts/MAPS-DZ-CRIMSON-EN.txt": b"doc"}
for m in MAPS: CORE["scripts/DOA5LR-Stages/DOA5LR-%s.asi" % m] = ("new-" + m).encode()
ZIP = os.path.join(T, "DOA5LR-Salons-0.3.16.zip")
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for rel, data in CORE.items(): z.writestr(rel, data)
import re
SRC = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Installer.cs"), encoding="utf-8").read()
def globs(name):
    line = re.search(r"public static readonly Component " + name + r" = new Component \{.*?Globs = new\[\] \{(.*?)\} \};", SRC).group(1)
    return re.findall(r'@"([^"]*)"', line)
bs = chr(92)
maps_globs = globs("Maps")
assert maps_globs[:11] == [("scripts" + bs + "DOA5LR-Stages" + bs + "DOA5LR-%s.asi") % m for m in MAPS], maps_globs[:11]
OPT = "optional_v7=maps|Maps: Danger Zone + The Crimson 1 and 2 (PS4 stages, offline Random; everyone in a room needs them)|" + ";".join(maps_globs)
OPT_V5 = "optional_v5=maps|Maps: Danger Zone + The Crimson 1 and 2 (PS4 stages, offline Random; everyone in a room needs them)|" + ";".join(globs("MapsScripts"))  # read by 1.3.5-1.3.10
DELETES = [("delete=scripts" + bs + "DOA5LR-%s.asi") % m for m in MAPS]
VT = os.path.join(T, "version.txt")
def manifest(with_deletes):
    lines = ["version=0.3.16", "url=" + ZIP, "sha256=" + sha(ZIP), "size=%d" % os.path.getsize(ZIP), "notes=test", "keep=*.ini", OPT, OPT_V5]
    open(VT, "w", newline="\n").write("\n".join(lines + (DELETES if with_deletes else [])) + "\n")
def run(*extra): return subprocess.run([EXE, "--auto", "--game", GAME, "--manifest", VT] + list(extra), timeout=180).returncode
def stale(): return [m for m in MAPS if ex("scripts/DOA5LR-%s.asi" % m)]
def fresh(): return [m for m in MAPS if ex("scripts/DOA5LR-Stages/DOA5LR-%s.asi" % m)]

def old_layout():
    put("game.exe", b"fake"); put("DOA5LR-Salons-VERSION.txt", b"0.3.15\n")
    for rel, data in CORE.items():
        if not rel.startswith("scripts/DOA5LR-Stages/"): put(rel, data)
    for m in MAPS: put("scripts/DOA5LR-%s.asi" % m, ("old-" + m).encode())
    put("DOA5LR-ExtraStages.ini", b"[Stages]\r\nFIREWORKS=1\r\n; personal\r\n")

print("1. 0.3.15 layout -> 0.3.16 with delete= lines")
old_layout(); manifest(True)
ok(run("--components", "maps=1") == 0, "installer --auto OK")
ok(fresh() == MAPS, "11 modules in scripts\\DOA5LR-Stages\\")
ok(stale() == [], "no maps module left in scripts\\ (no double load)")
ok(all(open(os.path.join(GAME, "scripts", "DOA5LR-Stages", "DOA5LR-%s.asi" % m), "rb").read() == ("new-" + m).encode() for m in MAPS), "new module contents")
ok(open(os.path.join(GAME, "DOA5LR-ExtraStages.ini"), "rb").read() == b"[Stages]\r\nFIREWORKS=1\r\n; personal\r\n", "player .ini kept")
ok(ex("DOA5LR-DebugArchive.asi") and ex("scripts/DOA5LR-Lobby.asi"), "DebugArchive (root) and salon modules untouched")
bk = sorted(glob.glob(os.path.join(GAME, "DOA5LR-Salons-Backups", "*")))[-1]
ok(all(os.path.exists(os.path.join(bk, "scripts", "DOA5LR-%s.asi" % m)) for m in MAPS), "old scripts\\ modules backed up")

print("2. safety net: a manifest WITHOUT delete= lines still leaves no duplicate")
for m in MAPS: put("scripts/DOA5LR-%s.asi" % m, ("old-" + m).encode())
manifest(False)
ok(run("--components", "maps=1") == 0, "installer --auto OK")
ok(stale() == [] and fresh() == MAPS, "duplicates removed by 1.3.11 itself")
ok("removed duplicate scripts\\DOA5LR-Crimson.asi" in open(LOG, encoding="utf-8", errors="replace").read(), "log line for the removed duplicate")

print("3. maps left out: every copy goes, .ini kept")
for m in MAPS[:3]: put("scripts/DOA5LR-%s.asi" % m, b"old")
manifest(True)
ok(run("--components", "maps=0") == 0, "installer --auto OK")
ok(stale() == [] and fresh() == [], "no maps module anywhere")
ok(ex("DOA5LR-ExtraStages.ini"), "player .ini kept")

print("4. maps ticked again")
ok(run("--components", "maps=1") == 0 and fresh() == MAPS and stale() == [], "11 modules back, only in the new folder")
print("ALL STAGES FOLDER TESTS PASSED")
