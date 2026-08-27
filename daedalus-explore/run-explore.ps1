# Launch the packaged first-person product. Package first if libs are missing.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$lib = Join-Path $here "target\dist\lib"
$jar = Get-ChildItem (Join-Path $here "target\daedalus-explore-*.jar") -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -notmatch "sources|javadoc|original" } |
    Select-Object -First 1
if (-not $jar -or -not (Test-Path $lib)) {
    Write-Host "Packaging daedalus-explore..."
    Push-Location (Join-Path $here "..")
    try {
        mvn -pl daedalus-explore -am package "-DskipTests" -q
    } finally {
        Pop-Location
    }
    $jar = Get-ChildItem (Join-Path $here "target\daedalus-explore-*.jar") |
        Where-Object { $_.Name -notmatch "sources|javadoc|original" } |
        Select-Object -First 1
}
if (-not $jar) {
    throw "explore jar missing after package"
}
$pass = $args
if ($null -eq $pass -or $pass.Count -eq 0) {
    $pass = @("--window")
}
& java -cp "$($jar.FullName);$lib\*" com.daedalus.explore.ExploreLauncher @pass
exit $LASTEXITCODE
