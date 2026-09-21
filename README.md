# DOA5LR-Salons — Community Lobby Mods for Dead or Alive 5 Last Round (PC)

Community mod pack by **FGCsnow & BonuStage**: online lobbies, Steam invites, private rooms, 60 fps menus, borderless window, wired/Wi-Fi indicator with real ping, controller fix (Xidi), AutoLink — and a one-click installer that keeps everything up to date.

**Support the project: https://www.patreon.com/cw/DoA5LRcommunitymod**

## Install / update

1. Download **`DOA5LR-Salons-Installer.exe`** from the [latest release](../../releases/latest).
2. Run it (the game must be closed). It finds the game through Steam — click **INSTALL MOD PACK** (or **UPDATE**).
3. Start the game via Steam. Online → **LOBBY**.

That's it. The installer backs up every file it touches (`DOA5LR-Salons-Backups\` in the game folder) and can restore it. When a new version is out, the installer offers it — and the game opens the installer by itself after you close it.

Prefer doing it by hand? Download the zip and read `READ-ME-FIRST-EN.txt`.

## What's inside

| Component | Version | Role |
|---|---|---|
| Lobby | 0.9.0 | Native LOBBY entry, invites, private rooms |
| InviteFix | 0.1.1 | Invite button compatibility fix |
| WiFi-Wired-Detector | 0.8.6 | Wired/Wi-Fi tag, netcode stats, ping in the lobby list |
| 60fps-menus | 0.13b | 60 fps menus, intros, win poses (offline and online), story cutscenes |
| Borderless | 1.1 | Borderless by default, F11 cycles Borderless / Window / Fullscreen |
| UpdateCheck | 1.0 | Reads `version.txt`, opens the installer at game exit when a new pack is out |
| Installer | 1.0.2 | One-click install / update / restore |
| Ultimate ASI Loader, AutoLink 3.30, Xidi 5.0.0 | | Loader, costumes, controllers |

## Privacy

The pack **sends nothing anywhere**, and our plugins **write no log files** (the only file written is Lobby 0.9.0's local `DOA5LR-Lobby.log` diagnostic, see `LOBBY-EN.txt`; it never leaves your PC). The only network access besides the game's own is `DOA5LR-UpdateCheck.asi` reading one public text file (`version.txt` on this branch) to know whether a newer pack exists. Every plugin is open source and shipped as a release build without logging code, with embedded version information; every binary is scanned with Microsoft Defender before release, and the installer verifies each download by SHA256. The pack contains **no game content and no Steam API / DLC files**. Sources are in this repository (see below) and in the zip (`scripts\*-Source\`, `Installer-Source\`).

## Build it yourself / verify a release

Every plugin and the installer are open source, in [`src/`](src/) — one C file per plugin, one C# file for the installer, exactly as released. `src/build-all.cmd` builds everything with [LLVM-MinGW](https://github.com/mstorsjo/llvm-mingw) (`winget install MartinStorsjo.LLVM-MinGW.UCRT`) and the C# compiler that ships in Windows; no SDK to install. Plugin builds are reproducible: your `.asi` should match `SHA256SUMS-unsigned.txt` attached to each release. Read [`src/README.md`](src/README.md).

The Lobby module (`DOA5LR-Lobby.asi`) is a third-party community build shipped as received; we do not hold its source.

## Antivirus warnings and code signing

An `.asi` plugin is a DLL that patches the game in memory — the same pattern some malware uses, so heuristic antivirus engines and SmartScreen ("not commonly downloaded") may complain. That is why the sources are public and reproducible: read, build, compare.

Since 0.3.6 our binaries are signed with a self-signed certificate (subject `CN=FGCsnow - DOA5LR-Salons`, thumbprint `0EBE9F4F8879992F594F99E7B38C4B024A68F978`, timestamped). It is **not** a CA-issued certificate — Windows shows it as untrusted, do not install it as a trusted root; it only guarantees a file was not altered since we signed it. If Defender flags a file, you can submit it as a false positive: https://www.microsoft.com/wdsi/filesubmission

## License

Our code (everything in `src/`) is released under the [MIT License](LICENSE). Third-party components keep their own terms.

## Credits

Original "Auto Installer for DOA5 Community Lobby Mods" concept: **BRG Hades**. `scripts\` layout: **WAZAAAAA**. Lobby module: community build. Ultimate ASI Loader: ThirteenAG. AutoLink: FallingCat. Xidi: Samuel Grossman. Optional resolution mod: Steffen André Langnes. Testers: everyone in the DOA5LR lobbies — thank you.
