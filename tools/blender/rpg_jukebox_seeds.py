# SPDX-License-Identifier: MIT
"""Feed the RPG realm music into the existing rd-jukebox (branch rd-jukebox, docs/rd-jukebox.md) as guest seed songs.

    python tools/blender/rpg_jukebox_seeds.py ART_ROOT [--covers COVER_ROOT]

rd-jukebox lists guest songs from `daedalus.jukebox.seed-songs-dir`: files must match `[a-z0-9][a-z0-9-]{0,80}.mp3`,
with an optional same-name `.webp` cover, and the title comes from the slug ("prismheart-battle" -> "Prismheart
Battle"). This converts the realm cue tracks written by rpg_audio.py (claude-audio/<realm>/Music_*.wav) into exactly
that: ART_ROOT/claude-audio/jukebox-seeds/<realm-slug>-<cue>.mp3 (+ .webp), 192 kbps, two passes of each loop so the
guest player (which plays a file once) hears it come round. It also writes realm-cues.json there: the realm's
ADR-052 cue vocabulary (FIELD, TOWN, CASTLE, CAVE, BATTLE, BOSS, VICTORY, DEFEAT, INN, TITLE) -> seed slug, the
mapping a cue route on the jukebox would use (the jukebox has no route for the realm's {cue, changed, sfx} posts yet).

Point the jukebox at it: DAEDALUS_JUKEBOX_ENABLED=true, DAEDALUS_JUKEBOX_SEED_SONGS_DIR=<ART_ROOT>/claude-audio/jukebox-seeds
Needs lameenc (MP3) and Pillow (webp covers); covers are optional.
"""
import glob
import io
import json
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rpg_audio as RA  # noqa: E402

SLUG = {"portal": "portal-realm", "prism": "prismheart"}
COVER_SOURCES = {   # cue -> art written by the RPG tools (first that exists wins)
    "FIELD": ["worldmap/map-demo.png"], "TOWN": ["town/town-demo.png"], "CASTLE": ["interiors/Interior_Castle.png"],
    "CAVE": ["dungeons/*_F2.png"], "BATTLE": ["ui/mockup.png"], "BOSS": ["dungeons/*_F4.png", "dungeons/*_F3.png"],
    "VICTORY": ["menus/Menu_Status.png"], "DEFEAT": ["dungeons/*_F1.png"], "INN": ["interiors/Interior_Inn.png"],
    "TITLE": ["spells/sheet-spells.png"],
}


def read_wav(path):
    with wave.open(path, "rb") as w:
        ch, sr, n = w.getnchannels(), w.getframerate(), w.getnframes()
        a = np.frombuffer(w.readframes(n), "<i2").reshape(-1, ch)
    return a, sr, ch


def mp3(a, sr, ch, kbps=192):
    import lameenc
    enc = lameenc.Encoder()
    enc.set_bit_rate(kbps)
    enc.set_in_sample_rate(sr)
    enc.set_channels(ch)
    enc.set_quality(2)
    return enc.encode(np.ascontiguousarray(a).tobytes()) + enc.flush()


def cover(kit_root, realm, cue, title):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    src = None
    for pat in COVER_SOURCES[cue]:
        hits = sorted(glob.glob(os.path.join(kit_root, realm, pat)))
        if hits:
            src = hits[0]
            break
    if src:
        im = Image.open(src).convert("RGB")
        s = min(im.size)
        im = im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width - s) // 2 + s, (im.height - s) // 2 + s))
        im = im.resize((128, 128), Image.NEAREST).resize((512, 512), Image.NEAREST)
    else:
        im = Image.new("RGB", (512, 512), (24, 20, 40))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 430, 512, 512), fill=(10, 10, 20) if realm == "portal" else (24, 34, 96))
    d.text((18, 446), title.upper(), fill=(255, 255, 255))
    d.text((18, 476), "PORTAL REALM - 8-BIT" if realm == "portal" else "PRISMHEART REALM - 16-BIT", fill=(248, 216, 120))
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=90)
    return buf.getvalue()


def build(art_root, kit_root=None):
    kit_root = kit_root or os.path.join(art_root, "claude-battle-kit")
    od = os.path.join(art_root, "claude-audio", "jukebox-seeds")
    os.makedirs(od, exist_ok=True)
    manifest = {"schema": "daedalus.realm-cues/v1", "source": "tools/blender/rpg_jukebox_seeds.py",
                "jukebox": "rd-jukebox guest seeds (docs/rd-jukebox.md); DAEDALUS_JUKEBOX_SEED_SONGS_DIR=this folder",
                "contract": "SDaedalusRealm POSTs {cue, changed, sfx} to daedalus.Jukebox (ADR-052); same cue never restarts",
                "realms": {}}
    made = []
    for realm in ("portal", "prism"):
        cues = {}
        for cue, track in RA.CUES.items():
            wav = os.path.join(art_root, "claude-audio", realm, "Music_%s.wav" % track)
            if not os.path.exists(wav):
                continue
            a, sr, ch = read_wav(wav)
            spec = RA.TRACKS[track]
            if spec[6]:                                                              # looping cue: two passes, short fade at the end
                loop_end = int(spec[3] * 4 * 60.0 / spec[2] * sr)
                body = a[:loop_end]
                a = np.concatenate([body, body, a[loop_end:]])
                fade = min(len(a), int(1.5 * sr))
                a[-fade:] = (a[-fade:].astype(np.float32) * np.linspace(1, 0, fade)[:, None]).astype("<i2")
            slug = "%s-%s" % (SLUG[realm], cue.lower())
            with open(os.path.join(od, slug + ".mp3"), "wb") as f:
                f.write(mp3(a, sr, ch))
            cv = cover(kit_root, realm, cue, "%s %s" % ("Portal" if realm == "portal" else "Prismheart", cue.title()))
            if cv:
                with open(os.path.join(od, slug + ".webp"), "wb") as f:
                    f.write(cv)
            cues[cue] = {"seed": slug, "file": slug + ".mp3", "loops": bool(spec[6]), "bpm": spec[2], "mode": spec[0]}
            made.append(slug)
        manifest["realms"][realm] = {"cues": cues, "sfx_pack": "claude-audio/jukebox-pack.json"}
    with open(os.path.join(od, "realm-cues.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    return made


if __name__ == "__main__":
    art = os.path.abspath(sys.argv[1])
    kit = os.path.abspath(sys.argv[sys.argv.index("--covers") + 1]) if "--covers" in sys.argv else None
    m = build(art, kit)
    print("JUKEBOX SEEDS", len(m))
