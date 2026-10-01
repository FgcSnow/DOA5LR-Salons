# DOA5LR-Salons 0.3.16 — correct stage thumbnails, tidier game folder, fewer antivirus false positives

**Update: download `DOA5LR-Salons-Installer.exe` below and open it (close the game first).** It only downloads what changed: about 10 MB when your stage files are intact. The other files are used by the installer automatically.

## Fixes

- **Wrong stage thumbnails:** some tiles showed the picture of another stage while still loading the right one (Lorelei Halloween, and the lower levels of Scramble, Plant and Circus you reach with the up arrow). Every tile has its own picture again, and The Crimson 1 now has its own PS4 picture.
- **Fewer antivirus false positives ("Wacatac" and similar):** the pack modules are now built with other compiler options (`-O1`, thanks WAZAAAAA) and every module is signed (JoinFix stays the validated 0.3 build). Same source code, same behaviour.
- **Tidier game folder** (thanks Odd): the stage modules and their `.ini` files are now in `scripts\DOA5LR-Stages\`, their logs in `DOA5LR-Logs\`. Your settings are moved with them and kept; the update removes the old copies.

## Changes

- **PS4 skins are no longer part of the pack.** If you installed them, the update leaves them in place (it no longer installs, checks or removes them).
- **Installer 1.3.11:** knows the new folder and never leaves a module in two places. Older installers offer it first: accept it.

## Files

| File | Use | SHA-256 |
| --- | --- | --- |
| `DOA5LR-Salons-Installer.exe` | **Install / update (recommended)** | `d5f4fec86a1b701e7e5596526bbac49e5e12915b165d8ef8b6a60a808c398d7d` |
| `DOA5LR-Salons-0.3.16.zip` | Full pack, manual install on a fresh game only | `0533954bb196c567444a73e5410a77921207324360a98e763679e25ad2f63b86` |
| `DOA5LR-Salons-core-0.3.16.zip` | Used by the installer | `b39dcc03b538b31d89445456c6cb08a6306ea3f8c7dc95c186739989aee23a98` |
| `DOA5LR-Salons-maps-data-2.zip` | Used by the installer (stage data) | `f1215a8013e84c2aa07fb91926218ed0da12809a6e1d6859116f96dbdf792249` |

PS: there is a little surprise hidden in this patch 👀 Have fun finding it.

Support the project: https://www.patreon.com/cw/DoA5LRcommunitymod
