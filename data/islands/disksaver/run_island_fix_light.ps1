$d='C:\Users\730ri\projects\bot-team\art\NOTES\disksaver'
Start-Process -FilePath python -ArgumentList "$d\ds_ue_send.py","$d\ds_island_fix_light_ue.py","420" -RedirectStandardOutput "$d\island_fix3l_run.out" -RedirectStandardError "$d\island_fix3l_run.err" -WindowStyle Hidden
'started'
