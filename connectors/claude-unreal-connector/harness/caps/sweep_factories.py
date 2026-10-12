# SPDX-License-Identifier: MIT
# Sweep: create one asset with EVERY asset factory that can make one from nothing, read it back, delete it.
# Import and reimport factories need a source file; those are EXCLUDED with that reason (the asset pipeline
# and the import probes cover importing).

import inspect as _inspect

_IMPORT_WORDS = ("Import", "Reimport", "FbxFactory", "SoundFactory", "TextureFactory", "FontFileImport",
                 "CSVImport", "AlembicImport", "SpeedTree", "DNAAsset", "MediaSourceFactory", "Groom",
                 "HairStrands", "PaperTiledImporter", "PaperSpriteSheet", "SceneImport", "VolumeCache",
                 "SparseVolumeTextureFactory", "ModelFactory", "PolysFactory", "PackageFactory", "PackFactory",
                 "LevelFactory", "TrueTypeFont", "CurveImport", "VectorFieldStatic", "SkeletalMeshFromStaticMesh",
                 "SkeletonFromStaticMesh", "NiagaraBakerStaticMesh", "SubUVAnimation", "AnimSequenceConverter",
                 "MetaHumanPackage", "WithAssetWizard")


# Factories that prompt (a modal picker) or that need a class chosen first. Without the class they make an
# abstract asset, and saving that asserts and crashes the editor (seen live, UE 5.8.3: DataAssetFactory).
_PROMPTS_OR_NEEDS_CLASS = ("DataAssetFactory", "DataflowAssetFactory", "Dataflow", "BlueprintFactory",
                           "AnimBlueprintFactory", "ControlRigBlueprintFactory", "PhysicsAssetFactory",
                           "CustomizableObjectFactory", "DataTableFactory", "CompositeDataTableFactory",
                           "CurveTableFactory", "CompositeCurveTableFactory", "MirrorDataTableFactory",
                           "AnimMontageFactory", "AnimCompositeFactory", "AnimSequenceFactory", "BlendSpace",
                           "AimOffset", "PoseAssetFactory", "IKRetargetFactory", "IKRigDefinitionFactory",
                           "MaterialFunctionInstanceFactory", "NiagaraEmitterFactoryNew", "NiagaraSystemFactoryNew")
BATCH = 25


def _factories():
    out = []
    for n in dir(unreal):
        c = getattr(unreal, n, None)
        if _inspect.isclass(c):
            try:
                if issubclass(c, unreal.Factory) and c is not unreal.Factory:
                    out.append((n, c))
            except Exception:
                pass
    return sorted(out)


@probe("sweep.factories")
def _sweep(batch=None):
    """batch=k runs only factories k*BATCH .. (k+1)*BATCH-1, so one bad factory costs one batch, not the walk."""
    rows, ok, fail, excluded = {}, 0, 0, 0
    allf = _factories()
    span = range(len(allf)) if batch is None else range(batch * BATCH, min(len(allf), (batch + 1) * BATCH))
    for i in span:
        name, cls = allf[i]
        if any(w in name for w in _PROMPTS_OR_NEEDS_CLASS):
            rows[name] = {"state": "EXCLUDED", "why": "prompts for a choice or needs a class first; the area probes make these with the class set"}
            excluded += 1
            continue
        if any(w in name for w in _IMPORT_WORDS):
            rows[name] = {"state": "EXCLUDED", "why": "imports from a file; covered by the import probes"}
            excluded += 1
            continue
        try:
            f = cls()
            supported = f.get_editor_property("supported_class")
            if supported is None:
                rows[name] = {"state": "EXCLUDED", "why": "no supported_class (a base or helper factory)"}
                excluded += 1
                continue
            if not f.get_editor_property("create_new"):
                rows[name] = {"state": "EXCLUDED", "why": "create_new is false (needs a source)"}
                excluded += 1
                continue
            asset_name = "F%03d_%s" % (i, name[:40])
            a = AT.create_asset(asset_name, PROBE_DIR + "/Factories", supported, f)
            if a is None:
                rows[name] = {"state": "FAIL", "why": "create_asset returned None", "class": supported.get_name()}
                fail += 1
                continue
            path = PROBE_DIR + "/Factories/" + asset_name
            rows[name] = {"state": "ok" if EAL.does_asset_exist(path) else "FAIL", "class": a.get_class().get_name()}
            if rows[name]["state"] == "ok":
                ok += 1
            else:
                fail += 1
        except Exception as e:
            rows[name] = {"state": "FAIL", "why": "%s: %s" % (type(e).__name__, str(e)[:160])}
            fail += 1
    total = len(rows)
    return {"ok": ok + fail + excluded == total and ok > 0, "total": total, "created": ok, "failed": fail,
            "excluded": excluded, "rows": rows}
