# DOA5LR-Salons 0.3.14 — fixes from your 0.3.13 reports

**Danger Zone no longer removed by Windows Defender, your own resolution again, your d3d9.dll kept, PLAY starts the game, new stages in offline Random only.**

## Fixes

- **Danger Zone / The Crimson stopped working for some players:** Windows Defender started flagging `DOA5LR-DangerZone.asi` of 0.3.13 (a false positive of its machine-learning scan) and removed it, which also stops The Crimson and the stage menu additions. The module is rebuilt from the same source without its own crash handler and is no longer flagged. **Update: the installer puts it back**, even if Defender removed the old one, and no longer fails when Defender blocks the old file.
- **"Forced 1920x1080" / "forced fullscreen":** the pack's AutoLink settings (`DInput8.ini`, `ResolutionMod=1`) forced your desktop resolution. That is only needed by **Borderless**. Installer 1.3.4 sets `ResolutionMod=0` when Borderless is unticked, so the resolution and window mode chosen in the game's launcher apply again. With Borderless ticked, rendering stays at the desktop size (untick Borderless for a lower resolution). A value you changed by hand is not turned back on.
- **Your `d3d9.dll` is kept:** installers since 0.3.4 deleted any `d3d9.dll` (meant for one bad file of the 0.3.3 pack), including ReShade. Now only that exact old file is removed. If yours was removed, it is in `DOA5LR-Salons-Backups\<date>\` in the game folder.
- **Random and the new stages:** Danger Zone and The Crimson 1/2 were also added to **online** Random (ranked, lobbies), where a player without the maps could get a stage they do not have. They are now drawn by **offline Random only**; online Random is the game's own again. Pick them by hand in rooms (everyone in the room needs the maps).

## Installer 1.3.4

- **PLAY** starts the game directly; **Set controls** opens the controls app (idea from Inyo). PLAY only goes through the controls app when experimental keyboard remapping is on in Keyboard mode (it checks that no controller is connected).
- Resolution and d3d9.dll fixes above. **Accept the installer update to 1.3.4 when it is offered.**

## Smaller logs, fewer files

- The Crimson effects log (up to 42 MB) now only records startup and errors, capped at 512 KB (`[Log] Level=0` in `DOA5LR-Crimson-VFX.ini` turns it off). ExtraStages' log can be turned off too (`[Log] Enabled=0`).
- Removed two diagnostic modules used while porting the stages: `DOA5LR-Crimson-EventLog.asi` and `DOA5LR-Crimson-BackendProbe.asi`.

## Windows 11: "Unable to load DOA5LR-....asi. Error: 4551"

That is **Smart App Control**, not Windows Defender: it blocks unsigned mod DLLs, so turning Defender off changes nothing. It can be turned off in Windows Security → App & browser control → Smart App Control (on many Windows versions it cannot be turned back on without resetting Windows). **Please do not use tools that disable Windows Defender.**

## Everything else

Every other pack file is byte-identical to 0.3.13 (Lobby, JoinFix, InviteFix, WiFi-Wired-Detector, UpdateCheck, Borderless, 60 fps, Replay Takeover 2.6, controls app, the other stage modules and the stage data, Diagnostic probe).

## Update

Close DOA5LR and run the installer (or accept the update notice after closing the game). Accept the installer update to 1.3.4 first. Your settings and component choices are kept.

| Download | Use it for |
| --- | --- |
| [DOA5LR-Salons-Installer.exe](https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.14/DOA5LR-Salons-Installer.exe) | Recommended for installing, updating or repairing the pack. |
| [DOA5LR-Salons-0.3.14.zip](https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.14/DOA5LR-Salons-0.3.14.zip) | Full pack archive for a new setup (includes the installer). |

## Signing

The installer and the four rebuilt stage modules are signed with the project's existing self-signed certificate (not a public certification authority: it does not satisfy Smart App Control and is no antivirus guarantee).

[Support the project](https://www.patreon.com/cw/DoA5LRcommunitymod)
