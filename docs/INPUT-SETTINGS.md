# DOA5LR-Salons 0.3.9 — Controls, installation and updates

DOA5LR-Salons 0.3.9 includes a **Keyboard / controller** settings app. Use it to remap keyboard controls, choose how to launch the game, or inspect connected controllers, arcade sticks and leverless controllers.

**The settings app is always available. Experimental in-game remapping is optional and off by default.** Opening the app or the desktop shortcut does not start DOA5LR.

The Lobby, InviteFix and network-tag binaries are unchanged from 0.3.8. The existing optional Borderless and offline 60 fps features remain available. This release does not introduce a new lobby or invite fix.

0.3.9 also includes UpdateCheck 1.1: a brief notification when a newer pack is available. It does not install an update during play.

## Choose a package

| Package | Use it for | Start with |
| --- | --- | --- |
| Installer (recommended) | Install, update or repair the pack while retaining personal settings | Download [DOA5LR-Salons-Installer.exe](https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.9/DOA5LR-Salons-Installer.exe) and open it |
| Portable controls app | First use of the app on an existing compatible pack | Download the [portable ZIP](https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.9/DOA5LR-Commandes-portable-0.3.9.zip), extract its complete `InputLab` folder to a new folder, then open `InputLab/DOA5LR-Commandes.exe` |

The installer downloads the pack by itself. Do not run anything from inside a ZIP. The portable app also needs its sibling executables, profiles and `payload` folder; copying only its EXE is not enough.

**If InputLab is already installed or active, update through the pack installer.** Do not extract a new full pack or portable app over your existing InputLab folder. That can overwrite profiles and default INIs, or replace runtime files without preserving the recorded module state. Keep your profiles and both kinds of backup.

The portable remapping module requires **the verified DOA5LR-Salons input setup (0.3.8 or 0.3.9)**, installed in a Steam library. The app checks the original input file before replacing it. If it reports a different input DLL, stop and repair the compatible pack rather than renaming or deleting files to bypass the check. Controller Finder can be used separately without enabling the module.

## Install or update the pack

1. Close DOA5LR.
2. Open `DOA5LR-Salons-Installer.exe` and check the selected game folder. If detection fails, choose the folder containing `game.exe`. If an older installer offers its own update, accept Installer 1.3.1 first, then continue with the pack.
3. Leave **Experimental in-game keyboard remapping (settings app always available)** unchecked unless you want the module installed immediately. Install or update the pack.
4. Open **Keyboard / controller**. This button works even with the experimental component unchecked.
5. Choose a mode and use **Play via Steam** when ready to play.

**Manual full-ZIP installation is for a new game/base setup without existing pack settings or an active InputLab module.** In that case, close the game and extract the [full 0.3.9 ZIP](https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.9/DOA5LR-Salons-0.3.9.zip) into the folder containing `game.exe`. Direct extraction copies the archive as supplied, including files for optional components; it does not apply installer checkbox choices. It does not activate keyboard remapping by itself.

For every upgrade, including 0.3.8 and the 0.3.9 preview, use the installer to keep personal INIs, saved input choices and module backups. Do not overwrite custom INIs with archive defaults. Preview testers must run the final installer directly: the older version comparator treats preview and final 0.3.9 as the same numeric version.

The installer can create a **DOA5LR (Lobby Mods)** desktop shortcut. It opens the pack configuration window first. Its launch button opens the controls choice; it does not silently start a match or choose an input mode for you.

If an older standalone prototype is active, use its **Restore previous setup** before installing this pack. The installer rejects that older unmanaged state so it does not mistake modified settings for your original setup.

## Choose an input mode

Change modes with DOA5LR completely closed. New pack installations default to **Controller (usual configuration)** with the experimental component off. Updates and repairs preserve an existing saved input choice. The settings app remains available in either case.

| Mode | What happens |
| --- | --- |
| **Controller (usual configuration)** | Uses the usual game/Steam controller setup. If the optional module is off, it stays off. If it is already installed, this mode disables its keyboard remapping path for the launch. |
| **Keyboard** | Applies your keyboard bindings. **Play via Steam** enables the optional module when needed, after checking connected controllers. |

**Keyboard + controller (experimental)** remains available for testing with matching profiles. Device switching during a session is not guaranteed.

For **Keyboard**, disconnect controllers before launching. DOA5LR can stop accepting keyboard input if a controller is connected at startup. The app blocks a keyboard launch while it detects a connected controller; it does not fix that game limitation. If the keyboard was already blocked, close the game, disconnect the controller and launch again in Keyboard mode.

The mode selector chooses the input path. It is not a controller-pairing wizard and does not configure Steam Input for you.

## Remap the keyboard

1. Choose **Keyboard**.
2. Click the key beside an action, then press your new key. **Esc** cancels capture.
3. Use **Save profile** to keep your choices.
4. With controllers disconnected and the game closed, click **Play via Steam** to apply the profile and launch.

**Enable module** applies the selected remapping settings without starting the game. Opening the app and saving a profile alone do not activate the module.

The action labels describe the game's default control assignments: Guard, Punch, Kick / Cancel, Throw / Confirm and the other listed commands. If you also changed button assignments inside DOA5LR, those in-game settings can change what an action does. Test your chosen layout in training first.

- The supplied profile keeps the game's native keyboard positions. The displayed letters follow the Windows keyboard layout: movement is ZQSD on AZERTY and WASD on QWERTY.
- **Default keyboard layout** resets all assignments to the native layout.
- **Move with arrow keys** resets the layout to the native assignments, then assigns movement to the arrows. It also resets any custom action keys.
- Assigning a key already used by another action swaps the two assignments.
- F1–F12 are reserved for the pack's shortcuts. Ctrl, Alt and Windows keys are not assignable in this release.
- Your profile is stored beside the app in `Profil-clavier.ini`. Keep this file with your app and backups.

## Find a controller, arcade stick or leverless controller

Open **Controller finder**, or run `InputLab/DOA5LR-Detecteur.exe` directly.

1. Connect the device and click **Detect / refresh**.
2. Search by device name or VID/PID.
3. Select a result to see its capabilities and profile status. **Copy selected ID** copies its identifier.

**VID** identifies the vendor and **PID** identifies the model. These are USB/device identifiers, not IP addresses and not unique serial numbers. The same model can have different identifiers or button layouts in different modes or firmware versions.

Search is local: it lists DirectInput devices detected by Windows and the profiles included in `DOA5LR-ControllerProfiles.ini`, including known profiles whose device is not connected. It does not query a universal database or download a driver.

**Detection is not a guarantee of playable support.** The experimental reader needs a matching, verified button profile. **Profile needed** means the finder sees the device but the experimental module does not have a mapping for it. **Open profiles** opens the INI file for manual configuration; there is no automatic mapping wizard in this build.

Only a **DualSense Edge (`VID_054C&PID_0DF2`)** has been tested on real controller hardware for this build. Other controller models, arcade sticks and leverless devices still need their own validation. The project does **not** emulate a PS5 controller.

## Steam, backups and turning the module off

Starting DOA5LR **directly from Steam** skips these configuration windows and uses the last applied game/input settings. Saving a profile does not apply it to that direct launch; apply it through **Enable module** or **Play via Steam** first.

To disable the experimental module in an installer-managed pack, close the game, reopen setup, uncheck **Experimental in-game keyboard remapping (settings app always available)** and apply the change. This restores the usual input path while keeping the settings app and personal profiles available. The installer preserves the previous input settings for restoration.

The app creates `InputLab/Sauvegarde-avant-prototype` before its own activation. **Restore previous setup** restores that saved input setup when this backup is available. Completed backups are retained with a dated suffix after restoration or reactivation; keep them if you want the history. On an installer-managed pack, the app also records the component state so setup can disable the module later.

The pack installer has a separate **Restore backup** feature for its installation snapshots in the game's `DOA5LR-Salons-Backups` folder. This restores a pack snapshot, which is a broader change than merely disabling InputLab. Do not delete these backups until you are satisfied with the new setup.

## Update notification

UpdateCheck 1.1 reads the public version manifest after a default delay of about **20 seconds** from startup. If a newer version is found, a small banner appears for **8 seconds** by default. This separate window is visible in borderless or windowed mode; it is not visible in exclusive fullscreen.

The existing update prompt remains tied to leaving the game: if a newer version was detected, normal exit opens the installer in update mode and you choose whether to install. The banner neither closes the game nor installs files during a match. A failed or unavailable version check is not proof that the installed pack is current.

The settings are in `scripts/DOA5LR-UpdateCheck.ini`. `Banner=0` hides the new banner; `Enabled=0` disables the check. Older personal INI values may be preserved by the installer.

## Known limits and troubleshooting

| Symptom | What to check |
| --- | --- |
| Keyboard does not work in the game | Close the game, disconnect controllers, select Keyboard and launch from the app. A controller connected at startup can block the keyboard. |
| Controller works, keyboard does not | Check the selected mode. Controller mode uses the usual controller setup; it is not an automatic keyboard/controller switch. |
| Finder sees a device, but its profile is unavailable | Check its profile status. Detection alone does not supply a button mapping. |
| An app file is missing | Repair an installed pack through the installer. For a first-use portable copy, re-extract the entire app into a new folder. Check antivirus protection history; keep protection enabled. |
| Setup rejects an existing prototype or different input DLL | Restore the older prototype with its own backup or repair the compatible pack. Do not bypass the file check. |
| Steam launch opens the game immediately | This is the direct Steam path. Use the pack shortcut or controls app to choose settings first. |

Rumble and controller button icons are not carried through the experimental keyboard input path. Online modes and other controller hardware have not been validated for this input patch.

The portable ZIP is an alternate distribution format, not an antivirus bypass or a guarantee that Windows Defender/SmartScreen will accept every file. Consult the [validation report](VALIDATION-0.3.9.md) and [Defender check](DEFENDER-CHECK-EN.md) for the recorded checks and their limits. A checksum verifies file identity; it does not prove that a file is safe.

## Report a problem

Describe what you expected, what actually happened and the shortest steps that reproduce it. Include the pack version, selected input mode, keyboard layout or controller model, whether Steam Input is used, and whether the controller was connected before launch. A screenshot of the exact error is useful.

In setup, open **Logs** to choose:

- **Open installer log** — opens the existing installer journal.
- **Open lobby log** — opens the existing Lobby journal from the game folder or `scripts`.
- **Export diagnostics ZIP...** — saves a local support archive to a new filename you choose outside the game folder. It does not upload the archive or enable debug logging.

The ZIP contains `README.txt`, a compact `report.txt` (pack/installer version, saved component choices and input mode, hashes of known mod files), and existing allowlisted logs. Only these four log names are collected, from the game root and `scripts`: `DOA5LR-Lobby.log`, `DOA5LR-Salons-Installer.log`, `DOA5LR-InputBridge.log` and `DOA5LR-InviteFix.log`. Each is limited to its **last 2 MiB**. Missing logs are listed in the report; old sessions may have been trimmed from large logs. The saved input mode is only relevant when its module is enabled.

No recursive folder copy is performed. Steam configuration, game saves, crash dumps, telemetry logs and mod binary contents are not selected for export. Linked files/folders are skipped. Export can read logs while the game is running if the writing process allows shared reading; an exclusively locked log may be listed as unavailable.

For a lobby or invite issue, include the existing **DOA5LR-Lobby.log** if it was created. Check the game folder and its `scripts` subfolder. This is Lobby's own local journal; the input patch does not add a new universal game logger. Reproduce the issue and collect the journal from that session before a later launch changes it. A missing log is also useful information to report.

**Logs are copied as-is, not anonymized.** Inspect the ZIP and its `README.txt` before sharing: logs can contain player names, Steam IDs, IP addresses, local paths or other session details. Remove sensitive information before sending the files. Never send Steam credentials, authentication tokens or game save data. Nothing is uploaded merely by opening the app or collecting local diagnostics.
