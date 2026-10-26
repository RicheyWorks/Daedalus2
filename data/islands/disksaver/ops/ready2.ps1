$f='C:\Users\730ri\projects\bot-team\link\outbox\disk-saver.jsonl'
$enc=New-Object System.Text.UTF8Encoding($false)
$names=(Get-Content 'C:\Users\730ri\projects\bot-team\art\NOTES\disksaver\batch2.json' -Raw | ConvertFrom-Json) | ForEach-Object { $_.asset }
$i=0; $t=''
foreach($a in $names){ $t+='{"to": "unreal-team", "type": "asset.ready", "body": {"asset": "'+$a+'"}}'+"`n"; $i++
  if($i % 150 -eq 0){ [IO.File]::AppendAllText($f,$t,$enc); $t=''; Start-Sleep 9 } }
if($t){ [IO.File]::AppendAllText($f,$t,$enc) }
$d='{"to": "*", "type": "note", "body": {"text": "DONE island:DiskSaver items 500/500 in Blender: batch 2 adds 440 per-asset .blend files in art\\Prop|Item|Mob (crops x3 stages x4, herb variants, rocks, fences/gates, 40 foods, 30 young/adult livestock, 40 water pieces (well, cistern, filter barrel, canteen, bucket, spring, gutter, pond edge), 60 terrain tiles, 40 trees, campfire/cauldron/hay/compost). asset.ready sent for all 440 (generator ds_items2.py). Import waits for the watcher drain."}}'
[IO.File]::AppendAllText($f,$d+"`n",$enc)
"sent $i"
