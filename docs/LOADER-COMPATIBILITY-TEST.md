# Costume loader compatibility test

Remove the requirement that an existing x86 Steam API proxy contains the literal string cream_api.ini. Compatible variants may omit it. Keep the existing PE/x86, Steam API, configuration and original-DLL checks; do not replace or execute either DLL during detection.

Synthetic offline tests pass for a proxy without the config filename and reject 64-bit proxies, invalid PE files, missing Steam API markers and incompatible original DLLs. Backup, restore and all costume-installation regression tests also pass. These tests do not establish runtime compatibility with every loader or explain the player's exact rejection.

This is a test build, not an automatic public release. Keep the game closed during installation. Confirm the affected player's real loader and costume behavior before distributing a new production installer.
