# SPDX-License-Identifier: MIT
import unittest
from check_bindings import analyze, ROOT


class BindingsTest(unittest.TestCase):
    def dump(self):
        mesh = ROOT+'/Mob_Lab_Guide/SkeletalMeshes/Guide.Guide'
        return {'schema':1, 'world_path':'/Game/World.World', 'captured_utc':'fixture',
                'loaded_only':True, 'atomic':False, 'registry_root':ROOT, 'errors':[],
                'assets':[{'path':mesh,'class':'SkeletalMesh'}],
                'roles':[{'path':'/Game/World.World:PersistentLevel.Guide','cast':'labyrinth',
                          'who':'Guide','candidate_ids':['Mob_Labyrinth_Guide','Mob_Lab_Guide'],
                          'art_found':'Mob_Lab_Guide','has_art':True,'mesh':mesh}]}

    def test_bound_alias_uses_native_order(self):
        self.assertTrue(analyze(self.dump())['passed'])

    def test_material_only_first_alias_shadows_later_mesh(self):
        dump=self.dump()
        dump['assets'].append({'path':ROOT+'/Mob_Labyrinth_Guide/M.M','class':'Material'})
        report=analyze(dump)
        self.assertFalse(report['passed'])
        self.assertEqual(report['roles'][0]['status'],'selected-folder-has-no-skeletal-mesh')

    def test_available_is_not_bound_and_missing_actor_is_gap(self):
        dump=self.dump(); dump['roles'][0]['has_art']=False
        report=analyze(dump,[('labyrinth','Guide'),('labyrinth','Missing')])
        self.assertEqual(report['counts'],{'art-available-not-bound':1})
        self.assertEqual(len(report['not_observed']),1)

    def test_observation_error_cannot_pass(self):
        dump=self.dump(); dump['errors']=[{'path':'other','error':'unavailable'}]
        self.assertFalse(analyze(dump)['passed'])


if __name__=='__main__':
    unittest.main()
