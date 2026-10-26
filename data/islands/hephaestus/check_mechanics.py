# Validates Hephaestus mechanics.json against disksaver-mechanics-v1 rules
# plus dual_cookbook herb membership and Great Forge Glow balance weights.
import json, sys, os
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
            bad.append((t.get('name'), i))

b = m['balance']
total = b['water'] + b['animals'] + b['herbs3'] + b['tea']
if total != 100:
    bad.append(('balance', total))
if (b['water'], b['animals'], b['herbs3'], b['tea']) != (30, 30, 30, 10):
    bad.append(('glow_weights', b))

# species must match herbs.json ids
doc_ids = []
for x in herbs_doc['herbs']:
    doc_ids.append(x['id'] if isinstance(x, dict) and 'id' in x else (x.get('name') if isinstance(x, dict) else x))
if set(doc_ids) != species or len(doc_ids) != 36:
    bad.append(('species_mismatch', len(species), len(doc_ids)))

# dual cookbook herbs must be in species; tea dual count matches
dual = herbs_doc.get('dual_cookbook', {}).get('recipes', [])
dual_ids = {r['id'] for r in dual}
tea_dual = {t['id'] for t in m['teas'] if t.get('quench') == 'dual'}
if dual_ids - tea_dual:
    bad.append(('missing_dual_teas', sorted(dual_ids - tea_dual)))
for r in dual:
    for h in r['herbs']:
        if h not in species:
            bad.append(('dual_herb', r['id'], h))

# livestock heads / water claim sanity
if m['livestock'].get('heads_total') != live.get('production_budget', {}).get('heads_total'):
    bad.append(('heads_total', m['livestock'].get('heads_total'), live.get('production_budget', {}).get('heads_total')))
if water.get('budget', {}).get('claim_check', {}).get('both_true') is not True:
    bad.append(('water_claim', False))

# water source keys exist in water.json sources by id
src_ids = {s['id'] for s in water.get('sources', []) if isinstance(s, dict) and 'id' in s}
for sid in m['water']['sources']:
    if sid not in src_ids:
        bad.append(('water_source', sid))

ft = m.get('forge_temper', {})
if ft.get('dual_window_s') != 10:
    bad.append(('dual_window', ft.get('dual_window_s')))
if ft.get('dual_recipe_count') != len(dual):
    bad.append(('dual_count', ft.get('dual_recipe_count'), len(dual)))

print('OK' if not bad else 'BAD %s' % bad)
sys.exit(1 if bad else 0)
