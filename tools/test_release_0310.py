"""Exercise the 0.3.10 release artifacts with the real installer in temporary fake game folders (never Steam).

python tools/test_release_0310.py --release-dir <DOA5LR-Salons-0.3.10-Release> --base-dir <DOA5LR-Salons-0.3.9-Release>
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
    pack = args.release_dir / "DOA5LR-Salons-0.3.10.zip"
    base_pack = args.base_dir / "DOA5LR-Salons-0.3.9.zip"
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
    same = [n for n in base if n not in ("DOA5LR-Salons-VERSION.txt", "SHA256SUMS.txt", *GUIDE_COPIES)]
    check_pack_guides(final, "0.3.10")
    require(True, "guide copies are the 0.3.10 guide (r2)")
    require(all(final[n] == base[n] for n in same), f"{len(same)} files of 0.3.9 byte-identical")
    require(sorted(set(final) - set(base)) == sorted(["scripts/DOA5LR-JoinFix.asi", "scripts/DOA5LR-JoinFix.ini", "scripts/JOINFIX-EN.txt",
            "scripts/JoinFix-Source/build.cmd", "scripts/JoinFix-Source/joinfix.c", "scripts/JoinFix-Source/version.rc"]), "only JoinFix files added")
    asi = final["scripts/DOA5LR-JoinFix.asi"]
    require(asi[:2] == b"MZ" and b"DOA5LR-JoinFix.log" not in asi and b"KeyTest" not in asi, "JoinFix release build: no log, no test mode")
    ini = final["scripts/DOA5LR-JoinFix.ini"].decode()
    require("KeyFix=1" in ini and "FastFail=0" in ini and "CopyLinkKey=118" in ini and "KeyTest" not in ini, "JoinFix defaults: KeyFix on, FastFail off")
    require(final["DOA5LR-Salons-VERSION.txt"] == b"0.3.10\r\n", "pack version file")
    require(final["DOA5LR-Salons-Installer.exe"] == exe.read_bytes() == (args.base_dir / exe.name).read_bytes(), "installer 1.3.1 unchanged")
    mf = (args.release_dir / "version.txt").read_text(encoding="utf-8")
    require(f"sha256={sha(pack.read_bytes())}" in mf and "version=0.3.10" in mf and "/v0.3.10/" in mf, "manifest points to the 0.3.10 assets")

    with tempfile.TemporaryDirectory(prefix="doa5lr-0310-") as td:
        temp = Path(td)

        def local_manifest(src_text, archive, name):
            t = "\n".join("url=" + str(archive) if l.startswith("url=") else l for l in src_text.splitlines()) + "\n"
            p = temp / name; p.write_text(t, encoding="utf-8"); return p
        m310 = local_manifest(mf, pack, "m310.txt")
        m39 = local_manifest((args.base_dir / "version.txt").read_text(encoding="utf-8-sig"), base_pack, "m39.txt")

        def game(name):
            g = temp / name; g.mkdir(); (g / "game.exe").write_bytes(b"fake game, never executed"); return g

        def install(g, mfile):
            r = subprocess.run([str(exe), "--auto", "--game", str(g), "--manifest", str(mfile)], capture_output=True, text=True)
            log = (g / "DOA5LR-Salons-Installer.log").read_text(encoding="utf-8", errors="replace")
            require(r.returncode == 0 and "auto: OK" in log.splitlines()[-1], f"installer --auto OK ({g.name}, {mfile.name})")
            return log

        fresh = game("fresh")
        install(fresh, m310)
        require((fresh / "DOA5LR-Salons-VERSION.txt").read_text().strip() == "0.3.10", "fresh install is 0.3.10")
        require((fresh / "scripts/DOA5LR-JoinFix.asi").read_bytes() == asi, "fresh install has JoinFix")
        require((fresh / "scripts/DOA5LR-JoinFix.ini").read_text().count("KeyFix=1") == 1, "fresh install has JoinFix.ini")

        upd = game("update")
        install(upd, m39)
        require((upd / "DOA5LR-Salons-VERSION.txt").read_text().strip() == "0.3.9", "starting point is 0.3.9")
        (upd / "scripts/DOA5LR-WiFi-Wired-Detector.ini").write_text("[NetBoost]\nLinkOverride=2\n", encoding="utf-8")
        install(upd, m310)
        require((upd / "DOA5LR-Salons-VERSION.txt").read_text().strip() == "0.3.10", "0.3.9 -> 0.3.10 update")
        require((upd / "scripts/DOA5LR-JoinFix.asi").read_bytes() == asi, "update adds JoinFix")
        require("LinkOverride=2" in (upd / "scripts/DOA5LR-WiFi-Wired-Detector.ini").read_text(), "user settings kept across the update")
        for n in ("scripts/DOA5LR-Lobby.asi", "scripts/DOA5LR-InviteFix.asi", "scripts/DOA5LR-WiFi-Wired-Detector.asi", "dinput8.dll"):
            require((upd / n).read_bytes() == base[n], "unchanged after update: " + n)

        # a player who already tuned JoinFix keeps their settings on a later reinstall
        (upd / "scripts/DOA5LR-JoinFix.ini").write_text("[JoinFix]\nKeyFix=1\nFastFail=1\n", encoding="utf-8")
        install(upd, m310)
        require("FastFail=1" in (upd / "scripts/DOA5LR-JoinFix.ini").read_text(), "JoinFix.ini kept on reinstall (keep=*.ini)")
    print("ALL PASS")


if __name__ == "__main__":
    main()
