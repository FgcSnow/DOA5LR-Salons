# DOA5LR-Salons — Community Lobby Mods for Dead or Alive 5 Last Round (PC)

Community mod pack by **FGCsnow & BonuStage**: online lobbies, Steam invites, private rooms, 60 fps menus, borderless window, wired/Wi-Fi indicator with real ping, controller fix (Xidi), AutoLink — and a one-click installer that keeps everything up to date.

**Support the project: https://www.patreon.com/cw/DoA5LRcommunitymod**

## Install / update

1. Download **`DOA5LR-Salons-Installer.exe`** from the [latest release](../../releases/latest) and save it in a folder (Downloads is fine). Never run it from inside an archive.
2. Run it (the game must be closed). It finds the game through Steam: click **INSTALL MOD PACK** (or **UPDATE**).
3. Start the game via Steam. Online → **LOBBY**.

That's it. The installer backs up every file it touches (`DOA5LR-Salons-Backups\` in the game folder) and can restore it. Since 1.0.3 it also **checks that every required file is present** (at start, after each install, and when the game closes) and warns you if your antivirus quarantined one: do not play with a partial pack, restore the file, add the game folder to the exclusions, click REINSTALL. When a new version is out, the installer offers it, and the game opens the installer by itself after you close it.

Prefer doing it by hand? Download the zip and read `READ-ME-FIRST-EN.txt`.

## What's inside

| Component | Version | Role |
|---|---|---|
| Lobby | 0.9.0 | Native LOBBY entry, invites, private rooms |
| InviteFix | 0.1.1 | Invite button compatibility fix |
| WiFi-Wired-Detector | 0.8.8 | Wired/Wi-Fi tag next to names (ping display removed in 0.3.7, force-wired setting removed in 0.3.8) — always installed |
| 60fps-menus | 0.13c | 60 fps menus, intros, win poses and story cutscenes **offline only** — does nothing at all in the Online menu |
| Borderless | 1.1 | Unchecked for new installer installations; existing choices preserved. F11 cycles display modes when installed |
| UpdateCheck | 1.0 | Reads `version.txt`, tells you at game exit when a new pack is out |
| Installer | 1.1.0 | One-click install / update / restore, check boxes for the optional components (Borderless, 60fps-menus) — source in `src/Installer`, separate download on each release |
| Ultimate ASI Loader, AutoLink 3.30, Xidi 5.0.0 | | Loader, costumes, controllers |

## Privacy

Release builds of the pack-maintained plugins disable diagnostic logging. Lobby 0.9.0 is an external exception and writes a local log. UpdateCheck reads a public version manifest; the installer downloads updates; WiFi-Wired exchanges connection information and ping messages with participating peers. Lobby's sources are not included and its binary is unsigned. Sources for the maintained components are in `src/` and `scripts\*-Source\`. The build scans binaries with Defender and the installer checks download hashes, but these checks and self-signed signatures do not guarantee safety or compatibility. The pack contains no game content or Steam API / DLC files.

## Build it yourself / verify a release

Sources for pack-maintained plugins and the installer are in [`src/`](src/). `src/build-all.cmd` builds these components, not external dependencies such as Lobby or AutoLink. See [`src/README.md`](src/README.md). Lobby 0.9.0 is unsigned and its source is not included; it is excluded from our source and reproducibility claims.

The Lobby module (`DOA5LR-Lobby.asi`) is a third-party community build shipped as received; we do not hold its source.

## Antivirus warnings and code signing

An `.asi` plugin is a DLL that patches the game in memory, and the installer downloads a zip and writes DLLs into a game folder: the same patterns some malware uses, so heuristic antivirus engines and SmartScreen ("not commonly downloaded") may complain. That is why the sources are public and reproducible: read, build, compare.

What we know from actual reports (September 2026): **Windows Defender** flagged some builds of the installer as `Trojan:Win32/Wacatac.B!ml` (cloud machine-learning verdict on a never-seen file: one build flagged, the next build of the same code passes). **Kaspersky** (`PDM:Trojan.Win32.Generic`, behavioral) let the install finish, then killed it and rolled every file back; its trigger included a hidden `cmd.exe` the installer used to replace itself on self-update. Installer 1.0.3 removed that (retested clean on Kaspersky, OpenTIP sandbox: Clean). False-positive reports are filed with Microsoft and Kaspersky (Allowlist program).

Since 0.3.6 our binaries are signed with a self-signed certificate (subject `CN=FGCsnow - DOA5LR-Salons`, thumbprint `0EBE9F4F8879992F594F99E7B38C4B024A68F978`, timestamped). It is **not** a CA-issued certificate: Windows shows it as untrusted, do not install it as a trusted root; it guarantees a file was not altered since we signed it and lets vendors whitelist the publisher.

**If your antivirus flags a file, please report it as a false positive**, every report counts: Microsoft Defender → https://www.microsoft.com/wdsi/filesubmission ; Kaspersky → https://opentip.kaspersky.com (upload the file, then "Report false positive") ; other vendors have a similar form. Then restore the file from the quarantine, add the game folder to the exclusions and click REINSTALL in the installer. Always extract the zip (or save the installer) to a folder before running anything, never from inside WinRAR/7-Zip.

## License

Our code (everything in `src/`: plugins and installer) is released under the [MIT License](LICENSE). It does not cover the third-party components shipped in the pack under their own terms: the Lobby module (community build), Ultimate ASI Loader (ThirteenAG), AutoLink (FallingCat), Xidi (Samuel Grossman) and the optional resolution mod (Steffen André Langnes).

## Credits

Original "Auto Installer for DOA5 Community Lobby Mods" concept: **BRG Hades**. `scripts\` layout: **WAZAAAAA**. Lobby module: community build. Ultimate ASI Loader: ThirteenAG. AutoLink: FallingCat. Xidi: Samuel Grossman. Optional resolution mod: Steffen André Langnes. Testers: everyone in the DOA5LR lobbies — thank you.
