"""Projection properties with synthetic corners; no bpy or runtime mocks."""
import copy
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("camera_fit_r1", HERE/"hearthjaw_inspection_camera_r1.py")
fit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fit)


def box(name, role, stage, center, size):
    return {"name": name, "role": role, "stage": stage,
            "world_corners": [[center[k]+sign[k]*size[k]/2 for k in range(3)]
                              for sign in itertools.product((-1, 1), repeat=3)]}


def fixture():
    camera = {"projection": "ORTHO", "location": [0, -20, 20], "right": [1, 0, 0],
              "up": [0, .6, .8], "forward": [0, .8, -.6], "shift": [0, 0],
              "sensor_fit": "AUTO", "clip_start": .1, "clip_end": 1000}
    objects = []
    for stage, dimensions in enumerate(((.1, .2, .25), (.7, .6, 1.1), (1.2, .9, 4.5))):
        x, y = stage*.8-2, (stage-1)*3.9
        objects.append(box("plant"+str(stage), "plant", stage, (x, y, dimensions[2]/2+.18), dimensions))
        objects.append(box("body"+str(stage), "pedestal", stage, (x, y, .07), (3.2, 3.2, .14)))
        objects.append(box("rim"+str(stage), "rim", stage, (x, y, .02), (3.3, 3.3, .045)))
    objects.append({"name": "Presentation_Floor", "role": "background", "stage": None})
    return objects, camera


class CameraFit(unittest.TestCase):
    def assert_projection(self, objects, result, margin=.08):
        # Independent normalized orthographic projection using returned camera
        # axes/scale and Blender's documented horizontal/vertical fit convention.
        xres, yres = result["resolution"]; px, py = result["pixel_aspect"]
        aspect = xres*px/(yres*py)
        axis = result["sensor_fit"]
        if axis == "AUTO": axis = "HORIZONTAL" if aspect >= 1 else "VERTICAL"
        w = result["ortho_scale"] if axis == "HORIZONTAL" else result["ortho_scale"]*aspect
        h = w/aspect
        uv = []
        for obj in objects:
            if obj["role"] == "background": continue
            for corner in obj["world_corners"]:
                delta = [corner[k]-result["location"][k] for k in range(3)]
                u = sum(delta[k]*result["right"][k] for k in range(3))/w+.5
                v = sum(delta[k]*result["up"][k] for k in range(3))/h+.5
                depth = sum(delta[k]*result["forward"][k] for k in range(3))
                self.assertGreaterEqual(min(u, v), margin-1e-10)
                self.assertLessEqual(max(u, v), 1-margin+1e-10)
                self.assertGreater(depth, result["clip_start"])
                self.assertLess(depth, result["clip_end"])
                uv.append((u, v))
        occupancy = [max(p[k] for p in uv)-min(p[k] for p in uv) for k in (0, 1)]
        self.assertAlmostEqual(max(occupancy), 1-2*margin, places=8)

    def test_tall_mixed_stages_and_all_pedestals_fit_tightly(self):
        objects, camera = fixture(); untouched = copy.deepcopy((objects, camera))
        result = fit.fit_camera(objects, camera, [1800, 1400])
        self.assert_projection(objects, result)
        self.assertEqual(len(result["subject_objects"]), 9)
        self.assertEqual((objects, camera), untouched)
        self.assertEqual(result["forward"], camera["forward"])
        self.assertFalse(result["runtime_ready"])

    def test_landscape_portrait_pixel_aspect_and_sensor_modes(self):
        objects, camera = fixture()
        for resolution, pixel, sensor in itertools.product(
                ([1800, 1400], [1400, 1800], [4000, 1000], [1000, 4000]),
                ([1, 1], [2, 1], [1, 2]), ("AUTO", "HORIZONTAL", "VERTICAL")):
            with self.subTest(resolution=resolution, pixel=pixel, sensor=sensor):
                camera["sensor_fit"] = sensor
                self.assert_projection(objects, fit.fit_camera(objects, camera, resolution, pixel))

    def test_rotated_translated_staging_and_camera_preserve_fit(self):
        objects, camera = fixture(); original = fit.fit_camera(objects, camera, [1800, 1400])
        # Compound X/Z rotation and large translation: all corners and camera
        # axes transform, so fitted scale must be rigid-transform invariant.
        a, b = .61, -.38
        def rotate(v):
            x, y, z = v; y, z = y*math.cos(a)-z*math.sin(a), y*math.sin(a)+z*math.cos(a)
            return [x*math.cos(b)-y*math.sin(b), x*math.sin(b)+y*math.cos(b), z]
        offset = [1200, -800, 300]
        def point(v): return [x+offset[k] for k, x in enumerate(rotate(v))]
        for obj in objects:
            if "world_corners" in obj: obj["world_corners"] = list(map(point, obj["world_corners"]))
        camera["location"] = point(camera["location"])
        for key in ("right", "up", "forward"): camera[key] = rotate(camera[key])
        result = fit.fit_camera(objects, camera, [1800, 1400])
        self.assert_projection(objects, result)
        self.assertAlmostEqual(result["ortho_scale"], original["ortho_scale"], places=9)
        for a, b in zip(result["location"], point(original["location"])): self.assertAlmostEqual(a, b, places=9)

    def test_rotated_subjects_with_unchanged_camera(self):
        objects, camera = fixture()
        for obj in objects:
            if "world_corners" in obj:
                obj["world_corners"] = [[p[0]*.6-p[1]*.8, p[0]*.8+p[1]*.6, p[2]] for p in obj["world_corners"]]
        self.assert_projection(objects, fit.fit_camera(objects, camera, [1800, 1400], margin=.12), .12)

    def test_missing_stage_parts_unknown_background_and_duplicates_reject(self):
        for mutation in (lambda o:o.pop(0), lambda o:o.append(copy.deepcopy(o[0])),
                         lambda o:o[-1].update(name="Hide_Mature_Leaves")):
            objects, camera = fixture(); mutation(objects)
            with self.assertRaises(ValueError): fit.fit_camera(objects, camera, [1800, 1400])
        _, camera = fixture()
        with self.assertRaises(ValueError): fit.fit_camera([], camera, [1800, 1400])

    def test_nonfinite_and_degenerate_corners_reject(self):
        for value in (float("nan"), float("inf"), True):
            objects, camera = fixture(); objects[0]["world_corners"][0][0] = value
            with self.assertRaises(ValueError): fit.fit_camera(objects, camera, [1800, 1400])
        objects, camera = fixture(); objects[0]["world_corners"] = [[0, 0, 0]]*8
        with self.assertRaises(ValueError): fit.fit_camera(objects, camera, [1800, 1400])
        objects, camera = fixture(); objects[0]["world_corners"] = [[x, x, x] for x in range(8)]
        with self.assertRaises(ValueError): fit.fit_camera(objects, camera, [1800, 1400])

    def test_finite_pixel_aspect_cannot_return_infinite_frame(self):
        objects, camera = fixture(); camera["sensor_fit"] = "VERTICAL"
        with self.assertRaisesRegex(ValueError, "finite"):
            fit.fit_camera(objects, camera, [1, 1], [1e308, 1])
        with self.assertRaisesRegex(ValueError, "positive display aspect"):
            fit.fit_camera(objects, camera, [1, 1], [1e-308, 1e308])

    def test_camera_projection_axes_shift_depth_and_output_metadata_reject(self):
        for key, value in (("projection", "PERSP"), ("shift", [.1, 0]), ("right", [2, 0, 0]),
                           ("forward", [0, 0, 1]), ("clip_end", 1), ("sensor_fit", "OTHER")):
            objects, camera = fixture(); camera[key] = value
            with self.assertRaises(ValueError): fit.fit_camera(objects, camera, [1800, 1400])
        objects, camera = fixture()
        for resolution, pixel, margin in (([0, 1400], [1, 1], .08), ([1800, 1400], [0, 1], .08),
                                         ([1800, 1400], [1, 1], 0), ([1800, 1400], [1, 1], .5)):
            with self.assertRaises(ValueError): fit.fit_camera(objects, camera, resolution, pixel, margin)

    def test_bounds_pin_and_exact_growth_names_required(self):
        objects, camera = fixture(); recipe = {"input_pins":[{"sha256":"a"*64}],
            "expected_plant_names":["plant0","plant1","plant2"], "margin_fraction_per_edge":.08,
            "expected_resolution":[1800,1400]}
        bounds = {"schema":"daedalus.hearthjaw-staged-bounds.v1", "units":"metres", "presentation_sha256":"a"*64,
                  "objects":objects,"camera":camera,"resolution":[1800,1400],"pixel_aspect":[1,1],"full_frame":True}
        self.assert_projection(objects, fit.plan_from_bounds(recipe,bounds))
        for key, value in (("presentation_sha256","b"*64),("units","centimetres"),("schema","unknown"),
                           ("full_frame",False),("resolution",[1400,1800])):
            changed=copy.deepcopy(bounds);changed[key]=value
            with self.assertRaises(ValueError):fit.plan_from_bounds(recipe,changed)
        changed=copy.deepcopy(bounds);changed["objects"][0]["name"]="foreign_stage"
        with self.assertRaises(ValueError):fit.plan_from_bounds(recipe,changed)

    def test_default_cli_is_file_only_pending_and_changed_pin_refuses(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/"copy.blend";source.write_bytes(b"file-only-pin-fixture")
            pin={"path":str(source),"bytes":source.stat().st_size,"sha256":hashlib.sha256(source.read_bytes()).hexdigest()}
            recipe={"schema":"daedalus.hearthjaw-inspection-camera.recipe.v1","source_only":True,"runtime_ready":False,
                    "render_authorized":False,"margin_fraction_per_edge":.08,"input_pins":[pin],"frozen_source_pins":[]}
            path=Path(directory)/"recipe.json";path.write_text(json.dumps(recipe))
            result=subprocess.run([sys.executable,"-B",str(HERE/"hearthjaw_inspection_camera_r1.py"),"--recipe",str(path)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)["state"],"CANONICAL_PINS_VERIFIED_ACTUAL_BOUNDS_PENDING")
            source.write_bytes(b"changed")
            result=subprocess.run([sys.executable,"-B",str(HERE/"hearthjaw_inspection_camera_r1.py"),"--recipe",str(path)],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertEqual(json.loads(result.stdout)["app_calls"],0)
        self.assertNotIn("bpy",sys.modules)

    def test_malformed_metadata_fails_as_value_error_before_any_app(self):
        recipe={"input_pins":[{"sha256":"a"*64}]}
        for value in (None, [], {"schema":"daedalus.hearthjaw-staged-bounds.v1","units":"metres",
                "presentation_sha256":"a"*64,"objects":[None]}):
            with self.assertRaises(ValueError):fit.plan_from_bounds(recipe,value)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"recipe.json";path.write_text("[]")
            with self.assertRaises(ValueError):fit.load_recipe(path)
        self.assertNotIn("bpy",sys.modules)


if __name__ == "__main__":
    unittest.main()
