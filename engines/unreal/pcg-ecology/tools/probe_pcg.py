import unreal, json
out = {}
out["version"] = unreal.SystemLibrary.get_engine_version()
for n in ["PCGGraph","PCGComponent","PCGVolume","PCGSurfaceSamplerSettings","PCGStaticMeshSpawnerSettings",
          "PCGDensityFilterSettings","PCGSelfPruningSettings","PCGAttributeFilteringSettings","PCGCreatePointsGridSettings",
          "PCGPythonInteropSettings","PCGMetadataOperationSettings","PCGPointMatchAndSetSettings","PCGDistanceSettings","PCGCreatePointsSettings"]:
    out[n] = hasattr(unreal, n)
g = unreal.PCGGraph
out["graph_methods"] = [m for m in dir(g) if any(k in m for k in ("node","edge","input","output","param"))]
out["comp_methods"] = [m for m in dir(unreal.PCGComponent) if any(k in m for k in ("generate","graph","cleanup","seed"))] if hasattr(unreal,"PCGComponent") else []
out["pcg_classes"] = sorted([n for n in dir(unreal) if n.startswith("PCG") and n.endswith("Settings")])[:400]
open(r"C:\Users\730ri\projects\Daedalus2-pcg-ecology\engines\unreal\pcg-ecology\probe.json","w").write(json.dumps(out,indent=1))
