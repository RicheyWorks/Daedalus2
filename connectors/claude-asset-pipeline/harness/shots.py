# SPDX-License-Identifier: MIT
"""Make the README's screenshots from real runs, so the pictures never go stale.

    python3 harness/shots.py [--blender-connector DIR] [--unreal-connector DIR]

docs/images/blender-scene.png   the e2e scene, rendered by Blender (bpy, Workbench)
docs/images/shipped.png         a real ship: every check, SHIPPED
docs/images/rejected.png        the same ship with a planted loss: REJECTED, naming the check
"""
import html
import io
import os
import subprocess
import sys
import contextlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "docs", "images")
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)


def blender_render(path):
    import bpy
    import e2e
    exec(e2e.SCENE, {"bpy": bpy})
    sc = bpy.context.scene
    bpy.ops.object.camera_add(location=(7.5, -9.0, 5.5), rotation=(1.13, 0, 0.69))
    sc.camera = bpy.context.active_object
    bpy.ops.object.light_add(type="SUN", rotation=(0.6, 0.2, 0.8))
    colors = {"Brass": (0.80, 0.60, 0.25, 1), "Glow": (1.0, 0.85, 0.5, 1), "Wood": (0.55, 0.36, 0.20, 1)}
    for name, c in colors.items():
        bpy.data.materials[name].diffuse_color = c
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.color_type = "MATERIAL"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.show_shadows = True
    sc.display.shading.show_cavity = True
    sc.world = sc.world or bpy.data.worlds.new("World")
    sc.render.resolution_x, sc.render.resolution_y = 1200, 600
    sc.render.film_transparent = False
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def terminal_png(text, path, title):
    rows = []
    for ln in text.rstrip().splitlines():
        cls = "ok" if ln.startswith(("ok", "SHIPPED")) else "bad" if ln.startswith(("FAIL", "REJECTED")) else ""
        rows.append('<div class="%s">%s</div>' % (cls, html.escape(ln)))
    page = """<html><body><div class="win"><div class="bar"><i></i><i></i><i></i><span>%s</span></div>
<pre>%s</pre></div></body>
<style>body{margin:0;background:#1b1712;padding:24px;font:14px/1.5 Consolas,'DejaVu Sans Mono',monospace}
.win{background:#0f1115;border:1px solid #3a3226;border-radius:10px;overflow:hidden;display:inline-block;min-width:1100px}
.bar{background:#241f18;padding:8px 12px;color:#b88538}.bar i{display:inline-block;width:11px;height:11px;border-radius:50%%;
background:#5a4a33;margin-right:6px}.bar span{margin-left:8px}pre{margin:0;padding:14px 18px;color:#cfd3da}
.ok{color:#7fd88f}.bad{color:#ff6b6b;font-weight:bold}</style></html>""" % (html.escape(title), "".join(rows))
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1200, "height": 400}, device_scale_factor=1)
        pg.set_content(page)
        pg.locator(".win").screenshot(path=path)
        b.close()


def main():
    os.makedirs(OUT, exist_ok=True)
    if "--render-only" in sys.argv:
        blender_render(os.path.join(OUT, "blender-scene.png"))
        return 0
    # Blender in its own process: bpy keeps global state.
    subprocess.run([sys.executable, __file__, "--render-only"], check=True, capture_output=True)
    import e2e
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--blender-connector")
    ap.add_argument("--unreal-connector")
    a = ap.parse_args()
    from asset_pipeline import ship as S, wire
    import tempfile
    import zipfile
    bdir = e2e._find("claude-blender-connector", a.blender_connector)
    udir = e2e._find("claude-unreal-connector", a.unreal_connector)
    work = tempfile.mkdtemp(prefix="pipeline-shots-")
    z = os.path.join(work, "bridge.zip")
    with zipfile.ZipFile(z, "w") as zf:
        zf.write(os.path.join(bdir, "addon", "claude_blender_bridge", "__init__.py"), "claude_blender_bridge/__init__.py")
    bp, up = e2e._port(), e2e._port()
    procs = [subprocess.Popen([sys.executable, os.path.join(bdir, "tests", "host.py"), z, str(bp), "300"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT),
             subprocess.Popen([sys.executable, os.path.join(HERE, "standin_unreal.py"), udir, str(up), "300"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)]
    try:
        e2e._wait(("127.0.0.1", bp), procs[0])
        e2e._wait(("127.0.0.1", up), procs[1])
        wire.call(("127.0.0.1", bp), "execute_code", code=e2e.SCENE)
        args = ["--name", "Props", "--dest", "/Game/Daedalus/Props", "--folder", work,
                "--blender-port", str(bp), "--unreal-port", str(up)]
        for fault, name in ((None, "shipped"), ("drop_tris", "rejected")):
            if fault:
                wire.call(("127.0.0.1", up), "pipeline.fault", kind=fault)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = S.main(args)
            text = "> python -m asset_pipeline --name Props --dest /Game/Daedalus/Props\n" + buf.getvalue() + \
                "(exit %d)" % code
            terminal_png(text, os.path.join(OUT, name + ".png"), "Blender -> Unreal")
    finally:
        for p in procs:
            p.terminate()
    for f in sorted(os.listdir(OUT)):
        print("wrote docs/images/" + f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
