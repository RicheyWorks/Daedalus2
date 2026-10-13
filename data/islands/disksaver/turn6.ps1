# round 6: save first, hero shot of brewing area, capture with temporary island-only lights, cleanup temps, do NOT save after
$d='C:\Users\730ri\projects\bot-team\art\NOTES\disksaver'; $shot="$d\diskSaver_island_v6.png"
python "$d\ds_ue_send.py" "$d\ds_save_ue.py" 60
python "$d\ds_ue_send.py" "$d\ds_capture_hero_ue.py" 60
Start-Sleep 8
python "$d\ds_ue_send.py" "$d\ds_capture_cleanup_ue.py" 60
if(Test-Path $shot){ "shot $((Get-Item $shot).Length) bytes $((Get-Item $shot).LastWriteTime)" } else { 'NO SHOT' }

