import unittest
from collections import Counter
from pathlib import Path
from portal_population import build


class PopulationTests(unittest.TestCase):
    def test_scope_identity_and_proof(self):
        source = Path(__file__).resolve().parents[2]/'daedalus-core/src/main/java/com/daedalus/world/retro/RetroMonster.java'
        roster = build(source.read_text())
        rows = roster['population']
        self.assertEqual(len(rows), 1000)
        self.assertEqual(len({r['id'] for r in rows}), 1000)
        self.assertEqual(Counter(r['faction'] for r in rows), {'enemy':500, 'friendly':500})
        counts = Counter((r['faction'], r['type']) for r in rows)
        self.assertEqual(len(counts), 100)
        self.assertEqual(set(counts.values()), {10})
        self.assertTrue(all(r['art_status']=='Planned' and r['unreal_status']=='Pending' for r in rows))
        self.assertEqual(sum(r['existing_rules_key'] is not None for r in rows), 150)
        self.assertTrue(all(b['id'] not in {r['id'] for r in rows} for b in roster['bosses']))

    def test_source_drift_requires_reconciliation(self):
        with self.assertRaises(ValueError):
            build('SLIME("Slime", 1)')


if __name__ == '__main__':
    unittest.main()
