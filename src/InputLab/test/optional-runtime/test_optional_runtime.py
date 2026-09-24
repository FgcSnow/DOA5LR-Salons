"""Exercise Controls in fake games. Launch callbacks never call Steam or game.exe."""
from pathlib import Path
import base64
from datetime import datetime
import hashlib
import os
import shutil
import zipfile
import subprocess

lab = Path(__file__).resolve().parents[2]
run = Path(__file__).resolve().parent / ("run-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
run.mkdir()
csc = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework/v4.0.30319/csc.exe"
original = run / "Xidi-original.bin"
with zipfile.ZipFile(os.environ["DOA5LR_BASE_ZIP"]) as base:
    original.write_bytes(base.read("dinput8ex.bin"))
assert hashlib.sha256(original.read_bytes()).hexdigest() == "7f2a1c7616515153d899b726c8ecf72d5fa81c27a9d14b5c394cdd2e09f325c5"
source = lab / "source/InputLab.cs"
components = "DOA5LR-Salons-Components.txt"
tracked = ["dinput8ex.bin", "DInput8.ini", "Xidi.ini", "DOA5LR-InputBridge.ini", "DOA5LR-InputBridge-Xidi.dll", "DOA5LR-ControllerProfiles.ini", "DOA5LR-Companion.exe", components, "InputLab/previous-settings.txt"]

harness = run / "Harness.cs"
harness.write_text(r'''using System;
using System.Reflection;
using System.Windows.Forms;
static class RuntimeHarness {
    static object Call(InputLab form,string name,params object[] args) { return typeof(InputLab).GetMethod(name,BindingFlags.Instance|BindingFlags.NonPublic).Invoke(form,args); }
    [STAThread] static int Main(string[] args) {
        try { using(var form=new InputLab()) {
            var mode=(ComboBox)typeof(InputLab).GetField("mode",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(form);
            if(args[0]=="saved-mode") { Console.WriteLine(mode.SelectedIndex); return 0; }
            mode.SelectedIndex=args[1]=="keyboard"?1:args[1]=="hybrid"?0:2;
            if(args[0]=="apply") Call(form,"Install");
            else if(args[0]=="restore") Call(form,"Restore");
            else { int launches=0; Action launch=delegate { ++launches; if(args[0]=="launch-fail")throw new InvalidOperationException("Simulated launch failure"); };
                Call(form,"PrepareAndRun",launch); if(launches!=1)throw new Exception("Expected exactly one launch callback"); }
        } Console.WriteLine("OK"); return 0;
        } catch(Exception e) { Console.WriteLine((e.InnerException??e).Message); return 1; }
    }
}''')
exe = run / "Check.exe"
subprocess.run([str(csc), "/nologo", "/target:exe", "/platform:x86", "/main:RuntimeHarness", "/r:System.Windows.Forms.dll", "/r:System.Drawing.dll", "/out:" + str(exe), str(source), str(harness)], check=True)
inventory_source = run / "Inventory.cs"
inventory_source.write_text('using System;using System.IO;static class Inventory{static void Main(){Console.Write(File.ReadAllText(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"inventory-output.txt")));}}')
inventory = run / "Inventory.exe"
subprocess.run([str(csc), "/nologo", "/target:exe", "/platform:x86", "/out:" + str(inventory), str(inventory_source)], check=True)

# Compile the actual installer's snapshot class, rather than reproducing its reader.
installer_source = (lab.parent / "Installer/Installer.cs").read_text(encoding="utf-8-sig")
snapshot_class = installer_source.split("static class InputLabSettings", 1)[1].split("// ---------------------------------------------------------------- install / restore engine", 1)[0]
compat_source = run / "InstallerSnapshot.cs"
compat_source.write_text('using System;using System.IO;using System.Text;using System.Linq;using System.Collections.Generic;using System.Runtime.InteropServices;\nstatic class InputLabSettings' + snapshot_class + '\nstatic class SnapshotHarness{static void Main(string[] args){InputLabSettings.VerifyExisting(args[0]);if(args.Length>1)InputLabSettings.Deactivate(args[0]);Console.WriteLine("Snapshot compatible");}}')
compat = run / "SnapshotCheck.exe"
subprocess.run([str(csc), "/nologo", "/target:exe", "/out:" + str(compat), str(compat_source)], check=True)

def fixture(name, pack=True, missing_xidi=False, missing_key=False):
    game = run / name
    app = game / "InputLab"
    (app / "payload").mkdir(parents=True)
    (game / "game.exe").write_bytes(b"Fake game, never executable")
    shutil.copy2(original, game / "dinput8ex.bin")
    (game / "DInput8.ini").write_bytes(b"[PATCH]\r\n" + (b"" if missing_key else b"KeyboardOnly=0\r\n") + b"[User]\r\nKeep=unchanged\r\n")
    if not missing_xidi:
        (game / "Xidi.ini").write_bytes(b"[Workarounds]\r\nActiveVirtualControllerMask=15\r\n[User]\r\nKeep=exact\r\n")
    (game / "DOA5LR-InputBridge.ini").write_bytes(b"[Input]\r\nMode=Hybrid\r\n[Keyboard]\r\n37=33\r\n")
    (game / components).write_bytes(b"# Keep my choices\r\nborderless=1\r\n60fps=0\r\n" + (b"inputlab=0\r\n" if pack else b""))
    for filename, data in [("payload/dinput8ex.bin",b"Fake bridge test payload"),("DOA5LR-ControllerProfiles.ini",b"[MyController]\nEnabled=1\n"),("DOA5LR-Companion.exe",b"Fake reader, never executable"),("Profil-clavier.ini",b"[Keyboard]\n37=37\n"),("inventory-output.txt",b"")]:
        (app / filename).write_bytes(data)
    shutil.copy2(exe, app / "Check.exe")
    shutil.copy2(inventory, app / "DOA5LR-Peripheriques.exe")
    return game, app

def state(game, include_profile=False):
    return {name:(game/name).read_bytes() if (game/name).is_file() else None for name in tracked + (["InputLab/Profil-clavier.ini"] if include_profile else [])}

def call(app, action, mode="keyboard", error=None):
    result = subprocess.run([str(app / "Check.exe"), action, mode], capture_output=True, text=True, timeout=20)
    assert result.returncode == (1 if error is not None else 0), result.stdout + result.stderr
    if error is not None: assert error in result.stdout, result.stdout
    return result.stdout.strip()

# Native OFF launch must leave all settings, profile and runtime untouched.
game, app = fixture("native-off")
before = state(game, True)
assert call(app,"saved-mode") == "2"
call(app,"launch","controller")
call(app,"apply","controller")
assert state(game, True) == before
assert not (app / "Sauvegarde-avant-prototype").exists()
print("PASS OFF/native Controller launch and Enable leave runtime and every INI unchanged")

# Guard runs before activation; profile also remains byte-for-byte unchanged.
(app / "inventory-output.txt").write_text("DualSense Edge\tVID_054C&PID_0DF2\n")
call(app,"launch","keyboard","still connected")
call(app,"apply","keyboard","still connected")
assert state(game, True) == before
print("PASS connected controller blocks Keyboard before any activation or profile changes")

# Snapshot semantics must match the actual installer, including absent files and keys.
for name, missing_xidi, missing_key in [("standard",False,False),("missing-values",True,True)]:
    game, app = fixture(name,missing_xidi=missing_xidi,missing_key=missing_key)
    before = state(game)
    call(app,"launch","keyboard")
    assert (game / "dinput8ex.bin").read_bytes() == (app / "payload/dinput8ex.bin").read_bytes()
    assert "inputlab=1" in (game/components).read_text()
    assert "60fps=0" in (game/components).read_text()
    assert "37=33" in (game/"DOA5LR-InputBridge.ini").read_text()
    assert "KeyboardOnly=0" in (game/"DInput8.ini").read_text()
    snapshot = dict(line.split("=",1) for line in (app/"previous-settings.txt").read_text(encoding="utf-8-sig").splitlines()[1:])
    assert snapshot["KeyboardOnly"] == ("-" if missing_key else base64.b64encode(b"0").decode())
    assert snapshot["XidiFileExisted"] == ("0" if missing_xidi else "1")
    assert snapshot["ActiveVirtualControllerMask"] == ("-" if missing_xidi else base64.b64encode(b"15").decode())
    subprocess.run([str(compat),str(game),"deactivate"],check=True,capture_output=True)
    if missing_xidi: assert not (game/"Xidi.ini").exists()
    else: assert "ActiveVirtualControllerMask=15" in (game/"Xidi.ini").read_text()
    call(app,"restore")
    assert state(game) == before
    assert call(app,"saved-mode") == "2"
    assert list(app.glob("Sauvegarde-avant-prototype-restored-*"))
    print("PASS",name,"activation, installer-compatible snapshot and exact restore")

# Hybrid has the established priority; failed launch rolls back activation too.
game, app = fixture("failed-launch")
before = state(game,True)
call(app,"launch-fail","hybrid","Simulated launch failure")
assert state(game,True) == before
assert list(app.glob("Sauvegarde-avant-prototype-activation-rolled-back-*"))
call(app,"apply","hybrid")
assert "KeyboardOnly=1" in (game/"DInput8.ini").read_text()
assert "Mode=Hybrid" in (game/"DOA5LR-InputBridge.ini").read_text()
on_state = state(game,True)
call(app,"launch-fail","controller","Simulated launch failure")
assert state(game,True) == on_state
call(app,"restore")
assert state(game) == {k:v for k,v in before.items() if k != "InputLab/Profil-clavier.ini"}
print("PASS failed first launch restores every changed file; failed active mode change restores previous mode")

# Simulate a write failure after the settings snapshot and Xidi preservation.
game, app = fixture("failed-file-copy")
(game/"DOA5LR-Companion.exe").mkdir()
before = state(game,True)
call(app,"apply","hybrid",error="")
assert state(game,True) == before
assert list(app.glob("Sauvegarde-avant-prototype-activation-rolled-back-*"))
print("PASS failed activation file copy rolls back marker, component choice and runtime")

# Installer disable restores original Xidi and component0, and removes its marker.
game, app = fixture("reenable")
before = state(game)
call(app,"apply","hybrid")
subprocess.run([str(compat),str(game),"deactivate"],check=True,capture_output=True)
shutil.copy2(original,game/"dinput8ex.bin")
(game/components).write_bytes(before[components])
(app/"previous-settings.txt").unlink(missing_ok=True)
old_backup={str(p.relative_to(app/"Sauvegarde-avant-prototype")):p.read_bytes() for p in (app/"Sauvegarde-avant-prototype").rglob("*") if p.is_file()}
call(app,"restore")  # Already OFF: does not restore an obsolete snapshot.
call(app,"apply","keyboard")
archives=list(app.glob("Sauvegarde-avant-prototype-before-reactivation-*"))
assert len(archives)==1
assert {str(p.relative_to(archives[0])):p.read_bytes() for p in archives[0].rglob("*") if p.is_file()} == old_backup
assert (app/"previous-settings.txt").exists()
print("PASS installer OFF then app ON archives old backup intact and creates a fresh compatible backup")

# Legacy0.3.8 has no component key: its original seven-file backup remains restorable.
game, app = fixture("standalone-038",pack=False)
before = state(game)
call(app,"apply","keyboard")
backup=app/"Sauvegarde-avant-prototype"
assert not (backup/"pack-managed-v1").exists()
assert not (app/"previous-settings.txt").exists()
assert (game/components).read_bytes() == before[components]
call(app,"restore")
assert state(game)==before
print("PASS legacy seven-file backup and no-inputlab-key standalone semantics preserved")
print("All tests passed; no Steam or game launch occurred. Artifacts:",run)
