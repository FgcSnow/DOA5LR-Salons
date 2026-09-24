"""Exercise the prelaunch controller check in a fake game folder; never launch Steam."""
from pathlib import Path
from datetime import datetime
import os
import subprocess

lab = Path(__file__).resolve().parents[1]
run = lab / "test" / ("keyboard-startup-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
game = run / "game"
app = game / "InputLab"
app.mkdir(parents=True)
(game / "game.exe").write_bytes(b"fake game, not executable")
(game / "DOA5LR-InputBridge.ini").write_text("[Input]\nMode=Keyboard\n[Keyboard]\n37=33\n")
csc = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework/v4.0.30319/csc.exe"
harness = run / "Harness.cs"
harness.write_text('''using System;
using System.Reflection;
static class KeyboardStartupHarness {
    [STAThread] static int Main() {
        try { using (var form = new InputLab()) {
            typeof(InputLab).GetMethod("CheckKeyboardStartup", BindingFlags.Instance | BindingFlags.NonPublic).Invoke(form, null);
        } Console.WriteLine("Keyboard startup check passed"); return 0;
        } catch(Exception e) { Console.WriteLine((e.InnerException ?? e).Message); return 1; }
    }
}''')
stub = run / "Inventory.cs"
stub.write_text('''using System; using System.IO;
static class Inventory {
    static int Main() {
        string value = File.ReadAllText(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "inventory-output.txt"));
        if(value == "FAIL") return 2;
        Console.Write(value); return 0;
    }
}''')
subprocess.run([str(csc), "/nologo", "/target:exe", "/platform:x86", "/main:KeyboardStartupHarness",
                "/r:System.Windows.Forms.dll", "/r:System.Drawing.dll", "/out:" + str(app / "Check.exe"),
                str(lab / "source/InputLab.cs"), str(harness)], check=True)
subprocess.run([str(csc), "/nologo", "/target:exe", "/platform:x86",
                "/out:" + str(app / "DOA5LR-Peripheriques.exe"), str(stub)], check=True)
before = (game / "DOA5LR-InputBridge.ini").read_bytes()
for output, expected_code, expected_text in [
    ("", 0, "check passed"),
    ("DualSense Edge\tVID_054C&PID_0DF2\t15 buttons\n", 1, "still connected"),
    ("FAIL", 1, "Unable to check"),
]:
    (app / "inventory-output.txt").write_text(output)
    result = subprocess.run([str(app / "Check.exe")], capture_output=True, text=True, timeout=15)
    assert result.returncode == expected_code and expected_text in result.stdout, result.stdout
    assert (game / "DOA5LR-InputBridge.ini").read_bytes() == before
    print("PASS:", expected_text)
print("No Steam or game launch was called. Settings were preserved.")
