import unreal
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
r = {}
for n in ("Island_DiskSaver", "/Game/DiskSaver/Maps/Island_DiskSaver"):
    try:
        s = unreal.GameplayStatics.get_streaming_level(w, n); r[n] = str(s.get_name()) if s else None
    except Exception as e: r[n] = "E " + str(e)
result = r
