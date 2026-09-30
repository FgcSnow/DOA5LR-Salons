"""Verify the actual PS4 release archives and install them into isolated fake games.

No Steam/game is started. Every installer child has a private TEMP/TMP cache.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile

from build_release_0314_ps4 import (
    CORE, FULL, INSTALLER, MAPS, OPTIONAL, PIN_BASE, PIN_SKINS, PS4_FULL,
    SKINS, read_zip, sha, sums, validate_native,
)
from pack_docs import check_pack_guides


def ok(condition, message):
    if not condition:
        raise AssertionError(message)
    print("OK " + message, flush=True)


def dll(proxy=False):
    data = bytearray(256)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3c, 128)
    data[128:132] = b"PE\0\0"
    struct.pack_into("<H", data, 132, 0x14c)
    return bytes(data) + b"SteamAPI_Init\0" + (b"cream_api.ini\0" if proxy else b"")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rel", type=Path, required=True)
    ap.add_argument("--base", type=Path, required=True)
    args = ap.parse_args()
    rel, base = args.rel.resolve(), args.base.resolve()
    report = json.loads((rel / "build-report.json").read_text())
    for name, row in report["assets"].items():
        data = (rel / name).read_bytes()
        ok(len(data) == row["bytes"] and sha(data) == row["sha256"], f"release checksum: {name}")
    old, legacy, core, maps, skins, complete = [read_zip(path) for path in (
        base / FULL, rel / FULL, rel / CORE, rel / MAPS, rel / SKINS, rel / PS4_FULL)]
    ok(core | maps == legacy and not core.keys() & maps.keys(), "legacy full = core + unchanged maps")
    ok(sha((rel / MAPS).read_bytes()) == PIN_BASE[MAPS], "maps ZIP byte-identical to validated release")
    ok(set(skins) == {"DLC/" + n for n in PIN_SKINS}, "skins archive contains only the four native files")
    for name, (size, digest) in PIN_SKINS.items():
        ok(len(skins["DLC/" + name]) == size and sha(skins["DLC/" + name]) == digest, f"audited costume file: {name}")
    validate_native(skins)
    ok(not any(n.lower().startswith("dlc/") for n in legacy), "old installers receive no native DLC payload")
    expected = legacy | skins
    expected["SHA256SUMS.txt"] = sums(expected)
    ok(expected == complete, "PS4 full ZIP contains complete legacy pack plus all skins")
    for payload in (legacy, complete):
        ok(payload["SHA256SUMS.txt"] == sums(payload), "archive internal checksum list complete")
        check_pack_guides(payload, "0.3.14")
    changed = set(report["changed_base_files"])
    ok(all(legacy[n] == b for n, b in old.items() if n not in changed), "every unannounced base file unchanged")
    ok(all(legacy[n] == b for n, b in old.items() if n.endswith((".asi", ".dll"))), "all game modules byte-identical")
    manifest = (rel / "version.txt").read_text(encoding="utf-8")
    ok(OPTIONAL in manifest.splitlines() and "installer_version=1.3.6" in manifest, "new component uses optional_v6 and installer 1.3.6")
    listing = json.loads(core["DOA5LR-Diagnostic/ps4skins-files.json"])
    ok({e["path"]: e["sha256"] for e in listing} == {n: sha(b) for n, b in skins.items()}, "skin integrity list matches actual payload")

    temp = Path(tempfile.mkdtemp(prefix="doa5lr-release-ps4-"))
    counter = 0
    exe = rel / INSTALLER
    local = rel / "version-TEST-LOCAL.txt"
    def game(name, loader=False):
        root = temp / name
        root.mkdir()
        (root / "game.exe").write_bytes(b"fake game - never launched")
        if loader:
            (root / "steam_api.dll").write_bytes(dll(True))
            (root / "original_api.dll").write_bytes(dll())
            (root / "cream_api.ini").write_bytes(b"; personal settings\r\n[steam]\r\nappid = 311730\r\norgapi = original_api.dll\r\nunlockall = false\r\n[dlc]\r\n1234 = unrelated entry\r\n")
        return root
    def run(root, man=local, binary=exe, *extra):
        nonlocal counter
        counter += 1
        cache = temp / f"cache-{counter}"
        cache.mkdir()
        env = dict(os.environ, TEMP=str(cache), TMP=str(cache))
        result = subprocess.run([str(binary), "--auto", "--game", str(root), "--manifest", str(man), *extra], env=env, timeout=180)
        log = (root / "DOA5LR-Salons-Installer.log").read_text(encoding="utf-8", errors="replace")
        if result.returncode:
            print(log[-4000:], flush=True)
        return result.returncode, log
    def skins_ok(root):
        return all((root / n).is_file() and sha((root / n).read_bytes()) == sha(b) for n, b in skins.items())
    def maps_ok(root):
        return all((root / n).is_file() and sha((root / n).read_bytes()) == sha(b) for n, b in maps.items())
    def choice(root, value):
        p = root / "DOA5LR-Salons-Components.txt"
        lines = [l for l in p.read_text().splitlines() if not l.startswith("ps4skins=")]
        p.write_text("\n".join(lines + ["ps4skins=" + str(value)]) + "\n")

    fresh = game("fresh-no-loader")
    code, _ = run(fresh)
    ok(code == 0 and maps_ok(fresh) and not (fresh / "DLC/990015").exists(), "fresh game without native loader: base pack succeeds, skins default off")
    ok("ps4skins=0" in (fresh / "DOA5LR-Salons-Components.txt").read_text(), "off choice recorded")

    g = game("native-loader", True)
    ini_before = (g / "cream_api.ini").read_bytes()
    proxy_before = (g / "steam_api.dll").read_bytes()
    (g / "DLC/9999").mkdir(parents=True)
    (g / "DLC/9999/personal.bin").write_bytes(b"keep unrelated DLC")
    code, _ = run(g)
    ok(code == 0 and skins_ok(g) and maps_ok(g), "fresh supported game installs all real skin and map data")
    ini_after = (g / "cream_api.ini").read_bytes()
    ok(ini_before in ini_after and ini_after.count(b"990015") == 1, "only the dedicated registration is appended")
    ok((g / "steam_api.dll").read_bytes() == proxy_before and (g / "original_api.dll").read_bytes() == dll(), "existing Steam libraries unchanged")
    ok(any(p.read_bytes() == ini_before for p in (g / "DOA5LR-Salons-Backups").rglob("cream_api.ini")), "original loader configuration backed up")

    # Omit BOTH data source archives entirely: intact installed files must suffice.
    intact_manifest = temp / "intact-only-core.txt"
    text = local.read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
        if line.startswith("url="):
            line = "url=" + str(rel / FULL)
        elif line.startswith("core="):
            line = line.replace("core=" + CORE, "core=" + str(rel / CORE))
        elif line.startswith("data="):
            line = line.replace(MAPS, "missing-maps.zip")
        elif line.startswith("skins_data="):
            line = line.replace(SKINS, "missing-skins.zip")
        lines.append(line)
    intact_manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    code, _ = run(g, intact_manifest)
    ok(code == 0 and skins_ok(g) and maps_ok(g), "intact maps and skins reused without either data archive")
    ok((g / "cream_api.ini").read_bytes() == ini_after, "reinstall keeps existing registration byte-identical")

    choice(g, 0)
    code, _ = run(g, intact_manifest)
    ok(code == 0 and not any((g / n).exists() for n in skins), "untick removes all four files without downloading skin data")
    ok((g / "DLC/9999/personal.bin").read_bytes() == b"keep unrelated DLC" and (g / "cream_api.ini").read_bytes() == ini_after, "untick preserves unrelated DLC and loader configuration")
    choice(g, 1)
    code, _ = run(g)
    ok(code == 0 and skins_ok(g), "re-enable restores exact skin payload")
    (g / "DLC/990015/data/990015.bin").write_bytes(b"damaged")
    code, _ = run(g)
    ok(code == 0 and skins_ok(g), "repair restores altered native catalog")

    offline = game("offline-full", True)
    code, _ = run(offline, rel / "version-PS4-COMPLET-LOCAL.txt")
    ok(code == 0 and skins_ok(offline) and maps_ok(offline), "complete PS4 archive installs through 1.3.6 offline manifest")

    older = game("older-installer", True)
    old_ini = (older / "cream_api.ini").read_bytes()
    code, _ = run(older, local, base / INSTALLER)
    ok(code == 0 and maps_ok(older) and not any((older / n).exists() for n in skins), "1.3.5 still installs core/maps safely while ignoring the new skin feature")
    ok((older / "cream_api.ini").read_bytes() == old_ini, "legacy installer never edits loader configuration")
    print("ALL PS4 RELEASE TESTS PASSED\nEvidence: " + str(temp), flush=True)


if __name__ == "__main__":
    main()
