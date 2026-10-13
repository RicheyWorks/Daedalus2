r"""youtube-master next-turn one-shot: lighting diag+fix (YTM_Island only), save, reset to persistent, then schedule the
tick-based screenshots. Orbit render is a SEPARATE call afterwards (ytm_orbit_render_ue.py) once YTM_SHOTS done."""
import traceback
D = r"C:\Users\730ri\projects\bot-team\art\NOTES\youtube-master" + "\\"
for step in ("ytm_light_ue.py", "ytm_save.py", "ytm_reset.py", "ytm_shots_ue.py"):
    try: exec(open(D + step, encoding="utf-8-sig").read(), {"__name__": "__main__"}); print("TURN5 ok", step)
    except Exception: print("TURN5 FAIL", step, traceback.format_exc()[-400:])
