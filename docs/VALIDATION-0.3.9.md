# Candidate validation

**Build:** DOA5LR-Salons `0.3.9-inputlab-draft`

**Date:** 24 September 2026

**Status:** preview for review; the public update channel remains 0.3.8.

## Verified behavior

| Area | Evidence | Result |
| --- | --- | --- |
| Input settings on the test PC | User confirmed the Keyboard / controller button works with the module unchecked | Passed |
| Default OFF / activation / deactivation | Isolated installer lifecycle tests, including personal profile preservation and backup restoration | Passed |
| Launcher routing | 18 isolated checks: configuration first, missing app handling, saved component refresh, unsaved selections preserved | Passed |
| Diagnostic export | Allowlist, 2 MiB tails, raw bytes, open-file sharing, filtered metadata, reparse junction guard and no game writes | Passed |
| Input mode after repair | Regression reproduced, then Keyboard/Controller/Hybrid repaired without changing mode, bindings or original-settings snapshot | Passed |
| Local preview manifest | Sibling ZIP and absolute path, SHA-256 requirement, remote opt-out and traversal rejection | Passed |
| Keyboard launch checks | No controller, connected controller and inventory-error cases; no game mutation on failure | Passed |
| Controls lifecycle | Eight test groups: native OFF launch, activation, exact restore, launch/copy rollback, reactivation, legacy backups | Passed |
| Installer/app compatibility | App ON -> installer OFF -> app reactivation/restore -> installer backup restoration in a fake game | Passed |
| Native input code | Clean repository build; remapping/chords/releases, ANSI/Unicode COM wrappers, buffered input, source ownership/focus tests | Passed |
| UpdateCheck 1.1 | Actual DLL in fake game: newer version shows banner and launches stub after exit; current version quiet; disabled banner still permits exit prompt | Passed |

No automated test launched Steam or the real game. The banner test reads the
public GitHub manifest and uses a harmless installer stub. Real-game exclusive
fullscreen cannot show this separate-window banner by design; borderless/windowed
behavior was checked with the fake host, not a fresh real-match test.

The final candidate was also installed on the local test PC with a backup.
The saved Controller mode, bindings, component choices and original-settings
snapshot were preserved; UpdateCheck 1.1 and the Logs menu are installed.
The existing Lobby, InviteFix and network-tag binaries are unchanged.
The game was not started during this final installation check.

## Artifact checks

The builder verifies the published 0.3.8 base ZIP hash, original Xidi, x86 PE
architecture, archive entry paths, internal checksums, complete portable app
contents, optional/runtime file ownership and generic keyboard defaults. Package
hashes are supplied alongside the artifacts. The exact final Defender result is
recorded separately in `DEFENDER-CHECK-EN.md`; this report does not predict it.

## Practical limits

- Real controller testing covered DualSense Edge only. Detection does not guarantee a working profile for another device.
- A controller connected before game startup can block keyboard input; Keyboard mode currently requires disconnection before launch.
- Experimental combined input is not a guarantee of automatic switching or verified online compatibility.
- 1 ms is the reader polling request, not measured button-to-screen latency.
- This preview does not change lobby/netcode modules. Lobby 0.9.0 remains an external binary with a local diagnostic log.
- Preview and final 0.3.9 have the same numeric version in the legacy update comparator. Preview testers should install the final release manually when it is published.
- New InputLab/installer files are unsigned; some existing maintained components are self-signed. Antivirus and SmartScreen behavior varies.

Publication is a separate step. The official `version.txt` has not been changed to
advertise this preview, and no user receives it through automatic update checks.
