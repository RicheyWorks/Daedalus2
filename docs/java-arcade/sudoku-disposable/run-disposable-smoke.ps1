# Disposable verification only. No installs, production source edits or existing services.
$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
if ((git -C $taskRoot rev-parse HEAD).Trim() -ne '973c73a35f8659a17022232f0996d4ffb0095997') {
    throw 'Source pin mismatch'
}
$taskClearNames = @(Get-ChildItem Env: | Where-Object {
    $_.Name -match '^(DB_|REDIS_|SPRING_|FCM_|ADMIN_|SUDOKUPRO_)' -or
    $_.Name -in @('MAVEN_OPTS','MAVEN_ARGS','JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS')
} | ForEach-Object { $_.Name })
foreach ($taskName in $taskClearNames) { Remove-Item -LiteralPath ('Env:\' + $taskName) }
$env:JAVA_HOME = 'C:\Program Files\Java\jdk-21.0.4'
Set-Location -LiteralPath $taskRoot
$taskArgs = @('-o','-B','-pl','server','-am','-Dtest=DisposableLoopbackSmokeTest',
    '-Dsurefire.failIfNoSpecifiedTests=false','-DforkedProcessTimeoutInSeconds=180','test')
& 'C:\Maven\apache-maven-3.9.9\bin\mvn.cmd' @taskArgs *> 'disposable-smoke.log'
$taskExit = $LASTEXITCODE
Get-Content -LiteralPath 'disposable-smoke.log' -Tail 30
if (Test-Path -LiteralPath 'disposable-evidence.json') {
    $taskEvidence = Get-Content -LiteralPath 'disposable-evidence.json' -Raw | ConvertFrom-Json
    $taskJvmRunning = $null -ne (Get-Process -Id $taskEvidence.jvmPid -ErrorAction SilentlyContinue)
    $taskEvidence | Add-Member -NotePropertyName ownedJvmExited -NotePropertyValue (-not $taskJvmRunning) -Force
    $taskEvidence | Add-Member -NotePropertyName mavenExitCode -NotePropertyValue $taskExit -Force
    $taskEvidence | Add-Member -NotePropertyName childEnvironmentSanitized -NotePropertyValue $true -Force
    $taskEvidence | Add-Member -NotePropertyName clearedEnvironmentFamilies -NotePropertyValue @(
        'DB_*','REDIS_*','SPRING_*','FCM_*','ADMIN_*','SUDOKUPRO_*',
        'MAVEN_OPTS','MAVEN_ARGS','JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS') -Force
    git diff --quiet -- model/src/main server/src/main
    $taskSourceUnchanged = $LASTEXITCODE -eq 0
    $taskEvidence | Add-Member -NotePropertyName pinnedProductionSourcesUnchanged -NotePropertyValue $taskSourceUnchanged -Force
    $taskTest = Join-Path $taskRoot 'server\src\test\java\com\xai\sudokupro\DisposableLoopbackSmokeTest.java'
    $taskEvidence | Add-Member -NotePropertyName harnessSha256 -NotePropertyValue (Get-FileHash -LiteralPath $taskTest -Algorithm SHA256).Hash.ToLowerInvariant() -Force
    $taskEvidence | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath 'disposable-evidence.json' -Encoding utf8NoBOM
    [PSCustomObject]@{
        Passed=$taskEvidence.passed; Cases=$taskEvidence.caseCount
        ListenerStopped=$taskEvidence.ownedListenerStopped; OwnedJvmExited=(-not $taskJvmRunning)
        HintCountDelta=$taskEvidence.hintCountDelta; HintGemDelta=$taskEvidence.hintGemDelta
        ProductionSourcesUnchanged=$taskSourceUnchanged
    } | ConvertTo-Json -Compress
    if ($taskJvmRunning -or -not $taskEvidence.ownedListenerStopped -or -not $taskSourceUnchanged) { $taskExit=1 }
}
exit $taskExit
