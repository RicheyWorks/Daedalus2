# round-4 runner: save first, then background canopy batches + finish (hooks, save, v4 shot)
$d='C:\Users\730ri\projects\bot-team\art\NOTES\disksaver'
"RAM $([math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,2)) GB $(Get-Date -Format HH:mm:ss)"
python "$d\ds_ue_send.py" "$d\ds_save_ue.py" 60
if(Test-Path "$d\turn4.done"){ Rename-Item "$d\turn4.done" ("turn4.done." + (Get-Date -Format HHmmss)) }
Start-Process powershell -ArgumentList '-File',"$d\turn4_bg.ps1" -WindowStyle Hidden; 'bg started'
