# SPDX-License-Identifier: MIT
"""One-shot original Prismheart title recovery; authored, not executed.

Run only in a later authorized generation slot: python tools/rpg_demo/recover_title.py
"""
import hashlib
import importlib
import json
from pathlib import Path
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
STAGE_ROOT = ROOT / "artifacts/prismheart-visual-r3"
RECIPES = STAGE_ROOT / "title-recipe"
PINS = ROOT / "data/assets/prismheart-visual-r3-title-recipe-pins.json"
OUTPUT = STAGE_ROOT / "title-recovery-r1"
REQUIRED = (
    "tools/blender/pixel_font.py",
    "tools/blender/pixel_png.py",
    "tools/blender/rpg_battle_ui.py",
    "tools/blender/rpg_menus.py",
    "tools/blender/rpg_title.py",
)


def main():
    started = time.monotonic()
    try:
        OUTPUT.mkdir(exist_ok=False)
    except OSError as error:
        print(f"Refusing recovery; output directory was not created: {error}", file=sys.stderr)
        return 2
    receipt = {
        "schema": "daedalus.prismheart.title-recovery/v1",
        "status": "ERROR", "stage": "OUTPUT_DIRECTORY_CREATED",
        "sourceRevision": "9175723ad200b05558a2ea12470763c3b9432152",
        "sourceInventory": str(PINS.relative_to(ROOT)),
        "sourcePins": [], "output": None,
        "visualAcceptance": "PENDING", "buildAcceptance": "PENDING",
    }
    image_path = OUTPUT / "TitleBg_1x.png"
    result = 1
    try:
        pin_bytes = PINS.read_bytes()
        receipt["sourceInventorySha256"] = hashlib.sha256(pin_bytes).hexdigest()
        pins = json.loads(pin_bytes)
        if len(pins) != 5 or {row["path"] for row in pins} != set(REQUIRED):
            raise ValueError("Recipe inventory must contain exactly the five original paths")
        for row in pins:
            source = RECIPES / row["path"]
            content = source.read_bytes()
            actual = hashlib.sha256(content).hexdigest()
            if len(content) != row["bytes"] or actual != row["sha256"]:
                raise ValueError(f"Recipe bytes/hash mismatch: {row['path']}")
            receipt["sourcePins"].append(dict(row))
        receipt["stage"] = "ALL_FIVE_SOURCES_VERIFIED"

        # Import only after all five recipes pass their saved pins.
        names = [Path(path).stem for path in REQUIRED]
        if any(name in sys.modules for name in names):
            raise RuntimeError("Use a fresh one-shot Python process; recipes are already loaded")
        sys.path.insert(0, str(RECIPES / "tools/blender"))
        np = importlib.import_module("numpy")
        title = importlib.import_module("rpg_title")
        for path in REQUIRED:
            module = sys.modules[Path(path).stem]
            if Path(module.__file__).resolve() != (RECIPES / path).resolve():
                raise RuntimeError(f"Unexpected imported recipe: {path}")
        receipt["stage"] = "PINNED_RECIPES_IMPORTED"
        receipt["numpyVersion"] = np.__version__
        frames = [title.title_backdrop("prism", frame) for frame in range(8)]
        strip = np.concatenate(frames, axis=1)
        if strip.shape != (224, 2560, 4):
            raise ValueError(f"Unexpected title strip shape: {strip.shape}")
        receipt["stage"] = "EIGHT_BACKGROUND_FRAMES_ASSEMBLED"
        if image_path.exists():
            raise FileExistsError(image_path)
        title.P.save_png(strip, str(image_path))
        png = image_path.read_bytes()
        if (png[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
                or struct.unpack(">IIBBBBB", png[16:29]) != (2560, 224, 8, 6, 0, 0, 0)):
            raise ValueError("Written output lacks the expected 2560x224 RGBA8 PNG header")
        receipt["stage"] = "PNG_WRITTEN_HEADER_VERIFIED"
        receipt["outputHeader"] = {"width": 2560, "height": 224, "bitDepth": 8, "colorType": 6}
        receipt["status"] = "GENERATED_PENDING_VISUAL_ACCEPTANCE"
        result = 0
    except BaseException as error:
        receipt["error"] = {"type": type(error).__name__, "message": str(error)}
        print(f"Title recovery failed at {receipt['stage']}: {error}", file=sys.stderr)
    finally:
        if image_path.is_file():
            content = image_path.read_bytes()
            receipt["output"] = {
                "path": str(image_path.relative_to(ROOT)), "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        receipt["elapsedSeconds"] = round(time.monotonic() - started, 3)
        # Keep partial output and its failure receipt; never retry over this directory.
        with (OUTPUT / "recovery-receipt.json").open("x", encoding="utf-8") as handle:
            json.dump(receipt, handle, indent=2)
            handle.write("\n")
    print(json.dumps({"status": receipt["status"], "output": receipt["output"]}))
    return result


if __name__ == "__main__":
    if len(sys.argv) != 1:
        raise SystemExit("This one-shot recovery accepts no arguments")
    raise SystemExit(main())
