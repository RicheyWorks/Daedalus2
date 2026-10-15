[CmdletBinding(DefaultParameterSetName='Inline')]
param(
    [Parameter(Mandatory,ParameterSetName='Inline')][string]$CachedClasspath,
    [Parameter(Mandatory,ParameterSetName='File')][string]$ClasspathFile,
    [Parameter(Mandatory)][string]$EvidenceRoot,
    [Parameter(Mandatory)][string]$JavaBin,
    [Parameter(Mandatory)][ValidateSet('selected','workspace','a4-portrait','a4-landscape')][string]$Mode,
    [Parameter(Mandatory)][ValidatePattern('^[a-z0-9-]{1,40}$')][string]$RunName,
    [ValidateRange(1,120)][int]$Seconds=120
)
$ErrorActionPreference='Stop'
$utf8=[Text.UTF8Encoding]::new($false,$true)
if($PSCmdlet.ParameterSetName -eq 'File'){
    $info=Get-Item -LiteralPath $ClasspathFile
    if($info.Length -gt 32768 -or $info.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Use a bounded regular classpath file.'}
    $CachedClasspath=[IO.File]::ReadAllText($info.FullName,$utf8).Trim()
}
if($CachedClasspath.Length -gt 32768){throw 'Classpath exceeds the fixture limit.'}
$jars=@($CachedClasspath.Split([IO.Path]::PathSeparator) | ForEach-Object { $_.Trim() })
if($jars.Count -lt 1 -or $jars.Count -gt 32){throw 'Supply 1..32 explicit cached JARs.'}
foreach($jar in $jars){
    if(-not $jar.EndsWith('.jar',[StringComparison]::OrdinalIgnoreCase) -or -not [IO.File]::Exists($jar)){throw 'Every classpath entry must be an existing cached JAR.'}
}
$requiredApplicationHash='6c5fe36af905f8f2ef5d02bc50d7dc648da439bc00ea94db0f90ce331e2b0e12'
$cachedJars=@($jars|ForEach-Object{@{path=[IO.Path]::GetFullPath($_);sha256=(Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash.ToLowerInvariant()}})
$application=@($cachedJars|Where-Object{$_.sha256 -ceq $requiredApplicationHash})
if($application.Count -ne 1){throw 'Supply the tested PR4 application JAR exactly once; its SHA-256 must match this fixture target.'}
# The known application must resolve before any other supplied library containing
# the same package. The generated class directory contains only this fixture.
$jars=@($application[0].path)+@($cachedJars|Where-Object{$_.sha256 -cne $requiredApplicationHash}|ForEach-Object{$_.path})
$jdk=[IO.Path]::GetFullPath($JavaBin)
foreach($binary in @('java.exe','javac.exe')){if(-not [IO.File]::Exists((Join-Path $jdk $binary))){throw 'JavaBin must contain cached java.exe and javac.exe.'}}
$root=[IO.Path]::GetFullPath($EvidenceRoot).TrimEnd([IO.Path]::DirectorySeparatorChar)
if(Test-Path -LiteralPath $root){throw 'EvidenceRoot must be a new test-owned directory; prior evidence is never replaced.'}
$parent=[IO.Path]::GetDirectoryName($root)
if(-not [IO.Directory]::Exists($parent)){throw 'The explicit evidence parent must already exist.'}
for($cursor=$parent;$cursor;$cursor=[IO.Path]::GetDirectoryName($cursor)){
    if((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Evidence parents must not contain reparse points.'}
}
[void](New-Item -ItemType Directory -Path $root -ErrorAction Stop)
$classes=Join-Path $root 'classes';$runs=Join-Path $root 'runs';$tempRoot=Join-Path $root 'tmp';$homeRoot=Join-Path $root 'home'
foreach($dir in @($classes,$runs,$tempRoot,$homeRoot)){[void][IO.Directory]::CreateDirectory($dir)}
$classpath=(@($classes)+$jars)-join [IO.Path]::PathSeparator
$source=Join-Path $PSScriptRoot 'PhotoFixtureLauncher.java'
$savedOptions=@{}
foreach($name in @('JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','_JAVA_OPTIONS')){
    $savedOptions[$name]=[Environment]::GetEnvironmentVariable($name,'Process')
    [Environment]::SetEnvironmentVariable($name,$null,'Process')
}
try{
    $compileArgs=@('-J-Xmx128m','--release','21','-cp',$classpath,'-d',$classes,$source)
    $priorErrorAction=$ErrorActionPreference
    try{$ErrorActionPreference='Continue';$output=@(& (Join-Path $jdk 'javac.exe') @compileArgs 2>&1);$compileExit=$LASTEXITCODE}
    finally{$ErrorActionPreference=$priorErrorAction}
    [IO.File]::WriteAllText((Join-Path $root 'compile.log'),(($output|ForEach-Object{$_.ToString()})-join "`n")+"`n",$utf8)
    if($compileExit -ne 0){throw 'Synthetic launcher compilation failed; see compile.log.'}
    $runtimeArguments=@('-Xms16m','-Xmx192m','-Djava.awt.headless=true','-Djava.net.useSystemProxies=false',
        '-Dhttp.proxyHost=','-Dhttps.proxyHost=','-DsocksProxyHost=','-Dhttp.nonProxyHosts=127.*|localhost',
        "-Djava.io.tmpdir=$tempRoot","-Duser.home=$homeRoot","-Dphoto.acceptanceRoot=$runs",'-cp',$classpath,
        'com.photostopdfpc.bridge.PhotoFixtureLauncher',$Mode,$RunName,[string]$Seconds)
    $started=[DateTime]::UtcNow
    Write-Output ('Fresh private pairing file, only while running: '+(Join-Path $runs "$RunName/private-pairing-link.txt"))
    $priorErrorAction=$ErrorActionPreference
    try{$ErrorActionPreference='Continue';$output=@(& (Join-Path $jdk 'java.exe') @runtimeArguments 2>&1);$runExit=$LASTEXITCODE}
    finally{$ErrorActionPreference=$priorErrorAction}
    $finished=[DateTime]::UtcNow
    [IO.File]::WriteAllText((Join-Path $root 'launcher.log'),(($output|ForEach-Object{$_.ToString()})-join "`n")+"`n",$utf8)
    $record=[ordered]@{
        schema='photospdf.synthetic-fixture-launch.v1';mode=$Mode;runName=$RunName;maxSeconds=$Seconds
        startedUtc=$started.ToString('o');finishedUtc=$finished.ToString('o');compileExitCode=$compileExit;exitCode=$runExit
        sourceSha256=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant()
        compileCommand=@((Join-Path $jdk 'javac.exe'))+$compileArgs;runCommand=@((Join-Path $jdk 'java.exe'))+$runtimeArguments
        requiredApplicationSha256=$requiredApplicationHash;applicationMatchesExactlyOnce=$true;cachedJars=$cachedJars
        downloads=0;sourceAppChanged=$false;nativeOrInstalledGuiRun=$false;processKill=$false;capabilityPrinted=$false
    }
    [IO.File]::WriteAllText((Join-Path $root 'command.json'),($record|ConvertTo-Json -Depth 6)+"`n",$utf8)
    if($runExit -ne 0){throw 'Synthetic fixture failed; see owned launcher.log/lifecycle evidence.'}
    Get-Content -LiteralPath (Join-Path $runs "$RunName/lifecycle.json") -Raw
}finally{
    foreach($name in $savedOptions.Keys){[Environment]::SetEnvironmentVariable($name,$savedOptions[$name],'Process')}
}
