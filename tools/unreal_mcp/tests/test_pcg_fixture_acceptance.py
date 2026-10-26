import copy
import unittest
from tools.unreal_mcp import pcg_fixture_acceptance as p


def valid():
    return {'graph': p.GRAPH, 'mesh': p.MESH, 'seed': 42, 'callback_count': 1, 'generated': True, 'busy': False,
            'instances': [{'mesh': p.MESH, 'position': list(v), 'quaternion_xyzw': [0., 0., 0., 1.], 'scale': [1., 1., 1.]} for v in p.POINTS]}


class Tests(unittest.TestCase):
    def test_complete_and_same_seed(self):
        r = valid(); s = valid(); s['instances'].reverse()
        self.assertTrue(p.qualify_repeat(r, s)['same_seed_output_equal'])
        self.assertFalse(p.qualify_output(r)['native_runtime_qualified'])

    def test_bad_identity_seed_completion(self):
        for field, value in [('graph', '/Game/Pythagoras/PCGEcology/PCG_Ecology.PCG_Ecology'), ('mesh', '/Engine/BasicShapes/Cone.Cone'),
                             ('seed', True), ('seed', 7), ('callback_count', 0), ('callback_count', 2), ('generated', False), ('busy', True)]:
            r = valid(); r[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(p.Refused): p.qualify_output(r)

    def test_missing_extra_duplicate_and_tampered_transform(self):
        variants = []
        r = valid(); r['instances'].pop(); variants.append(r)
        r = valid(); r['instances'].append(copy.deepcopy(r['instances'][0])); variants.append(r)
        r = valid(); r['instances'][1] = copy.deepcopy(r['instances'][0]); variants.append(r)
        r = valid(); r['instances'][0]['position'][0] += .001; variants.append(r)
        r = valid(); r['instances'][0]['scale'][0] = 2; variants.append(r)
        r = valid(); r['instances'][0]['position'][0] = float('nan'); variants.append(r)
        r = valid(); r['instances'][0]['mesh'] = '/Engine/BasicShapes/Cone.Cone'; variants.append(r)
        for r in variants:
            with self.assertRaises(p.Refused): p.qualify_output(r)


if __name__ == '__main__': unittest.main()
