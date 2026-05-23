# =====================================================================
# Daedalus2 -> GitHub one-shot setup
# Run this from PowerShell inside the Daedalus2 folder:
#     cd C:\Users\730ri\projects\Daedalus2
#     powershell -ExecutionPolicy Bypass -File .\_setup_github.ps1
#
# Choose mode at the prompt: 'gh' (uses GitHub CLI) or 'manual'.
# =====================================================================

$ErrorActionPreference = 'Stop'
$repoRoot = $PSScriptRoot
Set-Location $repoRoot

Write-Host ""
Write-Host "Working directory: $repoRoot" -ForegroundColor Cyan

# --- 0. Clean up any half-initialized .git left from earlier attempts ---
if (Test-Path ".git") {
    Write-Host "Removing existing .git folder (was partially initialized)..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force ".git"
}

# --- 1. git init ---
Write-Host ""
Write-Host "Initializing git repository on branch 'main'..." -ForegroundColor Cyan
git init -b main | Out-Null

# --- 2. Local identity (only for this repo, doesn't touch global config) ---
git config --local user.email "730richey730@gmail.com"
git config --local user.name  "Richmond"
git config --local core.autocrlf true

# --- 3. Stage and commit ---
Write-Host "Staging files (respecting .gitignore)..." -ForegroundColor Cyan
git add -A

$staged = (git diff --cached --name-only | Measure-Object -Line).Lines
Write-Host "  -> $staged files staged" -ForegroundColor Green

Write-Host "Committing..." -ForegroundColor Cyan
git commit -m "Initial commit: Daedalus2 multi-module Maven project" | Out-Null

# --- 4. Pick push mode ---
Write-Host ""
Write-Host "How do you want to push to GitHub?" -ForegroundColor Cyan
Write-Host "  [1] gh CLI (creates the repo on GitHub and pushes in one step)" -ForegroundColor White
Write-Host "  [2] Manual  (you create the repo on github.com first, then this script pushes)" -ForegroundColor White
$mode = Read-Host "Enter 1 or 2"

switch ($mode) {
    "1" {
        # gh CLI path
        $ghCheck = (Get-Command gh -ErrorAction SilentlyContinue)
        if (-not $ghCheck) {
            Write-Host ""
            Write-Host "GitHub CLI ('gh') is not installed or not on PATH." -ForegroundColor Red
            Write-Host "Install it from https://cli.github.com/ then re-run, or pick option 2." -ForegroundColor Yellow
            exit 1
        }
        Write-Host ""
        Write-Host "Creating public repo richmond423/Daedalus2 and pushing..." -ForegroundColor Cyan
        gh repo create richmond423/Daedalus2 --public --source=. --remote=origin --push
        Write-Host ""
        Write-Host "Done. View it at: https://github.com/richmond423/Daedalus2" -ForegroundColor Green
    }
    "2" {
        # Manual path
        Write-Host ""
        Write-Host "Open https://github.com/new in your browser and create:" -ForegroundColor Yellow
        Write-Host "  Owner:       richmond423" -ForegroundColor White
        Write-Host "  Repo name:   Daedalus2" -ForegroundColor White
        Write-Host "  Visibility:  Public" -ForegroundColor White
        Write-Host "  *** DO NOT add a README, .gitignore, or LICENSE *** (we already have them)" -ForegroundColor Red
        Write-Host ""
        Read-Host "Press Enter once the empty repo exists on GitHub"

        Write-Host "Adding remote and pushing..." -ForegroundColor Cyan
        git remote add origin "https://github.com/richmond423/Daedalus2.git"
        git push -u origin main
        Write-Host ""
        Write-Host "Done. View it at: https://github.com/richmond423/Daedalus2" -ForegroundColor Green
    }
    default {
        Write-Host ""
        Write-Host "No push performed. Local commit is in place. To push later, run either:" -ForegroundColor Yellow
        Write-Host "  gh repo create richmond423/Daedalus2 --public --source=. --remote=origin --push" -ForegroundColor White
        Write-Host "  -- or --" -ForegroundColor Gray
        Write-Host "  git remote add origin https://github.com/richmond423/Daedalus2.git" -ForegroundColor White
        Write-Host "  git push -u origin main" -ForegroundColor White
    }
}
