param(
    [string]$OutputFolder = "$PSScriptRoot\build-output"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Upstream = Join-Path $Root "upstream"
$PrivateSigning = Join-Path $Root "private-signing"
$UpstreamRepository = "https://github.com/jbourny/bluemetermobile.git"
$UpstreamCommit = "3c9d757cc0fd67971faf18447638c08044fb9b7c"

if (Test-Path $Upstream) {
    Remove-Item $Upstream -Recurse -Force
}

New-Item -ItemType Directory -Path $Upstream -Force | Out-Null
git -C $Upstream init
git -C $Upstream remote add origin $UpstreamRepository
git -C $Upstream fetch --depth 1 origin $UpstreamCommit
git -C $Upstream checkout --detach FETCH_HEAD

$ActualCommit = (git -C $Upstream rev-parse HEAD).Trim()
if ($ActualCommit -ne $UpstreamCommit) {
    throw "Upstream commit mismatch: $ActualCommit"
}
Set-Content -Path (Join-Path $Upstream "UPSTREAM_COMMIT.txt") `
    -Value $ActualCommit -Encoding UTF8

python (Join-Path $Root "patch\apply_lite_patch.py") $Upstream

$Keystore = Join-Path $PrivateSigning "bluemeter-lite-release.jks"
$KeyProperties = Join-Path $PrivateSigning "key.properties"

if ((Test-Path $Keystore) -and (Test-Path $KeyProperties)) {
    Copy-Item $Keystore `
        (Join-Path $Upstream "android\app\bluemeter-lite-release.jks") `
        -Force
    Copy-Item $KeyProperties `
        (Join-Path $Upstream "android\key.properties") `
        -Force
    Write-Host "Building with the permanent release key." -ForegroundColor Green
}
else {
    Write-Warning "Permanent signing files were not found. This local build will use debug signing."
}

Push-Location $Upstream
try {
    flutter --version
    flutter pub get
    flutter build apk --release --split-per-abi

    New-Item -ItemType Directory -Path $OutputFolder -Force | Out-Null
    Copy-Item "build\app\outputs\flutter-apk\*.apk" `
        $OutputFolder -Force
}
finally {
    Pop-Location
    Remove-Item (Join-Path $Upstream "android\key.properties") `
        -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $Upstream "android\app\bluemeter-lite-release.jks") `
        -Force -ErrorAction SilentlyContinue
}

Write-Host "APKs copied to: $OutputFolder" -ForegroundColor Green
