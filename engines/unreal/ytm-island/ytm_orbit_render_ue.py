r"""youtube-master: SHORT island orbit render that fits a 10-min turn: first 180 frames (6 s @30) of
/Game/YTM/Seq/WB_Flythrough_YTMIsland, 1280x720 JPG, 1 sample, via the light preset. RAM guard: refuses below 2 GB free.
Frames -> bot-team\art\NOTES\youtube-master\renders\WB_Flythrough_YTMIsland\####.jpg (assemble.sh upscales to 1080p)."""
import unreal, subprocess
free_gb = int(subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"],
                             capture_output=True, text=True).stdout.strip() or 0) / 1048576
print("YTM_ORBIT free GB %.2f" % free_gb)
if free_gb < 2.0:
    print("YTM_ORBIT skipped (RAM guard)")
else:
    D = r"C:\Users\730ri\projects\bot-team\art\NOTES\youtube-master" + "\\"
    g = {"__name__": "__main__"}
    exec(open(D + "ytm_render_preset_ue.py", encoding="utf-8-sig").read().split("seq = globals().get")[0], g)
    cfg = g["cfg"]; out = g["out"]
    out.output_resolution = unreal.IntPoint(1280, 720)
    out.use_custom_playback_range = True; out.custom_start_frame = 0; out.custom_end_frame = 180
    unreal.EditorAssetLibrary.save_loaded_asset(cfg)
    sub = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem); q = sub.get_queue()
    for j in list(q.get_jobs()): q.delete_job(j)
    job = q.allocate_new_job(unreal.MoviePipelineExecutorJob); s = "WB_Flythrough_YTMIsland"
    job.sequence = unreal.SoftObjectPath(f"/Game/YTM/Seq/{s}.{s}")
    job.map = unreal.SoftObjectPath("/Game/Daedalus/DaedalusWorld.DaedalusWorld")
    job.set_configuration(cfg)
    sub.render_queue_with_executor(unreal.MoviePipelinePIEExecutor)
    print("YTM_ORBIT render started (180 frames, 1280x720)")
