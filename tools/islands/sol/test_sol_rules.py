import json
import pathlib
import unittest
from sol_rules import Farm

ROOT = pathlib.Path(__file__).resolve().parents[3]
EFFECTS = json.loads((ROOT / 'data/herbs/combos.json').read_text())['effects']

class Rules(unittest.TestCase):
    def test_water_loop(self):
        f = Farm(clean_water=0, thirst=10)
        f.collect('well', 2)
        with self.assertRaises(ValueError): f.drink()
        f.filter(1); f.drink()
        self.assertEqual((f.thirst, f.clean_water, f.dirty_water), (45, 0, 1))

    def test_resource_conservation_and_no_dry_backlog(self):
        f = Farm(clean_water=1, feed=2)
        self.assertEqual(f.tick(1800), 1)
        self.assertEqual((f.eggs, f.milk, f.feed, f.clean_water), (1, 1, 1, 0))
        f.collect('spring', 1)
        self.assertEqual(f.tick(1), 0)
        self.assertEqual(f.tick(599), 1)

    def test_ring_order_and_failure_atomicity(self):
        f = Farm()
        before = f.save()
        with self.assertRaises(ValueError): f.brew(['dawnleaf', 'rillprism', 'cinderbud'], EFFECTS)
        self.assertEqual(f.save(), before)
        brew = f.brew(['dawnleaf', 'rillprism', 'dawnleaf'], EFFECTS)
        self.assertEqual(brew['id'], 'heat_shield')
        self.assertEqual(brew['dur_s'], EFFECTS['cool+cool']['dur_s'] * 2)
        self.assertEqual(f.clean_water, 19)
        self.assertEqual(f.herbs['dawnleaf'], 1)
        before=f.save()
        with self.assertRaises(ValueError): f.brew(['dawnleaf','rillprism','dawnleaf'],EFFECTS)
        self.assertEqual(f.save(),before)

    def test_cook_and_save_roundtrip(self):
        f = Farm(hunger=10)
        f.tick(600); f.cook()
        self.assertEqual(f.hunger, 30)
        self.assertEqual(Farm.restore(json.loads(json.dumps(f.save()))).save(), f.save())

    def test_nonfinite_inputs_and_bad_save(self):
        for value in (0, -1, float('nan'), float('inf'), True):
            with self.assertRaises(ValueError): Farm().tick(value)
        data = Farm().save(); data['clean_water'] = -1
        with self.assertRaises(ValueError): Farm.restore(data)

    def test_layout_separates_all_assets_inside_cell(self):
        from place_sol_island import layout
        assets=[{'asset':str(g)+'_'+str(v),'kind':'Prop','archetype':str(g),'variant':v}
                for g in range(20) for v in range(1,26)]
        rows=layout(assets)
        self.assertEqual(len({tuple(r['position_cm']) for r in rows}),500)
        self.assertTrue(all(1200000 <= r['position_cm'][0] <= 2800000 and
                            -800000 <= r['position_cm'][1] <= 800000 for r in rows))

    def test_adventure_requires_actual_actions_and_persists(self):
        f=Farm()
        self.assertEqual(f.adventure_stage(),'restore_waterworks')
        f.collect('well'); f.filter()
        self.assertEqual(f.adventure_stage(),'discover_ring')
        f.brew(['dawnleaf','rillprism','dawnleaf'],EFFECTS)
        self.assertEqual(f.adventure_stage(),'feed_the_keeper')
        f.tick(600); f.cook()
        self.assertEqual(Farm.restore(f.save()).adventure_stage(),'portal_ready')

    def test_adventure_kit_is_exact_and_inside_island(self):
        from place_sol_island import adventure_layout
        import math
        assets=[{'asset':name,'kind':'Prop','archetype':name} for name in
                ['ShadowGuideStone','BrokenRingMural','HiddenCisternStair','Keeper','KeeperHearth']]
        rows=adventure_layout(assets)
        self.assertTrue(all(math.hypot(r['position_cm'][0]-2000000,r['position_cm'][1])<12000 for r in rows))
        with self.assertRaises(ValueError): adventure_layout(assets[:-1])

if __name__ == '__main__': unittest.main()
