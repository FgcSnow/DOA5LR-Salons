# PS4 skins detection fix

An otherwise compatible existing loader without a [dlc] section is now supported: append the section and managed costume entry through the existing backup path, preserving original bytes and unrelated settings. Reinstallation is idempotent.

Configuration, proxy DLL and original DLL failures produce specific messages. Unsupported loaders remain rejected. Player screenshots do not establish their exact failure reason.

Validation: offline PS4 installer suite passed, including section creation, idempotency, backup/restore and incompatible configuration refusal. Published assets and real game files unchanged. JoinFix unchanged.

## Player reports, September 30

- One player reported a crash while browsing Marie Rose costumes; restarting restored normal menu behavior. Cause not established.
- Another player reported adding a missing costume registration manually, followed by an Ayane menu screenshot. Full combat validation was not reported.
- Yasha reported missing costume files, updated their DLC files and reported that the game launched. This is a report about content availability, not proof of an installer detection defect.
- Another installation still fails; a disk space explanation was considered and then ruled out by that player. Exact diagnostic error remains needed.

Installer 1.3.7 repairs the missing registration section for recognized loaders and improves rejection messages. It does not supply missing base-game DLC or establish a fix for the reported menu crash. If a costume crashes after installation, restart the game and verify the existing costume files; use repair for managed files. Untick PS4 skins to install the rest of the pack if loader validation fails.
