# DOA5LR-Salons — Community Lobby Mods for Dead or Alive 5 Last Round (PC)

Community mod pack by **FGCsnow & BonuStage**: online lobbies, Steam invites, private rooms, 60 fps menus, borderless window, wired/Wi-Fi indicator with real ping, controller fix (Xidi), AutoLink — and a one-click installer that keeps everything up to date.

**Support the project: https://www.patreon.com/cw/DoA5LRcommunitymod**

## Install / update

**0.3.6 (21 September 2026): manual install** — the one-click installer is set aside until Microsoft clears a false positive (see *Antivirus warnings* below).

1. Download **`DOA5LR-Salons-0.3.6.zip`** from the [latest release](../../releases/latest). Close the game.
2. Extract the zip **over the game folder** (Steam → right-click the game → Manage → Browse local files), replace everything. Updating from 0.3.3-0.3.5: that's all. From an older pack: read `READ-ME-FIRST-EN.txt` first (old root files to delete).
3. Start the game via Steam. Online → **LOBBY**.

If you already have `DOA5LR-Salons-Installer.exe` (from the 0.3.5 release) and your antivirus lets it run, UPDATE still installs this pack with a backup — extract it to a folder first, never run it from inside the archive. When a new version is out, `DOA5LR-UpdateCheck.asi` tells you at game exit.

## What's inside

| Component | Version | Role |
|---|---|---|
| Lobby | 0.9.0 | Native LOBBY entry, invites, private rooms |
| InviteFix | 0.1.1 | Invite button compatibility fix |
| WiFi-Wired-Detector | 0.8.6 | Wired/Wi-Fi tag, netcode stats, ping in the lobby list |
| 60fps-menus | 0.13c | 60 fps menus, intros, win poses and story cutscenes **offline only** — does nothing at all in the Online menu |
| Borderless | 1.1 | Borderless by default, F11 cycles Borderless / Window / Fullscreen |
| UpdateCheck | 1.0 | Reads `version.txt`, tells you at game exit when a new pack is out |
| Installer | 1.0.2 (set aside in 0.3.6) | One-click install / update / restore — source in `src/Installer`, back as a separate download once cleared |
| Ultimate ASI Loader, AutoLink 3.30, Xidi 5.0.0 | | Loader, costumes, controllers |

## Privacy

The pack **sends nothing anywhere**, and our plugins **write no log files** (the only file written is Lobby 0.9.0's local `DOA5LR-Lobby.log` diagnostic, see `LOBBY-EN.txt`; it never leaves your PC). The only network access besides the game's own is `DOA5LR-UpdateCheck.asi` reading one public text file (`version.txt` on this branch) to know whether a newer pack exists. Every plugin is open source and shipped as a release build without logging code, with embedded version information; every binary is scanned with Microsoft Defender before release, and the installer verifies each download by SHA256. The pack contains **no game content and no Steam API / DLC files**. Our binaries are signed (see below). Sources are in this repository (`src/`) and in the zip (`scripts\*-Source\`).

## Build it yourself / verify a release

Every plugin and the installer are open source, in [`src/`](src/) — one C file per plugin, one C# file for the installer, exactly as released. `src/build-all.cmd` builds everything with [LLVM-MinGW](https://github.com/mstorsjo/llvm-mingw) (`winget install MartinStorsjo.LLVM-MinGW.UCRT`) and the C# compiler that ships in Windows; no SDK to install. Plugin builds are reproducible: your `.asi` should match `SHA256SUMS-unsigned.txt` attached to each release. Read [`src/README.md`](src/README.md).

The Lobby module (`DOA5LR-Lobby.asi`) is a third-party community build shipped as received; we do not hold its source.

## Antivirus warnings and code signing

An `.asi` plugin is a DLL that patches the game in memory — the same pattern some malware uses, so heuristic antivirus engines and SmartScreen ("not commonly downloaded") may complain. That is why the sources are public and reproducible: read, build, compare.

Since 0.3.6 our binaries are signed with a self-signed certificate (subject `CN=FGCsnow - DOA5LR-Salons`, thumbprint `0EBE9F4F8879992F594F99E7B38C4B024A68F978`, timestamped). It is **not** a CA-issued certificate — Windows shows it as untrusted, do not install it as a trusted root; it only guarantees a file was not altered since we signed it. If your antivirus flags a file, please **report it as a false positive** — every report counts and helps the whole community: Microsoft Defender → https://www.microsoft.com/wdsi/filesubmission ; Kaspersky → https://opentip.kaspersky.com (upload the file, then "Report false positive") ; other vendors have a similar form. Kaspersky users: its System Watcher may kill the installer *after* a successful install and roll the files back (`PDM:Trojan.Win32.Generic`) — restore the installer from the quarantine, add it to *Trusted applications*, and always extract the zip to a folder before running it (never from inside WinRAR/7-Zip). We have submitted the installer to Microsoft and to the Kaspersky Allowlist program.

## License

Our code (everything in `src/`: plugins and installer) is released under the [MIT License](LICENSE). It does not cover the third-party components shipped in the pack under their own terms: the Lobby module (community build), Ultimate ASI Loader (ThirteenAG), AutoLink (FallingCat), Xidi (Samuel Grossman) and the optional resolution mod (Steffen André Langnes).

## Credits

Original "Auto Installer for DOA5 Community Lobby Mods" concept: **BRG Hades**. `scripts\` layout: **WAZAAAAA**. Lobby module: community build. Ultimate ASI Loader: ThirteenAG. AutoLink: FallingCat. Xidi: Samuel Grossman. Optional resolution mod: Steffen André Langnes. Testers: everyone in the DOA5LR lobbies — thank you.
