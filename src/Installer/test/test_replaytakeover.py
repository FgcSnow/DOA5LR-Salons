# Headless test of the Replay Takeover component (installer 1.3.2, manifest key optional_v3): fake game + fake pack.
# python test_replaytakeover.py   (PYTHONUTF8=1). Optional: DOA5LR_131_SOURCE = Installer.cs of 1.3.1 (legacy parse check).
import os, sys, zipfile, hashlib, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
EXE = os.path.join(HERE, "..", "DOA5LR-Salons-Installer.exe")
T = tempfile.mkdtemp(prefix="doa5lr-takeover-test-")
GAME = os.path.join(T, "game"); os.makedirs(GAME)
open(os.path.join(GAME, "game.exe"), "wb").write(b"fake")
LOG = os.path.join(GAME, "DOA5LR-Salons-Installer.log")
COMP = os.path.join(GAME, "DOA5LR-Salons-Components.txt")

def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def ex(rel): return os.path.exists(os.path.join(GAME, rel))
def rd(rel): return open(os.path.join(GAME, rel), "rb").read()
def ok(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        if os.path.exists(LOG): print(open(LOG, encoding="utf-8", errors="replace").read()[-2500:])
        sys.exit(1)

FILES = {"dinput8.dll": b"loader", "DInput8.ini": b"[PATCH]\r\n", "DOA5LR-Salons-VERSION.txt": b"0.3.11\n",
         "scripts/DOA5LR-Lobby.asi": b"lobby", "scripts/DOA5LR-InviteFix.asi": b"inv", "scripts/DOA5LR-WiFi-Wired-Detector.asi": b"wifi",
         "scripts/DOA5LR-UpdateCheck.asi": b"upd", "scripts/DOA5LR-Borderless.asi": b"border", "scripts/DOA5LR-60fps-menus.asi": b"fps",
         "DOA5LR-ReplayTakeover.asi": b"takeover 2.5", "DOA5LR-ReplayTakeover.ini": b"[ReplayTakeover]\r\nEnabled=1\r\n",
         "scripts/REPLAY-TAKEOVER-EN.txt": b"doc", "scripts/ReplayTakeover-Source/ReplayTakeover.cpp": b"src"}
ZIP = os.path.join(T, "DOA5LR-Salons-0.3.11.zip")
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for rel, data in FILES.items(): z.writestr(rel, data)
OPT = [r"optional=borderless|Borderless|scripts\DOA5LR-Borderless.asi;scripts\DOA5LR-Borderless.ini;scripts\BORDERLESS-EN.txt;scripts\Borderless-Source\*",
       r"optional=60fps|60 fps|scripts\DOA5LR-60fps-menus.asi;scripts\DOA5LR-60fps-menus.ini;scripts\60FPS-EN.txt;scripts\60fps-Source\*",
       r"optional_v3=replaytakeover|Replay Takeover|DOA5LR-ReplayTakeover.asi;DOA5LR-ReplayTakeover.ini;scripts\REPLAY-TAKEOVER-EN.txt;scripts\ReplayTakeover-Source\*"]
VT = os.path.join(T, "version.txt")
MAN = "\n".join(["version=0.3.11", "url=" + ZIP, "sha256=" + sha(ZIP), "size=%d" % os.path.getsize(ZIP), "notes=test", "keep=*.ini"] + OPT) + "\n"
open(VT, "w", newline="\n").write(MAN)
def run(*extra): return subprocess.run([EXE, "--auto", "--game", GAME, "--manifest", VT] + list(extra)).returncode
def comp(): return dict(l.strip().split("=") for l in open(COMP) if "=" in l and not l.startswith("#"))

print("1. a Takeover installed by hand (1.0 settings) is replaced in place, its .ini kept")
open(os.path.join(GAME, "DOA5LR-ReplayTakeover.asi"), "wb").write(b"takeover 2.0.2 by hand")
open(os.path.join(GAME, "DOA5LR-ReplayTakeover.ini"), "wb").write(b"[ReplayTakeover]\r\nBoutonPrise=0x8000\r\n")
ok(run() == 0, "installer --auto OK")
ok(rd("DOA5LR-ReplayTakeover.asi") == b"takeover 2.5", "root .asi = pack version (no second copy in scripts)")
ok(not ex("scripts/DOA5LR-ReplayTakeover.asi"), "no copy in scripts (plugin never loaded twice)")
ok(rd("DOA5LR-ReplayTakeover.ini") == b"[ReplayTakeover]\r\nBoutonPrise=0x8000\r\n", "personal .ini kept")
ok(comp().get("replaytakeover") == "1", "on by default, choice written: " + str(comp()))

print("2. left out: plugin, notice and sources removed, .ini kept")
ok(run("--components", "replaytakeover=0") == 0, "installer --auto OK")
ok(not ex("DOA5LR-ReplayTakeover.asi") and not ex("scripts/REPLAY-TAKEOVER-EN.txt") and not ex("scripts/ReplayTakeover-Source"), "Takeover removed")
ok(ex("DOA5LR-ReplayTakeover.ini"), ".ini kept")
ok(ex("scripts/DOA5LR-Lobby.asi") and ex("scripts/DOA5LR-WiFi-Wired-Detector.asi"), "required plugins untouched")
ok(run() == 0 and not ex("DOA5LR-ReplayTakeover.asi"), "choice remembered on update")

print("3. checked again")
ok(run("--components", "replaytakeover=1") == 0 and rd("DOA5LR-ReplayTakeover.asi") == b"takeover 2.5" and ex("scripts/ReplayTakeover-Source/ReplayTakeover.cpp"), "Takeover back")

print("4. manifest cannot widen the component")
open(VT, "w", newline="\n").write(MAN.replace("DOA5LR-ReplayTakeover.asi;", r"scripts\DOA5LR-Lobby.asi;DOA5LR-ReplayTakeover.asi;"))
ok(run("--components", "replaytakeover=0") != 0 and ex("scripts/DOA5LR-Lobby.asi"), "altered optional_v3 refused, Lobby intact")
open(VT, "w", newline="\n").write(MAN)

src131 = os.environ.get("DOA5LR_131_SOURCE")
if src131:
    print("5. installer 1.3.1 ignores optional_v3 and still reaches its self-update")
    csc = os.path.join(os.environ["WINDIR"], r"Microsoft.NET\Framework\v4.0.30319\csc.exe")
    h = os.path.join(T, "H.cs"); exe = os.path.join(T, "H.exe")
    open(h, "w").write('using System;using System.IO;using System.Linq;static class H{static void Main(string[] a){var m=Manifest.Parse(File.ReadAllText(a[0])+"installer_version=1.3.2\\n");'
                       'if(Cfg.AppVersion!="1.3.1"||m.Version!="0.3.11"||Util.CmpVer(m.InstallerVersion,Cfg.AppVersion)<=0||Component.Current.Any(c=>c.Id=="replaytakeover"))throw new Exception("1.3.1");Console.WriteLine("  OK   1.3.1 parses the 0.3.11 manifest");}}')
    subprocess.run([csc, "/nologo", "/target:exe", "/platform:x86", "/main:H", "/out:" + exe, "/r:System.IO.Compression.dll", "/r:System.IO.Compression.FileSystem.dll", src131, h], check=True, stdout=subprocess.DEVNULL)
    ok(subprocess.run([exe, VT]).returncode == 0, "legacy parse")
print("ALL REPLAY TAKEOVER TESTS PASSED")
