"""Shot lists for assemble.sh, built from real renders, capture/v1 stills, or placeholders.

shots.txt: one shot per line, in order: "<folder> <caption_key|-> [hold_seconds]".
  <folder> holds numbered frames (Movie Render Queue layout: <SequenceName>/0000.jpg ...) played at 30 fps,
  or a single still that is held for hold_seconds (default 4).

  python shots.py prepare <shotlist.txt> <work_dir> [--real ROOT] [--hold 4]
      real frames under ROOT/<folder>/ are copied in (renumbered); missing shots get a labelled placeholder still.
  python shots.py stills <capture manifest.json> <work_dir> [--hold 4] [--captions k=v,...]
      Daedalus tie-in: turns a tools/capture (capture/v1) manifest into a stills shot list, one shot per view.
"""
import argparse
import json
import os
import re
import shutil
import sys
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brand  # noqa: E402

FRAME = re.compile(r"\.(jpe?g|png)$", re.I)


def read_shots(path):
    out = []
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    for raw in lines:
        parts = raw.split("#", 1)[0].split()
        if not parts:
            continue
        hold = float(parts[2]) if len(parts) > 2 else None
        out.append((parts[0], parts[1] if len(parts) > 1 else "-", hold))
    return out


def write_shots(path, shots):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for folder, cap, hold in shots:
            f.write(" ".join([folder, cap or "-"] + (["%g" % hold] if hold else [])) + "\n")
    return path


def frames(folder):
    return sorted(p for p in os.listdir(folder) if FRAME.search(p)) if os.path.isdir(folder) else []


def placeholder(path, label):
    w, h = brand.VIDEO
    im = Image.new("RGB", (w, h), brand.LINE)
    d = ImageDraw.Draw(im)
    f = brand.font(56, True)
    d.text(((w - d.textlength(label, font=f)) / 2, h / 2 - 60), label, font=f, fill=brand.FG)
    f2 = brand.font(32)
    t = "placeholder: no render yet"
    d.text(((w - d.textlength(t, font=f2)) / 2, h / 2 + 20), t, font=f2, fill=brand.DIM)
    im.save(path)
    return path


def prepare(shotlist, work, real=None, hold=4.0):
    """Returns (shots, report) and writes work/shots.txt. report maps folder -> 'real:<n>' or 'placeholder'."""
    os.makedirs(work, exist_ok=True)
    shots, report = [], {}
    for folder, cap, h in read_shots(shotlist):
        dst = os.path.join(work, folder)
        shutil.rmtree(dst, ignore_errors=True)
        os.makedirs(dst)
        src = os.path.join(real, folder) if real else None
        fs = frames(src) if src else []
        if fs:
            for i, name in enumerate(fs):
                shutil.copyfile(os.path.join(src, name), os.path.join(dst, "%04d%s" % (i, os.path.splitext(name)[1].lower())))
            report[folder] = "real:%d" % len(fs)
            shots.append((folder, cap, h if len(fs) == 1 else None))
        else:
            placeholder(os.path.join(dst, "0000.png"), folder)
            report[folder] = "placeholder"
            shots.append((folder, cap, h or hold))
    write_shots(os.path.join(work, "shots.txt"), shots)
    return shots, report


def stills(manifest_path, work, hold=4.0, captions=None):
    """capture/v1 manifest -> one held still per captured file (only files that exist next to the manifest)."""
    with open(manifest_path, encoding="utf-8") as f:
        m = json.load(f)
    if not str(m.get("schema", "")).startswith("capture/v1"):
        raise ValueError("not a capture/v1 manifest: %s" % m.get("schema"))
    base = os.path.dirname(os.path.abspath(manifest_path))
    captions = captions or {}
    os.makedirs(work, exist_ok=True)
    shots = []
    for name in m.get("files", []):
        src = os.path.join(base, name)
        if not os.path.exists(src):
            continue
        view = os.path.splitext(name)[0]
        if view.startswith(m["job"] + "_"):
            view = view[len(m["job"]) + 1:]
        folder = "%s_%s" % (m["job"], view)
        os.makedirs(os.path.join(work, folder), exist_ok=True)
        shutil.copyfile(src, os.path.join(work, folder, "0000" + os.path.splitext(name)[1].lower()))
        shots.append((folder, captions.get(view, "-"), hold))
    write_shots(os.path.join(work, "shots.txt"), shots)
    return shots


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = a.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("shotlist"); p.add_argument("work"); p.add_argument("--real"); p.add_argument("--hold", type=float, default=4.0)
    s = sub.add_parser("stills")
    s.add_argument("manifest"); s.add_argument("work"); s.add_argument("--hold", type=float, default=4.0); s.add_argument("--captions", default="")
    o = a.parse_args(argv)
    if o.cmd == "prepare":
        _, rep = prepare(o.shotlist, o.work, o.real, o.hold)
        for k, v in rep.items():
            print("%-34s %s" % (k, v))
        print("real shots: %d / %d" % (sum(v.startswith("real") for v in rep.values()), len(rep)))
    else:
        caps = dict(kv.split("=", 1) for kv in o.captions.split(",") if "=" in kv)
        print("stills: %d shots -> %s" % (len(stills(o.manifest, o.work, o.hold, caps)), o.work))


if __name__ == "__main__":
    main()
