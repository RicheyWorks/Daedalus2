# SPDX-License-Identifier: MIT
# Cut the trailer from the latest take: frames -> 30 fps H.264, captions burned in per shot, fade in/out, an ambient
# pad synthesized by ffmpeg (no third-party music). Output: <take>\daedalus_hype.mp4
#   .\make_trailer.ps1 [-Take <run folder>]
param([string]$Take = "")
$root = "C:\Unreal\DaedalusRealm\Saved\Daedalus\trailer"
if (-not $Take) { $Take = (Get-Content (Join-Path $root "latest.txt") -Raw).Trim() }
$frames = Join-Path $Take "frames"
$n = (Get-ChildItem $frames -Filter "f_*.png").Count
if ($n -eq 0 -and (Test-Path (Join-Path $Take "frames_jpg"))) { $n = (Get-ChildItem (Join-Path $Take "frames_jpg") -Filter "f_*.jpg").Count }
if ($n -lt 30) { throw "only $n frames in $frames" }
# UE's PNGs trip ffmpeg's decoder ("chunk too big"); Pillow re-saves them as JPEGs ffmpeg reads cleanly.
$jpg = Join-Path $Take "frames_jpg"
if (Test-Path $frames) {
    & python (Join-Path $PSScriptRoot "normalize_frames.py") $frames $jpg | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "normalize_frames.py failed" }
}
$fps = 30
$dur = [math]::Round($n / $fps, 2)
$font = "C\:/Windows/Fonts/segoeuib.ttf"
# captions from the plan's shot table (start frame, frames, caption)
$py = "import sys; sys.path.insert(0, r'$PSScriptRoot'); import trailer_plan as t; [print('%d|%d|%s' % v) for v in t.shot_starts().values()]"
# a take that wrote its own captions (part 2, or a combined cut) uses them
$capFile = Join-Path $Take "captions.txt"
$rows = if (Test-Path $capFile) { Get-Content $capFile | Where-Object { $_ } } else { & python -c $py }
$draw = @()
foreach ($r in $rows) {
    $a, $b, $cap = $r.Split("|", 3)
    $t0 = [double]$a / $fps + 0.4; $t1 = ([double]$a + [double]$b) / $fps - 0.3
    $size = if ($cap -eq "DAEDALUS") { 120 } else { 54 }
    $y = if ($cap -eq "DAEDALUS") { "(h-text_h)/2" } else { "h-150" }
    $draw += "drawtext=fontfile='$font':text='$cap':fontsize=${size}:fontcolor=white:borderw=3:bordercolor=black@0.6:x=(w-text_w)/2:y=${y}:enable='between(t,$t0,$t1)':alpha='min(1,(t-$t0)*3)'"
}
$vf = ($draw + "fade=t=in:st=0:d=0.8", "fade=t=out:st=$([math]::Max(0,$dur-1.2)):d=1.2") -join ","
$audio = "aevalsrc='0.08*sin(2*PI*110*t)*(0.6+0.4*sin(2*PI*0.25*t))+0.06*sin(2*PI*164.8*t)+0.05*sin(2*PI*220*t)*(0.5+0.5*sin(2*PI*0.5*t))+0.03*sin(2*PI*329.6*t)':s=48000:d=$dur"
$out = Join-Path $Take "daedalus_hype.mp4"
& ffmpeg -y -loglevel error -framerate $fps -i (Join-Path $jpg "f_%05d.jpg") -f lavfi -i $audio `
    -vf $vf -af "afade=t=in:d=1.5,afade=t=out:st=$([math]::Max(0,$dur-2)):d=2" -c:v libx264 -pix_fmt yuv420p -crf 18 `
    -c:a aac -b:a 160k -shortest $out
if ($LASTEXITCODE -ne 0) { throw "ffmpeg failed" }
"wrote $out ($n frames, $dur s)"
