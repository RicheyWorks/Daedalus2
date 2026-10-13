r"""youtube-master next-turn one-shot: lighting diag (YTM_Island only), SceneCapture2D views (ytm_capture_ue.py, temp actor removed), save, reset;
viewport screenshots dropped (wrote nothing in round 5). Orbit render is a SEPARATE call afterwards (ytm_orbit_render_ue.py) after the captures."""
import traceback
D = r"C:\Users\730ri\projects\bot-team\art\NOTES\youtube-master" + "\\"
for step in ("ytm_light_ue.py", "ytm_capture_ue.py", "ytm_save.py", "ytm_reset.py"):
    try: exec(open(D + step, encoding="utf-8-sig").read(), {"__name__": "__main__"}); print("TURN5 ok", step)
    except Exception: print("TURN5 FAIL", step, traceback.format_exc()[-400:])
