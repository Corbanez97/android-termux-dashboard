param(
    [string]$RemoteHost = "android-termux",
    [string]$RemoteDir = "projects/android-termux-dashboard"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$StageDir = "$RemoteDir.incoming"
$PackageName = "android-termux-dashboard-deploy.tar"
$RemotePackage = "$StageDir/$PackageName"
$TempTar = Join-Path ([System.IO.Path]::GetTempPath()) ("android-termux-dashboard-" + [System.Guid]::NewGuid().ToString() + ".tar")

$tarExe = (Get-Command tar).Source
$scpExe = (Get-Command scp).Source
$sshExe = (Get-Command ssh).Source

Write-Host "Deploying $ProjectRoot to ${RemoteHost}:$RemoteDir"

try {
    & $tarExe `
        --exclude=.git `
        --exclude=.venv `
        --exclude=data `
        --exclude=__pycache__ `
        --exclude=*.pyc `
        --exclude=*.pyo `
        -C $ProjectRoot `
        -cf $TempTar `
        .

    if ($LASTEXITCODE -ne 0) {
        throw "tar failed with exit code $LASTEXITCODE"
    }

    & $sshExe $RemoteHost "mkdir -p '$StageDir' '$RemoteDir'"
    if ($LASTEXITCODE -ne 0) {
        throw "ssh setup failed with exit code $LASTEXITCODE"
    }

    & $scpExe $TempTar "${RemoteHost}:$RemotePackage"
    if ($LASTEXITCODE -ne 0) {
        throw "scp failed with exit code $LASTEXITCODE"
    }

    $remoteScript = @"
set -euo pipefail
mkdir -p '$StageDir' '$RemoteDir'
find '$StageDir' -mindepth 1 -maxdepth 1 ! -name '$PackageName' -exec rm -rf {} +
tar -xf '$RemotePackage' -C '$StageDir'

rm -rf \
  '$RemoteDir/app.py' \
  '$RemoteDir/README.md' \
  '$RemoteDir/requirements.txt' \
  '$RemoteDir/ecosystem.config.cjs' \
  '$RemoteDir/dashboard' \
  '$RemoteDir/scripts'

cp -a "$StageDir"/. "$RemoteDir"/
rm -f '$RemotePackage'

cd '$RemoteDir'
chmod +x scripts/*.sh

if [ ! -d .venv ]; then
  python -m venv .venv
fi

.venv/bin/pip install -r requirements.txt
./scripts/ensure-services.sh
"@

    & $sshExe $RemoteHost $remoteScript
    if ($LASTEXITCODE -ne 0) {
        throw "ssh deploy failed with exit code $LASTEXITCODE"
    }
}
finally {
    if (Test-Path $TempTar) {
        Remove-Item -LiteralPath $TempTar -Force
    }
}

Write-Host "Deployment complete."
