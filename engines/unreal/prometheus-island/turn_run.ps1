$ErrorActionPreference='Continue'; cd C:\Users\730ri\projects\bot-team\art\prometheus_island
function Post($t){ try{Invoke-RestMethod -Method Post http://127.0.0.1:9890/send -ContentType 'application/json' -Body (@{from='prometheus';to='*';type='note';body=@{text=$t}}|ConvertTo-Json -Depth 4)|Out-Null}catch{} }
Post 'DOING editor-slot grok prometheus: Wild Biomes place + Prometheus Island import/place starting.'
python "C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology\ue_send.py" "C:\Users\730ri\projects\bot-team\art\prometheus_ue\wild_biomes_place.py" 600 *> run_wb.txt
python "C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology\ue_send.py" "C:\Users\730ri\projects\bot-team\art\prometheus_ue\shot2.py" 300 *> run_wbshot.txt
python "C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology\ue_send.py" "C:\Users\730ri\projects\bot-team\art\prometheus_island\pi_place.py" 900 *> run_pi.txt
python "C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology\ue_send.py" "C:\Users\730ri\projects\bot-team\art\prometheus_island\pi_shot.py" 300 *> run_pishot.txt
"ALLDONE" | Out-File run_done.txt
