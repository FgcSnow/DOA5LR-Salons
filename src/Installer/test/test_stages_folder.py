# Installer 1.3.11: every stage-map file leaves the game folder for scripts\DOA5LR-Stages\ (the 11 modules and
# the seven .ini files; DebugArchive stays next to game.exe; logs go to DOA5LR-Logs\ by the modules themselves). Fake game, fake pack, local manifest.
# Checks: 0.3.15 layout upgraded, the player's settings migrated by move= and kept, old copies backed up and removed,
# nothing left twice (the ASI loader also loads sub-folders: a duplicate would be loaded twice), the 1.3.11 duplicate
# guard without delete= lines, maps left out / ticked again, a production-like manifest with optional_v7 + optional_v5.
#   python test_stages_folder.py            (EXE can be overridden with DOA5LR_TEST_INSTALLER)
import os, sys, zipfile, hashlib, subprocess, tempfile, glob, re
HERE = os.path.dirname(os.path.abspath(__file__))
EXE = os.environ.get("DOA5LR_TEST_INSTALLER") or os.path.join(HERE, "..", "DOA5LR-Salons-Installer.exe")
T = tempfile.mkdtemp(prefix="doa5lr-stages-test-")
GAME = os.path.join(T, "game"); os.makedirs(GAME)
LOG = os.path.join(GAME, "DOA5LR-Salons-Installer.log")
bs = chr(92)
MAPS = ["Crimson", "Crimson-Audio", "Crimson-VFX", "DangerZone", "DNZ-Complete", "DNZ-Name", "DNZ-Preview", "DNZ-SharedAudio",
        "DNZ-Thumbnail", "ExtraStages", "RandomStages"]
MODULES = ["DOA5LR-%s.asi" % m for m in MAPS]
INIS = ["DOA5LR-%s.ini" % m for m in ["Crimson-Audio", "Crimson-VFX", "DangerZone", "DNZ-Complete", "DNZ-SharedAudio", "ExtraStages", "RandomStages"]]
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def ok(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        if os.path.exists(LOG): print(open(LOG, encoding="utf-8", errors="replace").read()[-3000:])
        sys.exit(1)
def ex(rel): return os.path.exists(os.path.join(GAME, rel))
def rd(rel): return open(os.path.join(GAME, rel), "rb").read()
def put(rel, data):
    p = os.path.join(GAME, rel); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(data)

SRC = open(os.path.join(HERE, "..", "Installer.cs"), encoding="utf-8").read()
def globs(name):
    line = re.search(r"public static readonly Component " + name + r" = new Component \{.*?Globs = new\[\] \{(.*?)\} \};", SRC).group(1)
    return re.findall(r'@"([^"]*)"', line)
MAPS_GLOBS = globs("Maps")
ok(MAPS_GLOBS[:18] == ["scripts" + bs + "DOA5LR-Stages" + bs + n for n in MODULES + INIS], "Installer.cs: the v7 component starts with the 18 files of the new folder")

CORE = {"dinput8.dll": b"loader", "dinput8Hooked.dll": b"autolink", "DInput8.ini": b"[PATCH]\r\n", "dinput8ex.bin": b"xidi", "Xidi.32.dll": b"xidi32",
        "DOA5LR-Salons-VERSION.txt": b"0.3.16\n", "scripts/DOA5LR-Lobby.asi": b"lobby", "scripts/DOA5LR-InviteFix.asi": b"inv",
        "scripts/DOA5LR-WiFi-Wired-Detector.asi": b"wifi", "scripts/DOA5LR-UpdateCheck.asi": b"upd", "scripts/DOA5LR-JoinFix.asi": b"join",
        "scripts/DOA5LR-Borderless.asi": b"border", "scripts/DOA5LR-60fps-menus.asi": b"fps",
        "CodexCrimson/CRIMSON1.TMC": b"model", "DOA5LR-DebugArchive.asi": b"new-debug", "scripts/MAPS-DZ-CRIMSON-EN.txt": b"doc"}
for n in MODULES: CORE["scripts/DOA5LR-Stages/" + n] = ("new-" + n).encode()
for n in INIS: CORE["scripts/DOA5LR-Stages/" + n] = ("[default]\r\n" + n).encode()
ZIP = os.path.join(T, "DOA5LR-Salons-0.3.16.zip")
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for rel, data in CORE.items(): z.writestr(rel, data)
LABEL = "Maps: Danger Zone + The Crimson 1 and 2 (PS4 stages, offline Random; everyone in a room needs them)"
OPT = "optional_v7=maps|" + LABEL + "|" + ";".join(MAPS_GLOBS)
OPT_V5 = "optional_v5=maps|" + LABEL + "|" + ";".join(globs("MapsScripts"))  # read by installers 1.3.5-1.3.10
DELETES = ["delete=scripts" + bs + "DOA5LR-%s.asi" % m for m in MAPS] + ["delete=DOA5LR-DNZ-Menu.log", "delete=DOA5LR-DangerZone-crash.txt"]
MOVES = ["move=%s|scripts%sDOA5LR-Stages%s%s" % (n, bs, bs, n) for n in INIS]
VT = os.path.join(T, "version.txt")
def manifest(with_deletes=True):
    lines = ["version=0.3.16", "url=" + ZIP, "sha256=" + sha(ZIP), "size=%d" % os.path.getsize(ZIP), "notes=test", "keep=*.ini", OPT, OPT_V5] + MOVES
    open(VT, "w", newline="\n").write("\n".join(lines + (DELETES if with_deletes else [])) + "\n")
def run(*extra): return subprocess.run([EXE, "--auto", "--game", GAME, "--manifest", VT] + list(extra), timeout=180).returncode
def in_folder(): return [n for n in MODULES if ex("scripts/DOA5LR-Stages/" + n)]
def elsewhere(): return [p for n in MODULES for p in ("scripts/" + n, n) if ex(p)]
def root_stage_files(): return [f for f in os.listdir(GAME) if f.startswith("DOA5LR-") and f.endswith((".asi", ".ini", ".log"))
                                and any(k in f for k in ["Crimson", "DangerZone", "DNZ", "ExtraStages", "RandomStages", "DebugArchive"]) and f != "DOA5LR-DebugArchive.asi"]

def old_layout():
    put("game.exe", b"fake"); put("DOA5LR-Salons-VERSION.txt", b"0.3.15\n")
    for rel, data in CORE.items():
        if not rel.startswith("scripts/DOA5LR-Stages/"): put(rel, data)
    for m in MAPS: put("scripts/DOA5LR-%s.asi" % m, ("old-" + m).encode())
    put("DOA5LR-DebugArchive.asi", b"old-debug")
    for n in INIS: put(n, ("[personal]\r\n" + n).encode())
    put("DOA5LR-DNZ-Menu.log", b"orphan"); put("DOA5LR-DangerZone-crash.txt", b"orphan")

print("1. 0.3.15 layout -> 0.3.16 (production-like manifest: optional_v7 + optional_v5, move=, delete=)")
old_layout(); manifest()
ok(run("--components", "maps=1") == 0, "installer --auto OK")
ok(in_folder() == MODULES, "11 modules in scripts\\DOA5LR-Stages\\")
ok(elsewhere() == [], "no stage module left in scripts\\ or next to game.exe (no double load)")
ok(all(rd("scripts/DOA5LR-Stages/" + n) == ("new-" + n).encode() for n in MODULES), "new module contents")
ok(all(rd("scripts/DOA5LR-Stages/" + n) == ("[personal]\r\n" + n).encode() for n in INIS), "the player's 7 .ini moved into the folder and kept")
ok(root_stage_files() == [], "no stage .asi/.ini/.log left in the game folder (found: %s)" % root_stage_files())
ok(not ex("DOA5LR-DangerZone-crash.txt"), "orphan files removed")
ok(rd("DOA5LR-DebugArchive.asi") == b"new-debug" and not ex("scripts/DOA5LR-Stages/DOA5LR-DebugArchive.asi"), "DebugArchive updated next to game.exe")
ok(ex("scripts/DOA5LR-Lobby.asi") and ex("dinput8.dll"), "salon modules and loader untouched")
bk = sorted(glob.glob(os.path.join(GAME, "DOA5LR-Salons-Backups", "*")))[-1]
ok(all(os.path.exists(os.path.join(bk, "scripts", "DOA5LR-%s.asi" % m)) for m in MAPS) and os.path.exists(os.path.join(bk, "DOA5LR-DebugArchive.asi")),
   "old modules backed up")

print("2. second update: settings stay, nothing moves twice")
ok(run() == 0 and all(rd("scripts/DOA5LR-Stages/" + n) == ("[personal]\r\n" + n).encode() for n in INIS), "settings unchanged")

print("3. 1.3.11 duplicate guard (manifest WITHOUT delete= lines)")
for m in MAPS: put("scripts/DOA5LR-%s.asi" % m, b"old")
manifest(with_deletes=False)
ok(run() == 0, "installer --auto OK")
ok(elsewhere() == [] and in_folder() == MODULES, "duplicates in scripts\\ and next to game.exe removed by 1.3.11 itself")

print("4. maps left out: every module copy goes, settings kept")
for m in MAPS[:3]: put("scripts/DOA5LR-%s.asi" % m, b"old")
manifest()
ok(run("--components", "maps=0") == 0, "installer --auto OK")
ok(in_folder() == [] and elsewhere() == [], "no stage module anywhere")
ok(all(ex("scripts/DOA5LR-Stages/" + n) for n in INIS), "settings kept")

print("5. maps ticked again")
ok(run("--components", "maps=1") == 0 and in_folder() == MODULES and elsewhere() == [], "11 modules back, only in the new folder")
ok(all(rd("scripts/DOA5LR-Stages/" + n) == ("[personal]\r\n" + n).encode() for n in INIS), "settings still the player's")
print("ALL STAGES FOLDER TESTS PASSED")
