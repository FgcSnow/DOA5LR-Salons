"""Build an OFFLINE, local-only InputLab installer test archive from pack 0.3.8.

No network calls, no game-folder writes, no publication. The published 0.3.8 ZIP
is an immutable input; this script checks its SHA256 before making a draft copy.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
from pathlib import Path
import shutil
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


REPO = Path(__file__).resolve().parents[1]
LAB = REPO / "src" / "InputLab"
BASE_ZIP = REPO / "DOA5LR-Salons-0.3.8.zip"
BASE_MANIFEST = REPO / "version.txt"
INSTALLER_SOURCE = REPO / "src" / "Installer" / "Installer.cs"
INSTALLER_EXE = REPO / "src" / "Installer" / "DOA5LR-Salons-Installer.exe"
UPDATER = REPO / "src" / "UpdateCheck"
OUT = REPO / "preview-output"
VERSION = "0.3.9-inputlab-draft"
BASE_SHA256 = "6bffba7fdef2713d433879f01dfe2e0d9ca908bd8f8ec9be17c5e86f0cc14061"
XIDI_SHA256 = "7f2a1c7616515153d899b726c8ecf72d5fa81c27a9d14b5c394cdd2e09f325c5"
SCANS = (17, 31, 30, 32, 36, 37, 38, 50, 22, 23, 24, 49, 57, 28, 25)
OPTIONAL_LINE = (
    "optional=inputlab|Experimental in-game keyboard remapping (settings app always available)|"
    "DOA5LR-InputBridge-Xidi.dll;DOA5LR-InputBridge.ini;"
    "DOA5LR-ControllerProfiles.ini;DOA5LR-Companion.exe"
)
SOURCES = (
    "bridge.cpp", "bridge.def", "build.ps1", "companion_client.h",
    "companion_protocol.h", "companion_reader.cpp", "Detector.cs",
    "generate_mock.py", "generate_wrappers.py", "hybrid_keyboard.h",
    "InputLab.cs", "list_devices.cpp", "mocks.generated.h", "remap.h",
    "switch_state.h", "test_com.cpp", "test_remap.cpp", "test_switch.cpp",
    "wrappers.generated.h",
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(path: Path) -> bytes:
    if not path.is_file():
        raise FileNotFoundError(path)
    return path.read_bytes()


def pe_machine(blob: bytes) -> int:
    if blob[:2] != b"MZ":
        raise ValueError("binary has no MZ header")
    offset = int.from_bytes(blob[0x3C:0x40], "little")
    if blob[offset:offset + 4] != b"PE\0\0":
        raise ValueError("binary has no PE header")
    return int.from_bytes(blob[offset + 4:offset + 6], "little")


def check_x86(name: str, blob: bytes) -> None:
    if pe_machine(blob) != 0x14C:
        raise ValueError(f"{name} is not an x86 Windows PE")


def identity_profile() -> bytes:
    return ("[Keyboard]\r\n" + "".join(f"{scan}={scan}\r\n" for scan in SCANS)).encode("ascii")


def make_readme() -> bytes:
    return (
        "DOA5LR InputLab — LOCAL TEST DRAFT\r\n"
        "==================================\r\n"
        "Keyboard / controller settings remain available even when the\r\n"
        "experimental remapping component is unchecked in the installer.\r\n"
        "A fresh pack uses Controller mode with the usual input path.\r\n"
        "Existing saved modes and personal profiles are kept on update.\r\n"
        "Open DOA5LR-Commandes.exe, choose Keyboard or Controller,\r\n"
        "then click Play via Steam. Close the game before changing modes.\r\n"
        "The desktop shortcut opens the pack configuration window first.\r\n"
        "It never starts the game automatically. Review your settings, then\r\n"
        "click the launch button to open the input chooser.\r\n"
        "Launching directly from Steam skips these configuration screens\r\n"
        "and uses the last input mode and key bindings applied to the game.\r\n"
        "In Keyboard mode, click an action, then press its new key.\r\n"
        "Starting Keyboard mode enables the remapping module if needed.\r\n"
        "With remapping disabled, Controller mode starts the usual game\r\n"
        "configuration without enabling the experimental module.\r\n"
        "Controller finder opens the device search.\r\n\r\n"
        "USING THE APP WITHOUT THE AUTO-INSTALLER\r\n"
        "Extract the entire portable ZIP into a folder and keep that folder.\r\n"
        "The files beside the app and the payload folder are required.\r\n"
        "The finder works on its own. Enabling remapping requires the\r\n"
        "verified DOA5LR-Salons 0.3.8 pack already installed in the game.\r\n"
        "The app searches your Steam libraries for the game.\r\n"
        "Select Keyboard, then click Enable module or Play via Steam.\r\n"
        "A backup is created beside the app before any changes are made.\r\n"
        "Restore previous setup restores that backup.\r\n"
        "Unchecking the remapping component in the pack installer restores\r\n"
        "the usual input path while keeping the settings app and profiles.\r\n"
        "The portable ZIP does not require the auto-installer executable.\r\n\r\n"
        "If an older standalone InputLab prototype is installed, restore\r\n"
        "its original backup before using the pack installer. Without that\r\n"
        "backup, the original INI settings cannot be recovered reliably,\r\n"
        "so the installer refuses the migration.\r\n"
        "The module preserves the original Xidi in DOA5LR-InputBridge-Xidi.dll\r\n"
        "and uses a separate controller reader in experimental combined mode.\r\n"
        "DOA5LR-Commandes.exe lets you remap keyboard keys.\r\n"
        "DOA5LR-Detecteur.exe searches connected controllers by name or VID/PID.\r\n"
        "It lists connected devices and locally known profiles only.\r\n"
        "There is no universal ID database or PS5 controller emulation.\r\n"
        "The game's DOA5LR-ControllerProfiles.ini maps controller buttons.\r\n"
        "Only DualSense Edge VID_054C PID_0DF2 has been tested on real hardware.\r\n"
        "Other sticks, hitbox controllers and models need their own profiles.\r\n"
        "Known limitation: a PS5 controller connected before startup may\r\n"
        "block keyboard input in the menu. To play with the keyboard,\r\n"
        "disconnect the controller and restart the game.\r\n"
        "Keyboard mode checks for connected controllers before launching\r\n"
        "and asks you to disconnect them while this limitation remains.\r\n"
        "This is an unpublished local draft.\r\n"
        "Its new executables and DLLs are unsigned.\r\n"
    ).encode("utf-8-sig")


def make_manifest(old: str, zip_path: Path, zip_data: bytes) -> str:
    lines = []
    for line in old.splitlines():
        if line.startswith(("version=", "url=", "sha256=", "size=", "notes=", "installer=", "installer_version=", "installer_sha256=")):
            continue
        if line == OPTIONAL_LINE:
            continue
        lines.append(line)
    lines.insert(1, f"version={VERSION}")
    lines.insert(2, f"url={zip_path.name}")
    lines.insert(3, f"sha256={sha(zip_data)}")
    lines.insert(4, f"size={len(zip_data)}")
    lines.insert(5, "notes=0.3.9 candidate: keyboard/controller settings always available, optional remapping, configuration-first launcher, UpdateCheck 1.1 banner")
    lines.insert(6, "note=InputLab is experimental. The finder searches connected devices by name or VID/PID and locally known profiles only; it is not a universal controller ID database or PS5 emulation.")
    lines.insert(7, "note=Only DualSense Edge was tested; keyboard input can be unavailable if the pad is connected before game launch. New draft binaries are unsigned.")
    lines.insert(8, "note=Restore any separately installed InputLab prototype from its original backup before using this draft installer; its previous INI values cannot be inferred safely.")
    lines.insert(9, "note=UpdateCheck 1.1 adds a brief new-version banner in borderless/windowed mode, then opens the installer after normal game exit. Installing remains your choice.")
    lines.insert(10, "note=Logs > Export diagnostics ZIP collects existing named local journals and a small report for manual sharing. It does not upload anything or enable debug logging.")
    idx = next(i for i, line in enumerate(lines) if line.startswith("optional=60fps|")) + 1
    lines.insert(idx, OPTIONAL_LINE)
    return "\n".join(lines) + "\n"


def main() -> None:
    global LAB, BASE_ZIP, BASE_MANIFEST
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finder", type=Path, required=True, help="Compiled standalone searchable controller finder EXE")
    parser.add_argument("--installer-source", type=Path, default=INSTALLER_SOURCE)
    parser.add_argument("--installer-exe", type=Path, default=INSTALLER_EXE)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--lab", type=Path, default=LAB, help="InputLab source/build directory")
    parser.add_argument("--base-zip", type=Path, default=BASE_ZIP, help="Unmodified published 0.3.8 ZIP")
    parser.add_argument("--base-manifest", type=Path, default=BASE_MANIFEST)
    parser.add_argument("--updater", type=Path, default=UPDATER, help="Built UpdateCheck 1.1 directory")
    args = parser.parse_args()
    LAB, BASE_ZIP, BASE_MANIFEST = args.lab, args.base_zip, args.base_manifest

    base_bytes = load(BASE_ZIP)
    if sha(base_bytes) != BASE_SHA256:
        raise ValueError("Published 0.3.8 base ZIP checksum mismatch")
    with ZipFile(BASE_ZIP) as z:
        if z.testzip() is not None:
            raise ValueError("Published base ZIP has a corrupt entry")
        base_names = z.namelist()
        if len(base_names) != len(set(base_names)):
            raise ValueError("Published base ZIP has duplicate entries")
        payload = {n: z.read(n) for n in base_names}
    for name in payload:
        if name.startswith("/") or "\\" in name or ".." in name.split("/"):
            raise ValueError(f"Unsafe base ZIP path: {name}")
    if sha(payload["dinput8ex.bin"]) != XIDI_SHA256:
        raise ValueError("Published Xidi front-end checksum mismatch")

    bridge = load(LAB / "payload" / "dinput8ex.bin")
    companion = load(LAB / "DOA5LR-Companion.exe")
    commands = load(LAB / "DOA5LR-Commandes.exe")
    raw_devices = load(LAB / "DOA5LR-Peripheriques.exe")
    finder = load(args.finder)
    installer_exe = load(args.installer_exe)
    updater = load(args.updater / "DOA5LR-UpdateCheck.asi")
    check_x86("UpdateCheck 1.1", updater)
    updater_source = load(args.updater / "updatecheck.c")
    if b'#define UVER "1.1"' not in updater_source or "DOA5LR_UpdateCheck_Banner".encode("utf-16le") not in updater:
        raise ValueError("UpdateCheck 1.1 source/banner binary required")
    if args.installer_exe.stat().st_mtime < args.installer_source.stat().st_mtime:
        raise ValueError("Draft installer EXE is older than Installer.cs; rebuild it before staging")
    for name, blob in (
        ("InputLab bridge", bridge), ("companion", companion),
        ("commands UI", commands), ("raw devices", raw_devices),
        ("controller finder", finder),
        ("draft installer", installer_exe),
    ):
        check_x86(name, blob)
    if sha(bridge) == XIDI_SHA256:
        raise ValueError("InputLab bridge is identical to base Xidi binary")

    # Preserve the mandatory 0.3.8 front-end in the ZIP. The opt-in installer
    # overlays this bridge after extracting, and can revert to that exact Xidi.
    payload["DOA5LR-InputBridge-Xidi.dll"] = payload["dinput8ex.bin"]
    # Seed only fresh installs; keep=*.ini preserves an existing mode and profile.
    payload["DOA5LR-InputBridge.ini"] = b"[Input]\r\nMode=Controller\r\n" + identity_profile()
    payload["DOA5LR-ControllerProfiles.ini"] = load(LAB / "DOA5LR-ControllerProfiles.ini")
    payload["DOA5LR-Companion.exe"] = companion
    payload["InputLab/payload/dinput8ex.bin"] = bridge
    payload["InputLab/DOA5LR-Commandes.exe"] = commands
    payload["InputLab/DOA5LR-Companion.exe"] = companion
    payload["InputLab/DOA5LR-Peripheriques.exe"] = raw_devices
    payload[f"InputLab/{args.finder.name}"] = finder
    payload["InputLab/DOA5LR-ControllerProfiles.ini"] = payload["DOA5LR-ControllerProfiles.ini"]
    payload["InputLab/Profil-clavier.ini"] = identity_profile()
    payload["InputLab/README-TEST-EN.txt"] = make_readme()
    for source in SOURCES:
        payload[f"InputLab/source/{source}"] = load(LAB / "source" / source)
    payload["scripts/Installer-Source/Installer.cs"] = load(args.installer_source)
    payload["DOA5LR-Salons-Installer.exe"] = installer_exe
    payload["scripts/DOA5LR-UpdateCheck.asi"] = updater
    payload["scripts/DOA5LR-UpdateCheck.ini"] = load(args.updater / "DOA5LR-UpdateCheck.ini")
    for name in ("updatecheck.c", "version.rc", "build.cmd"):
        payload["scripts/UpdateCheck-Source/" + name] = load(args.updater / name)
    for name in ("START-HERE-EN.md", "CHANGELOG-EN.md", "BUG-REPORT-TEMPLATE.md"):
        guide = REPO / "docs" / {"START-HERE-EN.md": "INPUT-SETTINGS.md", "CHANGELOG-EN.md": "RELEASE-NOTES-0.3.9.md", "BUG-REPORT-TEMPLATE.md": "BUG-REPORT-TEMPLATE.md"}[name]
        if guide.is_file():
            payload["InputLab/" + name] = load(guide)
    payload["DOA5LR-Salons-VERSION.txt"] = (VERSION + "\r\n").encode("ascii")
    original_readme = payload["READ-ME-FIRST-EN.txt"]
    payload["READ-ME-FIRST-EN.txt"] = (
        "LOCAL INPUTLAB DRAFT - NOT A PUBLIC RELEASE\r\n"
        "This archive extends the published 0.3.8 pack for installer tests.\r\n"
        "New InputLab binaries and the matching draft installer are unsigned.\r\n"
        "The matching local draft installer and manifest install the pack.\r\n"
        "InputLab/DOA5LR-Commandes.exe opens the keyboard/controller launcher.\r\n"
        "It is also available in the separate portable ZIP without the installer.\r\n"
        "Read InputLab/README-TEST-EN.txt before manual activation.\r\n\r\n"
    ).encode("ascii") + original_readme
    current_guide = REPO / "docs" / "INPUT-SETTINGS.md"
    if current_guide.is_file():
        payload["READ-ME-FIRST-EN.txt"] = load(current_guide)
        payload["START-HERE.md"] = load(current_guide)
    payload.pop("SHA256SUMS.txt", None)
    sums = "".join(f"{sha(payload[n])} *{n}\n" for n in sorted(payload))
    payload["SHA256SUMS.txt"] = sums.encode("ascii")
    if len({n.lower() for n in payload}) != len(payload):
        raise ValueError("Case-insensitive path collision in draft ZIP")
    for name in payload:
        if name.startswith("/") or "\\" in name or ".." in name.split("/"):
            raise ValueError(f"Unsafe draft ZIP path: {name}")

    args.out.mkdir(parents=True, exist_ok=True)
    zip_path = (args.out / f"DOA5LR-Salons-{VERSION}.zip").resolve()
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED, compresslevel=9, strict_timestamps=True) as z:
        for name in sorted(payload):
            zi = ZipInfo(name, date_time=(2026, 9, 24, 0, 0, 0))
            zi.compress_type = ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, payload[name], compress_type=ZIP_DEFLATED, compresslevel=9)
    with ZipFile(zip_path) as z:
        if z.testzip() is not None:
            raise AssertionError("Draft ZIP corruption")
        actual = {n: z.read(n) for n in z.namelist()}
    if actual != payload:
        raise AssertionError("Draft ZIP entries changed unexpectedly")
    expected_sums = {line.split(" *", 1)[1]: line.split(" *", 1)[0] for line in actual["SHA256SUMS.txt"].decode("ascii").splitlines()}
    if set(expected_sums) != set(actual) - {"SHA256SUMS.txt"}:
        raise AssertionError("Checksum manifest does not cover all draft entries")
    for name, expected in expected_sums.items():
        if sha(actual[name]) != expected:
            raise AssertionError(f"Checksum mismatch: {name}")
    if sha(actual["dinput8ex.bin"]) != XIDI_SHA256 or sha(actual["DOA5LR-InputBridge-Xidi.dll"]) != XIDI_SHA256:
        raise AssertionError("Mandatory original Xidi frontend changed")
    if actual["InputLab/Profil-clavier.ini"] != identity_profile():
        raise AssertionError("A personalized keyboard profile entered the draft pack")
    owned = {name for name in actual if any(fnmatch.fnmatchcase(name.lower(), g.replace("\\", "/").lower()) for g in OPTIONAL_LINE.split("|", 2)[2].split(";"))}
    expected_owned = {
        "DOA5LR-InputBridge-Xidi.dll", "DOA5LR-InputBridge.ini",
        "DOA5LR-ControllerProfiles.ini", "DOA5LR-Companion.exe",
    }
    if owned != expected_owned or "dinput8ex.bin" in owned:
        raise AssertionError("Optional InputLab path ownership is incomplete or includes mandatory Xidi")
    if any(name.startswith("InputLab/") for name in owned):
        raise AssertionError("Settings app must remain installed when the runtime component is off")
    if b"[VID_054C&PID_0DF2]" not in actual["DOA5LR-ControllerProfiles.ini"]:
        raise AssertionError("Tested DualSense Edge profile is missing")

    zip_data = zip_path.read_bytes()
    manifest = make_manifest(load(BASE_MANIFEST).decode("utf-8-sig"), zip_path, zip_data)
    manifest_path = args.out / f"version-{VERSION}.txt"
    manifest_path.write_text(manifest, encoding="utf-8", newline="\n")
    digest_path = args.out / (zip_path.name + ".sha256")
    digest_path.write_text(f"{sha(zip_data)} *{zip_path.name}\n", encoding="ascii", newline="\n")
    installer_path = args.out / "DOA5LR-Salons-Installer-InputLab-draft.exe"
    shutil.copyfile(args.installer_exe, installer_path)
    (args.out / (installer_path.name + ".sha256")).write_text(
        f"{sha(installer_exe)} *{installer_path.name}\n", encoding="ascii", newline="\n"
    )

    # A self-contained app fallback: no installer EXE or full-pack root INIs.
    # Keep the companion alongside the UI because manual activation copies it
    # from the app directory to the existing, verified game installation.
    portable = {n: blob for n, blob in payload.items() if n.startswith("InputLab/")}
    required_portable = {
        "InputLab/DOA5LR-Commandes.exe", "InputLab/DOA5LR-Detecteur.exe",
        "InputLab/DOA5LR-Peripheriques.exe", "InputLab/DOA5LR-Companion.exe",
        "InputLab/DOA5LR-ControllerProfiles.ini", "InputLab/Profil-clavier.ini",
        "InputLab/payload/dinput8ex.bin", "InputLab/README-TEST-EN.txt",
    }
    if not required_portable.issubset(portable):
        raise AssertionError("Portable application dependencies are incomplete")
    portable["SHA256SUMS.txt"] = "".join(
        f"{sha(portable[n])} *{n}\n" for n in sorted(portable)
    ).encode("ascii")
    portable_path = args.out / "DOA5LR-Commandes-portable-draft.zip"
    with ZipFile(portable_path, "w", compression=ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted(portable):
            zi = ZipInfo(name, date_time=(2026, 9, 24, 0, 0, 0))
            zi.compress_type = ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, portable[name], compress_type=ZIP_DEFLATED, compresslevel=9)
    with ZipFile(portable_path) as z:
        if z.testzip() is not None or {n: z.read(n) for n in z.namelist()} != portable:
            raise AssertionError("Portable ZIP verification failed")
    portable_data = portable_path.read_bytes()
    (args.out / (portable_path.name + ".sha256")).write_text(
        f"{sha(portable_data)} *{portable_path.name}\n", encoding="ascii", newline="\n"
    )
    report = {
        "version": VERSION,
        "base_zip": str(BASE_ZIP),
        "base_sha256": sha(base_bytes),
        "draft_zip": str(zip_path),
        "draft_sha256": sha(zip_data),
        "draft_bytes": len(zip_data),
        "manifest": str(manifest_path.resolve()),
        "installer": str(installer_path.resolve()),
        "installer_sha256": sha(installer_exe),
        "zip_entries": len(actual),
        "original_xidi_sha256": sha(actual["dinput8ex.bin"]),
        "bridge_sha256": sha(bridge),
        "updatecheck_version": "1.1",
        "updatecheck_sha256": sha(updater),
        "finder": args.finder.name,
        "identity_keyboard_profile": True,
        "portable_zip": str(portable_path.resolve()),
        "portable_sha256": sha(portable_data),
        "portable_bytes": len(portable_data),
        "portable_entries": len(portable),
    }
    report_path = args.out / "build-report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
