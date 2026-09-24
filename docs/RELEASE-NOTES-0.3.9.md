# DOA5LR-Salons 0.3.9 candidate — Changes

Version: `0.3.9-inputlab-draft`

Base: verified DOA5LR-Salons 0.3.8 pack

Status: local test build; no public release is implied by this document.

## Added

- An English **Keyboard / controller** app with explicit Keyboard, Controller and experimental combined modes.
- Editable keyboard assignments, a saved personal profile, native-layout reset and an arrow-key preset.
- **Controller Finder** with connected-device inventory, local search by name or VID/PID, profile status and copying of model identifiers.
- A standalone portable ZIP containing the controls app, finder, supporting programs, profiles and module payload, for an existing compatible pack.
- Automatic backup before app-driven module activation, plus restoration of the previous input setup.
- UpdateCheck 1.1's brief in-game update notification: after the default 20-second startup delay, a detected newer version triggers an 8-second banner in borderless or windowed mode. The banner is not visible in exclusive fullscreen.
- A **Logs** menu to open the existing installer or Lobby journal and export a diagnostics ZIP locally. The export includes a small version/settings/hash report and the last 2 MiB of each existing allowlisted log. It does not enable debug logging or upload files; logs must be reviewed before sharing.

## Changed

- Reinstalling or repairing an enabled module now preserves the saved Keyboard/Controller input path instead of forcing combined-mode input flags.

- The settings app is included independently of the optional in-game module. **Keyboard / controller** stays available when the experimental component is unchecked.
- Experimental in-game keyboard remapping is **off by default**. A Keyboard launch can activate it on demand; Controller mode can keep the module off and use the usual game/Steam configuration.
- The desktop shortcut opens pack configuration first. The user chooses when to launch the game.
- Installer and app activation share the saved component state and original input settings, so disabling the module from setup keeps the app and personal profiles.
- Keyboard launches check for connected controllers before changing game settings. When a controller is present, the app explains the startup conflict and stops the launch.
- The experimental combined-mode reader requests a 1 ms polling interval. This setting is not an end-to-end latency measurement.

The update check and exit-time installer prompt already existed in UpdateCheck 1.0. Version 1.1 adds the visible banner; it does not introduce forced updates. Installation still requires the user's choice in the installer after leaving the game.

## Scope and current limits

This patch adds input configuration to the existing pack. It does not introduce a new lobby or private-invite fix, emulate a PS5 controller, or promise support for every controller, stick or leverless device.

Only the DualSense Edge profile `VID_054C&PID_0DF2` has been tested with real controller hardware for this build. Other models still require profile and hardware validation. Detection alone does not create a mapping. Combined mode remains experimental, and a controller connected at startup can prevent keyboard input. Keyboard mode therefore requires controllers to be disconnected before launch.

Rumble and controller button icons are not forwarded through the experimental keyboard path. Online modes have not been validated for this input patch. No zero-latency or universal antivirus-compatibility claim is made.
