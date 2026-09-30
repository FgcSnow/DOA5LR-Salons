# DOA5LR-Salons 0.3.14 — fixes from the 0.3.13 reports

## Display: your resolution again
The pack's AutoLink settings (`DInput8.ini`, `[PATCH] ResolutionMod=1`, `WindowResolution=desktop`) forced every game to the desktop resolution, so a lower resolution or a smaller window chosen in the game's launcher was ignored ("forced 1920x1080", "forced fullscreen"). That setting is only needed by **Borderless**, which renders at the monitor size.

Installer 1.3.4 now edits only that key, in place (same file encoding, one digit):
- fresh install, or Borderless ticked/unticked: `ResolutionMod` follows the box (1 with Borderless, 0 without);
- other updates: lowered to 0 when Borderless is off; a 0 you set by hand is never turned back to 1;
- a custom `WindowResolution` / `FullscreenResolution` (anything but `desktop`) is never touched.

## Your d3d9.dll is kept
Every installer since 0.3.4 removed any `d3d9.dll` from the game folder, because the 0.3.3 pack shipped one that hid the character grid. That also removed ReShade and other d3d9 mods. The manifest now uses a new `delete_if=` rule: only that exact old file (SHA-256 `badac2aa…`) is removed. A removed file is always in `DOA5LR-Salons-Backups\<date>\`.

## PLAY / Set controls (idea from Inyo)
**PLAY** starts the game directly through Steam. **Set controls** opens the controls app. PLAY still opens the controls app first when experimental keyboard remapping is on in Keyboard or combined mode, because that app checks that no controller is connected before a keyboard launch.

## Random: new stages offline only
RandomStages 2.1: Danger Zone and The Crimson 1/2 are drawn by offline Random only. Online Random (ranked, player match, lobbies) is the game's own again, so a player without the maps can never get one of them. Pick them by hand in lobbies (everyone in the room needs the maps). `Online=1` under `[RandomStages]` in `DOA5LR-RandomStages.ini` restores online Random for groups where everyone has the maps.

## Smaller logs, fewer files
- Crimson-VFX 25.1: at most 2 MB of log per game session, the previous session kept as `DOA5LR-Crimson-VFX.log.old` when the file is over 4 MB, `[Log] Enabled=0` turns it off. Effects unchanged.
- Removed: `DOA5LR-Crimson-EventLog.asi` (a diagnostic that logged every stage effect while the stage was ported) and `DOA5LR-Crimson-BackendProbe.asi` (a research probe that did nothing on its own), with their logs.

## Windows 11 error 4551
"Unable to load DOA5LR-....asi. Error: 4551" is **Smart App Control** (Windows 11), which blocks unsigned DLLs. It is not Windows Defender, so turning Defender off does not help, and we do not recommend tools that disable Defender. Smart App Control can be turned off in Windows Security → App & browser control; on many Windows versions it cannot be turned back on without resetting Windows.

## Unchanged
Every other file is byte-identical to 0.3.13 (Lobby, JoinFix, InviteFix, WiFi-Wired-Detector, UpdateCheck, Borderless, 60fps, Replay Takeover 2.6, controls app, the other maps modules and stage data, Diagnostic probe).
