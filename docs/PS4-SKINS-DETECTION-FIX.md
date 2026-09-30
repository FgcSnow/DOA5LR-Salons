# PS4 skins detection fix

An otherwise compatible existing loader without a [dlc] section is now supported: append the section and managed costume entry through the existing backup path, preserving original bytes and unrelated settings. Reinstallation is idempotent.

Configuration, proxy DLL and original DLL failures produce specific messages. Unsupported loaders remain rejected. Player screenshots do not establish their exact failure reason.

Validation: offline PS4 installer suite passed, including section creation, idempotency, backup/restore and incompatible configuration refusal. Published assets and real game files unchanged. JoinFix unchanged.
