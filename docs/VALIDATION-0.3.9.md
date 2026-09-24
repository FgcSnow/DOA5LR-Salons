# DOA5LR-Salons 0.3.9 — Validation

**Release:** pack 0.3.9, installer 1.3.1, UpdateCheck 1.1. Checked on 24 September 2026.

## Final package checks

The actual signed installer and final archives were tested in temporary game folders. No automated check launched Steam, closed the running game or changed the real game installation.

| Check | Result |
| --- | --- |
| Fresh install | Passed: remapping OFF, original Xidi active, settings app installed |
| Upgrade from the verified 0.3.8 archive | Passed: personal INI retained, remapping remains OFF |
| Enabled preview upgraded to the signed final module | Passed: Keyboard mode, custom bindings and original-settings snapshot retained |
| Restore the backup from that upgrade | Passed: previous unsigned bridge, profiles and settings restored byte for byte |
| Disable remapping after restoration | Passed: original Xidi restored and saved input settings reapplied |
| Installer placement | Passed: ZIP includes the same signed installer as the standalone download, where UpdateCheck can find it |
| Legacy compatibility with the actual final manifest | Passed: shipped 1.1.0 and preview 1.3.0 parsers read it and reach installer self-update eligibility |
| Component selection and launch routing | Passed: 11 manifest/UI checks and 18 launcher checks, including fresh OFF and saved choices |
| Archive integrity | Passed: ZIP CRCs, all 94 payload checksums, portable/full app equality, identical companion copies |
| Existing multiplayer components | Lobby, InviteFix and network-tag binaries are byte-identical to 0.3.8 |
| Runtime signing | Executable content matches the tested preview; only PE signature/checksum fields and certificate data changed |
| Microsoft Defender | Final delivery folder scanned locally; no threats reported. See the [scan report](DEFENDER-CHECK-EN.md) |

Installer 1.3.1 was rebuilt from the repository source for manifest compatibility. New `optional_v2` entries are understood by 1.3.1 and ignored by older installers, allowing them to offer their own update. The distributed 1.1 parser rejects an unknown component in the older `optional` field before reaching self-update. Existing preview manifests using `optional=inputlab` remain supported by 1.3.1.

Accept the installer update before updating the pack when offered. These tests cover parsing and update eligibility; they do not simulate a user clicking the network self-update prompt. Preview users should download the final installer directly because the legacy pack-version comparator treats preview and final 0.3.9 as equal.

## Earlier functional checks retained by this release

The unchanged preview runtime was checked for remapping/chords/releases, ANSI/Unicode COM wrappers, buffered input, source ownership and focus. Controls lifecycle checks covered activation, restoration, failed-launch rollback, reactivation, saved-mode repairs and personal-profile preservation. Keyboard startup checks covered no controller, a connected controller and inventory failure.

Diagnostic-export tests covered the allowlist, 2 MiB log tails, raw bytes, shared open files, filtered metadata, junction handling and absence of game writes. Local-manifest tests covered SHA-256 requirements, sibling archives, absolute paths and traversal rejection.

The actual UpdateCheck 1.1 DLL was exercised with a fake game host: a newer version displayed its banner and launched a harmless installer stub after exit; the current version remained quiet; disabling the banner retained the exit-time prompt. This was not a fresh real-match or exclusive-fullscreen test.

The user confirmed the settings button works with remapping unchecked and tested keyboard/controller input on the local PC during development. Final packaging tests do not establish support for other PCs or devices.

## Final artifacts

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `DOA5LR-Salons-0.3.9.zip` | 6605952 | `d8d9ca313709c15063fc635b2716e5f292d40f5f5a34219c9f8a891fe1610f3b` |
| `DOA5LR-Salons-Installer.exe` | 131032 | `c6e4e36c630bb5bfb0aab80e1571872e7e9d4eda483835ecbe8166d773ef4ee3` |
| `DOA5LR-Commandes-portable-0.3.9.zip` | 1061597 | `7c7f08d036d1e2cc638c38f735ced6cc3b6c6117188f004471bbce79daec137a` |

The full ZIP contains 95 entries, including its checksum inventory. Runtime source is included; the installer source in the archive matches the source used for 1.3.1. Authenticode timestamps mean rebuilding can produce different hashes.

## Remaining limits

- Real controller testing covered DualSense Edge only. Detection does not guarantee mapping or support for another device.
- Keyboard mode requires controllers to be disconnected before launch; it does not fix DOA5LR's input selection at startup.
- Automatic device switching and online behavior of the experimental input module are not validated.
- No end-to-end button-to-screen latency measurement or zero-latency claim is made.
- Lobby/invite connection failures reported between two players remain unresolved; this release does not change those binaries.
- Self-signing is not public publisher trust or an antivirus guarantee.

## Reproducing the release checks

Run `tools/test_release_039.py` with `--release-dir`, `--preview-dir` and `--base-zip`. See its help text and `src/Installer/test/` for the other isolated checks. The stable builder is documented in [src/README.md](../src/README.md).
