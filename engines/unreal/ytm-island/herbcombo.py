"""Herb mechanic: MELODY BREWING (youtube-master). Distinct from prometheus Harmonic Herbs.
Prometheus reads herbs as a CHORD (which notes sound together). Melody Brewing reads the ORDER you
drop herbs into the kettle as a TUNE: the contour and the size of the steps decide the tonic.
Pitch classes follow the shared canon (one pitch class per herb), so the two islands teach the same
ear: Prometheus = harmony, Youtube Master = melody.
Rules (3-5 herbs, order matters; interval = shortest signed step -6..+6 between successive notes):
- contour: all up = Rise (haste), all down = Fall (cure sickness), up then down = Arch (regen health),
  down then up = Valley (restore hunger), zig-zag = Dance (stamina)
- all steps <=2 semitones (stepwise) -> duration x2; any leap >=5 -> magnitude x2
- CADENCE: last herb is the same note as the first -> the tonic also PURIFIES WATER (links to the mandatory water loop)
- the same note twice in a row, or fewer than 3 herbs -> Noise (mild poison)
Tier = average growth stage (S1-S4). The bench plays the tune (prometheus audio hook OnMelodyBrewed(notes))."""
import json, sys, itertools
HERBS = {"Doleaf":0,"Sharpcress":1,"Rebell":2,"Flatfern":3,"Mimint":4,"Fasage":5,"Hushmoss":6,
         "Solthorn":7,"Gloryroot":8,"Lavine":9,"Dronebloom":10,"Tisquill":11}
CONTOUR = {"Rise":("Aug","haste"),"Fall":("Dim","cure_sickness"),"Arch":("Major","regen_health"),
           "Valley":("Minor","restore_hunger"),"Dance":("Sus","stamina_boost")}
def step(a,b): d=(b-a)%12; return d-12 if d>6 else d
def brew(items):
    """items: ordered list of (herb, stage 1-4)."""
    if not 3 <= len(items) <= 5: return {"tonic":"Item_YTM_Tonic_Dim_T1","melody":"Noise","effect":"poison_mild","tier":1,"why":"use 3-5 herbs"}
    notes=[HERBS[h] for h,_ in items]; steps=[step(a,b) for a,b in zip(notes,notes[1:])]
    tier=max(1,min(4,round(sum(s for _,s in items)/len(items))))
    if 0 in steps: return {"tonic":"Item_YTM_Tonic_Dim_T1","melody":"Noise","effect":"poison_mild","tier":1,"notes":notes}
    signs=[1 if s>0 else -1 for s in steps]; turns=sum(1 for a,b in zip(signs,signs[1:]) if a!=b)
    if turns==0: c="Rise" if signs[0]>0 else "Fall"
    elif turns==1: c="Arch" if signs[0]>0 else "Valley"
    else: c="Dance"
    cadence = notes[-1]==notes[0]
    q,eff=CONTOUR[c]
    mag=5*tier*len(notes)*(2 if any(abs(s)>=5 for s in steps) else 1)
    dur=60*tier*(2 if all(abs(s)<=2 for s in steps) else 1)
    return {"tonic":f"Item_YTM_Tonic_{'Seventh' if cadence else q}_T{tier}","melody":c+(" Cadence" if cadence else ""),
            "effect":eff,"purifies_water":cadence,"tier":tier,"magnitude":mag,"duration_s":dur,"notes":notes,"steps":steps}
def table():
    out=[]; names=list(HERBS)
    for combo in itertools.permutations(names,3):
        r=brew([(h,2) for h in combo])
        if r["melody"]!="Noise" and (r["melody"] in("Rise","Fall") or len(out)<400): out.append({"herbs":list(combo),**r})
    return out
if __name__=="__main__":
    assert brew([("Doleaf",2),("Rebell",2),("Mimint",2)])["melody"]=="Rise"
    assert brew([("Mimint",2),("Rebell",2),("Doleaf",2)])["melody"]=="Fall"   # same herbs, other order -> other tonic
    assert brew([("Doleaf",3),("Mimint",3),("Doleaf",3)])["purifies_water"] is True
    assert brew([("Doleaf",1),("Doleaf",1),("Mimint",1)])["melody"]=="Noise"
    t=table(); json.dump({"herbs":HERBS,"recipes":t},open(sys.argv[1] if len(sys.argv)>1 else "herb_combos.json","w"),indent=1)
    print("tests ok, recipes", len(t))
