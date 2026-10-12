"""Herb-combo mechanic: 'Chord Brewing' (youtube-master original).
Each of 12 note-herbs is a pitch class. Brew 2-4 herbs at a Brewbench; the set of pitch classes
is read as a chord. Chord quality -> tonic effect; root herb -> which stat; herb growth stage
(S1-S4) -> tier. Dissonant sets (no recognised chord) brew 'Noise' (mild poison), so players
learn harmony by ear: the bench plays the chord (prometheus audio hook: OnChordBrewed(notes)).
Pure Python, no Unreal import, so codex/unreal-team can port or call it."""
import json, sys
HERBS = {"Doleaf":0,"Sharpcress":1,"Rebell":2,"Flatfern":3,"Mimint":4,"Fasage":5,"Hushmoss":6,
         "Solthorn":7,"Gloryroot":8,"Lavine":9,"Dronebloom":10,"Tisquill":11}
QUALITY = {  # interval set from root -> (chord, effect)
 (0,4,7):("Major","regen_health"), (0,3,7):("Minor","restore_hunger"), (0,5,7):("Sus","stamina_boost"),
 (0,3,6):("Dim","night_vision"), (0,4,8):("Aug","haste"), (0,4,7,10):("Seventh","purify_water"),
 (0,7):("Power","strength"), (0,4,7,11):("Major","regen_health")}
STAT = ["health","hunger","stamina","thirst","warmth","luck","calm","harvest","craft","speed","sight","pet_bond"]
def brew(items):
    """items: list of (herb, stage 1-4). Returns dict result."""
    pcs = sorted({HERBS[h] for h,_ in items})
    if len(items) < 2 or len(items) > 4: return {"tonic":None,"why":"use 2-4 herbs"}
    tier = max(1, min(4, round(sum(s for _,s in items)/len(items))))
    for root in pcs:
        iv = tuple(sorted((p-root) % 12 for p in pcs))
        if iv in QUALITY:
            q, eff = QUALITY[iv]
            name = [k for k,v in HERBS.items() if v==root][0]
            return {"tonic":f"Item_YTM_Tonic_{q}_T{tier}" if q!="Power" else f"Item_YTM_Tonic_Sus_T{tier}",
                    "chord":f"{name} {q}","effect":eff,"stat":STAT[root],"tier":tier,
                    "magnitude":5*tier*(len(pcs)),"duration_s":60*tier,"notes":pcs}
    return {"tonic":"Item_YTM_Tonic_Dim_T1","chord":"Noise","effect":"poison_mild","tier":1,"notes":pcs}
def table():
    out=[]; names=list(HERBS)
    for a in names:
        for b in names:
            for c in names:
                if len({a,b,c})==3 and a<b<c:
                    r=brew([(a,2),(b,2),(c,2)])
                    if r.get("chord")!="Noise": out.append({"herbs":[a,b,c],**r})
    return out
if __name__=="__main__":
    assert brew([("Doleaf",4),("Mimint",4),("Solthorn",4)])["chord"]=="Doleaf Major"
    assert brew([("Lavine",1),("Doleaf",1),("Mimint",1)])["chord"]=="Lavine Minor"
    assert brew([("Doleaf",2),("Sharpcress",2)])["chord"]=="Noise"
    assert brew([("Doleaf",3),("Mimint",3),("Solthorn",3),("Dronebloom",3)])["effect"]=="purify_water"
    t=table(); json.dump({"herbs":HERBS,"recipes":t},open(sys.argv[1] if len(sys.argv)>1 else "herb_combos.json","w"),indent=1)
    print("tests ok, recipes", len(t))
