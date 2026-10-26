# Startup chooser. Always run from this repo — not CSRBT.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Show-Menu {
    Write-Host ""
    Write-Host "DAEDALUS — pick a host"
    Write-Host "  well      2D web well (opens the browser; starts the server if needed)"
    Write-Host "  desktop   JavaFX well"
    Write-Host "  explore   first-person dungeon"
    Write-Host ""
    Write-Host "Example:"
    Write-Host "  cd C:\Users\730ri\projects\Daedalus2"
    Write-Host "  powershell -File run-daedalus.ps1 well"
}

$choice = if ($args.Count -gt 0) { [string]$args[0] } else { "" }
if ($choice -eq "") {
    Show-Menu
    exit 0
}

switch ($choice.ToLowerInvariant()) {
    "well" {
        $up = $false
        try {
            $up = (Invoke-WebRequest -Uri "http://127.0.0.1:8080/" -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200
        } catch {
            $up = $false
        }
        if (-not $up) {
            Write-Host "Starting the web server in a new window..."
            Start-Process powershell -ArgumentList @(
                "-NoExit",
                "-Command",
                "Set-Location '$PSScriptRoot'; mvn -pl daedalus-server -am spring-boot:run"
            )
            Write-Host "Wait until it says Started, then refresh the browser."
        }
        Start-Process "http://127.0.0.1:8080/"
    }
    "desktop" {
        mvn -pl daedalus-desktop -am javafx:run
        exit $LASTEXITCODE
    }
    "explore" {
        powershell -File (Join-Path $PSScriptRoot "daedalus-explore\run-explore.ps1")
        exit $LASTEXITCODE
    }
    default {
        Show-Menu
        Write-Host "Unknown choice: $choice"
        exit 1
    }
}
