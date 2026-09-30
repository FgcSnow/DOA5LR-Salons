# Installer 1.3.4 headless test: ResolutionMod follows Borderless (DInput8.ini edited in place, UTF-16 kept) and
# delete_if removes only the exact old ui_mod d3d9.dll. Fake game + fake pack + local version.txt, never the real game.
#   python test_resolution_d3d9.py <real DInput8.ini of the pack> <old ui_mod d3d9.dll>
import os, sys, zipfile, hashlib, subprocess, tempfile
EXE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "DOA5LR-Salons-Installer.exe")
DINPUT, UIMOD = sys.argv[1], sys.argv[2]
UIMOD_SHA = "badac2aa7b4ca2d355cecdf36afad246f5e27891c86f7fa23dc42c1998ba4ee8"
T = tempfile.mkdtemp(prefix="doa5lr-res-test-")
GAME = os.path.join(T, "game"); os.makedirs(GAME)
open(os.path.join(GAME, "game.exe"), "wb").write(b"fake")
LOG = os.path.join(GAME, "DOA5LR-Salons-Installer.log")
def sha(b): return hashlib.sha256(b).hexdigest()
def ok(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        if os.path.exists(LOG): print(open(LOG, encoding="utf-8", errors="replace").read()[-2500:])
        sys.exit(1)
pack_ini = open(DINPUT, "rb").read()
assert sha(open(UIMOD, "rb").read()) == UIMOD_SHA
FILES = {"dinput8.dll": b"loader", "dinput8Hooked.dll": b"autolink", "DInput8.ini": pack_ini, "dinput8ex.bin": b"xidi", "Xidi.32.dll": b"x",
         "DOA5LR-Salons-VERSION.txt": b"0.3.14\r\n", "scripts/DOA5LR-Lobby.asi": b"l", "scripts/DOA5LR-InviteFix.asi": b"i",
         "scripts/DOA5LR-WiFi-Wired-Detector.asi": b"w", "scripts/DOA5LR-UpdateCheck.asi": b"u", "scripts/DOA5LR-JoinFix.asi": b"j",
         "scripts/DOA5LR-Borderless.asi": b"b", "scripts/DOA5LR-Borderless.ini": b"[Borderless]\r\nMode=2\r\n",
         "scripts/DOA5LR-60fps-menus.asi": b"f"}
ZIP = os.path.join(T, "DOA5LR-Salons-0.3.14.zip")
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for rel, data in FILES.items(): z.writestr(rel, data)
zb = open(ZIP, "rb").read()
OPT = [r"optional=borderless|Borderless fullscreen window (F11 in game; display mode below)|scripts\DOA5LR-Borderless.asi;scripts\DOA5LR-Borderless.ini;scripts\BORDERLESS-EN.txt;scripts\Borderless-Source\*",
       r"optional=60fps|60 fps menus, intros, win poses and Story cutscenes (offline only)|scripts\DOA5LR-60fps-menus.asi;scripts\DOA5LR-60fps-menus.ini;scripts\60FPS-EN.txt;scripts\60fps-Source\*"]
VT = os.path.join(T, "version.txt")
open(VT, "w", newline="\n").write("\n".join(["version=0.3.14", "url=" + ZIP, "sha256=" + sha(zb), "size=%d" % len(zb), "notes=test", "keep=*.ini",
    "delete_if=d3d9.dll|" + UIMOD_SHA, "delete_if=bad|nothex"] + OPT) + "\n")
def run(*extra): return subprocess.run([EXE, "--auto", "--game", GAME, "--manifest", VT] + list(extra)).returncode
D = os.path.join(GAME, "DInput8.ini")
def resmod():
    t = open(D, "rb").read()
    ok(t[:2] == b"\xff\xfe", "DInput8.ini keeps its UTF-16 BOM")
    s = t[2:].decode("utf-16-le"); patch = s[s.index("[PATCH]"):]
    return patch.split("ResolutionMod=", 1)[1][0], t
def diff_only_digit(a, b):
    d = [i for i in range(len(a)) if a[i] != b[i]]
    return len(a) == len(b) and len(d) == 1

print("1. fresh install, Borderless off by default -> ResolutionMod=0, only that digit changed")
ok(run() == 0, "installer --auto OK")
v, t = resmod(); ok(v == "0", "ResolutionMod=0"); ok(diff_only_digit(pack_ini, t), "file identical except the one digit")
print("2. Borderless ticked -> 1, then unticked -> 0")
ok(run("--components", "borderless=1") == 0, "installer OK"); v, t = resmod(); ok(v == "1" and t == pack_ini, "ResolutionMod=1, file = pack file")
ok(run("--components", "borderless=0") == 0, "installer OK"); v, _ = resmod(); ok(v == "0", "ResolutionMod=0")
def set_digit(d):
    t = open(D, "rb").read(); s2 = t[2:].decode("utf-16-le"); i = s2.index("[PATCH]"); j = s2.index("ResolutionMod=", i) + len("ResolutionMod=")
    open(D, "wb").write(t[:2] + (s2[:j] + d + s2[j + 1:]).encode("utf-16-le"))
print("2b. Borderless unchanged: a hand-set 0 stays 0 with Borderless on; a 1 goes to 0 with Borderless off")
ok(run("--components", "borderless=1") == 0, "installer OK"); v, _ = resmod(); ok(v == "1", "ticked again -> 1")
set_digit("0"); ok(run() == 0, "update, Borderless still on"); v, _ = resmod(); ok(v == "0", "player's ResolutionMod=0 kept")
set_digit("1"); ok(run() == 0, "update, Borderless still on"); v, _ = resmod(); ok(v == "1", "ResolutionMod=1 kept")
ok(run("--components", "borderless=0") == 0, "installer OK"); v, _ = resmod(); ok(v == "0", "unticked -> 0")
set_digit("1"); ok(run() == 0, "update, Borderless still off (0.3.13 player forced to desktop)"); v, _ = resmod(); ok(v == "0", "1 -> 0 without Borderless")
print("3. a player's own resolution is never touched")
s = open(D, "rb").read()[2:].decode("utf-16-le").replace("WindowResolution=desktop", "WindowResolution=1280x720")
s = s.replace("ResolutionMod=0\r\n\r\n; 解析度", "ResolutionMod=1\r\n\r\n; 解析度"); custom = b"\xff\xfe" + s.encode("utf-16-le")
open(D, "wb").write(custom)
ok(run() == 0 and open(D, "rb").read() == custom, "custom WindowResolution: file unchanged")
print("4. delete_if d3d9.dll: another mod's d3d9.dll stays, the old ui_mod goes")
open(D, "wb").write(pack_ini)
open(os.path.join(GAME, "d3d9.dll"), "wb").write(b"reshade or another d3d9 mod")
ok(run() == 0 and open(os.path.join(GAME, "d3d9.dll"), "rb").read() == b"reshade or another d3d9 mod", "foreign d3d9.dll kept")
ok("kept your d3d9.dll (not the old pack file)" in open(LOG, encoding="utf-8").read(), "log says it was kept")
open(os.path.join(GAME, "d3d9.dll"), "wb").write(open(UIMOD, "rb").read())
ok(run() == 0 and not os.path.exists(os.path.join(GAME, "d3d9.dll")), "old ui_mod d3d9.dll removed")
bk = [os.path.join(r, f) for r, _, fs in os.walk(os.path.join(GAME, "DOA5LR-Salons-Backups")) for f in fs if f == "d3d9.dll"]
ok(any(sha(open(p, "rb").read()) == UIMOD_SHA for p in bk), "removed ui_mod is in the backup")
print("ALL PASS")
