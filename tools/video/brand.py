"""Shared look for every Daedalus / richeyworks video asset: colours, sizes, fonts, dragon stamp.

Fonts: IBM Plex Mono (OFL, https://github.com/IBM/plex) is the house font. It is not vendored; point
DAEDALUS_VIDEO_FONTS at a folder holding plex-Regular.ttf / plex-Bold.ttf (any names containing
Regular/Bold work). Without it we fall back to DejaVu Sans Mono, then PIL's default, so tests run anywhere.
"""
import glob
import os
from PIL import Image, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BG, FG, DIM, LINE = (11, 11, 11), (255, 255, 255), (138, 138, 138), (42, 42, 42)
VIDEO = (1920, 1080)
THUMB = (1280, 720)
FPS = 30
STAMP = os.environ.get("DAEDALUS_VIDEO_STAMP", os.path.join(HERE, "brand", "dragon_white_1200.png"))
TAGLINES = ["a jukebox from the gods", "every seed grows a song no one has heard before.", "a dragon that sleeps in the sea"]
_FALLBACK = ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono{b}.ttf", "C:/Windows/Fonts/consola{bw}.ttf"]


def font_path(bold=False):
    d = os.environ.get("DAEDALUS_VIDEO_FONTS", os.path.join(HERE, "brand", "fonts"))
    want = "Bold" if bold else "Regular"
    for p in sorted(glob.glob(os.path.join(d, "*.ttf")) + glob.glob(os.path.join(d, "*.otf"))):
        if want.lower() in os.path.basename(p).lower():
            return p
    for pat in _FALLBACK:
        p = pat.format(b="-Bold" if bold else "", bw="b" if bold else "")
        if os.path.exists(p):
            return p
    return None


def font(size, bold=False):
    p = font_path(bold)
    if p:
        return ImageFont.truetype(p, size)
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def stamp(width):
    """Dragon stamp scaled to width px (RGBA), or None if the stamp file is missing."""
    if not os.path.exists(STAMP):
        return None
    im = Image.open(STAMP).convert("RGBA")
    return im.resize((width, max(1, int(width * im.height / im.width))))
