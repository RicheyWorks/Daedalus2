$d='C:\Users\730ri\projects\bot-team\art\NOTES\disksaver'
Start-Process -FilePath python -ArgumentList "$d\ds_ue_send.py","$d\ds_island_ue.py","500" -RedirectStandardOutput "$d\island_run.out" -RedirectStandardError "$d\island_run.err" -WindowStyle Hidden
'started'
