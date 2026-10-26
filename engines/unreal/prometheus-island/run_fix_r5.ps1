# Prometheus r5 runner: bridge ping first (process alive is not enough), then terrain fix + ground snap + capture. No imports.
$ping=python -c "import socket,json;s=socket.create_connection(('127.0.0.1',9877),5);print('bridge ok')" 2>&1
"$ping"; if("$ping" -notmatch 'bridge ok'){ "BRIDGE_DOWN"; exit 3 }
"RAM free " + [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB,2) + " GB"
python C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology\ue_send.py "$PSScriptRoot\prom_fix_terrain_r5.py" 420
