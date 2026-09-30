"""Add the existing native PS4 costume set to a separate, local 0.3.14 test build.

The tested 0.3.14 release is an immutable input. Only the installer and guides
change; no game module is rebuilt. Old installers receive the legacy full/core
without native DLC files. Installer 1.3.6 adds the independently verified skins
archive. The PS4 full ZIP is also supplied for offline installation with 1.3.6.
No publication, repository manifest update, or installed-game write occurs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import struct
import subprocess
from zipfile import ZipFile

from build_release_0311 import sha, sign, write_zip
from pack_docs import check_pack_guides, pack_guides

REPO = Path(__file__).resolve().parents[1]
VERSION = "0.3.14"
INSTALLER_VERSION = "1.3.6"
INSTALLER = "DOA5LR-Salons-Installer.exe"
FULL = "DOA5LR-Salons-0.3.14.zip"
CORE = "DOA5LR-Salons-core-0.3.14.zip"
MAPS = "DOA5LR-Salons-maps-data-1.zip"
SKINS = "DOA5LR-Salons-ps4skins-data-1.zip"
PS4_FULL = "DOA5LR-Salons-0.3.14-PS4.zip"
REL = "https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.14"
PIN_BASE = {
    FULL: "06d04fc0a34d1fe24569a8bac46c6868dc7b56e28edf579b2769aa629f438722",
    CORE: "721e205d67fa75f25462afc7b3d333c56465aa33cbe98e07fd4c34645d7bf5c9",
    MAPS: "6f16b041b35d2e2f065162264e1f889dc8ad38af828796c90b35ec024bacf99f",
    INSTALLER: "d04a173ff8cf8d3f2d87103f9812ce096f81dbf62afa9ed005e94b284447e07b",
    "version.txt": "15ae9fa62a410da05686237c4bc66da0d2516b514369c0610dbf0dc56469c297",
}
PIN_SKINS = {
    "990015/990015.bcm": (98, "d012baf7474eb77f2508eaddfd1ac327e3ca08c7355065acae4dd1ee0ef0eb22"),
    "990015/data/990015.bin": (5740, "6585063507c60d3de304f8f4c2deca9adf38beaf2e72fd5fcb52df57c98f45d8"),
    "990015/data/990015.blp": (1856, "cbaf9bce28fa61ec0c1b761e89646d50056320c0d53393f89a37650fe04f94e4"),
    "990015/data/990015.lnk": (158736384, "0937a57f94dd5b348baea428d42f2eb844fc0b41c78886f7c97c2c9989aae4a2"),
}
SKINS_GLOBS = ["DLC\\" + n.replace("/", "\\") for n in PIN_SKINS] + [r"scripts\PS4-SKINS-EN.txt"]
SKINS_LABEL = "PS4 skins: 15 costumes (existing local costume loader required)"
OPTIONAL = "optional_v6=ps4skins|" + SKINS_LABEL + "|" + ";".join(SKINS_GLOBS)


def read_zip(path):
    with ZipFile(path) as z:
        if z.testzip() is not None or len(z.namelist()) != len(set(z.namelist())):
            raise ValueError(f"Invalid archive: {path.name}")
        return {n: z.read(n) for n in z.namelist()}


def validate_native(payload):
    """Check the actual container tables, not just their reported checksums."""
    prefix = "DLC/990015/"
    bcm = payload[prefix + "990015.bcm"]
    cat = payload[prefix + "data/990015.bin"]
    blp = payload[prefix + "data/990015.blp"]
    lnk = payload[prefix + "data/990015.lnk"]
    assert cat[:4] == b"LFMO" and blp[:4] == b"1PIF" and lnk[:4] == b"PCDM"
    count = struct.unpack_from("<Q", lnk, 8)[0]
    assert count == 92 == struct.unpack_from("<I", cat, 8)[0] == struct.unpack_from("<I", blp, 4)[0]
    assert struct.unpack_from("<Q", lnk, 16)[0] == len(lnk)
    ids = set()
    for i in range(count):
        offset, size, unpacked, flags = struct.unpack_from("<4Q", lnk, 32 + i * 32)
        asset, bsize, _, _, _ = struct.unpack_from("<5I", blp, 16 + i * 20)
        _, index, name = struct.unpack_from("<3I", cat, 40 + i * 12)
        assert offset >= 32 + count * 32 and offset + size <= len(lnk)
        assert size == unpacked == bsize and flags == 0 and asset not in ids
        assert index == i and name < len(cat) and cat[name:name + 1] == b"/" and cat.find(b"\0", name) >= 0
        ids.add(asset)
    mode, _, costumes, checksum = struct.unpack_from("<BBHI", bcm)
    assert mode == 9 and costumes == 15
    pos, total = 8, 0
    for _ in range(costumes):
        char, costume, variants, hairs = bcm[pos:pos + 4]
        assert variants in (1, 4) and hairs == 1
        total += char * costume
        pos += 4 + 2 * hairs
    assert pos == len(bcm) and checksum == (((total & 4095) * 990016) & 0xffffffff) % (9 * 990015 + 17)


def sums(payload):
    return "".join(f"{sha(b)} *{n}\n" for n, b in sorted(payload.items()) if n != "SHA256SUMS.txt").encode("ascii")


def local_manifest(text, full=None):
    lines = []
    for line in text.splitlines():
        if line.startswith(("installer=", "installer_version=", "installer_sha256=")):
            continue
        if full and line.startswith(("core=", "data=", "skins_data=")):
            continue
        if line.startswith("url="):
            line = "url=" + (PS4_FULL if full else FULL)
        elif line.startswith("sha256=") and full:
            line = "sha256=" + sha(full)
        elif line.startswith("size=") and full:
            line = "size=" + str(len(full))
        elif line.startswith(("core=", "data=", "skins_data=")):
            parts = line.split("|")
            index = 1 if line.startswith("data=") else 0
            name = parts[index].rsplit("/", 1)[-1]
            parts[index] = (line.split("=", 1)[0] + "=" if index == 0 else "") + name
            line = "|".join(parts)
        lines.append(line)
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-dir", type=Path, required=True)
    ap.add_argument("--skins-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    base_dir, out = args.base_dir.resolve(), args.out.resolve()
    if out == base_dir or out.is_relative_to(base_dir) or base_dir.is_relative_to(out):
        raise ValueError("Output must be separate from the validated input release")
    if out.exists() and any(out.iterdir()):
        raise ValueError("Use an empty output directory; existing releases are never overwritten")
    for name, digest in PIN_BASE.items():
        if sha((base_dir / name).read_bytes()) != digest:
            raise ValueError(f"Input differs from the validated 0.3.14: {name}")
    base = read_zip(base_dir / FULL)
    maps = read_zip(base_dir / MAPS)
    assert read_zip(base_dir / CORE) | maps == base
    skins = {}
    for name, (size, digest) in PIN_SKINS.items():
        data = (args.skins_dir / name).read_bytes()
        if len(data) != size or sha(data) != digest:
            raise ValueError(f"Skin file differs from the audited native set: {name}")
        skins["DLC/" + name] = data
    validate_native(skins)
    installer_src = REPO / "src/Installer"
    source = (installer_src / "Installer.cs").read_bytes()
    for marker in (f'AppVersion = "{INSTALLER_VERSION}"', 'case "optional_v6"', 'case "skins_data"', SKINS_LABEL):
        if marker.encode() not in source:
            raise ValueError(f"Installer source missing: {marker}")
    # Exact allowlist must match the table compiled into the installer.
    for name in SKINS_GLOBS:
        assert name.encode() in source
    print("Building and signing installer 1.3.6; existing game modules remain byte-identical.", flush=True)
    subprocess.run(["cmd", "/c", str(installer_src / "build.cmd")], cwd=installer_src, check=True)
    installer = sign({INSTALLER: (installer_src / INSTALLER).read_bytes()})[INSTALLER]
    listing = [{"path": n, "sha256": sha(b), "size": len(b)} for n, b in skins.items()]
    changed = {
        INSTALLER: installer,
        "scripts/Installer-Source/Installer.cs": source,
        **pack_guides(VERSION),
    }
    added = {
        "scripts/PS4-SKINS-EN.txt": (REPO / "src/PS4Skins/PS4-SKINS-EN.txt").read_bytes(),
        "DOA5LR-Diagnostic/ps4skins-files.json": (json.dumps(listing, indent=2) + "\n").encode(),
    }
    legacy = {**base, **changed, **added}
    legacy["SHA256SUMS.txt"] = sums(legacy)
    core = {n: b for n, b in legacy.items() if n not in maps}
    complete = {**legacy, **skins}
    complete["SHA256SUMS.txt"] = sums(complete)
    for n, data in base.items():
        if n not in changed and n != "SHA256SUMS.txt":
            assert legacy[n] == data, n
    assert not any(n.lower().startswith("dlc/") for n in legacy)
    assert core | maps == legacy and not core.keys() & maps.keys()
    check_pack_guides(legacy, VERSION)
    check_pack_guides(complete, VERSION)
    out.mkdir(parents=True, exist_ok=True)
    for name, payload in ((FULL, legacy), (CORE, core), (SKINS, skins), (PS4_FULL, complete)):
        print(f"Writing and verifying {name} ({len(payload)} files)", flush=True)
        write_zip(out / name, payload)
    shutil.copy2(base_dir / MAPS, out / MAPS)
    (out / INSTALLER).write_bytes(installer)
    drop = ("url=", "sha256=", "size=", "core=", "data=", "skins_data=", "installer=", "installer_version=", "installer_sha256=", "optional_v6=", "notes=")
    lines = [l for l in (base_dir / "version.txt").read_text(encoding="utf-8-sig").splitlines() if not l.startswith(drop)]
    assets = {name: (sha((out / name).read_bytes()), (out / name).stat().st_size) for name in (FULL, CORE, MAPS, SKINS, PS4_FULL, INSTALLER)}
    lines[2:2] = [
        f"url={REL}/{FULL}", f"sha256={assets[FULL][0]}", f"size={assets[FULL][1]}",
        f"core={REL}/{CORE}|{assets[CORE][0]}|{assets[CORE][1]}",
        f"data=maps|{REL}/{MAPS}|{assets[MAPS][0]}|{assets[MAPS][1]}",
        f"skins_data={REL}/{SKINS}|{assets[SKINS][0]}|{assets[SKINS][1]}",
        f"installer={REL}/{INSTALLER}", f"installer_version={INSTALLER_VERSION}", f"installer_sha256={sha(installer)}",
        "notes=pack 0.3.14 + optional PS4 skins test: 15 native costumes, separate download, installer 1.3.6",
        "note=PS4 skins: requires an existing compatible local costume loader. Installer 1.3.6 checks it before installing; no Steam DLL is supplied or replaced. Snow confirmed the 15 costumes and color variants in combat and has played online with this set.",
        "note=PS4 skins use a separate download; intact installed data is reused. Older installers keep installing the core pack and stages, then need their own update to offer the skins option.",
        OPTIONAL,
    ]
    manifest = "\n".join(lines) + "\n"
    (out / "version.txt").write_text(manifest, encoding="utf-8", newline="\n")
    (out / "version-TEST-LOCAL.txt").write_text(local_manifest(manifest), encoding="utf-8", newline="\n")
    (out / "version-PS4-COMPLET-LOCAL.txt").write_text(local_manifest(manifest, (out / PS4_FULL).read_bytes()), encoding="utf-8", newline="\n")
    (out / "TESTER-PS4-LOCAL.cmd").write_text('@echo off\nrem Local test only; nothing is published.\n"%~dp0DOA5LR-Salons-Installer.exe" --manifest "%~dp0version-TEST-LOCAL.txt"\n', encoding="ascii", newline="\r\n")
    (out / "SHA256SUMS.txt").write_text("".join(f"{digest} *{name}\n" for name, (digest, _) in assets.items()), encoding="ascii", newline="\n")
    report = {
        "version": VERSION, "installer_version": INSTALLER_VERSION, "status": "local_test_not_published",
        "base_sha256": PIN_BASE[FULL], "costumes": 15, "resources": 92, "skins_uncompressed_bytes": sum(map(len, skins.values())),
        "assets": {n: {"sha256": digest, "bytes": size} for n, (digest, size) in assets.items()},
        "changed_base_files": sorted(changed.keys() | {"SHA256SUMS.txt"}), "added_legacy_files": sorted(added),
        "skins_files": listing, "existing_modules_unchanged": True,
        "gameplay_validation": "Snow confirmed all 15 costumes and variants in combat, including online use, on 2026-09-30", "prerequisite": "existing compatible native costume loader; no Steam DLL included",
    }
    (out / "build-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (out / "LIRE-MOI-PS4.txt").write_text(
        "PACK 0.3.14 + SKINS PS4 - TEST LOCAL\n\n"
        "15 costumes PS4 et leurs variantes, avec installateur 1.3.6. Rien n'est publie.\n"
        "Lancer TESTER-PS4-LOCAL.cmd puis verifier l'option PS4 skins. Le jeu doit etre ferme pour installer.\n"
        "Le format natif exige le chargeur de costumes compatible deja present sur ton installation.\n"
        "L'installateur ne fournit ni ne remplace les DLL Steam; il ajoute seulement l'entree locale 990015 au chargeur existant.\n"
        "Les reglages existants sont sauvegardes. Decocher PS4 skins retire seulement les quatre fichiers de ce lot.\n\n"
        "Le ZIP -PS4 est le pack complet avec les skins. Le ZIP sans -PS4 sert aux anciens installateurs;\n"
        "l'installateur 1.3.6 complete ce dernier avec ps4skins-data-1.zip quand l'option est active.\n"
        "Les donnees des maps et skins ne sont pas retéléchargees si elles sont intactes.\n\n"
        "Snow a confirme le 30/09/2026 que les 15 costumes et variantes fonctionnent en combat,\n"
        "et avoir deja joue en ligne avec ce lot. Les fichiers sont identiques a ce lot valide.\n"
        "Les emplacements sont indiques dans scripts/PS4-SKINS-EN.txt.\n"
        "Aucun effet experimental de destruction/transformation de tenue n'est inclus.\n",
        encoding="utf-8-sig", newline="\r\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
