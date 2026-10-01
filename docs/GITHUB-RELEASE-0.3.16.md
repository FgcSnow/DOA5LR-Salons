# DOA5LR-Salons 0.3.16 — correct stage thumbnails, tidier game folder, fewer antivirus false positives

**Update: download `DOA5LR-Salons-Installer.exe` below and open it (close the game first).** It only downloads what changed: about 10 MB when your stage files are intact. The other files are used by the installer automatically.

## Fixes

- **Wrong stage thumbnails:** some tiles showed the picture of another stage while still loading the right one (Lorelei Halloween, and the lower levels of Scramble, Plant and Circus you reach with the up arrow). Every tile has its own picture again, and The Crimson 1 now has its own PS4 picture.
- **Fewer antivirus false positives ("Wacatac" and similar):** the pack modules are now built with other compiler options (`-O1`, thanks WAZAAAAA) and every module is signed. Same source code, same behaviour.
- **Tidier game folder** (thanks Odd): the stage modules and their `.ini` files are now in `scripts\DOA5LR-Stages\`, their logs in `DOA5LR-Logs\`. Your settings are moved with them and kept; the update removes the old copies.

## Changes

- **PS4 skins are no longer part of the pack.** If you installed them, the update leaves them in place (it no longer installs, checks or removes them).
- **Installer 1.3.11:** knows the new folder and never leaves a module in two places. Older installers offer it first: accept it.

## Files

| File | Use | SHA-256 |
| --- | --- | --- |
| `DOA5LR-Salons-Installer.exe` | **Install / update (recommended)** | `bf76c2c1587640f28593c9a844bbe32575e191da0c665f0808e4766f76c1c147` |
| `DOA5LR-Salons-0.3.16.zip` | Full pack, manual install on a fresh game only | `926e5e566fd1f62f824c99044e2930fdf1ffdf16fb00bb73b54663242e6fe31f` |
| `DOA5LR-Salons-core-0.3.16.zip` | Used by the installer | `ca1d911db45e1882d7841c0678e2b6943fc484884731488bb642a077110bdcb6` |
| `DOA5LR-Salons-maps-data-2.zip` | Used by the installer (stage data) | `f1215a8013e84c2aa07fb91926218ed0da12809a6e1d6859116f96dbdf792249` |

Support the project: https://www.patreon.com/cw/DoA5LRcommunitymod
