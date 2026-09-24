# Microsoft Defender Antivirus — 0.3.9 release check

**Result: the local custom scan completed and reported no threats.** This applies to the exact artifacts below and the recorded engine/signatures. It is not antivirus certification or a prediction of future detections.

## Scope and identity

The `DOA5LR-Salons-0.3.9-Release` folder was scanned on **24 September 2026, 23:42:39–23:42:43 CEST (UTC+02:00)**. It contained eight files at the time, including the three release artifacts, checksums and preparation documents. All eight paths, sizes and SHA-256 hashes were identical before and after scanning. Documentation was finalized afterwards; the three artifacts below were not changed.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `DOA5LR-Salons-Installer.exe` | 131032 | `c6e4e36c630bb5bfb0aab80e1571872e7e9d4eda483835ecbe8166d773ef4ee3` |
| `DOA5LR-Salons-0.3.9.zip` | 6605952 | `d8d9ca313709c15063fc635b2716e5f292d40f5f5a34219c9f8a891fe1610f3b` |
| `DOA5LR-Commandes-portable-0.3.9.zip` | 1061597 | `7c7f08d036d1e2cc638c38f735ced6cc3b6c6117188f004471bbce79daec137a` |

## Defender state

| Item | Observed value |
| --- | --- |
| Running mode | Normal |
| Antivirus, real-time protection, behavior monitoring, tamper protection | Enabled |
| Platform/product version | `4.18.26080.4` |
| Engine version | `1.1.26080.3` |
| Antivirus signature version | `1.459.374.0` |
| Signature last updated | 24 September 2026, 06:55:01 CEST |
| Signatures out of date | False |

No antivirus settings or exclusions were changed. No manual sample submission to an external analysis service was performed.

## Command and result

The personal path is replaced with `<release folder>`:

```powershell
& 'C:\ProgramData\Microsoft\Windows Defender\Platform\4.18.26080.4-0\MpCmdRun.exe' -Scan -ScanType 3 -File '<release folder>' -DisableRemediation
```

Exit code: **0**. Complete scan output:

```text
Scan starting...
Scan finished.
Scanning <release folder> found no threats.
```

The command output is the scan evidence. `-DisableRemediation` controls remediation for this custom scan; it does not turn off real-time protection. See [Microsoft's MpCmdRun reference](https://learn.microsoft.com/en-us/defender-endpoint/command-line-arguments-microsoft-defender-antivirus).

## Signing and limits

The final installer and InputLab binaries are signed with the existing project certificate, `FGCsnow - DOA5LR-Salons`, with a DigiCert timestamp. The certificate is self-signed. Windows reports its signer chain as untrusted on the test PC; this is not a publicly trusted publisher signature. No certificate was added to Trusted Root authorities.

Other antivirus products, later definitions and other PCs were not tested here. SmartScreen reputation is separate and may still produce a warning; see [Microsoft's SmartScreen guidance](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation).

If a detection occurs, keep protection enabled and report the exact detection name, affected file, artifact hash and antivirus signature version. Do not assume every mod-related warning is harmless.

Public wording: **“The final 0.3.9 files were scanned locally with Microsoft Defender on 24 September 2026; no threats were reported. The project uses a self-signed certificate, so Windows trust and other antivirus results can differ.”**
