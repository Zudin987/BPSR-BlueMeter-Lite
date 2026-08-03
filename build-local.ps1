param(
    [string]$OutputFolder = "$PSScriptRoot\build-output"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Upstream = Join-Path $Root "upstream"

if (Test-Path $Upstream) {
    Remove-Item $Upstream -Recurse -Force
}

git clone --depth 1 https://github.com/jbourny/bluemetermobile.git $Upstream
python (Join-Path $Root "patch\apply_lite_patch.py") $Upstream

Push-Location $Upstream
try {
    flutter pub get
    flutter build apk --release --split-per-abi

    New-Item -ItemType Directory -Path $OutputFolder -Force | Out-Null
    Copy-Item "build\app\outputs\flutter-apk\*.apk" $OutputFolder -Force
}
finally {
    Pop-Location
}

Write-Host "APKs copied to: $OutputFolder" -ForegroundColor Green
