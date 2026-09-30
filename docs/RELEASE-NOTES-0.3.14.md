# DOA5LR-Salons 0.3.14 — fixes from the 0.3.13 reports

## Optional PS4 skins - local test build, Installer 1.3.6

This local build has not been published. It packages 15 PS4 costumes in their native slots, with four texture/color variants each for Honoka slot 41, Marie slots 25 and 51, and Nyotengu slot 51. Static package validation passed. On 2026-09-30, the user confirmed that all 15 costumes and their variants work in combat and that this set has already been used online. Installer checks are recorded separately in `validation-report.json` in the local release folder. Experimental costume destruction and transformations are excluded.

The new optional component is `ps4skins`. A compatible local native costume loader must already be installed; detection of its configuration alone does not establish that it works. Installer 1.3.6 recognizes an existing `cream_api.ini` and adds only the local `990015` entry. No Steam DLL is supplied or replaced. On a new setup, the component is selected by default only when that loader configuration is detected; existing component choices are retained.

Skin data is a separate `skins_data` archive: four files, 158,744,078 bytes unpacked, containing 92 resources. An update reuses the installed files when all their SHA-256 hashes match. Unticking the component removes only `DLC/990015/990015.bcm`, `DLC/990015/data/990015.bin`, `.blp` and `.lnk`, plus the component guide. The loader configuration and its `990015` entry remain intact because the entry may predate the installer; without its data files the package is inactive. Unrelated configuration and data are preserved. Full slot list: `scripts/PS4-SKINS-EN.txt`.

## Display: your resolution again
The pack's AutoLink settings (`DInput8.ini`, `[PATCH] ResolutionMod=1`, `WindowResolution=desktop`) forced every game to the desktop resolution, so a lower resolution or a smaller window chosen in the game's launcher was ignored ("forced 1920x1080", "forced fullscreen"). That setting is only needed by **Borderless**, which renders at the monitor size.

Installer 1.3.5 now edits only that key, in place (same file encoding, one digit):
- fresh install, or Borderless ticked/unticked: `ResolutionMod` follows the box (1 with Borderless, 0 without);
- other updates: lowered to 0 when Borderless is off; a 0 you set by hand is never turned back to 1;
- a custom `WindowResolution` / `FullscreenResolution` (anything but `desktop`) is never touched.

## Your d3d9.dll is kept
Every installer since 0.3.4 removed any `d3d9.dll` from the game folder, because the 0.3.3 pack shipped one that hid the character grid. That also removed ReShade and other d3d9 mods. The manifest now uses a new `delete_if=` rule: only that exact old file (SHA-256 `badac2aa…`) is removed. A removed file is always in `DOA5LR-Salons-Backups\<date>\`.

## Smaller updates
The stage data (CodexCrimson, CodexDangerZone, PS4Stages, about 260 MB) is published as its own archive. Installer 1.3.5 checks every installed stage file by SHA-256 and downloads that archive only when a file is missing or different; otherwise an update downloads only the rest of the pack (about 7 MB). New `version.txt` keys `core=` and `data=`; `url=` stays the full pack, which older installers keep using. Old downloads left in the temporary folder are removed.

If Defender blocks the old `DOA5LR-DangerZone.asi`, Installer 1.3.5 replaces it without failing (it cannot back it up). An older installer stops once with "the file contains a virus"; the next try works, because Defender has removed the file by then.

## PLAY / Set controls (idea from Inyo)
**PLAY** starts the game directly through Steam. **Set controls** opens the controls app. PLAY still opens the controls app first when experimental keyboard remapping is on in Keyboard or combined mode, because that app checks that no controller is connected before a keyboard launch.

## Random: new stages offline only
RandomStages 2.1: Danger Zone and The Crimson 1/2 are drawn by offline Random only. Online Random (ranked, player match, lobbies) is the game's own again, so a player without the maps can never get one of them. Pick them by hand in lobbies (everyone in the room needs the maps). `Online=1` under `[RandomStages]` in `DOA5LR-RandomStages.ini` restores online Random for groups where everyone has the maps.

## Danger Zone no longer removed by Windows Defender
Windows Defender started flagging `DOA5LR-DangerZone.asi` of 0.3.13 as `Trojan:Win32/Wacatac!ml`, a false positive of its machine-learning scan, and quarantined it. Without it, Danger Zone, The Crimson and the stage menu additions do not start. The module is rebuilt from the same source without its own crash handler (Windows crash reports and DOA5LR-Diagnostic cover crashes); the new file is not flagged. Updating puts it back even if Defender removed the old one. Stage behaviour is unchanged. ExtraStages 2.0.4: same stage code, its log can be turned off (`[Log] Enabled=0` in `DOA5LR-ExtraStages.ini`).

## Smaller logs, fewer files
- Crimson-VFX v26: the log records startup and errors only by default (no line per effect), capped at 512 KB (`[Log] MaxKB`); at startup a bigger log becomes `DOA5LR-Crimson-VFX.log.old` (deleted above 4 MB). `[Log] Level=0` turns it off, `Level=2` records every effect. Effects code unchanged.
- Removed: `DOA5LR-Crimson-EventLog.asi` (a diagnostic that logged every stage effect while the stage was ported) and `DOA5LR-Crimson-BackendProbe.asi` (a research probe that did nothing on its own), with their logs.

## Windows 11 error 4551
"Unable to load DOA5LR-....asi. Error: 4551" is **Smart App Control** (Windows 11), which blocks unsigned DLLs. It is not Windows Defender, so turning Defender off does not help, and we do not recommend tools that disable Defender. Smart App Control can be turned off in Windows Security → App & browser control; on many Windows versions it cannot be turned back on without resetting Windows.

## Unchanged
Every other file is byte-identical to 0.3.13 (Lobby, JoinFix, InviteFix, WiFi-Wired-Detector, UpdateCheck, Borderless, 60fps, controls app, the other maps modules and the stage data, Diagnostic probe).

## Replay Takeover 2.7

Replaces 2.6 (module, English guide, source). Scene tour from the testers' reports: no freeze around cliffhangers, falls and transitions (the jump back waits for the end of the sequence), clean jump back from another area or floor, hazards and breakable objects restored, crash after some Lost World transitions fixed. `.ini` default unchanged; still asleep online.
