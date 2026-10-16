param(
 [Parameter(Mandatory=$true)][ValidateSet('export','views','reopen')][string]$Stage,
 [Parameter(Mandatory=$true)][string]$Repo,
 [Parameter(Mandatory=$true)][string]$ManifestPath
)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'StagePolicy.psm1') -Force
$manifest=Get-Content -LiteralPath $ManifestPath -Raw|ConvertFrom-Json
$root=Join-Path $Repo $manifest.output_root
function Require([bool]$condition,[string]$message){if(-not $condition){throw $message}}
function CheckFile([string]$path,[string]$hash){
 Require (Test-Path -LiteralPath $path -PathType Leaf) "Missing file $path"
 Require ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -eq $hash) "Changed file $path"
}
function LocalPath([string]$relative){
 return Resolve-WillowPath -Root $root -Relative $relative
}
foreach($pin in $manifest.pins){CheckFile (Join-Path $Repo $pin.path) $pin.sha256}
$authored=Get-Content (Join-Path $root 'authored.json') -Raw|ConvertFrom-Json
$receiptName=@{export='exported.json';views='views.json';reopen='reopened.json'}[$Stage]
$receipt=Get-Content (Join-Path $root $receiptName) -Raw|ConvertFrom-Json
foreach($property in $authored.inputs.PSObject.Properties){
 Require ($receipt.inputs.($property.Name) -eq $property.Value) 'Stage input binding mismatch'
}
$verified=@()
if($Stage -eq 'export'){
 Require ($receipt.stage -eq 'exported') 'Not an exported receipt'
 Require (@($receipt.outputs).Count -eq 3) 'Exactly three export outputs required'
 $names=@()
 foreach($expected in $manifest.roles){
  $matches=@($receipt.outputs|Where-Object {$_.name -ceq $expected.name -and (ConvertTo-WillowPath $_.path) -ceq (ConvertTo-WillowPath $expected.path) -and $_.role -ceq $expected.role})
  Require ($matches.Count -eq 1) 'Role missing/duplicate/unexpected'
  $entry=$matches[0];$names+=$entry.name
  Require ($entry.units -eq 'metres') 'Export units mismatch'
  Require (($entry.pivot|ConvertTo-Json -Compress) -eq '[0,0,0]') 'Export pivot mismatch'
  $path=LocalPath $entry.path
  Require ((Get-Item $path).Length -eq $entry.bytes -and $entry.bytes -gt 20 -and $entry.bytes -le 67108864) 'Export byte length outside bounded contract'
  CheckFile $path $entry.sha256
  $bytes=[IO.File]::ReadAllBytes($path)
  Require ([Text.Encoding]::ASCII.GetString($bytes,0,4) -eq 'glTF') 'Not GLB'
  Require ([BitConverter]::ToUInt32($bytes,4) -eq 2 -and [BitConverter]::ToUInt32($bytes,8) -eq $bytes.Length) 'Bad GLB version/length'
  Require ([BitConverter]::ToUInt32($bytes,16) -eq 1313821514) 'First GLB chunk is not JSON'
  $length=[BitConverter]::ToUInt32($bytes,12)
  Require ($length -le $bytes.Length-20) 'Invalid JSON chunk length'
  $gltf=[Text.Encoding]::UTF8.GetString($bytes,20,$length)|ConvertFrom-Json
  Require (@($gltf.meshes).Count -eq 1) 'Export must contain one combined role mesh'
  Require (@($gltf.nodes|Where-Object {$_.PSObject.Properties.Name -contains 'mesh'}).Count -eq 1) 'Export must contain one mesh node'
  $node=@($gltf.nodes|Where-Object {$_.PSObject.Properties.Name -contains 'mesh'})[0]
  Require ($node.mesh -eq 0) 'Unexpected mesh index'
  foreach($field in @('translation','scale','rotation','matrix')){
   if($node.PSObject.Properties.Name -contains $field){
    $expected=@{translation=@(0,0,0);scale=@(1,1,1);rotation=@(0,0,0,1);matrix=@(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1)}[$field]
    Require (@($node.$field).Count -eq $expected.Count) 'Malformed export transform'
    for($i=0;$i -lt $expected.Count;$i++){
     $number=[double]$node.$field[$i]
     Require (-not [double]::IsNaN($number) -and -not [double]::IsInfinity($number) -and [math]::Abs($number-$expected[$i]) -lt 0.000001) 'Mesh node transform differs from baked identity'
    }
   }
  }
  Require (-not @($gltf.buffers|Where-Object {$_.uri}).Count) 'External buffers outside retained GLB contract'
  Require (@($gltf.meshes[0].primitives).Count -gt 0) 'No mesh primitives'
  foreach($primitive in $gltf.meshes[0].primitives){Require ($primitive.attributes.PSObject.Properties.Name -contains 'POSITION') 'Primitive missing positions'}
  Require (-not $gltf.skins -and -not $gltf.animations) 'Unexpected rig/animation in static role'
  $verified+=@{path=$entry.path;sha256=$entry.sha256;bytes=$entry.bytes;materials=@($gltf.materials).Count;mesh_count=1}
 }
 Require (@($names|Select-Object -Unique).Count -eq 3) 'Repeated role names'
}elseif($Stage -eq 'views'){
 Require ($receipt.stage -eq 'rendered-unreviewed') 'Views must stay unreviewed until inspected'
 Require (@($receipt.views).Count -eq 3) 'Exactly three review views required'
 foreach($key in @('engine','device','threads','samples','resolution','sun_energy','world_strength')){
  Require (($receipt.settings.$key|ConvertTo-Json -Compress) -eq ($manifest.view_settings.$key|ConvertTo-Json -Compress)) 'Matched view settings changed'
 }
 foreach($name in @('overview','player_contact','refuge_detail')){
  $matches=@($receipt.views|Where-Object {(ConvertTo-WillowPath $_.path) -ceq "views/$name.png"})
  Require ($matches.Count -eq 1 -and $matches[0].reviewed -eq $false) 'View missing/duplicate or review claim unexpected'
  $path=LocalPath $matches[0].path;CheckFile $path $matches[0].sha256
  Require ((Get-Item $path).Length -le 67108864) 'Review PNG exceeds bounded validator size'
  $bytes=[IO.File]::ReadAllBytes($path)
  Require ($bytes.Length -gt 24 -and [BitConverter]::ToString($bytes,0,8) -eq '89-50-4E-47-0D-0A-1A-0A') 'Invalid PNG signature'
  $width=$bytes[16]*16777216+$bytes[17]*65536+$bytes[18]*256+$bytes[19]
  $height=$bytes[20]*16777216+$bytes[21]*65536+$bytes[22]*256+$bytes[23]
  Require ($width -eq 1000 -and $height -eq 1000) 'Review image dimensions mismatch'
  $verified+=@{path=$matches[0].path;sha256=$matches[0].sha256;visual_review=$null}
 }
}else{
 Require ($receipt.stage -eq 'editable-reopened') 'Not a reopen receipt'
 Require ([IO.Path]::GetFullPath($receipt.filepath) -eq [IO.Path]::GetFullPath((Join-Path $root 'WillowPilot.blend'))) 'Wrong reopened file'
 Require ($receipt.objects -gt 0 -and $null -eq $receipt.visual_review) 'Invalid reopen fields'
}
Require ($null -eq $receipt.native) 'Stage cannot claim native acceptance'
@{stage=$Stage;evidence='retained-files-verified';verified=$verified;native=$null;quality_accepted=$null;observed_utc=[DateTimeOffset]::UtcNow.ToString('o')}
