"""Exercise actual release artifacts in temporary fake game folders, never Steam.

python tools/test_release_039.py --release-dir <dir> --preview-dir <dir> --base-zip <0.3.8.zip>
"""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
from zipfile import ZipFile

REPO = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise AssertionError(message)
    print("PASS:", message, flush=True)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def ini(path, key):
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", required=True, type=Path)
    parser.add_argument("--preview-dir", required=True, type=Path)
    parser.add_argument("--base-zip", required=True, type=Path)
    args = parser.parse_args()
    exe = args.release_dir / "DOA5LR-Salons-Installer.exe"
    pack = args.release_dir / "DOA5LR-Salons-0.3.9.zip"
    preview = args.preview_dir / "DOA5LR-Salons-0.3.9-inputlab-draft.zip"
    with ZipFile(pack) as z:
        require(z.testzip() is None, "full archive CRCs")
        final = {n: z.read(n) for n in z.namelist()}
    with ZipFile(preview) as z:
        previous = {n: z.read(n) for n in z.namelist()}
    with ZipFile(args.base_zip) as z:
        base = {n: z.read(n) for n in z.namelist() if not n.endswith("/")}
    original = base["dinput8ex.bin"]
    require(final["dinput8ex.bin"] == original, "native frontend unchanged from 0.3.8")
    require(final["DOA5LR-Salons-Installer.exe"] == exe.read_bytes(), "root and download installer match")
    require(final["DOA5LR-Companion.exe"] == final["InputLab/DOA5LR-Companion.exe"], "companion copies match")
    for line in final["SHA256SUMS.txt"].decode().splitlines():
        digest, name = line.split(" *", 1)
        if sha(final[name]) != digest:
            raise AssertionError("internal checksum: " + name)
    require(len(final["SHA256SUMS.txt"].decode().splitlines()) == len(final) - 1, "internal checksum coverage and values")
    with ZipFile(args.release_dir / "DOA5LR-Commandes-portable-0.3.9.zip") as z:
        require(all(z.read(n) == data for n, data in final.items() if n.startswith("InputLab/")), "portable app matches full pack")
    for name in ("scripts/DOA5LR-Lobby.asi", "scripts/DOA5LR-InviteFix.asi", "scripts/DOA5LR-WiFi-Wired-Detector.asi"):
        require(final[name] == base[name], "existing lobby/network binary unchanged: " + name)

    with tempfile.TemporaryDirectory(prefix="doa5lr-final-039-") as td:
        temp = Path(td)
        def manifest(source, archive, target):
            text = source.read_text(encoding="utf-8-sig")
            text = "\n".join("url=" + str(archive) if line.startswith("url=") else line for line in text.splitlines())
            target.write_text(text, encoding="utf-8")
            return target
        stable_manifest = manifest(args.release_dir / "version.txt", pack, temp / "stable.txt")
        old_manifest = manifest(args.preview_dir / "version-0.3.9-inputlab-draft.txt", preview, temp / "preview.txt")
        old_exe = temp / "previous.exe"
        old_exe.write_bytes(previous["DOA5LR-Salons-Installer.exe"])
        def game(name):
            folder = temp / name
            folder.mkdir()
            (folder / "game.exe").write_bytes(b"fake game, never executed")
            return folder
        def install(folder, binary=exe, mf=stable_manifest, selection=None):
            cmd = [str(binary), "--auto", "--game", str(folder), "--manifest", str(mf)]
            if selection is not None:
                cmd += ["--components", selection]
            result = subprocess.run(cmd, timeout=60, capture_output=True)
            if result.returncode:
                print((folder / "DOA5LR-Salons-Installer.log").read_text(encoding="utf-8-sig", errors="replace")[-5000:])
            require(result.returncode == 0, "install succeeds: " + folder.name)
        fresh = game("fresh")
        install(fresh)
        require(ini(fresh / "DOA5LR-Salons-Components.txt", "inputlab") == "0", "fresh remapping OFF")
        require((fresh / "dinput8ex.bin").read_bytes() == original, "fresh native frontend retained")
        require((fresh / "InputLab/DOA5LR-Commandes.exe").exists(), "settings app installed with remapping OFF")
        require((fresh / "DOA5LR-Salons-Installer.exe").read_bytes() == exe.read_bytes(), "UpdateCheck can find the installed installer")

        upgrade = game("upgrade-from-038")
        for name, data in base.items():
            target = upgrade / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        personal = (upgrade / "DInput8.ini").read_bytes() + b"\r\n[PersonalTest]\r\nKeep=mine\r\n"
        (upgrade / "DInput8.ini").write_bytes(personal)
        install(upgrade)
        require((upgrade / "DInput8.ini").read_bytes() == personal, "0.3.8 custom INI retained")
        require(ini(upgrade / "DOA5LR-Salons-Components.txt", "inputlab") == "0", "0.3.8 upgrade remains OFF")

        active = game("upgrade-active-preview")
        install(active, old_exe, old_manifest, "inputlab=1")
        config = active / "DOA5LR-InputBridge.ini"
        custom = config.read_text(encoding="utf-8-sig").replace("Mode=Controller", "Mode=Keyboard")
        config.write_text(custom, encoding="utf-8")
        profile = active / "InputLab/Profil-clavier.ini"
        profile.write_bytes(b"[Keyboard]\r\n37=33\r\n17=17\r\n")
        install(active, old_exe, old_manifest)
        before = {p: (active / p).read_bytes() for p in ["dinput8ex.bin", "DOA5LR-InputBridge.ini", "InputLab/Profil-clavier.ini", "InputLab/previous-settings.txt", "DInput8.ini", "Xidi.ini"]}
        old_backups = set((active / "DOA5LR-Salons-Backups").iterdir())
        install(active)
        new_backups = set((active / "DOA5LR-Salons-Backups").iterdir()) - old_backups
        require(len(new_backups) == 1, "upgrade creates one backup")
        require((active / "dinput8ex.bin").read_bytes() == final["InputLab/payload/dinput8ex.bin"], "preview bridge upgraded to final signed bridge")
        for name in ["DOA5LR-InputBridge.ini", "InputLab/Profil-clavier.ini", "InputLab/previous-settings.txt"]:
            require((active / name).read_bytes() == before[name], "preview choice/profile/snapshot preserved: " + name)
        require(ini(active / "Xidi.ini", "ActiveVirtualControllerMask") == "0", "Keyboard mode retained on upgrade")
        csc = Path(os.environ["WINDIR"]) / "Microsoft.NET/Framework/v4.0.30319/csc.exe"
        harness = temp / "restore-harness.exe"
        subprocess.run([str(csc), "/nologo", "/target:exe", "/platform:x86", "/main:RestoreHarness", "/out:" + str(harness), "/r:System.IO.Compression.dll", "/r:System.IO.Compression.FileSystem.dll", str(REPO / "src/Installer/Installer.cs"), str(REPO / "src/Installer/test/restore_harness.cs")], check=True, capture_output=True)
        subprocess.run([str(harness), str(active), str(next(iter(new_backups)))], check=True, capture_output=True, timeout=60)
        require(all((active / n).read_bytes() == data for n, data in before.items()), "backup restore returns previous unsigned bridge, settings and profiles exactly")
        install(active, selection="inputlab=0")
        require((active / "dinput8ex.bin").read_bytes() == original, "turning OFF restores native frontend")
        require(not (active / "InputLab/previous-settings.txt").exists(), "turning OFF consumes restored settings snapshot")
    print("ALL FINAL RELEASE INTEGRATION CHECKS PASSED")


if __name__ == "__main__":
    main()
