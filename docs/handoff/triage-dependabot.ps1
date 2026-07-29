# SPDX-License-Identifier: MIT
#
# Dependabot re-triage against Boot 4 (BACKLOG, hardening item) — the pass this script runs:
# the parent bump to spring-boot-starter-parent 4.1.0 re-pinned most managed dependency
# versions, so any open Dependabot PR bumping a Boot-managed artifact is either obsolete or
# actively conflicting. Close those; judge everything Boot does NOT manage (JavaFX,
# resilience4j, springdoc, build plugins, actions/*) on its own merits.
#
# Requires: gh CLI authenticated (gh auth status). Run from the repo root.
#
#   .\docs\handoff\triage-dependabot.ps1            # dry run — prints the verdicts, closes nothing
#   .\docs\handoff\triage-dependabot.ps1 -Close     # actually closes the superseded PRs
param([switch]$Close)

$ErrorActionPreference = "Stop"

# Artifacts whose versions the Boot 4.1 parent manages — a PR bumping one of these is
# superseded by the parent bump. (Prefix match on the PR title's package name.)
$bootManaged = @(
    "org.springframework", "spring-boot", "spring-security", "spring-data",
    "com.fasterxml.jackson", "jackson-", "io.micrometer", "micrometer-",
    "org.apache.tomcat", "tomcat-", "org.slf4j", "slf4j-", "logback",
    "org.junit", "junit-", "org.mockito", "mockito-", "org.assertj", "assertj-",
    "com.github.ben-manes.caffeine", "caffeine", "io.lettuce", "lettuce-",
    "org.apache.commons.commons-pool2", "commons-pool2"
)

$prs = gh pr list --author "app/dependabot" --state open --json number,title --limit 100 | ConvertFrom-Json
if (-not $prs) { Write-Host "No open Dependabot PRs — nothing to triage."; exit 0 }

foreach ($pr in $prs) {
    $managed = $false
    foreach ($prefix in $bootManaged) {
        if ($pr.title -match [regex]::Escape($prefix)) { $managed = $true; break }
    }
    if ($managed) {
        Write-Host ("CLOSE  #{0}  {1}" -f $pr.number, $pr.title)
        if ($Close) {
            gh pr close $pr.number --comment "Superseded by the Spring Boot 4.1.0 parent bump, which re-pins this artifact's managed version. Re-triage pass recorded in BACKLOG.md."
        }
    } else {
        Write-Host ("KEEP   #{0}  {1}   <- not Boot-managed; judge on its own merits" -f $pr.number, $pr.title)
    }
}
if (-not $Close) { Write-Host "`nDry run only. Re-run with -Close to close the CLOSE-marked PRs." }
