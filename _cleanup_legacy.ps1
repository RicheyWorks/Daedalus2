# =====================================================================
# Daedalus2 -> Legacy archive cleanup
# Run from PowerShell inside the Daedalus2 folder:
#     cd C:\Users\730ri\projects\Daedalus2
#     powershell -ExecutionPolicy Bypass -File .\_cleanup_legacy.ps1
#
# What this does:
#   1. Diagnoses whether OneDrive (or another cloud sync) is shadowing
#      this folder and would re-restore deletions.
#   2. Deletes all 13 .zip files in _migration\legacy-archives\
#      (and the nested versions/ folder).
#   3. Optionally deletes the extracted legacy version folders and the
#      _migration cruft (duplicate-root-files, daedalus-* skeletons).
#
# All paths are inside _migration\, which is gitignored, so nothing
# here ever reaches GitHub. Worst case: you can delete _migration\
# entirely and the GitHub repo is unaffected.
# =====================================================================

$ErrorActionPreference = 'Stop'
$repoRoot = $PSScriptRoot
Set-Location $repoRoot

Write-Host ""
Write-Host "Working directory: $repoRoot" -ForegroundColor Cyan
Write-Host ""

# ----------- 1. OneDrive / cloud-sync diagnostic --------------------
Write-Host "===== Cloud-sync diagnostic =====" -ForegroundColor Magenta

$oneDrive   = $env:OneDrive
$oneDriveCM = $env:OneDriveCommercial
$inOneDrive = $false
if ($oneDrive   -and $repoRoot.StartsWith($oneDrive,   [StringComparison]::OrdinalIgnoreCase)) { $inOneDrive = $true }
if ($oneDriveCM -and $repoRoot.StartsWith($oneDriveCM, [StringComparison]::OrdinalIgnoreCase)) { $inOneDrive = $true }

if ($inOneDrive) {
    Write-Host "  WARNING: this project lives inside a OneDrive-synced path." -ForegroundColor Red
    Write-Host "  When you delete files locally OneDrive will replay them from cloud." -ForegroundColor Red
    Write-Host "  Recommended: move C:\Users\730ri\projects\ outside OneDrive entirely." -ForegroundColor Yellow
} else {
    Write-Host "  This folder is NOT inside OneDrive's user path." -ForegroundColor Green
}

# Check the OneDrive 'Known Folder Move' (KFM) trio: Documents, Desktop, Pictures
$kfmDocs = (Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders' -ErrorAction SilentlyContinue).Personal
if ($kfmDocs -and $kfmDocs -like '*OneDrive*') {
    Write-Host "  Note: Documents folder is OneDrive-synced (KFM enabled). projects\ is outside Documents so this should be fine." -ForegroundColor DarkYellow
}

# Check for File History (the Windows backup that can re-restore)
$fhPath = (Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\FileHistory' -ErrorAction SilentlyContinue).ProtectedUpToTime
if ($fhPath) {
    Write-Host "  Note: Windows File History is enabled. Verify projects\ is in its excluded folders if you don't want restore-on-delete." -ForegroundColor DarkYellow
}

Write-Host ""

# ----------- 2. Inventory the zips ----------------------------------
Write-Host "===== Zip files queued for deletion =====" -ForegroundColor Magenta
$zips = Get-ChildItem -Path .\_migration -Filter *.zip -Recurse -File -ErrorAction SilentlyContinue
if (-not $zips) {
    Write-Host "  (no zip files found — already clean)" -ForegroundColor Green
} else {
    $totalKB = [math]::Round(($zips | Measure-Object Length -Sum).Sum / 1KB, 1)
    foreach ($z in $zips) {
        $rel = $z.FullName.Substring($repoRoot.Length + 1)
        Write-Host ("  {0,8:N0} KB  {1}" -f ($z.Length/1KB), $rel)
    }
    Write-Host ""
    Write-Host ("  Total: {0} files, {1} KB" -f $zips.Count, $totalKB) -ForegroundColor Cyan
}
Write-Host ""

# ----------- 3. Confirm + delete zips -------------------------------
if ($zips) {
    $confirm = Read-Host "Delete all of the above zip files? (yes/no)"
    if ($confirm -eq 'yes' -or $confirm -eq 'y') {
        foreach ($z in $zips) {
            try {
                Remove-Item -LiteralPath $z.FullName -Force
                Write-Host "  deleted: $($z.Name)" -ForegroundColor Green
            } catch {
                Write-Host "  FAILED:  $($z.Name) -- $_" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "  Skipped zip deletion." -ForegroundColor Yellow
    }
}

Write-Host ""

# ----------- 4. Offer to nuke the rest of the legacy cruft -----------
Write-Host "===== Other legacy cruft in _migration\ =====" -ForegroundColor Magenta

$cruftDirs = @(
    '_migration\legacy-archives\Daedalus_Complete_Master_Portfolio',
    '_migration\legacy-archives\Daedalus_Ultimate_Complete_Portfolio_v1.3',
    '_migration\legacy-archives\Daedalus_Ultimate_Complete_Portfolio_v1.4',
    '_migration\legacy-archives\daedalus-complete-audit-2026-05-03 (1)',
    '_migration\legacy-archives\daedalus-server-audit-2026-05-03',
    '_migration\duplicate-root-files',
    '_migration\daedalus-core',
    '_migration\daedalus-desktop',
    '_migration\daedalus-plugin-api',
    '_migration\daedalus-plugin-runtime',
    '_migration\daedalus-server'
)

$existing = $cruftDirs | Where-Object { Test-Path $_ }
if (-not $existing) {
    Write-Host "  (no extracted legacy folders or skeleton dirs left)" -ForegroundColor Green
} else {
    foreach ($d in $existing) {
        $size = (Get-ChildItem -Path $d -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum / 1KB
        Write-Host ("  {0,8:N0} KB  {1}" -f $size, $d)
    }
    Write-Host ""
    Write-Host "These are the extracted versions of the zips above plus duplicates of files" -ForegroundColor DarkGray
    Write-Host "you already have in PDFs\ and Audit\. The intent that survives them is in" -ForegroundColor DarkGray
    Write-Host "BACKLOG.md (just created at the repo root)." -ForegroundColor DarkGray
    Write-Host ""
    $confirm2 = Read-Host "Delete all of the above folders? (yes/no)"
    if ($confirm2 -eq 'yes' -or $confirm2 -eq 'y') {
        foreach ($d in $existing) {
            try {
                Remove-Item -LiteralPath $d -Recurse -Force
                Write-Host "  deleted: $d" -ForegroundColor Green
            } catch {
                Write-Host "  FAILED:  $d -- $_" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "  Skipped folder deletion." -ForegroundColor Yellow
    }
}

# ----------- 5. Final summary --------------------------------------
Write-Host ""
Write-Host "===== Final state of _migration\ =====" -ForegroundColor Magenta
if (Test-Path '_migration') {
    Get-ChildItem -Path .\_migration | Format-Table Name, @{N='SizeKB';E={
        if ($_.PSIsContainer) {
            [math]::Round((Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum / 1KB, 1)
        } else {
            [math]::Round($_.Length / 1KB, 1)
        }
    }}, LastWriteTime -AutoSize
} else {
    Write-Host "  _migration\ no longer exists." -ForegroundColor Green
}

Write-Host ""
Write-Host "Done. Reminder: _migration\ is in .gitignore, so none of this affects what's pushed to GitHub." -ForegroundColor Cyan
Write-Host ""
Write-Host "If files come back after you delete them:" -ForegroundColor Yellow
Write-Host "  1. Check that this folder is NOT inside C:\Users\730ri\OneDrive\" -ForegroundColor Yellow
Write-Host "  2. In Explorer, right-click the folder -> 'Always keep on this device' is OFF, but the folder is also not 'Free up space' (which can re-download)" -ForegroundColor Yellow
Write-Host "  3. If the folder must live near OneDrive, exclude it: OneDrive Settings -> Sync and backup -> Advanced settings -> Excluded folders" -ForegroundColor Yellow
