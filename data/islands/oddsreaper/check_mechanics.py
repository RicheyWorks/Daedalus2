# Validates OddsReaper mechanics.json against disksaver-mechanics-v1 rules
# plus storm_parlay_cookbook membership and water/livestock source docs.
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
m = json.loads((HERE / 'mechanics.json').read_text(encoding='utf-8'))
herbs_doc = json.loads((HERE / 'herbs.json').read_text(encoding='utf-8'))
live = json.loads((HERE / 'livestock.json').read_text(encoding='utf-8'))
water = json.loads((HERE / 'water.json').read_text(encoding='utf-8'))

bad = []
species = set(m['herbs']['species'])
prods = {a['product'] for a in m['livestock']['animals'].values()}
extra = {'CleanWater', 'BoiledWater', 'any3herbs'}
for t in m['teas']:
    for i in t['in']:
        if i not in species | prods | extra:
            bad.append(('tea_in', t.get('name'), i))

b = m['balance']
total = b['water'] + b['animals'] + b['herbs3'] + b['tea']
if total != 100:
    bad.append(('balance', total))
if (b['water'], b['animals'], b['herbs3'], b['tea']) != (30, 30, 30, 10):
    bad.append(('ledger_weights', b))

doc_ids = [x['id'] for x in herbs_doc['herbs']]
if set(doc_ids) != species or len(doc_ids) != 8:
    bad.append(('species_mismatch', sorted(species), sorted(doc_ids)))

cookbook = herbs_doc.get('storm_parlay_cookbook', {}).get('recipes', [])
cook_ids = {r['id'] for r in cookbook}
tea_ids = {t['id'] for t in m['teas']}
if cook_ids != tea_ids:
    bad.append(('cookbook_teas', sorted(cook_ids - tea_ids), sorted(tea_ids - cook_ids)))
for r in cookbook:
    for h in r['herbs']:
        if h not in species:
            bad.append(('cookbook_herb', r['id'], h))
    tea = next((t for t in m['teas'] if t['id'] == r['id']), None)
    if tea is None:
        continue
    if set(tea['in']) - {'CleanWater'} != set(r['herbs']):
        bad.append(('tea_herbs', r['id'], tea['in'], r['herbs']))

live_ids = {x['id'] for x in live.get('livestock', [])}
for aid in m['livestock']['animals']:
    if aid not in live_ids:
        bad.append(('livestock', aid))

src_ids = {s['id'] for s in water.get('sources', []) if isinstance(s, dict) and 'id' in s}
dist_ids = {d['id'] for d in water.get('distribution', []) if isinstance(d, dict) and 'id' in d}
for sid in m['water']['sources']:
    if sid not in src_ids | dist_ids:
        bad.append(('water_source', sid))

wl = m.get('wager_ledger', {})
if wl.get('storm_parlay_recipe_count') != len(cookbook):
    bad.append(('parlay_count', wl.get('storm_parlay_recipe_count'), len(cookbook)))
if m['livestock'].get('heads_cap_total') != 14:
    bad.append(('heads_cap', m['livestock'].get('heads_cap_total')))

print('OK' if not bad else 'BAD %s' % bad)
sys.exit(1 if bad else 0)
