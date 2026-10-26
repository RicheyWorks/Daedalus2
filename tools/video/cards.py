"""Title card, end card, lower-third captions and a YouTube thumbnail for one episode.

usage: python cards.py <episode.json> [--out DIR] [--thumb-bg FRAME.png]
episode.json (see episodes/recording-isle/episode.json):
  {"title": ["richeyworks", "the recording isle"], "end": ["daedalus", "richeyworks"], "end_sub": "music: ...",
   "thumb": ["the recording", "isle"], "kicker": "daedalus", "captions": {"spring": "drink before you build.", ...}}
Writes title.png, end.png, cap_<key>.png (transparent overlay) and thumb.png into DIR (default <episode dir>/cards).
"""
import argparse
import json
import os
import sys
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brand  # noqa: E402

W, H = brand.VIDEO


def _paste_stamp(im, width, xy_fn):
    s = brand.stamp(width)
    if s is not None:
        im.paste(s, xy_fn(s), s)


def card(path, lines, stamp=360, sub=None):
    im = Image.new("RGB", (W, H), brand.BG)
    d = ImageDraw.Draw(im)
    if stamp:
        _paste_stamp(im, stamp, lambda s: ((W - s.width) // 2, H // 2 - s.height - 40))
    y = H // 2 + (20 if stamp else -60)
    for i, t in enumerate(lines):
        f = brand.font(64 if i == 0 else 40, i == 0)
        d.text(((W - d.textlength(t, font=f)) / 2, y), t, font=f, fill=brand.FG if i == 0 else brand.DIM)
        y += 90 if i == 0 else 60
    if sub:
        f = brand.font(28)
        d.text(((W - d.textlength(sub, font=f)) / 2, H - 90), sub, font=f, fill=brand.DIM)
    im.save(path)
    return path


def caption(path, text):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = brand.font(44)
    d.rectangle([80, H - 170, 80 + d.textlength(text, font=f) + 60, H - 90], fill=brand.BG + (170,))
    d.text((110, H - 160), text, font=f, fill=brand.FG)
    _paste_stamp(im, 90, lambda s: (W - 150, 50))
    im.save(path)
    return path


def thumb(path, lines, kicker="daedalus", bg=None):
    tw, th = brand.THUMB
    src = Image.open(bg).convert("RGB") if bg else Image.new("RGB", (tw, th), brand.LINE)
    r = max(tw / src.width, th / src.height)
    src = src.resize((int(src.width * r) + 1, int(src.height * r) + 1))
    l, t = (src.width - tw) // 2, (src.height - th) // 2
    im = Image.blend(src.crop((l, t, l + tw, t + th)), Image.new("RGB", (tw, th), brand.BG), 0.55)
    d = ImageDraw.Draw(im)
    f = brand.font(112, True)
    y = th - 300
    for line in lines:
        d.text((70, y), line, font=f, fill=brand.FG)
        y += 120
    if kicker:
        d.text((74, 90), kicker, font=brand.font(40), fill=brand.DIM)
    _paste_stamp(im, 200, lambda s: (tw - 250, 60))
    im.save(path)
    return path


def build(ep, out, thumb_bg=None):
    os.makedirs(out, exist_ok=True)
    made = [card(os.path.join(out, "title.png"), ep["title"]),
            card(os.path.join(out, "end.png"), ep.get("end", ["richeyworks"]), stamp=260, sub=ep.get("end_sub"))]
    for k, t in ep.get("captions", {}).items():
        made.append(caption(os.path.join(out, "cap_%s.png" % k), t))
    made.append(thumb(os.path.join(out, "thumb.png"), ep.get("thumb", ep["title"][-1:]), ep.get("kicker", "daedalus"), thumb_bg))
    return made


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument("episode")
    a.add_argument("--out")
    a.add_argument("--thumb-bg", default=os.environ.get("THUMB_BG"))
    o = a.parse_args(argv)
    ep = json.load(open(o.episode, encoding="utf-8"))
    out = o.out or os.path.join(os.path.dirname(os.path.abspath(o.episode)), "cards")
    made = build(ep, out, o.thumb_bg)
    print("cards ok: %d files in %s" % (len(made), out))


if __name__ == "__main__":
    main()
