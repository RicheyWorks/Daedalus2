"""Pure supplemental orthographic fit; never opens Blender or renders.

World-space bounding corners and camera axes must come from a separately
authorized observation of a COPY of the pinned presentation. No such observation
or render is implied by computing a fit. Canonical assets/settings stay intact.
Scale convention: Blender 4.3.1 BKE_camera_view_frame_ex / BKE_camera_sensor_fit:
https://github.com/blender/blender/blob/v4.3.1/source/blender/blenkernel/intern/camera.cc
"""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    require(type(value) in (int, float), "finite number required")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    require(finite, "finite number required")
    return value


def vector(value, width=3):
    require(isinstance(value, (list, tuple)) and len(value) == width, "vector size differs")
    return tuple(number(x) for x in value)


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def camera_axes(camera):
    require(isinstance(camera, dict), "camera metadata object required")
    require(camera.get("projection") == "ORTHO", "only orthographic cameras supported")
    require(vector(camera.get("shift"), 2) == (0, 0), "nonzero camera shift unsupported")
    axes = [vector(camera.get(key)) for key in ("right", "up", "forward")]
    require(all(abs(dot(a, a)-1) <= 1e-6 for a in axes)
            and all(abs(dot(axes[i], axes[j])) <= 1e-6 for i in range(3) for j in range(i)),
            "camera axes must be orthonormal")
    require(abs(dot(cross(axes[0], axes[1]), axes[2])+1) <= 1e-6,
            "camera right/up/forward handedness differs")
    return axes


def fit_camera(objects, camera, resolution, pixel_aspect=(1, 1), margin=.08):
    """Fit all nine staged bounds; exclude only the named background floor.

    Each object has name, role (plant/pedestal/rim/background), stage (0..2)
    and eight evaluated world_corners. Every stage must have all three roles.
    Full-frame camera local +X/+Y/-Z become right/up/forward; orientation/depth stay fixed.
    Output is a plan only. It makes no observed-data or runtime-ready assertion.
    """
    require(isinstance(objects, list) and objects, "nonempty complete object inventory required")
    right, up, forward = camera_axes(camera)
    location = vector(camera.get("location"))
    clip_start, clip_end = number(camera.get("clip_start")), number(camera.get("clip_end"))
    require(0 < clip_start < clip_end, "ordered positive clip planes required")
    width, height = vector(resolution, 2)
    require(type(width) is int and type(height) is int and width > 0 and height > 0,
            "positive integer resolution required")
    px, py = vector(pixel_aspect, 2)
    require(px > 0 and py > 0, "positive pixel aspect required")
    margin = number(margin)
    require(0 < margin < .45, "margin must be between0 and0.45")
    aspect = number((width*px)/(height*py))
    require(aspect > 0, "finite positive display aspect required")
    fit_axis = camera.get("sensor_fit")
    require(fit_axis in ("AUTO", "HORIZONTAL", "VERTICAL"), "unsupported sensor fit")
    if fit_axis == "AUTO":
        fit_axis = "HORIZONTAL" if aspect >= 1 else "VERTICAL"
    names, membership, points, excluded = set(), set(), [], []
    for obj in objects:
        require(isinstance(obj, dict) and isinstance(obj.get("name"), str)
                and obj["name"] and obj["name"] not in names, "distinct named objects required")
        names.add(obj["name"])
        if obj.get("role") == "background":
            require(obj["name"] == "Presentation_Floor" and obj.get("stage") is None,
                    "only the background floor may be excluded")
            excluded.append(obj["name"])
            continue
        role, stage = obj.get("role"), obj.get("stage")
        require(role in ("plant", "pedestal", "rim") and type(stage) is int and 0 <= stage <= 2,
                "every non-background mesh needs a stage and supported role")
        require((stage, role) not in membership, "duplicate staged role")
        membership.add((stage, role))
        corners = obj.get("world_corners")
        require(isinstance(corners, list) and len(corners) == 8, "eight world bounding corners required")
        corners = [vector(p) for p in corners]
        require(len(set(corners)) == 8, "degenerate object bounding corners")
        edges = [tuple(p[k]-corners[0][k] for k in range(3)) for p in corners[1:]]
        extent = max(abs(x) for edge in edges for x in edge)
        require(math.isfinite(extent) and extent > 0, "degenerate corner extent")
        edges = [tuple(x/extent for x in edge) for edge in edges]
        require(max(abs(dot(a, cross(b, c))) for a, b, c in itertools.combinations(edges, 3)) > 1e-10,
                "degenerate three-dimensional object bounds")
        points.extend(corners)
    require(membership == {(stage, role) for stage in range(3) for role in ("plant", "pedestal", "rim")},
            "all three growth stages and both pedestal parts required")
    require(excluded == ["Presentation_Floor"], "complete inventory must include the background floor")
    projected = [tuple(dot(tuple(p[k]-location[k] for k in range(3)), axis)
                       for axis in (right, up, forward)) for p in points]
    require(all(clip_start < p[2] < clip_end for p in projected),
            "subject corner outside unchanged near/far clip planes")
    low = [min(p[k] for p in projected) for k in (0, 1)]
    high = [max(p[k] for p in projected) for k in (0, 1)]
    span = [high[k]-low[k] for k in (0, 1)]
    require(all(math.isfinite(v) and v > 1e-9 for v in span), "degenerate projected group")
    usable = 1-2*margin
    frame_height = number(max(span[1]/usable, span[0]/(usable*aspect))*(1+1e-10))
    frame_width = number(frame_height*aspect)
    cx, cy = [(low[k]+high[k])/2 for k in (0, 1)]
    # Solve the three dot constraints exactly, including small observed axis
    # roundoff: translate in the image plane while preserving forward depth.
    det = dot(right, cross(up, forward))
    move = [(cross(up, forward)[k]*cx+cross(forward, right)[k]*cy)/det for k in range(3)]
    fitted_location = [number(location[k]+move[k]) for k in range(3)]
    scale = number(frame_width if fit_axis == "HORIZONTAL" else frame_height)
    require(scale > 0, "positive finite fitted scale required")
    for p in points:
        local = tuple(dot(tuple(p[k]-fitted_location[k] for k in range(3)), axis)
                      for axis in (right, up, forward))
        uv = (local[0]/frame_width+.5, local[1]/frame_height+.5)
        require(all(margin-1e-12 <= x <= 1-margin+1e-12 for x in uv)
                and clip_start < local[2] < clip_end, "fitted projection loses containment numerically")
    return {"projection": "ORTHO", "location": fitted_location,
            "right": list(right), "up": list(up), "forward": list(forward),
            "sensor_fit": camera["sensor_fit"], "effective_sensor_fit": fit_axis,
            "shift": [0, 0], "clip_start": clip_start, "clip_end": clip_end,
            "resolution": list(resolution), "pixel_aspect": list(pixel_aspect),
            "ortho_scale": scale, "frame_width_m": frame_width, "frame_height_m": frame_height,
            "margin_fraction_per_edge": margin, "projected_group_span_m": span,
            "subject_objects": sorted(names-set(excluded)), "excluded_objects": excluded,
            "source_only": True, "runtime_ready": False, "render_authorized": False}


def load_recipe(path):
    recipe = json.loads(Path(path).read_text(encoding="utf-8"))
    require(isinstance(recipe, dict), "recipe metadata object required")
    require(recipe.get("schema") == "daedalus.hearthjaw-inspection-camera.recipe.v1"
            and recipe.get("source_only") is True and recipe.get("runtime_ready") is False
            and recipe.get("render_authorized") is False, "unapproved or unknown recipe")
    require(0 < number(recipe["margin_fraction_per_edge"]) < .45, "invalid recipe margin")
    require(all(isinstance(recipe.get(key), list) and all(isinstance(p, dict) for p in recipe[key])
                for key in ("input_pins", "frozen_source_pins")), "pin lists required")
    for pin in recipe["input_pins"]+recipe["frozen_source_pins"]:
        raw = Path(pin["path"]).read_bytes()
        require(len(raw) == pin["bytes"] and hashlib.sha256(raw).hexdigest() == pin["sha256"],
                "pinned canonical input changed")
    return recipe


def plan_from_bounds(recipe, bounds):
    require(isinstance(bounds, dict), "bounds metadata object required")
    require(bounds.get("schema") == "daedalus.hearthjaw-staged-bounds.v1"
            and bounds.get("units") == "metres", "unsupported bounds metadata")
    require(bounds.get("presentation_sha256") == recipe["input_pins"][0]["sha256"],
            "bounds must identify the pinned presentation copy")
    require(bounds.get("full_frame") is True and bounds.get("resolution") == recipe["expected_resolution"],
            "unchanged full-frame canonical output required; cropped renders unsupported")
    require(isinstance(bounds.get("objects"), list)
            and all(isinstance(o, dict) for o in bounds["objects"]), "object inventory list required")
    plants = {o.get("name") for o in bounds["objects"] if o.get("role") == "plant"}
    require(plants == set(recipe["expected_plant_names"]), "growth-stage subject membership differs")
    return fit_camera(bounds["objects"], bounds["camera"], bounds["resolution"],
                      bounds["pixel_aspect"], recipe["margin_fraction_per_edge"])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recipe", type=Path, default=Path(__file__).with_suffix(".recipe.json"))
    parser.add_argument("--bounds", type=Path, help="Separately observed evaluated world-corner JSON; file-only")
    args = parser.parse_args(argv)
    try:
        recipe = load_recipe(args.recipe)
        result = {"state": "CANONICAL_PINS_VERIFIED_ACTUAL_BOUNDS_PENDING", "source_only": True,
                  "runtime_ready": False, "render_authorized": False, "app_calls": 0}
        if args.bounds:
            bounds = json.loads(args.bounds.read_text(encoding="utf-8"))
            result.update(state="PURE_CAMERA_FIT_COMPUTED_UNOBSERVED_RENDER", camera=plan_from_bounds(recipe, bounds))
        print(json.dumps(result, allow_nan=False))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(json.dumps({"state": "REFUSED_FILE_ONLY", "error": str(error), "app_calls": 0}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
