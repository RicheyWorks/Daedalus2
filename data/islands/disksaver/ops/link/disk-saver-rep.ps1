'TOP10'; Get-Process | Sort-Object WorkingSet64 -Desc | Select-Object -First 10 | ForEach-Object { '{0} {1:N2}' -f $_.Name, ($_.WorkingSet64/1GB) }
$os=Get-CimInstance Win32_OperatingSystem
'COMMIT used/limit GB: {0:N1}/{1:N1}' -f (($os.TotalVirtualMemorySize-$os.FreeVirtualMemory)/1MB), ($os.TotalVirtualMemorySize/1MB)
Get-CimInstance Win32_PageFileUsage | ForEach-Object { 'PAGEFILE {0} alloc {1} MB used {2} MB' -f $_.Name,$_.AllocatedBaseSize,$_.CurrentUsage }
Get-PSDrive -PSProvider FileSystem | ForEach-Object { 'DRIVE {0}: free {1:N1} GB used {2:N1} GB' -f $_.Name,($_.Free/1GB),($_.Used/1GB) }
foreach($p in 'C:\Users\730ri\projects\Daedalus2\Saved','C:\Users\730ri\projects\Daedalus2\Intermediate','C:\Users\730ri\projects\Daedalus2\Content','C:\Users\730ri\projects\Daedalus2\Content\Daedalus\Art','C:\Users\730ri\projects\bot-team\art\glb'){
 if(Test-Path $p){ $s=(Get-ChildItem $p -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum); 'SIZE {0} {1:N2} GB {2} files' -f $p,($s.Sum/1GB),$s.Count } else { "MISSING $p" } }
