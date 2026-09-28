"""Exercise the 0.3.12 release artifacts with the real installer in temporary fake game folders (never Steam).

python tools/test_release_0312.py --release-dir <DOA5LR-Salons-0.3.12-Release> --base-dir <DOA5LR-Salons-0.3.11-Release>
"""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile
from zipfile import ZipFile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pack_docs import GUIDE_COPIES, check_pack_guides  # noqa: E402

TAKEOVER = ["DOA5LR-ReplayTakeover.asi", "scripts/REPLAY-TAKEOVER-EN.txt",
            "scripts/ReplayTakeover-Source/ReplayTakeover.cpp", "scripts/ReplayTakeover-Source/build.cmd"]


def require(condition, message):
    if not condition:
        raise AssertionError(message)
    print("PASS:", message, flush=True)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--release-dir", required=True, type=Path)
    ap.add_argument("--base-dir", required=True, type=Path)
    args = ap.parse_args()
    exe = args.release_dir / "DOA5LR-Salons-Installer.exe"
    pack = args.release_dir / "DOA5LR-Salons-0.3.12.zip"
    base_pack = args.base_dir / "DOA5LR-Salons-0.3.11.zip"
    with ZipFile(pack) as z:
        require(z.testzip() is None, "archive CRCs")
        final = {n: z.read(n) for n in z.namelist()}
    with ZipFile(base_pack) as z:
        base = {n: z.read(n) for n in z.namelist()}
    for line in final["SHA256SUMS.txt"].decode().splitlines():
        digest, name = line.split(" *", 1)
        if sha(final[name]) != digest:
            raise AssertionError("internal checksum: " + name)
    require(len(final["SHA256SUMS.txt"].decode().splitlines()) == len(final) - 1, "internal checksum coverage and values")
    check_pack_guides(final, "0.3.12")
    require(True, "guide copies are the 0.3.12 guide")
    require(set(final) == set(base), "same file list as 0.3.11")
    diff = sorted(n for n in final if final[n] != base[n])
    require(diff == sorted(TAKEOVER + ["DOA5LR-Salons-VERSION.txt", "SHA256SUMS.txt", *GUIDE_COPIES]),
            "only Replay Takeover files, guides, version and checksums differ from 0.3.11")
    asi = final["DOA5LR-ReplayTakeover.asi"]
    require(asi[:2] == b"MZ" and "Takeover 2.6".encode() in asi and b"En ligne : module en veille" in asi, "Replay Takeover 2.6 binary")
    require(final["DOA5LR-Salons-VERSION.txt"] == b"0.3.12\r\n", "pack version file")
    require(final["DOA5LR-Salons-Installer.exe"] == exe.read_bytes() == (args.base_dir / exe.name).read_bytes(), "installer 1.3.2 unchanged")
    mf = (args.release_dir / "version.txt").read_text(encoding="utf-8")
    require(f"sha256={sha(pack.read_bytes())}" in mf and "version=0.3.12" in mf and "/v0.3.12/DOA5LR-Salons-Installer.exe" in mf
            and "installer_version=1.3.2" in mf and "optional_v3=replaytakeover|" in mf, "manifest points to the 0.3.12 assets")

    with tempfile.TemporaryDirectory(prefix="doa5lr-0312-") as td:
        temp = Path(td)

        def local_manifest(src_text, archive, name):
            t = "\n".join("url=" + str(archive) if l.startswith("url=") else l for l in src_text.splitlines()) + "\n"
            p = temp / name; p.write_text(t, encoding="utf-8"); return p
        m312 = local_manifest(mf, pack, "m312.txt")
        m311 = local_manifest((args.base_dir / "version.txt").read_text(encoding="utf-8-sig"), base_pack, "m311.txt")

        def game(name):
            g = temp / name; g.mkdir(); (g / "game.exe").write_bytes(b"fake game, never executed"); return g

        def install(g, mfile):
            r = subprocess.run([str(exe), "--auto", "--game", str(g), "--manifest", str(mfile)], capture_output=True, text=True)
            log = (g / "DOA5LR-Salons-Installer.log").read_text(encoding="utf-8", errors="replace")
            require(r.returncode == 0 and "auto: OK" in log.splitlines()[-1], f"installer --auto OK ({g.name}, {mfile.name})")
            return log

        fresh = game("fresh")
        install(fresh, m312)
        require((fresh / "DOA5LR-Salons-VERSION.txt").read_text().strip() == "0.3.12", "fresh install is 0.3.12")
        require((fresh / "DOA5LR-ReplayTakeover.asi").read_bytes() == asi, "fresh install has Replay Takeover 2.6 next to game.exe")

        upd = game("update")
        install(upd, m311)
        require((upd / "DOA5LR-Salons-VERSION.txt").read_text().strip() == "0.3.11", "starting point is 0.3.11")
        require((upd / "DOA5LR-ReplayTakeover.asi").read_bytes() == base["DOA5LR-ReplayTakeover.asi"], "0.3.11 has Takeover 2.5")
        (upd / "DOA5LR-ReplayTakeover.ini").write_text("[ReplayTakeover]\nEnabled=1\nPasRattrapage=6\n", encoding="utf-8")
        install(upd, m312)
        require((upd / "DOA5LR-Salons-VERSION.txt").read_text().strip() == "0.3.12", "0.3.11 -> 0.3.12 update")
        require((upd / "DOA5LR-ReplayTakeover.asi").read_bytes() == asi, "update replaces Takeover 2.5 with 2.6")
        require("PasRattrapage=6" in (upd / "DOA5LR-ReplayTakeover.ini").read_text(), "Replay Takeover settings kept")
        for n in ("scripts/DOA5LR-Lobby.asi", "scripts/DOA5LR-JoinFix.asi", "scripts/DOA5LR-InviteFix.asi", "dinput8.dll"):
            require((upd / n).read_bytes() == base[n], "unchanged after update: " + n)

        # a player who unticked Replay Takeover in 0.3.11 does not get it back with 0.3.12
        off = game("unticked")
        install(off, m311)
        (off / "DOA5LR-Salons-Components.txt").write_text("borderless=1\n60fps=1\ninputlab=0\nreplaytakeover=0\n", encoding="utf-8")
        install(off, m311)
        require(not (off / "DOA5LR-ReplayTakeover.asi").exists(), "0.3.11 with Replay Takeover unticked")
        install(off, m312)
        require(not (off / "DOA5LR-ReplayTakeover.asi").exists() and
                (off / "DOA5LR-Salons-VERSION.txt").read_text().strip() == "0.3.12", "unticked choice kept by the 0.3.12 update")
    print("ALL PASS")


if __name__ == "__main__":
    main()
