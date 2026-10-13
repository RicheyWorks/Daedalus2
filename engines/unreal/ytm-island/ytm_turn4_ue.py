r"""youtube-master round-4 one-shot (single ue_send call, light): 1) import + place hero props incl. 13 new READY
records/rack (ytm_hero_ue.py, saves YTM_Island), 2) rebuild flythrough sequences incl. 5 island detail shots,
3) viewport screenshots, 4) save YTM_Island + DaedalusWorld, reset current level, report. Each step guarded so one
failure does not stop the rest. No Play, no render (render separately only if FreeRAM > 2 GB)."""
import unreal, traceback
D = r"C:\Users\730ri\projects\bot-team\art\NOTES\youtube-master" + "\\"
for step in ("ytm_hero_ue.py", "ytm_flythrough_ue.py", "ytm_shots_ue.py", "ytm_save.py", "ytm_reset.py"):
    try:
        exec(open(D + step, encoding="utf-8-sig").read(), {"__name__": "__main__"}); print("TURN4 ok", step)
    except Exception:
        print("TURN4 FAIL", step, traceback.format_exc()[-400:])
