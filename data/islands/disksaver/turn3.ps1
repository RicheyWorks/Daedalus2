# disk-saver round-3 turn runner: save first, pick full or RAM-light fix by free RAM, report.
$d='C:\Users\730ri\projects\bot-team\art\NOTES\disksaver'
$r=[math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,2); "RAM $r GB $(Get-Date -Format HH:mm:ss)"
python "$d\ds_ue_send.py" "$d\ds_save_ue.py" 60
if($r -lt 1.0){ powershell -File "$d\run_island_fix_light.ps1"; 'variant LIGHT' } else { powershell -File "$d\run_island_fix.ps1"; 'variant FULL' }
