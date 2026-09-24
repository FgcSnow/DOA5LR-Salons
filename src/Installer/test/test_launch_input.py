"""Test input launch dispatch in a fake game folder without launching Steam/game/UI."""
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
CSC = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework/v4.0.30319/csc.exe"

with tempfile.TemporaryDirectory(prefix="doa5lr-input-launch-") as temp:
    temp = Path(temp)
    harness = temp / "launch-input-harness.exe"
    subprocess.run([
        str(CSC), "/nologo", "/target:exe", "/platform:x86", "/main:LaunchInputHarness",
        "/out:" + str(harness), "/r:System.IO.Compression.dll", "/r:System.IO.Compression.FileSystem.dll",
        str(HERE.parent / "Installer.cs"), str(HERE / "launch_input_harness.cs"),
    ], check=True)
    subprocess.run([str(harness), str(temp / "Steam library with spaces" / "Dead or Alive 5 Last Round")], check=True)
