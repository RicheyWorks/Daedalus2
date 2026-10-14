import unittest
from cast_manifest_parity import audit,candidates
class ParityTest(unittest.TestCase):
    def test_native_alias_forms(self):
        self.assertIn('Mob_Bricks_GlueWitch',candidates('bricks','Glue Witch'))
        self.assertIn('Mob_Lab_ArchitectApprentice',candidates('labyrinth',"The Architect's Apprentice"))
        self.assertIn('Mob_Parcels_LostLetterGhost',candidates('parcels','Lost-Letter Ghost'))
    def test_missing_role_and_extra_hero(self):
        report=audit('bricks','who Glue Witch\n',[{'id':'Mob_Bricks_Builder'}])
        self.assertFalse(report['ok']);self.assertEqual(report['matched'],0)
        self.assertEqual(report['unbound_manifest_ids'],['Mob_Bricks_Builder'])
    def test_alias_fills_gap_without_consuming_hero(self):
        report=audit('bricks','who Glue Witch\n',[{'id':'Mob_Bricks_Builder'},{'id':'Mob_Bricks_GlueWitch'}])
        self.assertTrue(report['ok']);self.assertEqual(report['matched'],1)
    def test_empty_or_duplicates_refused(self):
        for text,records in [('',[]),('who A\nwho A\n',[]),('who A\n',[{'id':'X'},{'id':'X'}])]:
            with self.assertRaises(ValueError):audit('bricks',text,records)
if __name__=='__main__':unittest.main(verbosity=2)
