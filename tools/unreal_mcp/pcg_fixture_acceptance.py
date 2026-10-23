"""Three-point owned PCG acceptance. No imports, engine calls or historical adoption."""
import math

GRAPH = '/Game/CodexToolEvaluation/PCGMinimal/R1/PCG_WillowFixture.PCG_WillowFixture'
MESH = '/Game/Daedalus/Art/Prop/Prop_Tree_Willow_Mature/Prop_Tree_Willow_Mature/StaticMeshes/Prop_Tree_Willow_Mature.Prop_Tree_Willow_Mature'
POINTS = [[700000., 700000., 300000.], [700300., 700000., 300000.], [700000., 700300., 300000.]]
SEED = 42


class Refused(ValueError):
    pass


def require(value, reason):
    if not value:
        raise Refused(reason)


def qualify_output(receipt):
    require(type(receipt) is dict, 'Actual complete receipt required')
    require(receipt.get('graph') == GRAPH and receipt.get('mesh') == MESH, 'Wrong private graph/Blender mesh')
    require(type(receipt.get('seed')) is int and receipt['seed'] == SEED, 'Wrong observed component seed')
    require(type(receipt.get('callback_count')) is int and receipt['callback_count'] == 1, 'Unique completed generation callback required')
    require(receipt.get('generated') is True and receipt.get('busy') is False, 'Actual idle generated state required')
    instances = receipt.get('instances')
    require(type(instances) is list and len(instances) == 3, 'Exactly three actual instances required')
    positions = []
    for item in instances:
        require(type(item) is dict and item.get('mesh') == MESH, 'Wrong instance mesh')
        for name, size in [('position', 3), ('quaternion_xyzw', 4), ('scale', 3)]:
            value = item.get(name)
            require(type(value) is list and len(value) == size and all(type(v) in (int, float) and math.isfinite(v) for v in value), 'Malformed transform')
        require(item['quaternion_xyzw'] in ([0., 0., 0., 1.], [0., 0., 0., -1.]) and item['scale'] == [1., 1., 1.], 'Unexpected instance rotation/scale')
        positions.append(item['position'])
    require(sorted(positions) == sorted(POINTS), 'Actual transforms differ from independently authored fixture points')
    return {'three_point_output_accepted': True, 'scope': 'EXPLICIT_PRIVATE_THREE_POINT_WILLOW_FIXTURE_ONLY', 'native_runtime_qualified': False}


def qualify_repeat(first, second):
    qualify_output(first); qualify_output(second)
    key = lambda x: sorted(x['instances'], key=lambda row: row['position'])
    require(key(first) == key(second), 'Same-seed instance output changed')
    return {'same_seed_output_equal': True, 'native_runtime_qualified': False}
