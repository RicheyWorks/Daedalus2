"""Melody Brewing data pass (youtube-master): balance stats + FOUND TUNES (seed-song signatures).
Output: found_tunes.csv (UE DataTable rows), balance.json."""
import sys, itertools, collections, csv, json
sys.path.insert(0, '/workspace/ytm'); import herbcombo as hc
H = hc.HERBS; N = {v: k for k, v in H.items()}
# balance: contour share for 3/4/5-herb tunes (all stage 2)
bal = {}
for n in (3, 4, 5):
    c = collections.Counter(); cad = 0; tot = 0
    for combo in itertools.product(H, repeat=n):
        r = hc.brew([(h, 2) for h in combo]); c[r["melody"].split()[0]] += 1; tot += 1; cad += bool(r.get("purifies_water"))
    bal[n] = {k: round(v / tot, 3) for k, v in c.most_common()} | {"purify_share": round(cad / tot, 3)}
# FOUND TUNES: each seed-song record carries a 4-5 note motif (pitch classes). Play the record at the jukebox
# to learn it; brewing exactly that order makes a named tonic with a unique bonus. Harmonic Herbs has no
# equivalent (it is order-free chords), so this is the order-only, song-tied hook.
TUNES = [("american_old_time", [7, 9, 11, 7], "homestead_regen", "regen +50% while near water"),
 ("alpine", [0, 4, 7, 4, 0], "thin_air", "stamina drain -40% on cliffs"),
 ("celtic_pipes", [2, 4, 5, 9, 2], "sea_legs", "swim speed +30%"),
 ("gamelan", [0, 2, 4, 7, 0], "bronze_skin", "damage -15%"),
 ("andean_pan_pipes", [9, 0, 2, 4], "high_breath", "sprint +20%"),
 ("appalachian_high_lonesome", [7, 5, 2, 0], "lonesome", "animals stay calm"),
 ("arabic_maqam", [0, 1, 4, 5, 0], "desert_thirst", "thirst drain -50%"),
 ("arabic_takht", [5, 4, 1, 0], "night_eyes", "see in dark 120 s"),
 ("armenian_duduk", [2, 3, 5, 3, 2], "slow_ember", "warmth 300 s"),
 ("balkan_brass", [0, 3, 6, 3], "march", "carry weight +25%"),
 ("baroque_counterpoint", [0, 7, 2, 9, 4], "clockwork", "craft speed +30%"),
 ("cairo_orchestra", [7, 8, 11, 0, 7], "river_blessing", "crops grow +25% (area)")]
rows = []
for song, notes, key, bonus in TUNES:
    herbs = [N[x] for x in notes]; r = hc.brew([(h, 2) for h in herbs])
    assert r["melody"] != "Noise", (song, r)
    rows.append({"Name": "Tune_" + key, "SeedSong": song, "Herbs": "|".join(herbs), "Notes": "|".join(map(str, notes)),
                 "BaseMelody": r["melody"], "BaseEffect": r["effect"], "Bonus": bonus, "Tonic": "Item_YTM_Tonic_Found_" + key,
                 "LearnedFrom": "Item_YTM_Record_" + "".join(w.capitalize() for w in song.split("_"))})
with open("found_tunes.csv", "w", newline="") as f:
    w = csv.DictWriter(f, rows[0].keys()); w.writeheader(); w.writerows(rows)
json.dump(bal, open("balance.json", "w"), indent=1)
print(json.dumps(bal, indent=1)); [print(r["Name"], r["Herbs"], r["BaseMelody"]) for r in rows]
