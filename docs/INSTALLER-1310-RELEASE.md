# Installer 1.3.10: compatible legacy DLC registration

Recognize the existing DLC configuration format instead of requiring users to replace their INI. Modern [dlc] registration remains supported. Legacy [dlc_subscription]/[dlc_index] configurations receive the missing PS4 subscription, next index, and optional display name; an already-present modern registration does not bypass this repair.

Missing appid/orgapi defaults and the broader x86 loader detection from 1.3.9 are retained. Existing DLLs are not changed. Existing backup/restore handling applies to configuration edits. Explicitly disabled PS4 subscriptions, duplicate or ambiguous sections, invalid DLLs and conflicting indices are still rejected rather than silently overwritten.

Validation: offline installer regression suite passed for modern and legacy inputs, existing mixed-format registration, idempotency, LF/CRLF, duplicate keys/sections, disabled subscription, index gaps and name collisions. SheikProject confirmed the equivalent manual three-entry correction exposes the PS4 costumes in game. That validates the configuration repair for his setup, not every loader version.
