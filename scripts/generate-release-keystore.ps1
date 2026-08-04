param(
    [string]$OutputDirectory = "$PSScriptRoot\..\private-signing",
    [string]$Alias = "bluemeter-lite"
)

$ErrorActionPreference = "Stop"

function New-RandomPassword {
    $raw = (
        [guid]::NewGuid().ToString("N") +
        [guid]::NewGuid().ToString("N")
    )
    return $raw.Substring(0, 40)
}

$keytool = Get-Command keytool.exe -ErrorAction SilentlyContinue
if (-not $keytool) {
    $keytool = Get-Command keytool -ErrorAction SilentlyContinue
}
if (-not $keytool) {
    throw "keytool was not found. Install Java 17 and reopen PowerShell."
}

$OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null

$keystorePath = Join-Path $OutputDirectory "bluemeter-lite-release.jks"
$propertiesPath = Join-Path $OutputDirectory "key.properties"
$secretsPath = Join-Path $OutputDirectory "github-secrets.txt"

if (Test-Path $keystorePath) {
    throw "A signing key already exists at $keystorePath. Do not overwrite it."
}

$storePassword = New-RandomPassword
$keyPassword = $storePassword

& $keytool.Source `
    -genkeypair `
    -v `
    -keystore $keystorePath `
    -storetype JKS `
    -storepass $storePassword `
    -keypass $keyPassword `
    -alias $Alias `
    -keyalg RSA `
    -keysize 4096 `
    -validity 10000 `
    -dname "CN=MrEz, OU=BlueMeter Lite, O=BlueMeter Lite, C=MY"

if ($LASTEXITCODE -ne 0) {
    throw "keytool failed with exit code $LASTEXITCODE."
}

$keystoreBase64 = [Convert]::ToBase64String(
    [System.IO.File]::ReadAllBytes($keystorePath)
)

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$propertiesContent = @"
storePassword=$storePassword
keyPassword=$keyPassword
keyAlias=$Alias
storeFile=bluemeter-lite-release.jks
"@
[System.IO.File]::WriteAllText(
    $propertiesPath,
    $propertiesContent.Trim() + [Environment]::NewLine,
    $utf8NoBom
)

$secretsContent = @"
ANDROID_KEYSTORE_BASE64=$keystoreBase64
ANDROID_KEYSTORE_PASSWORD=$storePassword
ANDROID_KEY_ALIAS=$Alias
ANDROID_KEY_PASSWORD=$keyPassword
"@
[System.IO.File]::WriteAllText(
    $secretsPath,
    $secretsContent.Trim() + [Environment]::NewLine,
    $utf8NoBom
)

Write-Host ""
Write-Host "Permanent signing files created:" -ForegroundColor Green
Write-Host "  $keystorePath"
Write-Host "  $propertiesPath"
Write-Host "  $secretsPath"
Write-Host ""
Write-Host "Back up the entire private-signing folder in at least two secure places." `
    -ForegroundColor Yellow
Write-Host "Never upload this folder or any .jks file to GitHub." `
    -ForegroundColor Yellow
Write-Host "Open github-secrets.txt locally and add its four values as GitHub Actions secrets."
