# DOA5LR-Salons — Community Lobby Mods for Dead or Alive 5 Last Round (PC)

Community mod pack by **FGCsnow & BonuStage**: online lobbies, Steam invites, private rooms, 60 fps menus, borderless window, wired/Wi-Fi indicator with real ping, controller fix (Xidi), AutoLink, anonymous telemetry — and a one-click installer that keeps everything up to date.

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
| 60fps-menus | 0.11 | 60 fps menus, intros, win poses |
| Borderless | 1.0 | Borderless fullscreen window |
| Telemetry | 0.3.1 | Anonymous session/crash reports, F9 diag, update prompt |
| Installer | 1.0.0 | One-click install / update / restore |
| Ultimate ASI Loader, AutoLink 3.30, Xidi 5.0.0 | | Loader, costumes, controllers |

The pack contains **no game content and no Steam API / DLC files**. Sources of every plugin and of the installer are in the zip (`scripts\*-Source\`, `Installer-Source\`). Every binary is scanned with Microsoft Defender before release; the installer verifies each download by SHA256.

`version.txt` on this branch is the update manifest read by the installer and by the Telemetry plugin.

## Credits

Original "Auto Installer for DOA5 Community Lobby Mods" concept: **BRG Hades**. `scripts\` layout: **WAZAAAAA**. Lobby module: community build. Ultimate ASI Loader: ThirteenAG. AutoLink: FallingCat. Xidi: Samuel Grossman. Optional resolution mod: Steffen André Langnes. Testers: everyone in the DOA5LR lobbies — thank you.
