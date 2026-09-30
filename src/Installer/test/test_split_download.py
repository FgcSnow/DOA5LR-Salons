# Installer 1.3.4 headless test: split download (core= / data=) on a fake game with a fake pack. Never the real game.
#   python test_split_download.py
# a. fresh install, Maps on -> core + stage data merged, installed, temporary merged ZIP removed
# b. data already installed and intact -> core only (the data archive is not even present)
# c. one data file altered -> data downloaded again and the file repaired
# d. Maps unticked -> no data download, data removed; ticked again -> downloaded
# e. data archive corrupted (SHA-256 mismatch) -> refused, game unchanged
# f. manifest without core=/data= -> the full ZIP as before
import hashlib, json, os, shutil, subprocess, sys, tempfile, zipfile
EXE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "DOA5LR-Salons-Installer.exe")
T = tempfile.mkdtemp(prefix="doa5lr-split-test-")
GAME = os.path.join(T, "game"); os.makedirs(GAME)
open(os.path.join(GAME, "game.exe"), "wb").write(b"fake")
LOG = os.path.join(GAME, "DOA5LR-Salons-Installer.log")
CACHE = os.path.join(tempfile.gettempdir(), "DOA5LR-Salons")
def sha(b): return hashlib.sha256(b).hexdigest()
def ok(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        if os.path.exists(LOG): print(open(LOG, encoding="utf-8", errors="replace").read()[-3000:])
        sys.exit(1)
def log(): return open(LOG, encoding="utf-8", errors="replace").read() if os.path.exists(LOG) else ""

MAPS_GLOBS = ("DOA5LR-Crimson.asi;DOA5LR-Crimson-Audio.asi;DOA5LR-Crimson-Audio.ini;DOA5LR-Crimson-BackendProbe.asi;"
              "DOA5LR-Crimson-EventLog.asi;DOA5LR-Crimson-VFX.asi;DOA5LR-Crimson-VFX.ini;DOA5LR-DangerZone.asi;DOA5LR-DangerZone.ini;"
              "DOA5LR-DebugArchive.asi;DOA5LR-DNZ-Complete.asi;DOA5LR-DNZ-Complete.ini;DOA5LR-DNZ-Name.asi;DOA5LR-DNZ-Preview.asi;"
              "DOA5LR-DNZ-SharedAudio.asi;DOA5LR-DNZ-SharedAudio.ini;DOA5LR-DNZ-Thumbnail.asi;DOA5LR-ExtraStages.asi;"
              "DOA5LR-ExtraStages.ini;DOA5LR-RandomStages.asi;DOA5LR-RandomStages.ini;CodexCrimson\\*;CodexDangerZone\\*;"
              "PS4Stages\\*;scripts\\MAPS-DZ-CRIMSON-EN.txt")
DATA = {"CodexCrimson/CRIMSON1.TMC": os.urandom(300000), "CodexCrimson/CRIMSON2.TMCL": os.urandom(200000),
        "CodexDangerZone/DANGER_ZONE.TMC": b"dz" * 50000, "PS4Stages/MENU/STAGESELECT31.LAY": b"lay" * 100}
CORE = {"DOA5LR-Salons-VERSION.txt": b"0.3.14\r\n", "dinput8.dll": b"loader", "dinput8Hooked.dll": b"autolink", "DInput8.ini": b"[PATCH]\r\n",
        "dinput8ex.bin": b"xidi", "Xidi.32.dll": b"x", "scripts/DOA5LR-Lobby.asi": b"l", "scripts/DOA5LR-InviteFix.asi": b"i",
        "scripts/DOA5LR-WiFi-Wired-Detector.asi": b"w", "scripts/DOA5LR-UpdateCheck.asi": b"u", "scripts/DOA5LR-JoinFix.asi": b"j",
        "scripts/DOA5LR-60fps-menus.asi": b"f", "DOA5LR-Crimson.asi": b"crimson", "DOA5LR-DangerZone.asi": b"dz",
        "DOA5LR-ExtraStages.asi": b"es", "DOA5LR-RandomStages.asi": b"rs", "scripts/MAPS-DZ-CRIMSON-EN.txt": b"guide"}
maps_list = [{"path": n, "sha256": sha(b), "size": len(b)} for n, b in list(DATA.items()) + [(k, CORE[k]) for k in ("DOA5LR-Crimson.asi", "DOA5LR-DangerZone.asi", "DOA5LR-ExtraStages.asi", "DOA5LR-RandomStages.asi")]]
CORE["DOA5LR-Diagnostic/maps-files.json"] = json.dumps(maps_list, indent=2).encode()
def mkzip(path, files):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in files.items(): z.writestr(n, b)
    return open(path, "rb").read()
P = os.path.join(T, "pack"); os.makedirs(P)
FULL, COREZ, DATAZ = (os.path.join(P, n) for n in ("full.zip", "core.zip", "data.zip"))
fb, cb, db = mkzip(FULL, {**CORE, **DATA}), mkzip(COREZ, CORE), mkzip(DATAZ, DATA)
DATA_BYTES = db
BASE = ["version=0.3.14", "url=" + FULL, "sha256=" + sha(fb), "size=%d" % len(fb), "notes=test", "keep=*.ini",
        r"optional=borderless|B|scripts\DOA5LR-Borderless.asi;scripts\DOA5LR-Borderless.ini;scripts\BORDERLESS-EN.txt;scripts\Borderless-Source\*",
        r"optional=60fps|F|scripts\DOA5LR-60fps-menus.asi;scripts\DOA5LR-60fps-menus.ini;scripts\60FPS-EN.txt;scripts\60fps-Source\*",
        "optional_v4=maps|Maps|" + MAPS_GLOBS]
SPLIT = BASE + ["core=%s|%s|%d" % (COREZ, sha(cb), len(cb)), "data=maps|%s|%s|%d" % (DATAZ, sha(db), len(db))]
VS, VF = os.path.join(T, "split.txt"), os.path.join(T, "full.txt")
open(VS, "w", newline="\n").write("\n".join(SPLIT) + "\n"); open(VF, "w", newline="\n").write("\n".join(BASE) + "\n")
def clear_cache():
    if os.path.isdir(CACHE):
        for f in os.listdir(CACHE):
            if f.startswith("DOA5LR-Salons-"): os.remove(os.path.join(CACHE, f))
def run(man, *extra):
    if os.path.exists(LOG): os.remove(LOG)
    return subprocess.run([EXE, "--auto", "--game", GAME, "--manifest", man] + list(extra)).returncode
def data_ok(): return all(os.path.isfile(os.path.join(GAME, n)) and open(os.path.join(GAME, n), "rb").read() == b for n, b in DATA.items())
def merged_left(): return os.path.isdir(CACHE) and any(f.endswith("-merged.zip") for f in os.listdir(CACHE))

print("a. fresh install with Maps: core + data")
clear_cache()
ok(run(VS) == 0, "installer --auto OK")
ok(data_ok() and open(os.path.join(GAME, "DOA5LR-Crimson.asi"), "rb").read() == b"crimson", "core files and stage data installed")
ok("stage data to download: 4 of 4" in log() and "merged" in log(), "log: data downloaded and merged")
ok(not merged_left(), "temporary merged ZIP removed")

print("b. data installed and intact: core only")
os.rename(DATAZ, DATAZ + ".away"); clear_cache()
ok(run(VS) == 0, "installer --auto OK without the data archive")
ok("stage data up to date (4 files checked): only the core pack downloaded" in log() and data_ok(), "core only, data untouched")
BK = os.path.join(GAME, "DOA5LR-Salons-Backups"); last = sorted(os.listdir(BK))[-1]
man = open(os.path.join(BK, last, "backup-manifest.txt"), encoding="utf-8").read()
ok("DOA5LR-Crimson.asi" in man and "Codex" not in man and "PS4Stages" not in man, "stage data not touched by this install (not in its backup)")
os.rename(DATAZ + ".away", DATAZ)

print("c. one data file altered: downloaded again and repaired")
open(os.path.join(GAME, "CodexCrimson", "CRIMSON2.TMCL"), "wb").write(b"truncated")
ok(run(VS) == 0 and data_ok(), "file repaired")
ok("stage data to download: 1 of 4 files missing or different (CodexCrimson\\CRIMSON2.TMCL)" in log(), "log names the bad file")

print("d. Maps unticked, then ticked")
ok(run(VS, "--components", "maps=0") == 0, "installer OK")
ok("maps left out: stage data not downloaded" in log() and not any(os.path.exists(os.path.join(GAME, n)) for n in DATA), "no data download, data removed")
ok(run(VS, "--components", "maps=1") == 0 and data_ok() and "stage data to download: 4 of 4" in log(), "ticked again: data downloaded")

print("e. corrupted data archive: refused, game unchanged")
os.remove(os.path.join(GAME, "PS4Stages", "MENU", "STAGESELECT31.LAY")); clear_cache()
bad = bytearray(DATA_BYTES); bad[len(bad) // 2] ^= 0xFF; open(DATAZ, "wb").write(bytes(bad))
before = open(os.path.join(GAME, "DOA5LR-Salons-VERSION.txt"), "rb").read()
ok(run(VS) != 0 and "SHA256 mismatch" in log(), "refused with SHA256 mismatch")
ok(open(os.path.join(GAME, "DOA5LR-Salons-VERSION.txt"), "rb").read() == before and not os.path.exists(os.path.join(GAME, "PS4Stages", "MENU", "STAGESELECT31.LAY")), "game unchanged")
open(DATAZ, "wb").write(DATA_BYTES); clear_cache()

print("f. manifest without core=/data=: full ZIP")
ok(run(VF) == 0 and data_ok() and "stage data" not in log(), "full pack installed as before")
print("ALL SPLIT DOWNLOAD TESTS PASSED")
