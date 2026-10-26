# SPDX-License-Identifier: MIT
"""Original chiptune music and sound effects for the two RPG realms, synthesised with numpy (no samples, no deps).

    python tools/blender/rpg_audio.py OUT_ROOT [ROOT_FOR_DATA]

Portal Realm (8-bit): 22,050 Hz mono, the four classic channels - two pulse waves (12.5/25/50 % duty), a triangle
bass and a noise drum - with hard note edges.
Prismheart Realm (16-bit): 32,000 Hz stereo, six voices - soft lead (filtered saw), bell (2-op FM), strings pad
(detuned saws, slow attack), round bass, pluck arpeggio, noise/kick drums - panned, with a feedback echo.

Every track is composed by rule, not copied: a mode and chord progression per mood, a two-bar melodic motif built
from chord tones on strong beats and steps between them, repeated / varied / transposed in an A A' B A form with a
cadence home, bass and arpeggio patterns by style, and drums by style. Seeds are fixed so a rebuild is identical.
Tracks: Title, Overworld, Town, Dungeon, Battle, Boss, Victory, Inn (jingle), GameOver, Castle - one per touring
jukebox cue (CUES). Effects: one per sound event the realm core emits (EVENTS), plus BLIP:0..11 voice blips.
Also writes the jukebox cue pack (claude-audio/jukebox-pack.json, data/rpg/jukebox.json) that tools/audio/realm_jukebox.py plays.
Effects (both realms): Cursor, Confirm, Cancel, Hit, Critical, Miss, Cast, Heal, LevelUp, Chest, Door, Stairs,
Encounter, Escape, Coin.
Outputs OUT_ROOT/claude-audio/<realm>/Music_<Track>.wav, Sfx_<Name>.wav, spectrogram sheet; data/rpg/audio.json:
file, bpm, key/mode, bars, loop start/end in samples, and which maps / screens use each track.
"""
import json
import math
import os
import random
import struct
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SR = {"portal": 22050, "prism": 32000}
MODES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10], "dorian": [0, 2, 3, 5, 7, 9, 10],
         "lydian": [0, 2, 4, 6, 7, 9, 11], "harmonic": [0, 2, 3, 5, 7, 8, 11], "phrygian": [0, 1, 3, 5, 7, 8, 10], "mixolydian": [0, 2, 4, 5, 7, 9, 10]}
# name: mode, tonic midi, bpm, bars, progression (scale degrees, one per bar), style, loop, used by
TRACKS = {
    "Title":     ("major", 62, 92, 16, [1, 5, 6, 4, 1, 5, 4, 5, 6, 4, 1, 5, 4, 5, 1, 1], "anthem", True, ["title screen"]),
    "Overworld": ("mixolydian", 64, 124, 16, [1, 7, 4, 1, 1, 7, 4, 5, 6, 4, 1, 5, 6, 4, 5, 1], "march", True, ["world map"]),
    "Town":      ("lydian", 65, 100, 16, [1, 2, 1, 2, 6, 5, 4, 5, 1, 2, 1, 2, 4, 5, 1, 1], "waltzish", True, ["towns", "interiors (not inn)"]),
    "Dungeon":   ("phrygian", 57, 80, 16, [1, 2, 1, 7, 1, 2, 6, 5, 1, 2, 1, 7, 6, 2, 5, 1], "sparse", True, ["dungeons"]),
    "Battle":    ("minor", 57, 156, 16, [1, 6, 7, 1, 1, 6, 4, 5, 6, 7, 1, 1, 4, 5, 6, 5], "drive", True, ["random encounters"]),
    "Boss":      ("harmonic", 55, 168, 16, [1, 1, 6, 5, 1, 1, 6, 5, 4, 4, 6, 5, 4, 2, 5, 5], "drive", True, ["boss fights"]),
    "Victory":   ("major", 67, 136, 8, [1, 1, 4, 5, 1, 4, 5, 1], "fanfare", True, ["after a won battle"]),
    "Inn":       ("major", 67, 96, 4, [1, 4, 5, 1], "jingle", False, ["rest at an inn"]),
    "GameOver":  ("minor", 57, 66, 6, [1, 6, 4, 5, 1, 1], "sparse", False, ["party defeated"]),
    "Castle":    ("dorian", 62, 84, 16, [1, 4, 1, 5, 6, 4, 5, 1, 1, 4, 7, 4, 6, 5, 4, 1], "anthem", True, ["castles", "throne rooms"]),
}
# The touring jukebox's cue vocabulary (ADR-052; SDaedalusRealm posts {cue, changed, sfx}) -> our tracks.
CUES = {"FIELD": "Overworld", "TOWN": "Town", "CASTLE": "Castle", "CAVE": "Dungeon", "BATTLE": "Battle", "BOSS": "Boss",
        "VICTORY": "Victory", "DEFEAT": "GameOver", "INN": "Inn", "TITLE": "Title"}
# Every sound event DaedalusRealmCore / DaedalusDialogueCore emit -> an effect name (BLIP:0..11 added in effects()).
EVENTS = {"TICK": "Cursor", "PICK": "Confirm", "PAGE": "Page", "OPEN": "Open", "BUMP": "Bump", "CHEST": "Chest", "LOCKED": "Locked",
          "DOOR": "Door", "STAIRS": "Stairs", "ENTER": "Enter", "PORTAL": "Portal", "HURT": "Hurt", "BLESS": "Bless", "BUY": "Coin",
          "INN": "Rest", "TORCH": "Torch", "WINGS": "Wings", "ITEM": "Item", "SPELL": "Cast", "EQUIP": "Equip", "AMBUSH": "Ambush",
          "SHINY": "Shiny", "LAND": "Land", "DEED": "Deed", "EGG": "Egg", "HATCH": "Hatch", "CALL": "Call", "CRIT": "Critical",
          "DEFEAT": "Down", "FALL": "Fall", "LEVEL": "LevelUp", "MISS": "Miss", "POISON": "Poison", "RUN": "Escape",
          "SPORES": "Spores", "SWING": "Swing", "VICTORY": "Win", "ZAP": "Zap", "HIT": "Hit", "HEAL": "Heal", "ENCOUNTER": "Encounter",
          "CANCEL": "Cancel"}


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def chord(mode, tonic, deg):
    sc = MODES[mode]
    i = deg - 1
    return [tonic + sc[(i + k) % 7] + 12 * ((i + k) // 7) for k in (0, 2, 4)]


def scale_note(mode, tonic, step):
    sc = MODES[mode]
    return tonic + sc[step % 7] + 12 * (step // 7)


# ---- composition ------------------------------------------------------------------------------------------------
RHYTHMS = {   # per bar, in 8ths: list of (start, length)
    "anthem": [[(0, 3), (3, 1), (4, 2), (6, 2)], [(0, 2), (2, 2), (4, 4)], [(0, 1), (1, 1), (2, 2), (4, 3), (7, 1)]],
    "march": [[(0, 2), (2, 1), (3, 1), (4, 2), (6, 2)], [(0, 1), (1, 1), (2, 2), (4, 1), (5, 1), (6, 2)], [(0, 3), (3, 1), (4, 4)]],
    "waltzish": [[(0, 3), (3, 3), (6, 2)], [(0, 2), (2, 2), (4, 4)], [(0, 4), (4, 2), (6, 2)]],
    "sparse": [[(0, 4), (4, 4)], [(0, 6), (6, 2)], [(0, 2), (2, 6)]],
    "drive": [[(0, 1), (1, 1), (2, 1), (3, 1), (4, 2), (6, 2)], [(0, 2), (2, 1), (3, 1), (4, 1), (5, 1), (6, 2)], [(0, 3), (3, 1), (4, 3), (7, 1)]],
    "fanfare": [[(0, 1), (1, 1), (2, 1), (3, 3), (6, 2)], [(0, 2), (2, 2), (4, 4)]],
    "jingle": [[(0, 1), (1, 1), (2, 2), (4, 4)], [(0, 2), (2, 2), (4, 4)]],
}


def compose(name, seed):
    mode, tonic, bpm, bars, prog, style, loop, _ = TRACKS[name]
    rng = random.Random(seed)
    sc_len = 7

    def tone_steps(deg):
        return [(deg - 1 + k) for k in (0, 2, 4)]                                   # scale steps of the chord

    def motif_for(deg, base_rh):
        notes = []
        cur = rng.choice(tone_steps(deg)) + 7
        for i, (st, ln) in enumerate(base_rh):
            strong = st in (0, 4)
            if strong:
                cand = [s + 7 for s in tone_steps(deg)] + [s + 14 for s in tone_steps(deg)]
                cur = min(cand, key=lambda s: abs(s - cur) + rng.random() * 2)
            else:
                cur += rng.choice((-1, 1, 1, -1, 2, -2))
            cur = max(5, min(17, cur))
            notes.append((st, ln, cur))
        return notes

    rhs = RHYTHMS[style]
    rh_a, rh_b = rng.choice(rhs), rng.choice(rhs)
    motif_a = [motif_for(prog[0], rh_a), motif_for(prog[1 % bars], rh_b)]
    melody = []
    for b in range(bars):
        section = (b // 4) % 4                                                       # A A' B A
        deg = prog[b]
        if section == 2:
            m = motif_for(deg, rng.choice(rhs))
        else:
            src = motif_a[b % 2]
            shift = 0 if section == 0 else (tone_steps(deg)[0] - tone_steps(prog[b % 2])[0]) % sc_len
            if shift > 3:
                shift -= sc_len
            m = [(st, ln, max(5, min(18, s + shift))) for st, ln, s in src]
            if section == 1 and b % 2 == 1:                                          # A': vary the tail
                m = m[:-1] + [(m[-1][0], m[-1][1], m[-1][2] + rng.choice((-2, 2)))]
        if b == bars - 1:                                                            # cadence home
            m = [(0, 4, 7 + (2 if style != "sparse" else 0)), (4, 4, 7)]
        for st, ln, s in m:
            melody.append((b * 8 + st, ln, scale_note(mode, tonic, s)))
    return {"mode": mode, "tonic": tonic, "bpm": bpm, "bars": bars, "prog": prog, "style": style, "loop": loop, "melody": melody}


# ---- synthesis --------------------------------------------------------------------------------------------------

def env(n, sr, a=0.005, d=0.05, s=0.7, r=0.04):
    t = np.arange(n) / sr
    e = np.ones(n) * s
    na, nd = int(a * sr), int(d * sr)
    e[:na] = np.linspace(0, 1, max(1, na))[:len(e[:na])]
    e[na:na + nd] = np.linspace(1, s, max(1, nd))[:len(e[na:na + nd])]
    nr = min(n, int(r * sr))
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def osc(kind, f, n, sr, duty=0.5, rng=None):
    t = np.arange(n) / sr
    ph = (f * t) % 1.0
    if kind == "pulse":
        return np.where(ph < duty, 1.0, -1.0)
    if kind == "tri":
        q = np.floor(ph * 32) / 32                                                   # 4-bit stepped triangle, like the console
        return 4 * np.abs(q - 0.5) - 1
    if kind == "saw":
        x = 2 * ph - 1
        k = np.ones(9) / 9                                                           # soften
        return np.convolve(x, k, mode="same")
    if kind == "bell":
        return np.sin(2 * np.pi * f * t + 2.5 * np.exp(-t * 6) * np.sin(2 * np.pi * f * 3.5 * t))
    if kind == "sine":
        return np.sin(2 * np.pi * f * t)
    if kind == "noise":
        return (rng or np.random).uniform(-1, 1, n)
    raise ValueError(kind)


def mix_note(buf, start, wavef, gain, pan=0.0):
    end = min(len(buf), start + len(wavef))
    if end <= start:
        return
    w = wavef[:end - start] * gain
    if buf.ndim == 1:
        buf[start:end] += w
    else:
        buf[start:end, 0] += w * math.sqrt(0.5 * (1 - pan))
        buf[start:end, 1] += w * math.sqrt(0.5 * (1 + pan))


def render_track(realm, name, comp, seed):
    sr = SR[realm]
    stereo = realm == "prism"
    spb = 60.0 / comp["bpm"]                                                         # seconds per beat
    e8 = spb / 2
    bars = comp["bars"]
    total = int(bars * 4 * spb * sr) + int(sr * 0.6)
    buf = np.zeros((total, 2) if stereo else total)
    rng = np.random.default_rng(seed)
    style, mode, tonic, prog = comp["style"], comp["mode"], comp["tonic"], comp["prog"]
    # lead
    for st, ln, m in comp["melody"]:
        n = int(ln * e8 * sr)
        s0 = int(st * e8 * sr)
        f = mtof(m + 12 if realm == "portal" else m + 12)
        if realm == "portal":
            w = osc("pulse", f, n, sr, duty=0.25 if style != "sparse" else 0.5) * env(n, sr, 0.002, 0.08, 0.6, 0.03)
            mix_note(buf, s0, w, 0.19)
        else:
            vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * np.arange(n) / sr) * np.clip(np.arange(n) / sr - 0.15, 0, 1)
            kind = "bell" if style in ("waltzish", "jingle") else "saw"
            w = osc(kind, f, n, sr) * env(n, sr, 0.01, 0.12, 0.65, 0.08)
            if kind == "saw":
                w = np.interp(np.cumsum(vib) % n, np.arange(n), w)
            mix_note(buf, s0, w, 0.19, pan=-0.15)
    # harmony / arpeggio
    for b in range(bars):
        ch = chord(mode, tonic, prog[b])
        bar0 = int(b * 4 * spb * sr)
        if style in ("drive", "march", "anthem", "fanfare"):
            step = e8 / 2
            for k in range(16 if style == "drive" else 8):
                m = ch[k % 3] + (12 if (k // 3) % 2 else 0)
                n = int(step * sr * (1 if style == "drive" else 2))
                s0 = bar0 + int(k * step * (1 if style == "drive" else 2) * sr)
                if realm == "portal":
                    mix_note(buf, s0, osc("pulse", mtof(m), n, sr, duty=0.125) * env(n, sr, 0.001, 0.03, 0.4, 0.01), 0.07)
                else:
                    mix_note(buf, s0, osc("saw", mtof(m + 12), n, sr) * np.exp(-np.arange(n) / sr * 14), 0.07, pan=0.45)
        else:                                                                         # sustained chord / pad
            n = int(4 * spb * sr)
            for m in ch:
                if realm == "portal":
                    if style != "sparse":
                        for beat in range(0, 4, 1 if style == "waltzish" else 2):
                            nn = int(spb * sr * 0.9)
                            mix_note(buf, bar0 + int(beat * spb * sr), osc("pulse", mtof(m + 12), nn, sr, duty=0.5) * env(nn, sr, 0.002, 0.1, 0.3, 0.05), 0.035)
                else:
                    det = (osc("saw", mtof(m) * 1.004, n, sr) + osc("saw", mtof(m) * 0.996, n, sr)) / 2
                    mix_note(buf, bar0, det * env(n, sr, 0.35, 0.3, 0.7, 0.4), 0.05, pan=(m % 3 - 1) * 0.4)
    # bass
    for b in range(bars):
        root = chord(mode, tonic, prog[b])[0] - 24
        bar0 = int(b * 4 * spb * sr)
        pat = {"drive": [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1), (7, 1)], "march": [(0, 2), (2, 2), (4, 2), (6, 2)],
               "anthem": [(0, 4), (4, 4)], "waltzish": [(0, 2), (2, 2), (4, 2), (6, 2)], "sparse": [(0, 8)], "fanfare": [(0, 2), (2, 2), (4, 4)],
               "jingle": [(0, 4), (4, 4)]}[style]
        for i, (st, ln) in enumerate(pat):
            m = root + (12 if style == "drive" and i % 2 else 0) + (7 if style == "waltzish" and i % 2 else 0)
            n = int(ln * e8 * sr * 0.92)
            kind = "tri" if realm == "portal" else "sine"
            w = osc(kind, mtof(m), n, sr) * env(n, sr, 0.003, 0.05, 0.85, 0.03)
            if realm == "prism":
                w += 0.35 * osc("sine", mtof(m) * 2, n, sr) * env(n, sr, 0.003, 0.05, 0.5, 0.03)
            mix_note(buf, bar0 + int(st * e8 * sr), w, 0.17 if realm == "portal" else 0.15)
    # drums
    if style not in ("waltzish", "jingle", "sparse") or name == "Dungeon":
        for b in range(bars):
            bar0 = int(b * 4 * spb * sr)
            hits = {"drive": "K.H.S.H.K.KHS.H.", "march": "K...S...K.K.S...", "anthem": "K.......S.......", "fanfare": "K...S...K...S.S.",
                    "sparse": "K...............", "waltzish": "", "jingle": ""}[style]
            step = spb / 4
            for k, c in enumerate(hits):
                s0 = bar0 + int(k * step * sr)
                if c == "K":
                    n = int(0.12 * sr)
                    t = np.arange(n) / sr
                    w = np.sin(2 * np.pi * np.cumsum(120 * np.exp(-t * 30) + 45) / sr) * np.exp(-t * 18)
                    mix_note(buf, s0, w, 0.3 if realm == "prism" else 0.22)
                elif c == "S":
                    n = int(0.14 * sr)
                    w = osc("noise", 0, n, sr, rng=rng) * np.exp(-np.arange(n) / sr * 22)
                    if realm == "portal":
                        w = np.repeat(w[::4], 4)[:n]                                       # crunchy NES noise
                    mix_note(buf, s0, w, 0.12)
                elif c == "H":
                    n = int(0.04 * sr)
                    w = osc("noise", 0, n, sr, rng=rng) * np.exp(-np.arange(n) / sr * 80)
                    mix_note(buf, s0, w, 0.05, pan=0.3)
    if stereo:                                                                        # feedback echo, 3/8 beat
        d = int(spb * 0.75 * sr)
        out = buf.copy()
        for k in range(1, 4):
            g = 0.32 ** k
            out[d * k:, 0] += buf[:-d * k, 1] * g
            out[d * k:, 1] += buf[:-d * k, 0] * g
        buf = out
    peak = np.max(np.abs(buf)) or 1
    buf = buf / peak * 0.89
    loop_end = int(bars * 4 * spb * sr)
    return buf, loop_end


# ---- effects ----------------------------------------------------------------------------------------------------

def sweep(sr, f0, f1, dur, kind="pulse", duty=0.5, decay=8.0):
    n = int(dur * sr)
    t = np.arange(n) / sr
    f = f0 * (f1 / f0) ** (t / dur)
    ph = np.cumsum(f) / sr % 1
    if kind == "pulse":
        w = np.where(ph < duty, 1.0, -1.0)
    elif kind == "tri":
        w = 4 * np.abs(ph - 0.5) - 1
    else:
        w = np.sin(2 * np.pi * ph)
    return w * np.exp(-t * decay)


def notes_seq(sr, midis, dur, kind="pulse", duty=0.25):
    parts = []
    for m in midis:
        n = int(dur * sr)
        w = osc("pulse" if kind == "pulse" else "bell", mtof(m), n, sr, duty=duty) * env(n, sr, 0.002, 0.04, 0.6, 0.02)
        parts.append(w)
    return np.concatenate(parts)


def noise_burst(sr, dur, decay, crunch=1, rng=None):
    n = int(dur * sr)
    w = (rng or np.random.default_rng(1)).uniform(-1, 1, n) * np.exp(-np.arange(n) / sr * decay)
    if crunch > 1:
        w = np.repeat(w[::crunch], crunch)[:n]
    return w


def effects(realm):
    sr = SR[realm]
    kind = "pulse" if realm == "portal" else "bell"
    rng = np.random.default_rng(7)
    cr = 4 if realm == "portal" else 1
    fx = {
        "Cursor": sweep(sr, 1800, 1800, 0.04, "pulse", 0.5, 40),
        "Confirm": notes_seq(sr, [76, 83], 0.06, kind),
        "Cancel": notes_seq(sr, [71, 64], 0.06, kind),
        "Hit": noise_burst(sr, 0.18, 22, cr, rng) * 0.9 + 0.5 * np.pad(sweep(sr, 220, 60, 0.12, "tri", decay=20), (0, int(0.06 * sr))),
        "Critical": np.concatenate([noise_burst(sr, 0.1, 10, cr, rng), noise_burst(sr, 0.25, 12, cr, rng)]) * 1.0,
        "Miss": sweep(sr, 900, 300, 0.2, "sine", decay=6) * 0.6,
        "Cast": np.concatenate([sweep(sr, 300, 1600, 0.35, "pulse", 0.25, 2), sweep(sr, 1600, 2400, 0.15, "pulse", 0.125, 10)]),
        "Heal": notes_seq(sr, [72, 76, 79, 84, 88], 0.07, kind),
        "LevelUp": notes_seq(sr, [67, 71, 74, 79, 74, 79, 83, 86], 0.08, kind),
        "Chest": np.concatenate([noise_burst(sr, 0.08, 30, cr, rng) * 0.6, notes_seq(sr, [72, 79, 84], 0.09, kind)]),
        "Door": np.concatenate([noise_burst(sr, 0.06, 40, cr, rng), sweep(sr, 160, 90, 0.18, "tri", decay=10)]),
        "Stairs": np.concatenate([sweep(sr, 500 - 60 * k, 480 - 60 * k, 0.07, "pulse", 0.5, 25) for k in range(5)]),
        "Encounter": np.concatenate([sweep(sr, 200 + 120 * k, 1400, 0.09, "pulse", 0.25, 4) for k in range(5)]),
        "Escape": sweep(sr, 1200, 150, 0.45, "pulse", 0.5, 3),
        "Coin": notes_seq(sr, [83, 88], 0.07, kind, duty=0.5),
        "Page": sweep(sr, 1200, 1200, 0.03, "pulse", 0.25, 60),
        "Open": np.concatenate([sweep(sr, 600, 900, 0.05, "pulse", 0.5, 20), sweep(sr, 900, 1300, 0.05, "pulse", 0.5, 20)]),
        "Bump": sweep(sr, 140, 70, 0.09, "tri", decay=25),
        "Locked": np.concatenate([sweep(sr, 180, 170, 0.07, "pulse", 0.5, 12), np.zeros(int(0.03 * sr)), sweep(sr, 150, 140, 0.09, "pulse", 0.5, 12)]),
        "Enter": sweep(sr, 300, 700, 0.16, "pulse", 0.125, 9),
        "Portal": sweep(sr, 200, 2200, 0.7, "sine", decay=2) * (0.6 + 0.4 * np.sin(np.arange(int(0.7 * sr)) / sr * 2 * np.pi * 18)),
        "Hurt": noise_burst(sr, 0.12, 25, cr, rng) * 0.7 + 0.6 * sweep(sr, 400, 120, 0.12, "pulse", 0.5, 15),
        "Bless": notes_seq(sr, [79, 84, 88, 91, 96], 0.06, kind),
        "Rest": notes_seq(sr, [84, 79, 76, 72], 0.12, kind),
        "Torch": noise_burst(sr, 0.35, 4, cr, rng) * (0.5 + 0.5 * np.abs(np.sin(np.arange(int(0.35 * sr)) / sr * 2 * np.pi * 9))),
        "Wings": np.concatenate([noise_burst(sr, 0.06, 30, cr, rng) for _ in range(4)] + [sweep(sr, 500, 1500, 0.25, "pulse", 0.25, 5)]),
        "Item": notes_seq(sr, [74, 81], 0.07, kind),
        "Equip": np.concatenate([sweep(sr, 2400, 2200, 0.05, "pulse", 0.125, 35), sweep(sr, 3000, 2800, 0.08, "pulse", 0.125, 30)]),
        "Ambush": np.concatenate([sweep(sr, 1400 - 200 * k, 200, 0.07, "pulse", 0.5, 5) for k in range(5)]),
        "Shiny": notes_seq(sr, [91, 96, 100, 103, 108], 0.045, kind, duty=0.125),
        "Land": np.concatenate([sweep(sr, 120, 60, 0.1, "tri", decay=20), notes_seq(sr, [79, 84], 0.08, kind)]),
        "Deed": notes_seq(sr, [72, 76, 79, 84, 84], 0.1, kind),
        "Egg": np.concatenate([sweep(sr, 900, 850, 0.03, "pulse", 0.5, 60), np.zeros(int(0.08 * sr)), sweep(sr, 950, 900, 0.03, "pulse", 0.5, 60)]),
        "Hatch": np.concatenate([noise_burst(sr, 0.1, 30, cr, rng), notes_seq(sr, [76, 81, 88], 0.08, kind)]),
        "Call": np.concatenate([notes_seq(sr, [67], 0.18, "pulse", 0.5), notes_seq(sr, [74], 0.28, "pulse", 0.5)]),
        "Down": notes_seq(sr, [64, 60, 57, 52], 0.16, kind),
        "Fall": sweep(sr, 1600, 80, 0.8, "pulse", 0.5, 1.5),
        "Poison": sweep(sr, 200, 160, 0.4, "sine", decay=3) * (0.5 + 0.5 * np.sin(np.arange(int(0.4 * sr)) / sr * 2 * np.pi * 14)),
        "Spores": np.concatenate([noise_burst(sr, 0.1, 18, max(1, cr // 2), rng) * 0.6 for _ in range(3)]),
        "Swing": noise_burst(sr, 0.1, 30, cr, rng) * np.linspace(0.3, 1, int(0.1 * sr)),
        "Win": notes_seq(sr, [72, 76, 79, 84], 0.09, kind),
        "Zap": np.concatenate([sweep(sr, 2000, 300, 0.08, "pulse", 0.25, 8), sweep(sr, 300, 2000, 0.08, "pulse", 0.25, 8)]),
    }
    for k in range(12):                                                             # NPC voice blips (DaedalusDialogueCore "BLIP:<pitch>")
        fx["Blip_%d" % k] = osc("pulse", mtof(72 + k), int(0.035 * sr), sr, duty=0.25) * env(int(0.035 * sr), sr, 0.001, 0.01, 0.6, 0.01) * 0.6
    out = {}
    for k, w in fx.items():
        w = w / (np.max(np.abs(w)) or 1) * 0.85
        if realm == "prism":                                                        # small room echo, stereo
            d = int(0.09 * sr)
            st = np.zeros((len(w) + 3 * d, 2))
            st[:len(w), 0] += w
            st[:len(w), 1] += w
            for j in range(1, 3):
                st[d * j:d * j + len(w), j % 2] += w * 0.3 ** j
            w = st / (np.max(np.abs(st)) or 1) * 0.85
        out[k] = w
    return out


def write_wav(path, buf, sr):
    a = np.clip(buf, -1, 1)
    pcm = (a * 32767).astype("<i2")
    with wave.open(path, "wb") as f:
        f.setnchannels(1 if a.ndim == 1 else 2)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(pcm.tobytes())


def spectro_sheet(items, path):
    import pixel_png as P
    tiles = []
    for name, buf, sr in items:
        mono = buf if buf.ndim == 1 else buf.mean(1)
        n = 512
        hop = max(1, len(mono) // 240)
        cols = []
        for i in range(0, len(mono) - n, hop):
            seg = mono[i:i + n] * np.hanning(n)
            sp = np.abs(np.fft.rfft(seg))[:160]
            cols.append(np.log1p(sp * 4))
        S = np.array(cols).T[::-1]
        S = S / (S.max() or 1)
        img = np.zeros((S.shape[0], S.shape[1], 4), np.float32)
        img[..., 0] = S ** 0.6
        img[..., 1] = S ** 1.2
        img[..., 2] = 0.25 + 0.5 * S
        img[..., 3] = 1
        tiles.append(img)
    P.save_png(P.grid_sheet(tiles, 3), path)


def build(out_root, data_root=None):
    rows = []
    for ri, realm in enumerate(("portal", "prism")):
        od = os.path.join(out_root, "claude-audio", realm)
        os.makedirs(od, exist_ok=True)
        sr = SR[realm]
        spec = []
        for ti, name in enumerate(TRACKS):
            comp = compose(name, 1000 + ti)                                          # same tune in both realms, two arrangements
            buf, loop_end = render_track(realm, name, comp, 77 + ti)
            fn = "Music_%s.wav" % name
            write_wav(os.path.join(od, fn), buf, sr)
            spec.append((name, buf, sr))
            mode, tonic, bpm, bars, prog, style, loop, used = TRACKS[name]
            rows.append({"realm": realm, "kind": "music", "name": name, "file": "engines/unreal/art/claude-audio/%s/%s" % (realm, fn),
                         "sample_rate": sr, "channels": 2 if realm == "prism" else 1, "bpm": bpm, "key": ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"][tonic % 12],
                         "mode": mode, "bars": bars, "loop": loop, "loop_start": 0, "loop_end": loop_end if loop else None,
                         "seconds": round(len(buf) / sr, 2), "used_by": used})
        for name, w in effects(realm).items():
            fn = "Sfx_%s.wav" % name
            write_wav(os.path.join(od, fn), w, sr)
            rows.append({"realm": realm, "kind": "sfx", "name": name, "file": "engines/unreal/art/claude-audio/%s/%s" % (realm, fn),
                         "sample_rate": sr, "seconds": round(len(w) / sr, 3)})
        spectro_sheet(spec, os.path.join(od, "spectrograms.png"))
    pack = {"schema": "daedalus.jukebox-cues/v1", "source": "tools/blender/rpg_audio.py",
            "contract": "SDaedalusRealm POSTs {cue, changed, sfx} to the daedalus.Jukebox URL (ADR-052); this pack maps them to files",
            "root": "engines/unreal/art/claude-audio", "realms": {}}
    for realm in ("portal", "prism"):
        music = {r["name"]: r for r in rows if r["realm"] == realm and r["kind"] == "music"}
        pack["realms"][realm] = {
            "sample_rate": SR[realm], "channels": 2 if realm == "prism" else 1,
            "cues": {cue: {"file": "%s/Music_%s.wav" % (realm, t), "loop": music[t]["loop"], "loop_start": 0, "loop_end": music[t]["loop_end"],
                           "bpm": music[t]["bpm"]} for cue, t in CUES.items()},
            "events": dict({ev: "%s/Sfx_%s.wav" % (realm, fx) for ev, fx in EVENTS.items()},
                           **{"BLIP:%d" % k: "%s/Sfx_Blip_%d.wav" % (realm, k) for k in range(12)}),
            "touring_cues": ["FIELD", "TOWN", "INN"],
        }
    os.makedirs(os.path.join(out_root, "claude-audio"), exist_ok=True)
    with open(os.path.join(out_root, "claude-audio", "jukebox-pack.json"), "w", encoding="utf-8") as f:
        json.dump(pack, f, indent=1)
    if data_root:
        with open(os.path.join(data_root, "data", "rpg", "jukebox.json"), "w", encoding="utf-8") as f:
            json.dump(pack, f, indent=1)
        with open(os.path.join(data_root, "data", "rpg", "audio.json"), "w", encoding="utf-8") as f:
            json.dump({"schema": "daedalus.audio/v1", "source": "tools/blender/rpg_audio.py", "note": "original compositions generated by rule; "
                       "loop_end is in samples; music and sfx are 16-bit PCM WAV", "tracks": rows}, f, indent=1)
    return rows


if __name__ == "__main__":
    out = os.path.abspath(sys.argv[1])
    dr = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None
    r = build(out, dr)
    print("AUDIO", len([x for x in r if x["kind"] == "music"]), "tracks,", len([x for x in r if x["kind"] == "sfx"]), "sfx")
