"""youtube-master: light Movie Render Queue preset for YouTube (1080p30, low RAM). Run in an editor turn:
  ue_send.py ytm_render_preset_ue.py 120             -> creates/updates /Game/YTM/Render/MRQ_YT_1080p30_Light
  ue_send.py ytm_render_preset_ue.py 900 YTM_RENDER=WB_Flythrough_Master   -> also queues + renders that sequence
Low-RAM choices: 1 spatial/1 temporal sample, no high-res tiling, JPG frames (stitched to mp4 off-editor with ffmpeg),
game overrides (cinematic scalability off, texture streaming on), in-editor PIE executor (no second process).
Output: C:\\Users\\730ri\\projects\\bot-team\\art\\NOTES\\youtube-master\\renders\\{sequence_name}\\{frame_number}.jpg"""
import unreal
PATH = "/Game/YTM/Render"; NAME = "MRQ_YT_1080p30_Light"
OUT = r"C:\\Users\\730ri\\projects\\bot-team\\art\\NOTES\\youtube-master\\renders"
eas = unreal.EditorAssetLibrary
if not eas.does_directory_exist(PATH): eas.make_directory(PATH)
full = f"{PATH}/{NAME}"
cfg = eas.load_asset(full) if eas.does_asset_exist(full) else unreal.AssetToolsHelpers.get_asset_tools().create_asset(
    NAME, PATH, unreal.MoviePipelinePrimaryConfig, unreal.MoviePipelinePrimaryConfigFactory())
out = cfg.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
out.output_resolution = unreal.IntPoint(1920, 1080); out.use_custom_frame_rate = True; out.output_frame_rate = unreal.FrameRate(30, 1)
out.output_directory = unreal.DirectoryPath(OUT); out.file_name_format = "{sequence_name}/{frame_number}"; out.override_existing_output = True
aa = cfg.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
aa.spatial_sample_count = 1; aa.temporal_sample_count = 1
cfg.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
cfg.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_JPG)
go = cfg.find_or_add_setting_by_class(unreal.MoviePipelineGameOverrideSetting)
go.cinematic_quality_settings = False
eas.save_loaded_asset(cfg)
unreal.log(f"YTM: render preset saved {full}")
seq = globals().get("YTM_RENDER")
if seq:
    sub = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem); q = sub.get_queue()
    for j in list(q.get_jobs()): q.delete_job(j)
    job = q.allocate_new_job(unreal.MoviePipelineExecutorJob)
    job.sequence = unreal.SoftObjectPath(f"/Game/YTM/Seq/{seq}.{seq}")
    job.map = unreal.SoftObjectPath("/Game/Daedalus/DaedalusWorld.DaedalusWorld")
    job.set_configuration(cfg)
    sub.render_queue_with_executor(unreal.MoviePipelinePIEExecutor)
    unreal.log(f"YTM: render started for {seq} -> {OUT}")
