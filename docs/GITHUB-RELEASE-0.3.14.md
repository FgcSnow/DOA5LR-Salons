# DOA5LR-Salons 0.3.14 â€” fixes from your 0.3.13 reports

**Installer 1.3.6 adds optional PS4 skins. JoinFix remains the released 0.3 version; experimental JoinFix builds are excluded.**

**Danger Zone no longer removed by Windows Defender, your own resolution again, your d3d9.dll kept, PLAY starts the game, new stages in offline Random only.**

## Optional PS4 skins

- **15 native costume slots:** Ayane, Honoka, Kasumi, Marie and Nyotengu. Honoka slot 41, Marie slots 25 and 51, and Nyotengu slot 51 each include four texture/color variants. Experimental costume destruction and transformation tests are excluded.
- **Existing loader required:** Installer 1.3.6 recognizes an existing compatible local native costume loader configuration (`cream_api.ini`) and registers only costume package `990015`. No Steam DLL is supplied or replaced. On a new setup, the optional `ps4skins` component is selected by default only when that configuration is detected; existing choices are kept. Configuration detection does not prove that the loader works.
- **Separate skin data:** the `skins_data` archive is reused when all four installed files match their SHA-256 hashes. Unticking the option removes only those four files in `DLC/990015` and the component guide. The loader configuration and its `990015` entry are kept because the entry may predate the installer; without the data files the package is inactive. Unrelated data and settings are preserved.
- **Static checks and user gameplay confirmation:** the package contains 92 resources in four files (158,744,078 bytes unpacked). On 2026-09-30, the user confirmed all 15 costumes and their variants work in combat and reported having played online with this set. Guide and exact slots: `scripts/PS4-SKINS-EN.txt`.

## Fixes

- **Danger Zone / The Crimson stopped working for some players:** Windows Defender started flagging `DOA5LR-DangerZone.asi` of 0.3.13 (a false positive of its machine-learning scan) and removed it, which also stops The Crimson and the stage menu additions. The module is rebuilt from the same source without its own crash handler and is no longer flagged. **Update: the installer puts it back**, even if Defender removed the old one, and no longer fails when Defender blocks the old file.
- **"Forced 1920x1080" / "forced fullscreen":** the pack's AutoLink settings (`DInput8.ini`, `ResolutionMod=1`) forced your desktop resolution. That is only needed by **Borderless**. Installer 1.3.6 sets `ResolutionMod=0` when Borderless is unticked, so the resolution and window mode chosen in the game's launcher apply again. With Borderless ticked, rendering stays at the desktop size (untick Borderless for a lower resolution). A value you changed by hand is not turned back on.
- **Your `d3d9.dll` is kept:** installers since 0.3.4 deleted any `d3d9.dll` (meant for one bad file of the 0.3.3 pack), including ReShade. Now only that exact old file is removed. If yours was removed, it is in `DOA5LR-Salons-Backups\<date>\` in the game folder.
- **Random and the new stages:** Danger Zone and The Crimson 1/2 were also added to **online** Random (ranked, lobbies), where a player without the maps could get a stage they do not have. They are now drawn by **offline Random only**; online Random is the game's own again. Pick them by hand in rooms (everyone in the room needs the maps).

## Installer 1.3.6

- **PLAY** starts the game directly; **Set controls** opens the controls app (idea from Inyo). PLAY only goes through the controls app when experimental keyboard remapping is on in Keyboard mode (it checks that no controller is connected).
- **Much smaller updates:** the stage data (about 260 MB) is now a separate download. When your stage files are already installed and intact, an update downloads only about 7 MB; a missing or damaged stage file is downloaded again automatically.
- Resolution and d3d9.dll fixes above. **Accept the installer update to 1.3.6 when it is offered.** If an older installer stops with "the file contains a virus", run the update again: Defender has removed the old DangerZone.asi in the meantime.

## Smaller logs, fewer files

- The Crimson effects log (up to 42 MB) now only records startup and errors, capped at 512 KB (`[Log] Level=0` in `DOA5LR-Crimson-VFX.ini` turns it off). ExtraStages' log can be turned off too (`[Log] Enabled=0`).
- Removed two diagnostic modules used while porting the stages: `DOA5LR-Crimson-EventLog.asi` and `DOA5LR-Crimson-BackendProbe.asi`.

## Replay Takeover 2.7

- **No more freeze or dead controller** around cliffhangers, falls, jumps over an obstacle and stage transitions: during one of these sequences the jump back waits until it ends, and the checkpoint is set at its end.
- **Jumping back from another area or floor** (Lost World, Glacier, jungle waterfall, Temple of the Dragon floorsâ€¦) rebuilds everything cleanly: no camera left below, no character falling from the sky.
- **Stage hazards and objects come back correctly:** Scramble's ghost pillar, circus lights and wall, Sky City's Buddha, Hot Zone's barrel, Flow's raft tree, the street train, Temple of the Dragon's table and vases.
- Crash fixed after some Lost World transitions; taking control during the intro sets the checkpoint at the start of the fight; "Replay" from the replay menu during takeover gives the replay back.
- Still fully asleep online (lobbies, online matches, spectating). Guide: `scripts\REPLAY-TAKEOVER-EN.txt`.

## Tidier game folder

- The maps modules (`DOA5LR-DangerZone.asi`, `DOA5LR-DNZ-*.asi`, `DOA5LR-Crimson*.asi`, `DOA5LR-ExtraStages.asi`, `DOA5LR-RandomStages.asi`) now live in the **`scripts`** folder like every other module of the pack (thanks WAZAAAAA). The update removes the old copies next to `game.exe`, with any installer version, so they are never loaded twice. Their `.ini` files and the stage data stay next to `game.exe`.

## Windows 11: "Unable to load DOA5LR-....asi. Error: 4551"

That is **Smart App Control**, not Windows Defender: it blocks unsigned mod DLLs, so turning Defender off changes nothing. It can be turned off in Windows Security â†’ App & browser control â†’ Smart App Control (on many Windows versions it cannot be turned back on without resetting Windows). **Please do not use tools that disable Windows Defender.**

## Everything else

Every other pack file is byte-identical to 0.3.13 (the moved maps modules included) (Lobby, JoinFix, InviteFix, WiFi-Wired-Detector, UpdateCheck, Borderless, 60 fps, controls app, the other stage modules and the stage data, Diagnostic probe).

## Update

Close DOA5LR and run the installer (or accept the update notice after closing the game). Accept the installer update to 1.3.6 first. Your settings and component choices are kept.

| Download | Use it for |
| --- | --- |
| [DOA5LR-Salons-Installer.exe](https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.14/DOA5LR-Salons-Installer.exe) | Recommended for installing, updating or repairing the pack. |
| [DOA5LR-Salons-0.3.14.zip](https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.14/DOA5LR-Salons-0.3.14.zip) | Classic full pack, without PS4 skins, compatible with older installers. |
| `DOA5LR-Salons-core-0.3.14.zip`, `DOA5LR-Salons-maps-data-1.zip` | Used by the installer (pack without the stage data + the stage data). No need to download them yourself. |

## Signing

The installer and the four rebuilt stage modules are signed with the project's existing self-signed certificate (not a public certification authority: it does not satisfy Smart App Control and is no antivirus guarantee).

[Support the project](https://www.patreon.com/cw/DoA5LRcommunitymod)

PS4 full archive: [DOA5LR-Salons-0.3.14-PS4.zip](https://github.com/FgcSnow/DOA5LR-Salons/releases/download/v0.3.14/DOA5LR-Salons-0.3.14-PS4.zip). Skin data archive is downloaded automatically by Installer 1.3.6 when enabled.
