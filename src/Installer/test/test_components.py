# Test headless des composants optionnels (installateur 1.1.0) : faux jeu + faux pack (layout scripts\) + version.txt local.
# python test_components.py   (PYTHONUTF8=1)
import os, sys, shutil, zipfile, hashlib, subprocess, tempfile
EXE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "DOA5LR-Salons-Installer.exe")
T = tempfile.mkdtemp(prefix="doa5lr-inst-test-")
GAME = os.path.join(T, "game"); os.makedirs(GAME)
open(os.path.join(GAME, "game.exe"), "wb").write(b"fake")

def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
def ok(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond: print(open(LOG, encoding="utf-8", errors="replace").read()[-2500:]); sys.exit(1)
def ex(rel): return os.path.exists(os.path.join(GAME, rel))

FILES = {"dinput8.dll": b"loader", "dinput8Hooked.dll": b"autolink", "DInput8.ini": b"[PATCH]\r\n", "dinput8ex.bin": b"xidi", "Xidi.32.dll": b"xidi32",
         "DOA5LR-Salons-VERSION.txt": b"0.3.8\n", "READ-ME-FIRST-EN.txt": b"readme", "AutoLink/NAME.txt": b"x",
         "scripts/DOA5LR-Lobby.asi": b"lobby", "scripts/DOA5LR-InviteFix.asi": b"inv", "scripts/DOA5LR-WiFi-Wired-Detector.asi": b"wifi", "scripts/DOA5LR-WiFi-Wired-Detector.ini": b"[NetBoost]\r\nLinkOverride=0\r\n",
         "scripts/DOA5LR-UpdateCheck.asi": b"upd", "scripts/DOA5LR-UpdateCheck.ini": b"[UpdateCheck]\r\nVersionUrl=\r\n",
         "scripts/DOA5LR-Borderless.asi": b"border", "scripts/DOA5LR-Borderless.ini": b"[Borderless]\r\nMode=2\r\n", "scripts/BORDERLESS-EN.txt": b"doc", "scripts/Borderless-Source/borderless.c": b"src", "scripts/Borderless-Source/build.cmd": b"src",
         "scripts/DOA5LR-60fps-menus.asi": b"fps", "scripts/DOA5LR-60fps-menus.ini": b"[Menus]\r\nEnabled=1\r\n", "scripts/60FPS-EN.txt": b"doc", "scripts/60fps-Source/fps60_menus.c": b"src",
         "scripts/LOBBY-EN.txt": b"doc"}
P = os.path.join(T, "pack")
for rel, data in FILES.items():
    p = os.path.join(P, rel); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "wb").write(data)
ZIP = os.path.join(T, "DOA5LR-Salons-0.3.8.zip")
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for rel in FILES: z.write(os.path.join(P, rel), rel)
OPT = ["optional=borderless|Borderless fullscreen window (F11 in game; display mode below)|scripts\\DOA5LR-Borderless.asi;scripts\\DOA5LR-Borderless.ini;scripts\\BORDERLESS-EN.txt;scripts\\Borderless-Source\\*",
       "optional=60fps|60 fps menus, intros, win poses and Story cutscenes (offline only)|scripts\\DOA5LR-60fps-menus.asi;scripts\\DOA5LR-60fps-menus.ini;scripts\\60FPS-EN.txt;scripts\\60fps-Source\\*"]
VT = os.path.join(T, "version.txt")
open(VT, "w", newline="\n").write("\n".join(["version=0.3.8", "url=" + ZIP, "sha256=" + sha(ZIP), "size=%d" % os.path.getsize(ZIP), "notes=test", "keep=*.ini"] + OPT) + "\n")
LOG = os.path.join(GAME, "DOA5LR-Salons-Installer.log")
COMP = os.path.join(GAME, "DOA5LR-Salons-Components.txt")

def run(*extra):
    r = subprocess.run([EXE, "--auto", "--game", GAME, "--manifest", VT] + list(extra))
    return r.returncode
def comp(): return dict(l.strip().split("=") for l in open(COMP) if "=" in l and not l.startswith("#"))

print("0. nouvelle installation : Borderless desactive par defaut")
open(os.path.join(GAME, "DInput8.ini"), "wb").write(b"personal settings")
ok(run() == 0, "installateur --auto OK")
ok(open(os.path.join(GAME, "DInput8.ini"), "rb").read() == b"personal settings", "reglages existants preserves meme sans ancien pack")
ok(not ex("scripts/DOA5LR-Borderless.asi"), "Borderless absent par defaut")
ok(comp() == {"borderless": "0", "60fps": "1"}, "choix initial memorise")
ok(run() == 0 and not ex("scripts/DOA5LR-Borderless.asi"), "choix conserve lors de la mise a jour")
os.remove(COMP)
ok(run() == 0 and ex("scripts/DOA5LR-Borderless.asi"), "ancien pack sans choix : Borderless conserve")

print("1. installation avec 60fps decoche et Borderless choisi")
ok(run("--components", "60fps=0,borderless=1") == 0, "installateur --auto OK")
ok(ex("scripts/DOA5LR-Borderless.asi") and ex("scripts/Borderless-Source/borderless.c"), "Borderless installe")
ok(not ex("scripts/DOA5LR-60fps-menus.asi") and ex("scripts/DOA5LR-60fps-menus.ini") and not ex("scripts/60FPS-EN.txt") and not ex("scripts/60fps-Source"), "60fps retire, ini conserve")
ok(ex("scripts/DOA5LR-WiFi-Wired-Detector.asi") and ex("scripts/DOA5LR-Lobby.asi") and ex("scripts/DOA5LR-InviteFix.asi") and ex("scripts/DOA5LR-UpdateCheck.asi"), "obligatoires presents (WiFi-Wired, Lobby, InviteFix, UpdateCheck)")
ok(comp() == {"borderless": "1", "60fps": "0"}, "Components.txt = " + str(comp()))
ok("components: left out: 60fps" in open(LOG, encoding="utf-8").read(), "journal : composants")

print("2. mise a jour sans --components : le choix est relu")
ok(run() == 0, "installateur --auto OK")
ok(not ex("scripts/DOA5LR-60fps-menus.asi") and ex("scripts/DOA5LR-Borderless.asi"), "60fps toujours absent, Borderless toujours la")
ok(comp() == {"borderless": "1", "60fps": "0"}, "Components.txt inchange")

print("3. on recoche 60fps, on decoche Borderless (ini perso a garder)")
open(os.path.join(GAME, "scripts", "DOA5LR-Borderless.ini"), "wb").write(b"[Borderless]\r\nMode=1\r\n")
ok(run("--components", "60fps=1,borderless=0") == 0, "installateur --auto OK")
ok(ex("scripts/DOA5LR-60fps-menus.asi") and ex("scripts/DOA5LR-60fps-menus.ini") and ex("scripts/60fps-Source/fps60_menus.c"), "60fps installe")
ok(not ex("scripts/DOA5LR-Borderless.asi") and not ex("scripts/BORDERLESS-EN.txt") and not ex("scripts/Borderless-Source"), "Borderless retire (asi, notice, dossier sources)")
ok(ex("scripts/DOA5LR-Borderless.ini") and open(os.path.join(GAME, "scripts", "DOA5LR-Borderless.ini"), "rb").read() == b"[Borderless]\r\nMode=1\r\n", "Borderless.ini perso conserve")
ok(comp() == {"borderless": "0", "60fps": "1"}, "Components.txt = " + str(comp()))
bk = sorted(os.listdir(os.path.join(GAME, "DOA5LR-Salons-Backups")))[-1]
ok(os.path.exists(os.path.join(GAME, "DOA5LR-Salons-Backups", bk, "scripts", "DOA5LR-Borderless.asi")), "Borderless.asi sauvegarde avant retrait (" + bk + ")")

print("4. tout recoche")
ok(run("--components", "60fps=1,borderless=1") == 0, "installateur --auto OK")
ok(ex("scripts/DOA5LR-Borderless.asi") and ex("scripts/DOA5LR-60fps-menus.asi") and ex("scripts/Borderless-Source/borderless.c"), "tout installe")
ok(open(os.path.join(GAME, "scripts", "DOA5LR-Borderless.ini"), "rb").read() == b"[Borderless]\r\nMode=1\r\n", "Borderless.ini perso toujours conserve (keep=*.ini)")
ok(comp() == {"borderless": "1", "60fps": "1"}, "Components.txt = " + str(comp()))

print("5. manifeste sans optional= : liste par defaut de l'installateur")
open(VT, "w", newline="\n").write("\n".join(["version=0.3.8", "url=" + ZIP, "sha256=" + sha(ZIP), "size=%d" % os.path.getsize(ZIP), "notes=test", "keep=*.ini"]) + "\n")
ok(run("--components", "borderless=0") == 0, "installateur --auto OK")
ok(not ex("scripts/DOA5LR-Borderless.asi") and ex("scripts/DOA5LR-60fps-menus.asi"), "Borderless retire via la liste par defaut")

print("\nTOUT OK —", GAME)
print("6. un manifeste ne peut pas rendre le detecteur optionnel")
baseline = open(VT).read()
for optional in ["optional=wifi|WiFi|scripts\\DOA5LR-WiFi-Wired-Detector.asi", "optional=borderless|Bad|scripts\\*"]:
    open(VT, "w").write(baseline + optional + "\n")
    ok(run("--components", "wifi=0,borderless=0") != 0, "manifeste optionnel dangereux refuse")
    ok(ex("scripts/DOA5LR-WiFi-Wired-Detector.asi"), "detecteur obligatoire intact")
open(VT, "w").write(baseline + "delete=../outside.txt\n")
outside = os.path.join(T, "outside.txt")
open(outside, "w").write("untouched")
ok(run() != 0 and open(outside).read() == "untouched", "suppression hors du jeu refusee")
print("ALL COMPONENT TESTS PASSED")
