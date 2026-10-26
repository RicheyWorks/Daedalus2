# Prometheus r2 make-up runner: 1 GB free-RAM guard, then send prom_turn_r2.py through the pcg-ecology bridge helper.
$free=[math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,2)
if($free -lt 0.5){ "RAM_GUARD_FAIL free=$free GB"; exit 2 }
"RAM ok free=$free GB"
python C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology\ue_send.py "$PSScriptRoot\prom_turn_r2.py" 480
