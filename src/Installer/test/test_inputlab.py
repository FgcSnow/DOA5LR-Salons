"""Headless InputLab component lifecycle against a fake game directory.

Requires a freshly compiled unsigned installer in the parent directory. Never uses
the real DOA5LR installation; ZIP bytes for the bridge/tools are harmless stubs.
"""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXE = ROOT / "DOA5LR-Salons-Installer.exe"
with zipfile.ZipFile(os.environ["DOA5LR_BASE_ZIP"]) as base:
    ORIGINAL = base.read("dinput8ex.bin")
ORIGINAL_SHA = "7f2a1c7616515153d899b726c8ecf72d5fa81c27a9d14b5c394cdd2e09f325c5"
assert hashlib.sha256(ORIGINAL).hexdigest() == ORIGINAL_SHA
BRIDGE = b"InputLab bridge test payload (not executable)"

OPTIONAL = (
    r"optional=inputlab|Controller detection and keyboard remapping (experimental)|"
    r"DOA5LR-InputBridge-Xidi.dll;DOA5LR-InputBridge.ini;"
    r"DOA5LR-ControllerProfiles.ini;DOA5LR-Companion.exe"
)
FILES = {
    "DOA5LR-Salons-VERSION.txt": b"0.3.9-inputlab-draft\n",
    "DInput8.ini": b"[PATCH]\r\nKeyboardOnly=0\r\n",
    "dinput8ex.bin": ORIGINAL,
    "DOA5LR-InputBridge-Xidi.dll": ORIGINAL,
    "DOA5LR-InputBridge.ini": b"[Input]\r\nMode=Hybrid\r\n",
    "DOA5LR-ControllerProfiles.ini": b"[Profiles]\r\n",
    "DOA5LR-Companion.exe": b"companion stub",
    "InputLab/payload/dinput8ex.bin": BRIDGE,
    "InputLab/DOA5LR-Commandes.exe": b"remapper stub",
    "InputLab/DOA5LR-Companion.exe": b"companion stub",
    "InputLab/DOA5LR-Peripheriques.exe": b"inventory stub",
    "InputLab/DOA5LR-Detecteur.exe": b"device finder stub",
    "InputLab/DOA5LR-ControllerProfiles.ini": b"[Profiles]\r\n",
    "InputLab/Profil-clavier.ini": b"[Keyboard]\r\nK=Punch\r\n",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(condition, message, game):
    if not condition:
        log = game / "DOA5LR-Salons-Installer.log"
        print("FAILED:", message)
        if log.exists():
            print(log.read_text(encoding="utf-8", errors="replace")[-5000:])
        raise AssertionError(message)
    print("OK:", message)


def val(path, key):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.casefold().startswith(key.casefold() + "="):
            return line.split("=", 1)[1].strip()
    return None


def write_pack(zip_path, manifest_path, files):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for rel, payload in files.items():
            archive.writestr(rel, payload)
    manifest_path.write_text(
        "\n".join([
            "version=0.3.9-inputlab-draft",
            "url=" + str(zip_path),
            "sha256=" + sha(zip_path),
            "size=" + str(zip_path.stat().st_size),
            "keep=*.ini",
            OPTIONAL,
            "",
        ]), encoding="utf-8"
    )


def build_restore_harness(output):
    csc = Path(os.environ["WINDIR"]) / "Microsoft.NET" / "Framework" / "v4.0.30319" / "csc.exe"
    cmd = [str(csc), "/nologo", "/target:exe", "/platform:x86", "/main:RestoreHarness",
           "/out:" + str(output), "/r:System.IO.Compression.dll", "/r:System.IO.Compression.FileSystem.dll",
           str(ROOT / "Installer.cs"), str(HERE / "restore_harness.cs")]
    subprocess.run(cmd, check=True, capture_output=True)


def main():
    with tempfile.TemporaryDirectory(prefix="doa5lr-inputlab-test-") as temp:
        temp = Path(temp)
        game = temp / "Alternate Steam Library" / "Dead or Alive 5 Last Round"
        game.mkdir(parents=True)
        (game / "game.exe").write_bytes(b"fake game")
        (game / "dinput8ex.bin").write_bytes(b"existing frontend")
        dinput = game / "DInput8.ini"
        xidi = game / "Xidi.ini"
        dinput.write_bytes(b"[PATCH]\r\nKeyboardOnly=0\r\n[User]\r\nKeep=before\r\n")
        xidi.write_bytes(b"[Workarounds]\r\nActiveVirtualControllerMask=15\r\n[User]\r\nKeep=before\r\n")
        zip_path = temp / "DOA5LR-Salons-0.3.9-inputlab-draft.zip"
        manifest = temp / "version.txt"
        write_pack(zip_path, manifest, FILES)
        restore = temp / "restore-harness.exe"
        build_restore_harness(restore)

        def run(*args):
            proc = subprocess.run([str(EXE), "--auto", "--game", str(game), "--manifest", str(manifest), *args],
                                  capture_output=True, text=True, timeout=30)
            return proc.returncode

        def backups():
            root = game / "DOA5LR-Salons-Backups"
            return set(root.iterdir()) if root.exists() else set()

        active = game / "dinput8ex.bin"
        marker = game / "InputLab" / "previous-settings.txt"
        finder = game / "InputLab" / "DOA5LR-Detecteur.exe"
        profile = game / "InputLab" / "Profil-clavier.ini"
        root_profile = game / "DOA5LR-ControllerProfiles.ini"
        sub_profile = game / "InputLab" / "DOA5LR-ControllerProfiles.ini"
        comp = game / "DOA5LR-Salons-Components.txt"

        check(run() == 0, "default install succeeds", game)
        check(active.read_bytes() == ORIGINAL and finder.exists() and not marker.exists(),
              "runtime is OFF by default, core apps installed and original Xidi remains active", game)
        check(all((game / rel).exists() for rel in FILES if rel.startswith("InputLab/")),
              "all InputLab settings tools and activation payload are installed while OFF", game)
        check(not (game / "DOA5LR-Companion.exe").exists() and not (game / "DOA5LR-InputBridge-Xidi.dll").exists(),
              "OFF does not install root runtime binaries", game)
        check(val(dinput, "KeyboardOnly") == "0" and val(xidi, "ActiveVirtualControllerMask") == "15",
              "OFF leaves prior keyboard and Xidi settings intact", game)
        check(val(comp, "inputlab") == "0", "OFF choice recorded", game)

        finder_bytes = finder.read_bytes()
        finder.unlink()
        probe = subprocess.run([str(restore), "--missing", str(game), str(manifest)],
                               capture_output=True, text=True, timeout=30)
        check(probe.returncode == 0 and r"InputLab\DOA5LR-Detecteur.exe" in probe.stdout
              and "DOA5LR-InputBridge-Xidi.dll" not in probe.stdout,
              "OFF detects missing core app without requiring root runtime", game)
        finder.write_bytes(finder_bytes)
        before_incomplete = backups()
        bad = dict(FILES)
        del bad["InputLab/DOA5LR-Detecteur.exe"]
        write_pack(zip_path, manifest, bad)
        check(run() != 0 and active.read_bytes() == ORIGINAL and backups() == before_incomplete,
              "OFF rejects incomplete core app archive before any game change", game)
        write_pack(zip_path, manifest, FILES)

        check(run("--components", "inputlab=1") == 0, "InputLab ON install succeeds", game)
        check(active.read_bytes() == BRIDGE and (game / "DOA5LR-InputBridge-Xidi.dll").read_bytes() == ORIGINAL,
              "bridge active and original Xidi retained", game)
        check(finder.exists() and marker.exists() and val(comp, "inputlab") == "1",
              "device finder installed and settings snapshot recorded", game)
        check(val(dinput, "KeyboardOnly") == "1" and val(xidi, "ActiveVirtualControllerMask") == "0",
              "ON selects keyboard-only AutoLink and disables native Xidi controllers", game)
        original_marker = marker.read_bytes()

        profile.write_bytes(b"[Keyboard]\r\nF=Poing\r\n")
        root_profile.write_bytes(b"[Profiles]\r\nVID_1234_PID_ABCD=custom-root\r\n")
        sub_profile.write_bytes(b"[Profiles]\r\nVID_1234_PID_ABCD=custom-sub\r\n")
        with dinput.open("ab") as stream:
            stream.write(b"UserDuringInputLab=changed\r\n")
        with xidi.open("ab") as stream:
            stream.write(b"UserDuringInputLab=changed\r\n")
        check(run() == 0, "selected InputLab reinstalls on update", game)
        check(profile.read_bytes().endswith(b"F=Poing\r\n") and b"custom-root" in root_profile.read_bytes()
              and b"custom-sub" in sub_profile.read_bytes(), "custom F mapping and controller profiles survive update", game)
        check(marker.read_bytes() == original_marker, "original settings snapshot survives update", game)
        check(active.read_bytes() == BRIDGE, "bridge remains active after update", game)

        # A repair must preserve the mode applied by the controls app. In
        # particular, forcing the Hybrid flags here silently disables PS5 input
        # in Controller mode until the player launches through the app again.
        bridge_config = game / "DOA5LR-InputBridge.ini"
        for mode_name, keyboard_only, controller_mask in [
            ("Keyboard", "0", "0"), ("Controller", "0", "15"), ("Hybrid", "1", "0")
        ]:
            applied_config = ("[Input]\r\nMode=" + mode_name + "\r\n[Keyboard]\r\n37=33\r\n17=17\r\n").encode("ascii")
            bridge_config.write_bytes(applied_config)
            for ini, key, value in [(dinput, "KeyboardOnly", keyboard_only), (xidi, "ActiveVirtualControllerMask", controller_mask)]:
                previous = val(ini, key)
                ini.write_bytes(ini.read_bytes().replace((key + "=" + previous).encode("ascii"), (key + "=" + value).encode("ascii"), 1))
            check(run() == 0, "ON repair succeeds after app selected " + mode_name, game)
            check(val(dinput, "KeyboardOnly") == keyboard_only and val(xidi, "ActiveVirtualControllerMask") == controller_mask,
                  "ON repair retains " + mode_name + " input flags", game)
            check(bridge_config.read_bytes() == applied_config and profile.read_bytes().endswith(b"F=Poing\r\n"),
                  "ON repair retains " + mode_name + " and custom punch mapping", game)
            check(marker.read_bytes() == original_marker and active.read_bytes() == BRIDGE and val(comp, "inputlab") == "1",
                  "ON repair keeps original snapshot and active runtime for " + mode_name, game)
        finder_bytes = finder.read_bytes()
        finder.unlink()
        probe = subprocess.run([str(restore), "--missing", str(game), str(manifest)],
                               capture_output=True, text=True, timeout=30)
        check(probe.returncode == 0 and r"InputLab\DOA5LR-Detecteur.exe" in probe.stdout,
              "selected InputLab missing finder is detected", game)
        old_manifest = temp / "old-version.txt"
        old_manifest.write_text(manifest.read_text(encoding="utf-8").replace(OPTIONAL + "\n", ""), encoding="utf-8")
        probe = subprocess.run([str(restore), "--missing", str(game), str(old_manifest)],
                               capture_output=True, text=True, timeout=30)
        check(probe.returncode == 0 and "InputLab" not in probe.stdout,
              "older manifest does not demand InputLab files", game)
        finder.write_bytes(finder_bytes)

        before_bad = backups()
        bad = dict(FILES)
        del bad["InputLab/DOA5LR-Detecteur.exe"]
        write_pack(zip_path, manifest, bad)
        check(run() != 0 and active.read_bytes() == BRIDGE and backups() == before_bad,
              "incomplete optional payload rejected before any game change", game)
        bad = dict(FILES)
        bad["DOA5LR-InputBridge-Xidi.dll"] = b"wrong backend"
        write_pack(zip_path, manifest, bad)
        check(run() != 0 and active.read_bytes() == BRIDGE and backups() == before_bad,
              "wrong original Xidi hash rejected before any game change", game)
        write_pack(zip_path, manifest, FILES)

        before_off = backups()
        check(run("--components", "inputlab=0") == 0, "InputLab OFF update succeeds", game)
        off_backup = (backups() - before_off).pop()
        check(active.read_bytes() == ORIGINAL and finder.exists() and not marker.exists()
              and not (game / "DOA5LR-Companion.exe").exists() and not (game / "DOA5LR-InputBridge-Xidi.dll").exists(),
              "OFF restores original Xidi, removes runtime/snapshot and keeps settings app", game)
        check(all((game / rel).exists() for rel in FILES if rel.startswith("InputLab/")),
              "ON to OFF keeps every core app and payload for later activation", game)
        check(val(dinput, "KeyboardOnly") == "0" and val(xidi, "ActiveVirtualControllerMask") == "15",
              "OFF restores exact prior settings", game)
        check(b"UserDuringInputLab=changed" in dinput.read_bytes() and b"UserDuringInputLab=changed" in xidi.read_bytes(),
              "OFF retains unrelated user INI edits", game)
        check(profile.read_bytes().endswith(b"F=Poing\r\n") and b"custom-root" in root_profile.read_bytes()
              and b"custom-sub" in sub_profile.read_bytes(), "OFF retains personal profile INIs", game)
        check(val(comp, "inputlab") == "0", "OFF choice recorded", game)

        proc = subprocess.run([str(restore), str(game), str(off_backup)], capture_output=True, text=True, timeout=30)
        check(proc.returncode == 0, "backup restore engine succeeds", game)
        check(active.read_bytes() == BRIDGE and finder.exists() and marker.exists() and val(comp, "inputlab") == "1",
              "backup restores active bridge, helper, snapshot and choice", game)
        check(val(dinput, "KeyboardOnly") == "1" and val(xidi, "ActiveVirtualControllerMask") == "0",
              "backup restores ON input settings", game)

        marker.unlink()
        before_missing = backups()
        active_before = active.read_bytes()
        dinput_before = dinput.read_bytes()
        xidi_before = xidi.read_bytes()
        check(run("--components", "inputlab=0") != 0, "missing prior-settings marker fails safely", game)
        check(active.read_bytes() == active_before and dinput.read_bytes() == dinput_before
              and xidi.read_bytes() == xidi_before and backups() == before_missing,
              "failed opt-out changes nothing", game)

        clean_game = temp / "Second Library" / "DOA5LR without Xidi.ini"
        clean_game.mkdir(parents=True)
        (clean_game / "game.exe").write_bytes(b"fake game")
        (clean_game / "DInput8.ini").write_bytes(b"[PATCH]\r\nKeyboardOnly=0\r\n")
        def clean_run(choice):
            return subprocess.run([str(EXE), "--auto", "--game", str(clean_game), "--manifest", str(manifest),
                                   "--components", "inputlab=" + choice], capture_output=True, timeout=30).returncode
        check(clean_run("1") == 0 and (clean_game / "Xidi.ini").exists(),
              "ON creates Xidi.ini when none existed", clean_game)
        clean_before_off = set((clean_game / "DOA5LR-Salons-Backups").iterdir())
        check(clean_run("0") == 0 and not (clean_game / "Xidi.ini").exists(),
              "OFF removes installer-created Xidi.ini", clean_game)
        clean_off_backup = (set((clean_game / "DOA5LR-Salons-Backups").iterdir()) - clean_before_off).pop()
        check((clean_game / "DInput8.ini.new").exists(), "OFF preserves packaged INI default beside user settings", clean_game)
        proc = subprocess.run([str(restore), str(clean_game), str(clean_off_backup)], capture_output=True, timeout=30)
        check(proc.returncode == 0 and not (clean_game / "DInput8.ini.new").exists(),
              "backup restore removes newly created .ini.new", clean_game)

        legacy = temp / "Third Library" / "DOA5LR with standalone prototype"
        legacy.mkdir(parents=True)
        (legacy / "game.exe").write_bytes(b"fake game")
        legacy_bridge = b"MZ\x00\x00standalone" + "DOA5LR-InputBridge-Xidi.dll".encode("utf-16le")
        (legacy / "dinput8ex.bin").write_bytes(legacy_bridge)
        (legacy / "DOA5LR-InputBridge-Xidi.dll").write_bytes(ORIGINAL)
        (legacy / "DOA5LR-InputBridge.ini").write_bytes(b"[Input]\r\nMode=Hybrid\r\n")
        (legacy / "DInput8.ini").write_bytes(b"[PATCH]\r\nKeyboardOnly=1\r\n")
        (legacy / "Xidi.ini").write_bytes(b"[Workarounds]\r\nActiveVirtualControllerMask=0\r\n")
        for choice in ("0", "1"):
            before = {p.name: p.read_bytes() for p in legacy.iterdir() if p.is_file() and p.name != "DOA5LR-Salons-Installer.log"}
            proc = subprocess.run([str(EXE), "--auto", "--game", str(legacy), "--manifest", str(manifest),
                                   "--components", "inputlab=" + choice], capture_output=True, timeout=30)
            after = {p.name: p.read_bytes() for p in legacy.iterdir() if p.is_file() and p.name != "DOA5LR-Salons-Installer.log"}
            check(proc.returncode != 0 and after == before and not (legacy / "DOA5LR-Salons-Backups").exists(),
                  "legacy standalone prototype blocks inputlab=" + choice + " before any game mutation", legacy)
            check("backup created before the standalone prototype" in
                  (legacy / "DOA5LR-Salons-Installer.log").read_text(encoding="utf-8", errors="replace"),
                  "legacy error instructs restoring its pre-prototype backup", legacy)

    print("ALL INPUTLAB INSTALLER TESTS PASSED")


if __name__ == "__main__":
    main()
