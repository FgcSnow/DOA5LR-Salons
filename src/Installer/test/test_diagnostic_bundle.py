"""Isolated diagnostics allowlist/bounds/read-only checks. Never opens the real game."""
from pathlib import Path
import hashlib
import os
import subprocess
import tempfile
import zipfile

SOURCE = Path(__file__).resolve().parents[1] / "Installer.cs"
ROOT = Path(tempfile.mkdtemp(prefix="doa5lr-diagnostics-test-"))
HARNESS = ROOT / "Harness.cs"
HARNESS.write_text(r'''
using System;
using System.IO;
class Harness {
    static int Main(string[] args) {
        try {
            if (args.Length > 2 && args[2] == "shared") {
                using (var writer = new FileStream(Path.Combine(args[0], "DOA5LR-Lobby.log"), FileMode.Open, FileAccess.ReadWrite, FileShare.ReadWrite))
                    DiagnosticBundle.Export(args[0], args[1]);
            } else DiagnosticBundle.Export(args[0], args[1]);
            return 0;
        } catch(Exception e) { Console.WriteLine(e.Message); return 2; }
    }
}
''', encoding="utf-8")
EXE = ROOT / "Harness.exe"
CSC = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework/v4.0.30319/csc.exe"
subprocess.run([str(CSC), "/nologo", "/target:exe", "/platform:x86", "/main:Harness", "/out:" + str(EXE),
                "/r:System.IO.Compression.dll", "/r:System.IO.Compression.FileSystem.dll", str(SOURCE), str(HARNESS)], check=True)


def put(game, name, data):
    target = game / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data if isinstance(data, bytes) else data.encode("utf-8"))


def snapshot(game):
    return {str(p.relative_to(game)): (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
            for p in game.rglob("*") if p.is_file() and not p.is_symlink()}


def export(game, destination, shared=False, expected=0):
    before = snapshot(game)
    result = subprocess.run([str(EXE), str(game), str(destination)] + (["shared"] if shared else []), capture_output=True, text=True)
    assert result.returncode == expected, result.stdout + result.stderr
    assert snapshot(game) == before, "export mutated the game folder"


game = ROOT / "game"
game.mkdir()
put(game, "game.exe", b"fake game executable, must never be included")
put(game, "DOA5LR-Salons-VERSION.txt", "0.3.9-inputlab-draft\r\n")
put(game, "DOA5LR-Salons-Components.txt", "borderless=1\n60fps=0\ninputlab=0\nsecret=UNRELATED_COMPONENT_SECRET\n")
put(game, "DOA5LR-InputBridge.ini", "[Input]\nMode=Keyboard\nToken=INPUT_CONFIG_SECRET\n[Keyboard]\n17=999\n")
logs = ["DOA5LR-Lobby.log", "DOA5LR-Salons-Installer.log", "DOA5LR-InputBridge.log", "DOA5LR-InviteFix.log"]
for name in logs:
    put(game, name, "root log: " + name)
    put(game, "scripts/" + name, "script log: " + name)
known_binary = b"known module bytes"
put(game, "scripts/DOA5LR-Lobby.asi", known_binary)
put(game, "dinput8ex.bin", b"known input frontend")
put(game, "InputLab/DOA5LR-Commandes.exe", b"known controls frontend")
for name in ["steam/config/loginusers.vdf", "savedata/save.dat", "scripts/DOA5LR-Telemetry.log", "DOA5LR-Telemetry.log",
             "scripts/foreign.log", "scripts/foreign.asi", "memory.dmp", "InputLab/DOA5LR-Lobby.log", "nested/DOA5LR-Lobby.log"]:
    put(game, name, b"FOREIGN_SECRET_MUST_NOT_BE_COLLECTED")

archive = ROOT / "normal.zip"
export(game, archive, shared=True)
with zipfile.ZipFile(archive) as z:
    expected = {"README.txt", "report.txt"} | {"logs/" + prefix + name for prefix in ["", "scripts/"] for name in logs}
    assert set(z.namelist()) == expected
    assert all(".." not in name and not name.startswith(("/", "\\")) and ":" not in name for name in z.namelist())
    everything = b"\n".join(z.read(n) for n in z.namelist())
    for secret in [b"FOREIGN_SECRET", b"INPUT_CONFIG_SECRET", b"UNRELATED_COMPONENT_SECRET", known_binary, str(game).encode()]:
        assert secret not in everything, secret
    report = z.read("report.txt").decode()
    assert "Pack version: 0.3.9-inputlab-draft" in report
    assert "Component inputlab: 0" in report and "Saved input mode: Keyboard" in report
    assert hashlib.sha256(known_binary).hexdigest() in report
    assert "foreign.asi" not in report and "game.exe:" not in report
    readme = z.read("README.txt").decode()
    for word in ["Nothing was uploaded", "NOT anonymized", "Steam IDs", "IP addresses", "2 MiB", "review before sharing"]:
        assert word in readme, word
print("PASS: exact allowlist, filtered metadata, known hashes only, relative paths, shared reader, no game writes")

cap = 2 * 1024 * 1024
tail = (b"\xff\x00\xe2\x82\xac_tail_record_" * (cap // 17 + 1))[-cap:]
large = b"HEAD_SECRET_SHOULD_BE_CUT" + b"a" * 512 + tail
put(game, "DOA5LR-Lobby.log", large)
archive = ROOT / "bounded.zip"
export(game, archive)
with zipfile.ZipFile(archive) as z:
    data = z.read("logs/DOA5LR-Lobby.log")
    assert len(data) == cap and data == large[-cap:]
    assert b"HEAD_SECRET_SHOULD_BE_CUT" not in data
    assert "(tail only)" in z.read("report.txt").decode()
print("PASS: 2 MiB byte cap and exact tail for non-UTF log content")

empty = ROOT / "empty-game"
empty.mkdir()
put(empty, "game.exe", b"fake")
put(empty, "DOA5LR-Salons-VERSION.txt", "0.3.9\nPRIVATE_VERSION_EXTRA")
put(empty, "DOA5LR-Salons-Components.txt", "inputlab=SECRET_COMPONENT_VALUE\n")
put(empty, "DOA5LR-InputBridge.ini", "[Input]\nMode=SECRET_MODE_VALUE\n")
archive = ROOT / "missing.zip"
export(empty, archive)
with zipfile.ZipFile(archive) as z:
    assert set(z.namelist()) == {"README.txt", "report.txt"}
    report = z.read("report.txt").decode()
    assert "Pack version: missing or invalid" in report and "DOA5LR-Lobby.log: missing" in report
    assert "PRIVATE_" not in report and "SECRET_" not in report
print("PASS: missing logs and invalid metadata handled without including arbitrary values")

existing = ROOT / "existing.zip"
existing.write_bytes(b"do not overwrite")
export(empty, existing, expected=2)
assert existing.read_bytes() == b"do not overwrite"
export(empty, empty / "do-not-create.zip", expected=2)
assert not (empty / "do-not-create.zip").exists()
print("PASS: existing destination and output inside game refused")

outside = ROOT / "outside"
outside.mkdir()
put(outside, "DOA5LR-Lobby.log", b"EXTERNAL_LINK_SECRET")
linked_game = ROOT / "linked-game"
linked_game.mkdir()
put(linked_game, "game.exe", b"fake")
try:
    os.symlink(outside / "DOA5LR-Lobby.log", linked_game / "DOA5LR-Lobby.log")
    os.symlink(outside, linked_game / "scripts", target_is_directory=True)
except OSError as e:
    if getattr(e, "winerror", None) != 1314:
        raise
    # Directory junctions exercise the same reparse-ancestor guard without
    # requiring the symlink privilege unavailable on some Windows test hosts.
    subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(linked_game / "scripts"), str(outside)], capture_output=True, check=True)
    print("NOTE: file symlink creation needs a Windows privilege; testing a directory junction instead")
archive = ROOT / "linked.zip"
export(linked_game, archive)
with zipfile.ZipFile(archive) as z:
    assert set(z.namelist()) == {"README.txt", "report.txt"}
    assert "linked path: skipped" in z.read("report.txt").decode()
    assert b"EXTERNAL_LINK_SECRET" not in b"\n".join(z.read(n) for n in z.namelist())
print("PASS: available reparse links skipped; no external content copied")

print("ALL DIAGNOSTICS TESTS PASSED")
print(ROOT)
