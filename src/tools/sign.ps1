#Requires -Version 7
# Signs PE files (.exe / .dll / .asi) with a self-signed code-signing certificate, no Windows SDK needed.
# Usage:  pwsh -NoProfile -File sign.ps1 <file> [<file> ...]      (or  sign.cmd <files>)
#
# What it does / does NOT do:
#   - creates (once) a self-signed cert "FGCsnow - DOA5LR-Salons" in CurrentUser\My, valid 10 years,
#     Code Signing EKU, and exports its public part next to this script (DOA5LR-Salons-signing.cer)
#   - signs with SHA-256 + RFC3161 timestamp (signature stays valid after the cert expires)
#   - records a signing identity; it does not guarantee fewer antivirus detections
#   - does NOT remove the SmartScreen "not commonly downloaded" warning: that one needs reputation
#     (download volume over time) or a real CA-issued certificate (Azure Trusted Signing / SignPath / OV cert)
param([Parameter(Mandatory, ValueFromRemainingArguments)][string[]]$Files)
$ErrorActionPreference = 'Stop'
$Subject   = if ($env:SIGN_SUBJECT) { $env:SIGN_SUBJECT } else { 'CN=FGCsnow - DOA5LR-Salons, O=FGCsnow & BonuStage' }   # set SIGN_SUBJECT to sign with your own certificate
$Timestamp = 'http://timestamp.digicert.com'
$CerOut    = Join-Path $PSScriptRoot ($(if ($env:SIGN_SUBJECT) { 'my-signing.cer' } else { 'DOA5LR-Salons-signing.cer' }))

$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert | Where-Object Subject -eq $Subject |
        Sort-Object NotAfter -Descending | Select-Object -First 1
if (-not $cert) {
    Write-Host "Creating self-signed code-signing certificate: $Subject"
    $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $Subject -CertStoreLocation Cert:\CurrentUser\My `
        -KeyAlgorithm RSA -KeyLength 3072 -HashAlgorithm SHA256 -KeyExportPolicy Exportable `
        -NotAfter (Get-Date).AddYears(10) -FriendlyName 'DOA5LR-Salons code signing'
}
if (-not (Test-Path $CerOut)) { Export-Certificate -Cert $cert -FilePath $CerOut -Type CERT | Out-Null; Write-Host "Exported public cert: $CerOut" }
Write-Host ("Using cert {0}  (thumbprint {1}, valid to {2:yyyy-MM-dd})" -f $cert.Subject, $cert.Thumbprint, $cert.NotAfter)

$fail = 0
foreach ($f in $Files) {
    if (-not (Test-Path $f)) { Write-Warning "missing: $f"; $fail++; continue }
    $r = Set-AuthenticodeSignature -FilePath $f -Certificate $cert -HashAlgorithm SHA256 -TimestampServer $Timestamp -IncludeChain All
    if ($r.Status -eq 'Valid' -or $r.Status -eq 'UnknownError') {
        # UnknownError = signed but chain not trusted on this PC (expected for self-signed). Verify the blob is there:
        $chk = Get-AuthenticodeSignature $f
        if ($chk.SignerCertificate -and $chk.SignerCertificate.Thumbprint -eq $cert.Thumbprint) {
            Write-Host ("SIGNED  {0}  ({1}, timestamp {2})" -f (Split-Path $f -Leaf), $chk.Status, ($(if ($chk.TimeStamperCertificate) {'ok'} else {'NONE'})))
            continue
        }
    }
    Write-Warning ("FAILED  {0}: {1} {2}" -f $f, $r.Status, $r.StatusMessage); $fail++
}
exit $fail
