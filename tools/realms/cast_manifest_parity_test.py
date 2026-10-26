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
    def test_indented_missing_role_is_counted_instead_of_false_green(self):
        report=audit('bricks','who A\n    who B\n',[{'id':'Mob_Bricks_A'}])
        self.assertFalse(report['ok'])
        self.assertEqual(report['matched'],1)
        self.assertEqual(report['total'],2)
        self.assertEqual([row['who'] for row in report['roles']],['A','B'])
        self.assertFalse(report['roles'][1]['ok'])
    def test_leading_and_trailing_whitespace_is_trimmed_like_native_dcs(self):
        report=audit('bricks',' \twho   A  \t\n\twho B\t \n',
                     [{'id':'Mob_Bricks_A'},{'id':'Mob_Bricks_B'}])
        self.assertTrue(report['ok'])
        self.assertEqual(report['matched'],2)
        self.assertEqual(report['total'],2)
        self.assertEqual([row['who'] for row in report['roles']],['A','B'])
    def test_case_insensitive_duplicate_roles_are_refused(self):
        for text in ('who A\nwho a\n','who A\n \twho a  \n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                audit('bricks',text,[{'id':'Mob_Bricks_A'}])
    def test_bare_or_empty_who_is_not_ignored_beside_a_valid_role(self):
        for text in ('who A\nwho\n','who A\nwho    \n',
                     'who A\n   who \t \n','who\nwho A\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                audit('bricks',text,[{'id':'Mob_Bricks_A'}])
    def test_a_tab_does_not_replace_the_native_literal_space_separator(self):
        with self.assertRaises(ValueError):
            audit('bricks','who\tA\n',[{'id':'Mob_Bricks_A'}])
if __name__=='__main__':unittest.main(verbosity=2)
