# DOA5LR-Salons 0.3.9 — Your controls, clearer setup and easier bug reports

Version 0.3.9 adds an English **Keyboard / controller** app, keyboard remapping, a local Controller Finder, a visible update notification and a **Logs** menu for support.

**Experimental in-game remapping is off by default. The settings app is always available.** New pack installations use the usual Controller configuration; upgrades and repairs keep your saved choices.

## What is new

| Feature | What you can do |
| --- | --- |
| **Keyboard remapping** | Click an action, press a replacement key and save your profile. Native-layout reset and an arrow-key movement preset are included. |
| **Choose before launch** | The desktop shortcut opens configuration. Choose Keyboard or Controller, then start through Steam when ready. |
| **Optional remapping** | Keep the usual game/Steam controller path, or enable keyboard remapping when needed. Opening settings or saving a profile does not activate the module. |
| **Controller Finder** | Inspect connected pads, arcade sticks and leverless devices; search names or VID/PID and check the profiles available locally. |
| **Portable controls app** | Use the complete app folder on a compatible pack without the installer executable. |
| **Update banner** | UpdateCheck 1.1 displays a brief notice when it detects a newer pack. Installation remains your choice after leaving the game. |
| **Logs and diagnostics** | Open existing installer/Lobby journals or export a local ZIP with a compact report and bounded log tails. Nothing is uploaded automatically. |
| **Preserved settings** | Installer 1.3.1 retains personal INIs, component choices, saved input modes and the original-settings backup when updating or repairing. |

The Lobby, InviteFix and network-tag binaries are unchanged from 0.3.8. This release does not introduce a new lobby or private-invite fix.

## Downloads

| Download | Use it for |
| --- | --- |
| [DOA5LR-Salons-Installer.exe](https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.9/DOA5LR-Salons-Installer.exe) | Recommended for installing, updating or repairing the pack. It downloads the required package. |
| [DOA5LR-Salons-0.3.9.zip](https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.9/DOA5LR-Salons-0.3.9.zip) | Full pack archive for a new game/base setup without existing pack settings. Includes the installer. |
| [DOA5LR-Commandes-portable-0.3.9.zip](https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.9/DOA5LR-Commandes-portable-0.3.9.zip) | Complete controls app for first use on a compatible 0.3.8/0.3.9 input setup. |

Close DOA5LR, open the installer and check the detected game folder and component choices. If an older installer offers its own update, accept **Installer 1.3.1** first, then continue with the pack. Leave experimental remapping unchecked to keep the usual controller path. Install or update, then open **Keyboard / controller** when you want to choose your controls. Keep the installation backups.

**Use the full installer for every upgrade, especially when InputLab is already installed or active.** Do not overwrite an existing pack or InputLab folder with the full ZIP or portable files. Direct extraction can replace custom INIs, profiles and runtime files without applying saved component choices. Manual full-ZIP extraction is only for a new game/base setup with no existing pack settings or active InputLab module; it copies the optional files supplied in the archive and does not apply installer checkbox choices.

For first use of the portable app, extract its complete `InputLab` folder to a new folder and open `DOA5LR-Commandes.exe`. Keep the supporting executables, profiles and `payload` folder together. Activation checks the compatible original input setup; do not bypass a failed file check.

**Preview testers:** run the final 0.3.9 installer directly. The older update comparator treats preview and final 0.3.9 as equal, so the preview cannot announce this transition as a newer version.

## Before playing

- **Keyboard:** disconnect controllers before launch. DOA5LR can ignore keyboard input when a controller is connected at startup; the app checks and blocks that keyboard launch.
- **Device support:** Finder detection does not create a button mapping. Only DualSense Edge has real controller testing for this input module. Other pads, sticks and leverless devices need profile and hardware validation. The project does not emulate a PS5 controller.
- **Input limits:** rumble and controller button icons are not forwarded through the experimental keyboard path. Online modes have not been validated for the input patch.
- **Launching:** the pack shortcut opens configuration first. A direct Steam launch uses the last applied settings.
- **Update notice:** the default check begins after about 20 seconds; a newer version produces an 8-second banner in borderless/windowed mode. Exclusive fullscreen cannot show the separate banner window. No update is installed during a match.

## Signing and verification

The 0.3.9 installer and InputLab builds use the project's existing self-signed certificate. It is not issued by a public certification authority and does not guarantee Windows trust, SmartScreen reputation or antivirus acceptance. Do not add it to Trusted Root authorities. Third-party components retain their upstream signing status.

Consult the [validation report](https://github.com/FgcSnow/DOA5LR-Salons/blob/v0.3.9/docs/VALIDATION-0.3.9.md) and [Defender check](https://github.com/FgcSnow/DOA5LR-Salons/blob/v0.3.9/docs/DEFENDER-CHECK-EN.md) for exact artifact identities, recorded checks and limitations. A scan applies to those files at that time; a checksum establishes identity, not safety.

## Reporting a problem

Use **Logs → Export diagnostics ZIP...**, inspect the archive, then share it manually with the pack version, input mode, device model, Steam Input setting and reproduction steps. The ZIP contains a compact report and the last 2 MiB of existing allowlisted logs. Export does not enable debug logging or upload anything.

Logs are not anonymized and may contain player names, Steam IDs, IP addresses or local paths. Remove sensitive details before sharing. For lobby or invite problems, include the existing Lobby journal if available; a missing log is also useful information.

[Complete controls and installation guide](https://github.com/FgcSnow/DOA5LR-Salons/blob/v0.3.9/docs/INPUT-SETTINGS.md) · [Full release notes](https://github.com/FgcSnow/DOA5LR-Salons/blob/v0.3.9/docs/RELEASE-NOTES-0.3.9.md) · [Support the project](https://www.patreon.com/cw/DoA5LRcommunitymod)
