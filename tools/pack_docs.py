"""Pack guide (READ-ME-FIRST-EN.txt and its two START-HERE copies), shared by every release builder from 0.3.11 on.

0.3.10 was built from the 0.3.9 archive without touching the guide, so it shipped a README titled "0.3.9".
A builder must now call pack_guides(VERSION) to write the three copies and check_pack_guides(payload, VERSION)
before zipping: both refuse a guide whose title or download links do not match the version being built.

  python tools/pack_docs.py                    # checks docs/INPUT-SETTINGS.md against the repo version.txt
  python tools/pack_docs.py --zip <pack.zip>   # checks the guide copies inside a built archive
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
from zipfile import ZipFile

REPO = Path(__file__).resolve().parents[1]
GITHUB = "FgcSnow/DOA5LR-Salons"
GUIDE = REPO / "docs" / "INPUT-SETTINGS.md"
GUIDE_COPIES = ("READ-ME-FIRST-EN.txt", "START-HERE.md", "InputLab/START-HERE-EN.md")
# assets that stay on an older release on purpose (the portable controls app was not rebuilt after 0.3.9)
FROZEN_ASSETS = {"DOA5LR-Commandes-portable-0.3.9.zip"}


def release_doc(path: Path, version: str) -> bytes:
    """Bundled docs live outside repo/docs, so relative links become permanent release-tag links."""
    text = path.read_text(encoding="utf-8-sig")

    def replace(match):
        target = match.group(1)
        if ":" in target or target.startswith("#"):
            return match.group(0)
        dest = (path.parent / target.split("#", 1)[0]).resolve()
        if not dest.is_file():
            raise AssertionError(f"missing documentation link in {path.name}: {target}")
        rel = dest.relative_to(REPO).as_posix()
        anchor = "#" + target.split("#", 1)[1] if "#" in target else ""
        return f"](https://github.com/{GITHUB}/blob/v{version}/{rel}{anchor})"
    return re.sub(r"\]\(([^)]+)\)", replace, text).encode("utf-8")


def guide_problems(text: str, version: str) -> list[str]:
    problems = []
    first = text.lstrip("﻿").splitlines()[0] if text.strip() else ""
    if not re.match(rf"# DOA5LR-Salons {re.escape(version)}(?![\d.])", first):
        problems.append(f"title is {first!r}, expected '# DOA5LR-Salons {version} ...'")
    if f"What's new in {version}" not in text:
        problems.append(f"no \"What's new in {version}\" section")
    for tag, asset in re.findall(rf"github\.com/{re.escape(GITHUB)}/releases/download/v([^/]+)/([^)\s]+)", text):
        if tag != version and asset not in FROZEN_ASSETS:
            problems.append(f"download link to v{tag}/{asset} (expected v{version}, or add it to FROZEN_ASSETS)")
    return problems


def pack_guides(version: str) -> dict[str, bytes]:
    guide = release_doc(GUIDE, version)
    problems = guide_problems(guide.decode("utf-8"), version)
    if problems:
        raise AssertionError(f"{GUIDE.relative_to(REPO)} is not ready for {version}: " + "; ".join(problems))
    return {n: guide for n in GUIDE_COPIES}


def check_pack_guides(payload: dict[str, bytes], version: str) -> None:
    missing = [n for n in GUIDE_COPIES if n not in payload]
    if missing:
        raise AssertionError(f"guide copies missing from the pack: {missing}")
    if len({payload[n] for n in GUIDE_COPIES}) != 1:
        raise AssertionError("the three guide copies differ")
    problems = guide_problems(payload[GUIDE_COPIES[0]].decode("utf-8"), version)
    if problems:
        raise AssertionError(f"READ-ME-FIRST-EN.txt is not the {version} guide: " + "; ".join(problems))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zip", type=Path)
    ap.add_argument("--version")
    args = ap.parse_args()
    if args.zip:
        with ZipFile(args.zip) as z:
            payload = {n: z.read(n) for n in z.namelist()}
        version = args.version or payload["DOA5LR-Salons-VERSION.txt"].decode("ascii").strip()
        check_pack_guides(payload, version)
    else:
        version = args.version or re.search(r"^version=(\S+)", (REPO / "version.txt").read_text(encoding="utf-8-sig"), re.M).group(1)
        pack_guides(version)
    print(f"OK: pack guide matches {version}")


if __name__ == "__main__":
    main()
