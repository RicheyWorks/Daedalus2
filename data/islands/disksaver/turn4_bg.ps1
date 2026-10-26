$d='C:\Users\730ri\projects\bot-team\art\NOTES\disksaver'
python "$d\run_canopy.py" 330 0.5 *> "$d\canopy_run.log"
python "$d\ds_ue_send.py" "$d\ds_finish_ue.py" 120 *> "$d\finish_run.out"
'END' | Out-File "$d\turn4.done"
