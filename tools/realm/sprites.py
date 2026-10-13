# SPDX-License-Identifier: MIT
"""DSP 1, the 8-bit realm's sprite pack: write it from PNG sheets, read it back (a line-for-line port of
DaedalusRealmSprites.h's parser, so Python and C++ agree on every refusal).

    python sprites.py pack <png dir> <out.dsp>     every <id>.png in the dir becomes a sprite; frames side by side,
                                                   frame width = height (people: 8 frames; monsters: 2)
    python sprites.py check <file.dsp>             parse and print the sprite count

A PNG's alpha (< 128) is transparent. Colours are quantized to the pack's palette (up to 62, nearest RGB).
Ids come from file names: BLIGHT_SLIME.png, BLIGHT_SLIME.2.png (tier 2 -> "BLIGHT_SLIME:2"), MEMBER.HERO.png ->
"MEMBER:HERO", NPC.INN.png -> "NPC:INN". Original art only.
"""
import os
import sys

DIGITS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
MAX_SPRITES, MAX_SIZE, MAX_FRAMES, MAX_COLOURS, MAX_LINE = 4096, 128, 16, 62, 1024


def is_id(s):
    return 0 < len(s) <= 64 and all(c.isalnum() or c in "_:-" for c in s)


def parse(text):
    """(pack, None) or (None, "line N: why"). pack = {"palette": [rgb...], "sprites": {id: (w, h, frames, rows)}}."""
    lines = text.replace("\r", "").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines or lines[0] != "DSP 1":
        return None, "line 1: expected 'DSP 1'"
    palette, sprites = [], {}
    open_id, rows_left, rows = None, 0, []
    for i, line in enumerate(lines[1:], start=2):
        if len(line) > MAX_LINE:
            return None, "line %d: line too long" % i
        if rows_left > 0:
            w = sprites[open_id][0]
            if len(line) != w:
                return None, "line %d: row of %d for a sprite %d wide" % (i, len(line), w)
            for c in line:
                if c == ".":
                    continue
                d = DIGITS.find(c)
                if d < 0 or d >= len(palette):
                    return None, "line %d: colour '%s' is not in the palette" % (i, c)
            rows.append(line)
            rows_left -= 1
            if rows_left == 0:
                w, h, f, _ = sprites[open_id]
                sprites[open_id] = (w, h, f, rows)
                open_id, rows = None, []
            continue
        if not line or line[0] == "#":
            continue
        if "\t" in line:
            return None, "line %d: tab" % i
        f = [x for x in line.split(" ") if x]
        if f[0] == "palette":
            if palette:
                return None, "line %d: a second palette" % i
            if len(f) < 2:
                return None, "line %d: expected 'palette <n> <hex>...'" % i
            n = int(f[1]) if f[1].isdigit() else 0
            if n < 1 or n > MAX_COLOURS or len(f) != n + 2:
                return None, "line %d: palette count does not match" % i
            for hx in f[2:]:
                if len(hx) != 6 or any(c not in "0123456789abcdefABCDEF" for c in hx):
                    return None, "line %d: bad colour %s" % (i, hx)
                v = int(hx, 16) or 0x010101
                palette.append(v)
        elif f[0] == "sprite":
            if not palette:
                return None, "line %d: sprite before the palette" % i
            if len(f) != 5:
                return None, "line %d: expected 'sprite <id> <w> <h> <frames>'" % i
            if not is_id(f[1]):
                return None, "line %d: bad sprite id" % i
            if f[1] in sprites:
                return None, "line %d: duplicate sprite %s" % (i, f[1])
            if len(sprites) >= MAX_SPRITES:
                return None, "line %d: too many sprites" % i
            try:
                w, h, fr = int(f[2]), int(f[3]), int(f[4])
            except ValueError:
                w = h = fr = 0
            if w < 1 or w > MAX_SIZE or h < 1 or h > MAX_SIZE:
                return None, "line %d: bad size" % i
            if fr < 1 or fr > MAX_FRAMES:
                return None, "line %d: bad frame count" % i
            sprites[f[1]] = (w, h, fr, None)
            open_id, rows_left, rows = f[1], h * fr, []
        else:
            return None, "line %d: unknown record %s" % (i, f[0])
    if rows_left > 0:
        return None, "line %d: sprite %s ends early" % (len(lines) + 1, open_id)
    if not palette:
        return None, "line %d: no palette" % (len(lines) + 1)
    return {"palette": palette, "sprites": sprites}, None


def write(palette, sprites):
    """palette: [rgb int]; sprites: {id: (w, h, frames, rows)} -> text."""
    out = ["DSP 1\n", "palette %d %s\n" % (len(palette), " ".join("%06X" % c for c in palette))]
    for sid in sorted(sprites):
        w, h, f, rows = sprites[sid]
        out.append("sprite %s %d %d %d\n" % (sid, w, h, f))
        out.extend(r + "\n" for r in rows)
    return "".join(out)


def _id_from_name(name):
    base = name[:-4]
    parts = base.split(".")
    if len(parts) == 2 and parts[1].isdigit():
        return parts[0] + ":" + parts[1]
    return ":".join(parts)


def pack_dir(png_dir):
    """Quantize every PNG in the dir to one palette and return (palette, sprites)."""
    from PIL import Image
    files = sorted(n for n in os.listdir(png_dir) if n.lower().endswith(".png"))
    images = {}
    for n in files:
        im = Image.open(os.path.join(png_dir, n)).convert("RGBA")
        if im.height > MAX_SIZE or im.width % im.height != 0:
            raise SystemExit("%s: frames must be square, side <= %d, laid side by side" % (n, MAX_SIZE))
        images[_id_from_name(n)] = im
    # one palette for the pack: the most used opaque colours, then nearest-match the rest
    counts = {}
    for im in images.values():
        for r, g, b, a in im.getdata():
            if a >= 128:
                c = (r << 16) | (g << 8) | b
                counts[c] = counts.get(c, 0) + 1
    palette = [c for c, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:MAX_COLOURS]]
    if not palette:
        raise SystemExit("no opaque pixels in " + png_dir)

    def nearest(c):
        r, g, b = c >> 16, (c >> 8) & 255, c & 255
        best, bd = 0, 1 << 30
        for i, p in enumerate(palette):
            d = (r - (p >> 16)) ** 2 + (g - ((p >> 8) & 255)) ** 2 + (b - (p & 255)) ** 2
            if d < bd:
                best, bd = i, d
        return best

    sprites = {}
    for sid, im in images.items():
        h = im.height
        frames = im.width // h
        if frames > MAX_FRAMES:
            raise SystemExit("%s: %d frames, at most %d" % (sid, frames, MAX_FRAMES))
        px = list(im.getdata())
        rows = []
        for f in range(frames):
            for y in range(h):
                row = []
                for x in range(h):
                    r, g, b, a = px[y * im.width + f * h + x]
                    row.append("." if a < 128 else DIGITS[nearest((r << 16) | (g << 8) | b)])
                rows.append("".join(row))
        sprites[sid] = (h, h, frames, rows)
    return palette, sprites


def main(argv):
    if len(argv) >= 3 and argv[0] == "pack":
        palette, sprites = pack_dir(argv[1])
        text = write(palette, sprites)
        pack, err = parse(text)
        if err:
            raise SystemExit("wrote a pack the parser refuses: " + err)
        with open(argv[2], "w", newline="\n") as f:
            f.write(text)
        print("%s: %d sprites, %d colours" % (argv[2], len(sprites), len(palette)))
        return 0
    if len(argv) == 2 and argv[0] == "check":
        with open(argv[1], encoding="utf-8") as f:
            pack, err = parse(f.read())
        print(err or "%d sprites, %d colours" % (len(pack["sprites"]), len(pack["palette"])))
        return 1 if err else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
