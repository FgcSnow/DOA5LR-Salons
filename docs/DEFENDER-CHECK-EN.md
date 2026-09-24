# Microsoft Defender Antivirus check

**Result: the local custom scan completed and reported no threats.** This applies to the preview artifacts identified below, with the Defender engine and signatures recorded here. It is not an antivirus certification or a guarantee about future detections.

## Scope and artifact identity

The entire `DOA5LR-Salons-0.3.9-Preview` delivery folder was scanned on **24 September 2026, 22:09:55–22:09:56 CEST (UTC+02:00)**. The folder contained 15 delivery files, including the installer, both ZIP archives, checksums and documentation. This is the delivery-file count, not an internal Defender count of files unpacked from archives.

| Artifact | Size in bytes | SHA-256 |
| --- | ---: | --- |
| `DOA5LR-Salons-Installer-InputLab-draft.exe` | 123392 | `ecfd56fa8951c30e832d5f6b93d84068cc1c14bd494a2e71ca76d48d8c35e21c` |
| `DOA5LR-Salons-0.3.9-inputlab-draft.zip` | 6560234 | `d15d5fc0b38abd07a44b3ecf8e6107eae1cd02017fc059f46ef5e4f5b3bce85d` |
| `DOA5LR-Commandes-portable-draft.zip` | 1028783 | `159d0f844639649a0dcb6cb7c2daba3379570302dd87df5211b347235e979ab5` |

All 15 delivery files had identical paths, sizes and SHA-256 hashes before and after the scan. This report was updated afterwards to record that result. Changes to documentation do not change the identity of the three artifacts above.

## Defender state at the time of the scan

| Item | Observed value |
| --- | --- |
| Running mode | Normal |
| Antivirus service and antivirus protection | Enabled |
| Real-time protection | Enabled |
| Behavior monitoring | Enabled |
| Tamper protection | Enabled |
| Platform/product version | `4.18.26080.4` |
| Engine version | `1.1.26080.3` |
| Antivirus signature version | `1.459.374.0` |
| Signature last updated | 24 September 2026, 06:55:01 CEST |
| `DefenderSignaturesOutOfDate` | False |

No Defender settings or exclusions were changed. No manual sample submission to an external analysis service was performed.

## Command and result

Exact executable and arguments, with only the personal delivery-folder path replaced by `<preview folder>`:

```powershell
& 'C:\ProgramData\Microsoft\Windows Defender\Platform\4.18.26080.4-0\MpCmdRun.exe' -Scan -ScanType 3 -File '<preview folder>' -DisableRemediation
```

The process returned **exit code 0**. Complete command output, with the same path substitution:

```text
Scan starting...
Scan finished.
Scanning <preview folder> found no threats.
```

`-ScanType 3` selects a custom scan. Microsoft documents that `-DisableRemediation` scans archives, ignores file exclusions, reports detections in command output and does not apply remediation for this scan. It does not disable real-time protection. This scan's command output is the evidence; an empty Windows Security history is not a substitute for it. See [Microsoft's MpCmdRun reference](https://learn.microsoft.com/en-us/defender-endpoint/command-line-arguments-microsoft-defender-antivirus).

The session used a non-elevated token. A separate read-only exclusion query was denied with `0x80070005`; the custom scan itself completed successfully with the output shown above. No exclusion list is included in this report.

## What this result does and does not establish

- Microsoft Defender found no threats in this local scan of these specific artifacts.
- Other antivirus engines, later signatures, download hosts and other PCs were not tested by this check.
- The standalone installer is **not digitally signed**, as confirmed by `Get-AuthenticodeSignature`. This scan does not establish publisher identity.
- SmartScreen evaluates download and publisher reputation separately. New or unsigned software can still produce a warning despite a clean local antivirus scan. See [Microsoft's SmartScreen guidance for app developers](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation).
- Do not disable antivirus protection or add blanket exclusions to install the preview. If a detection occurs, stop and report the exact detection name, affected filename, artifact hash and Defender signature version for investigation.

Suggested public wording: **“This preview was scanned locally with Microsoft Defender on 24 September 2026; no threats were reported. The installer is unsigned, and SmartScreen or other antivirus products may behave differently.”**
