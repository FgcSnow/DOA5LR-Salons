# DOA5LR-Salons

### Community lobbies, a clearer setup, your choice of controls

A community mod pack for **Dead or Alive 5 Last Round on PC**, maintained by **FGCsnow & BonuStage**. Play in lobbies, invite Steam friends, identify wired/Wi-Fi connections and choose the optional display and offline 60 fps features you want.

**Published release: 0.3.8.** This branch prepares the **0.3.9 candidate** with InputLab controls and UpdateCheck 1.1. Candidate features described below are not a claim that 0.3.9 is already published.

[Download the published release](https://github.com/FgcSnow/DOA5LR-Salons/releases/latest) · [Input settings guide](docs/INPUT-SETTINGS.md) · [0.3.9 release notes](docs/RELEASE-NOTES-0.3.9.md) · [Validation report](docs/VALIDATION-0.3.9.md) · [Support the project](https://www.patreon.com/cw/DoA5LRcommunitymod)

## Start playing

1. Download the installer from the [published release](https://github.com/FgcSnow/DOA5LR-Salons/releases/latest), save it to a folder and close DOA5LR.
2. Open the installer, check the game folder and your component choices, then install or update. Keep its backups.
3. Start the game through Steam and open **Online → Lobby**.

For the **0.3.9 candidate**, follow the bundled local-package instructions. Its desktop shortcut opens configuration first; **Keyboard / controller** lets you choose the input mode before **Play via Steam**. Opening the shortcut does not immediately launch the game.

Prefer the portable controls app? Extract its complete `InputLab` folder and open `DOA5LR-Commandes.exe`. Activating its remapping module requires the verified 0.3.8 input setup. Do not copy only the EXE; keep its supporting files and backups. See the [input guide](docs/INPUT-SETTINGS.md).

## What the pack does

| Feature | What you get |
| --- | --- |
| **Community lobbies** | A native Lobby menu entry, Steam invites and private rooms through Lobby 0.9.0 and InviteFix 0.1.1. |
| **Connection tag** | A wired/Wi-Fi indicator beside player names. The pack does not display a ping number. |
| **Borderless display** | An optional borderless window module; F11 cycles its display modes. |
| **Offline 60 fps** | Optional 60 fps menus, intros, win poses and story cutscenes. The module does not apply its changes in the Online menu. |
| **Controls app — candidate** | Remap keyboard keys, save a profile and choose Keyboard or Controller before launch. The app remains available even with the experimental module off. |
| **Controller Finder — candidate** | Inspect connected controllers, arcade sticks and leverless devices. Search local names or VID/PID identifiers and check profile status. |
| **Update notice — candidate** | A brief UpdateCheck 1.1 banner when a newer pack is detected. Installation remains your choice after leaving the game. |
| **Installer and restoration** | Install, update, check required files and restore saved pack snapshots. Optional components keep their own choices. |
| **Diagnostics — candidate** | Open existing installer/Lobby logs or save a local support ZIP with a compact report and bounded log tails. You review and share it yourself. |

The pack also includes Ultimate ASI Loader, AutoLink and Xidi. The 0.3.9 candidate adds input configuration and the update banner; it does not claim a new lobby or invite fix.

## Keyboard or controller: choose before launch

The **experimental in-game keyboard module is off by default**. Its settings app is always installed and accessible. New pack installations use **Controller (usual configuration)** by default; updates and repairs preserve an existing saved input choice.

| Choice | Behavior |
| --- | --- |
| **Controller (usual configuration)** | Uses the usual game/Steam controller configuration. The optional module can stay off. |
| **Keyboard** | Applies your saved bindings and enables the module on demand. Disconnect controllers before launching. |

Click a key in the app, press its replacement and save the profile. Use **Play via Steam** to apply the chosen mode and launch. Starting directly from Steam skips the app and uses the last applied settings.

**Current compatibility limits:**

- A controller connected at startup can make DOA5LR ignore the keyboard. Keyboard mode checks for connected controllers and stops that launch; close the game, disconnect the controller and retry.
- Finder detection is not automatic button mapping or universal device support. Only **DualSense Edge (`VID_054C&PID_0DF2`)** has been tested on real controller hardware for this candidate.
- This project does **not** emulate a PS5 controller. Other devices need profile and hardware validation.
- Rumble and controller button icons are not forwarded through the experimental keyboard path. Online modes have not been validated for this input patch.

See [the controls guide](docs/INPUT-SETTINGS.md) for profiles, startup checks, portable installation and restoring the usual input setup.

## Update notifications that leave you in control

UpdateCheck 1.1 checks the public version manifest after a default startup delay of about **20 seconds**. If a newer pack is detected, a small notice appears for **8 seconds** in borderless/windowed mode. The separate banner is not visible in exclusive fullscreen.

The installer opens in update mode when you leave the game normally; you choose whether to install. It does not install files during a match. The exit-time update prompt already existed in UpdateCheck 1.0; the visible banner is the new part.

## Backups and troubleshooting

The installer saves changed files in `DOA5LR-Salons-Backups` inside the game folder. Its **Restore backup** action can return to a saved pack snapshot. The controls app also creates an input backup before its own activation. Keep those folders.

To stop using InputLab, close the game, uncheck the experimental remapping component in setup and apply the change. The app and personal profiles stay available.

| Problem | First step |
| --- | --- |
| Keyboard stops responding | Close DOA5LR, disconnect controllers, select Keyboard and launch from the app. |
| Finder shows **Profile needed** | See the input guide for profile status and device support limits; detection alone does not provide a button mapping. |
| The pack reports missing files | Check the install log and antivirus protection history. Do not continue with a partial installation. |
| Steam skips configuration | Use the pack shortcut or app. Direct Steam launches use the last applied settings. |
| An older standalone prototype prevents installation | Restore that prototype using its saved backup, then retry the compatible pack. |

For a bug report, include the pack version, selected input mode, controller model/keyboard layout, Steam Input status, reproduction steps and a screenshot of the error. **Logs → Export diagnostics ZIP...** saves a local archive: a compact version/settings/hash report and the last 2 MiB of existing allowlisted Lobby, Installer, InputBridge and InviteFix logs. No debug logger is activated and no upload is performed.

Logs are **not anonymized**. Review the ZIP before sharing and remove sensitive session details, player names, Steam IDs, IP addresses or local paths as needed. Never send Steam credentials, authentication tokens or game saves. The exporter does not recursively collect folders, Steam configuration, saves, crash dumps, telemetry logs or mod binaries. See the [input guide](docs/INPUT-SETTINGS.md) for the reporting checklist.

## Verification, antivirus and signing

See the [candidate validation report](docs/VALIDATION-0.3.9.md) for the tested artifacts, hashes, scan results and remaining limits. A local scan describes those exact files at that time; it cannot guarantee every antivirus product or future definition will accept them. Checksums verify identity, not safety.

The new candidate **InputLab and installer executables are unsigned**. Some existing pack components use the project's self-signed certificate, which is not a certificate from a public certification authority. Windows may show it as untrusted. Do not add that certificate to Trusted Root authorities.

If an antivirus flags a file, keep protection enabled, record the exact detection and file hash, and compare the source and validation report. Ask the antivirus vendor to review the file when you suspect a false positive: [Microsoft submission portal](https://www.microsoft.com/wdsi/filesubmission) or [Kaspersky OpenTIP](https://opentip.kaspersky.com/). Do not treat a mod-related warning as automatically harmless.

The portable app is an alternate package format, not an antivirus bypass.

## Privacy and source scope

Controller Finder searches local connected devices and the included profile file. It does not query an online controller catalogue.

The pack does use the network: UpdateCheck reads a public version manifest, the installer downloads manifests and packages, and the lobby/network components communicate with other players. WiFi-Wired exchanges connection information and ping messages with participating peers even though a ping number is not displayed.

Maintained plugin release builds generally disable their diagnostic logs. **Lobby 0.9.0 is an external exception and writes a local log.** Configuration files, profiles, installer logs and backups are also written locally. This is not a blanket claim of no file writes or no network traffic.

Sources for maintained components are in [`src/`](src/). The external Lobby binary is shipped as received; its source is not included and it is outside the project's source/reproducibility claims. See the [build instructions](src/README.md) for the supported components and toolchain. The pack contains no game content or Steam API/DLC files.

## Credits and license

Pack maintained by **FGCsnow & BonuStage**. Original auto-installer concept: **BRG Hades**. `scripts` layout: **WAZAAAAA**. Thanks to the community lobby testers.

Third-party components: **Lobby** community build; **Ultimate ASI Loader** by ThirteenAG; **AutoLink** by FallingCat; **Xidi** by Samuel Grossman; optional resolution mod by **Steffen André Langnes**.

The project's maintained code is available under the [MIT License](LICENSE). Third-party components retain their own terms; the pack's license does not relicense them.
