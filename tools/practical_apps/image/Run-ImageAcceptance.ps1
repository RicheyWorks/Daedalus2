param(
    [Parameter(Mandatory=$true)][string]$AppRepo,
    [Parameter(Mandatory=$true)][string]$CachedThumbnailatorJar,
    [Parameter(Mandatory=$true)][string]$EvidenceRoot,
    [Parameter(Mandatory=$true)][ValidateSet('compile','run','verify-persisted','serve','serve-smoke')][string]$Mode
)
$ErrorActionPreference='Stop'
$repo=(Resolve-Path -LiteralPath $AppRepo).Path
$dependency=(Resolve-Path -LiteralPath $CachedThumbnailatorJar).Path
$evidence=[IO.Path]::GetFullPath($EvidenceRoot)
$classes=Join-Path $evidence 'classes'
$temporary=Join-Path $evidence 'temp'
$expected='bdd47836cedb5c5261d281cb4ab132a1e89fcb91'
$head=(& git -C $repo rev-parse HEAD).Trim()
if($LASTEXITCODE -ne 0 -or $head -ne $expected){throw 'Image source head changed; review this pinned acceptance fixture again.'}
if(-not(Test-Path -LiteralPath $dependency -PathType Leaf) -or [IO.Path]::GetExtension($dependency) -ne '.jar'){throw 'Explicit cached Thumbnailator JAR is absent; this launcher never downloads dependencies.'}
$dependencyHash=(Get-FileHash -LiteralPath $dependency -Algorithm SHA256).Hash.ToLowerInvariant()
if($dependencyHash -ne '3f64835132076ba7d01e2780747eb2304f67f296cfb71729af3bdbdae71eab3a'){throw 'Cached dependency does not match the verified Thumbnailator 0.4.20 JAR.'}
$expectedPaths=@(
    'src/main/java/com/terpenepirate/imageoptimizer/ImageOptimizationService.java',
    'src/main/java/com/terpenepirate/imageoptimizer/ImageOptimizer.java',
    'src/main/java/com/terpenepirate/imageoptimizer/OptimizationJobService.java',
    'src/main/java/com/terpenepirate/imageoptimizer/OptimizationPlan.java',
    'src/main/java/com/terpenepirate/imageoptimizer/WorkspaceApprovalDialog.java',
    'src/main/java/com/terpenepirate/imageoptimizer/bridge/ImageBatch.java',
    'src/main/java/com/terpenepirate/imageoptimizer/bridge/RealmImageBridge.java',
    'src/main/java/com/terpenepirate/imageoptimizer/bridge/RealmImageWorkspace.java'
)
$actual=@(Get-ChildItem -LiteralPath (Join-Path $repo 'src/main/java') -Recurse -Filter '*.java' -File | ForEach-Object {$_.FullName.Substring($repo.Length+1).Replace('\','/')})
if($actual.Count -ne 8 -or @(Compare-Object $expectedPaths $actual).Count -ne 0){throw 'Unexpected source scope; expected exactly the pinned eight application Java files.'}
$sources=@()
foreach($relative in $expectedPaths){
    $file=Join-Path $repo $relative
    $pin=(& git -C $repo rev-parse ($expected+':'+$relative)).Trim()
    if($LASTEXITCODE -ne 0){throw 'Pinned app source blob unavailable; no download attempted.'}
    $current=(& git -C $repo hash-object ('--path='+$relative) '--' $file).Trim()
    if($LASTEXITCODE -ne 0 -or $pin -ne $current){throw 'Application source differs from the pinned commit; review before executing.'}
    $sources+=$file
}
& git -C $repo diff --quiet $expected '--' 'src/main/resources'
if($LASTEXITCODE -ne 0){throw 'Application resources changed from the pinned commit.'}
New-Item -ItemType Directory -Force -Path $classes,$temporary | Out-Null
if($Mode -eq 'compile'){
    & javac '-J-Xmx128m' '--release' '21' '-encoding' 'UTF-8' '-cp' $dependency '-d' $classes @sources (Join-Path $PSScriptRoot 'ImageWorkspaceAcceptance.java')
    if($LASTEXITCODE -ne 0){throw 'Bounded offline javac did not succeed.'}
    $manifest=@($sources | ForEach-Object { [ordered]@{path=$_.Substring($repo.Length+1).Replace('\','/');sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash.ToLowerInvariant()} })
    [ordered]@{sourceHead=$head;offline=$true;appSourceFiles=8;compilerHeapMiB=128;files=$manifest;runnerSha256=(Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'ImageWorkspaceAcceptance.java') -Algorithm SHA256).Hash.ToLowerInvariant();dependency=[ordered]@{path=$dependency;sha256=$dependencyHash}} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $evidence 'compile-provenance.json') -Encoding utf8
    Write-Output 'Compiled eight pinned unchanged app sources plus the evidence runner; no Maven/native build or download.'
    exit 0
}
if(-not(Test-Path -LiteralPath (Join-Path $classes 'com/terpenepirate/imageoptimizer/bridge/ImageWorkspaceAcceptance.class'))){throw 'Run -Mode compile first; no implicit compilation or download occurs.'}
$provenance=Get-Content -LiteralPath (Join-Path $evidence 'compile-provenance.json') -Raw | ConvertFrom-Json
if($provenance.sourceHead -ne $expected -or $provenance.dependency.sha256 -ne $dependencyHash -or $provenance.runnerSha256 -ne (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'ImageWorkspaceAcceptance.java') -Algorithm SHA256).Hash.ToLowerInvariant()){throw 'Compiled evidence provenance changed; compile a new evidence packet.'}
$separator=[IO.Path]::PathSeparator
$classPath=$classes+$separator+(Join-Path $repo 'src/main/resources')+$separator+$dependency
& java '-Xms16m' '-Xmx128m' '-Djava.awt.headless=true' ('-Djava.io.tmpdir='+$temporary) '-cp' $classPath 'com.terpenepirate.imageoptimizer.bridge.ImageWorkspaceAcceptance' $Mode $evidence
if($LASTEXITCODE -ne 0){throw 'Synthetic service acceptance did not complete.'}
