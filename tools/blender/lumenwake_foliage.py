"""Original, art-directed planting for Lumenwake Sanctuary / Riverjoin Commons.

This module owns vegetation only.  It uses the generator's injected geometry
API, never resets the scene, and never writes or imports another team's assets.
All coordinates are metres in the island's local frame.  Large crowns, fallen
tips, roots, folded flower petals, fern pinnae and grass ribbons are modeled;
there are no sphere-cloud trees or scatter-particle dependencies.

Entry point: build_foliage(api, terrain, variant='hero', exclusions=[]).
The result contains created objects, an authored planting summary and suggested
close-up camera targets.  Exclusions are (x, y, radius) circles in local metres.
"""

from math import cos, sin, pi, sqrt
from random import Random


def _add(a, b):
    return tuple(a[i] + b[i] for i in range(3))


def _sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def _mul(a, s):
    return tuple(v * s for v in a)


def _unit(a):
    mag = sqrt(sum(v * v for v in a))
    return _mul(a, 1.0 / max(mag, 0.00001))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _lerp(a, b, t):
    return _add(_mul(a, 1 - t), _mul(b, t))


class _Mesh:
    """Small mesh accumulator: one object for a whole botanical material layer."""

    def __init__(self):
        self.verts = []
        self.faces = []

    def vertex(self, p):
        self.verts.append(tuple(p))
        return len(self.verts) - 1

    def tube(self, points, radii, sides=9, phase=0.0):
        """Tapered connected stem with stable cross-sections and closed ends."""
        if len(points) < 2:
            return
        rings = []
        for i, p in enumerate(points):
            direction = _unit(_sub(points[min(i + 1, len(points) - 1)],
                                   points[max(0, i - 1)]))
            reference = (0, 0, 1) if abs(direction[2]) < 0.95 else (1, 0, 0)
            side = _unit(_cross(direction, reference))
            up = _unit(_cross(direction, side))
            ring = []
            for j in range(sides):
                angle = 2 * pi * j / sides + phase
                # Gentle lobes make bark read as grown, without random noise.
                radius = radii[i] * (1 + 0.055 * sin(3 * angle + i * 0.3))
                offset = _add(_mul(side, cos(angle) * radius),
                              _mul(up, sin(angle) * radius))
                ring.append(self.vertex(_add(p, offset)))
            rings.append(ring)
        self.faces.append(tuple(reversed(rings[0])))
        self.faces.append(tuple(rings[-1]))
        for i in range(len(rings) - 1):
            for j in range(sides):
                k = (j + 1) % sides
                self.faces.append((rings[i][j], rings[i][k],
                                   rings[i + 1][k], rings[i + 1][j]))

    def blade(self, origin, direction, length, width, bend=0.12, roll=0.0):
        """Folded tapered leaf/petal with a raised central rib and curved tip."""
        direction = _unit(direction)
        side = _unit(_cross(direction, (0, 0, 1)))
        if abs(direction[2]) > 0.98:
            side = (cos(roll), sin(roll), 0)
        up = _unit(_cross(side, direction))
        if roll:
            side, up = (_add(_mul(side, cos(roll)), _mul(up, sin(roll))),
                        _add(_mul(up, cos(roll)), _mul(side, -sin(roll))))
        base = self.vertex(origin)
        rings = []
        for t, spread in ((0.23, 0.62), (0.55, 1.0), (0.80, 0.60)):
            center = _add(origin, _add(_mul(direction, length * t),
                                      _mul(up, length * bend * t * t)))
            ridge = self.vertex(_add(center, _mul(up, width * 0.13 * sin(pi * t))))
            left = self.vertex(_add(center, _mul(side, -width * spread / 2)))
            right = self.vertex(_add(center, _mul(side, width * spread / 2)))
            rings.append((left, ridge, right))
        tip = self.vertex(_add(origin, _add(_mul(direction, length),
                                          _mul(up, length * bend))))
        a, b, c = rings[0]
        self.faces.extend(((base, b, a), (base, c, b)))
        for before, after in zip(rings, rings[1:]):
            a, b, c = before
            d, e, f = after
            self.faces.extend(((a, b, e, d), (b, c, f, e)))
        a, b, c = rings[-1]
        self.faces.extend(((a, b, tip), (b, c, tip)))

    def cushion(self, center, scale, seed, rings=6, sides=16):
        """Sculpted scalloped canopy lobe, asymmetrical and slightly swept."""
        rng = Random(seed)
        phase = rng.uniform(-pi, pi)
        x, y, z = center
        rx, ry, rz = scale
        bottom = self.vertex((x + 0.12 * rx, y, z - rz))
        bands = []
        for i in range(1, rings):
            latitude = -pi / 2 + pi * i / rings
            band = []
            for j in range(sides):
                angle = 2 * pi * j / sides
                scallop = 1 + 0.072 * sin(5 * angle + phase)
                scallop += 0.035 * sin(3 * angle - latitude * 2)
                radial = cos(latitude) * scallop
                # Off-center apex and a gently dripping lip break the ball shape.
                sweep = 0.20 * rx * sin(latitude) ** 2
                px = x + rx * cos(angle) * radial + sweep
                py = y + ry * sin(angle) * radial
                pz = z + rz * sin(latitude)
                pz -= 0.15 * rz * sin(4 * angle + phase) * cos(latitude) ** 2
                band.append(self.vertex((px, py, pz)))
            bands.append(band)
        top = self.vertex((x + 0.23 * rx, y - 0.08 * ry, z + rz))
        for j in range(sides):
            k = (j + 1) % sides
            self.faces.append((bottom, bands[0][k], bands[0][j]))
            self.faces.append((bands[-1][j], bands[-1][k], top))
        for before, after in zip(bands, bands[1:]):
            for j in range(sides):
                k = (j + 1) % sides
                self.faces.append((before[j], before[k], after[k], after[j]))

    def fan(self, origin, direction, length, width, lift, phase):
        """Thick sculpted conifer branch fan with scalloped, drooping margins."""
        direction = _unit((direction[0], direction[1], 0))
        side = (-direction[1], direction[0], 0)
        center = self.vertex(_add(origin, (0, 0, lift * 0.28)))
        rim = []
        # A rounded shield outline, rather than stacked cones.
        outline = ((0.05, -0.13), (0.25, -0.47), (0.49, -0.50),
                   (0.71, -0.39), (0.92, -0.18), (1.0, 0.0),
                   (0.92, 0.18), (0.71, 0.39), (0.49, 0.50),
                   (0.25, 0.47), (0.05, 0.13))
        for i, (along, across) in enumerate(outline):
            ripple = 1 + 0.07 * sin(i * 2.9 + phase)
            p = _add(origin, _add(_mul(direction, along * length * ripple),
                                 _mul(side, across * width)))
            p = _add(p, (0, 0, lift * sin(pi * along) - length * 0.18 * along))
            rim.append(self.vertex(p))
        lower = self.vertex(_add(origin, (0, 0, -0.26)))
        for i in range(len(rim)):
            j = (i + 1) % len(rim)
            self.faces.append((center, rim[i], rim[j]))
            self.faces.append((lower, rim[j], rim[i]))

    def emit(self, api, name, material, result, smooth=True):
        if not self.verts:
            return None
        obj = api['mesh'](name, self.verts, self.faces, material)
        # API outputs are normally Blender objects.  Plain adapters also work.
        if obj is not None:
            if smooth and hasattr(obj, 'data') and hasattr(obj.data, 'polygons'):
                for polygon in obj.data.polygons:
                    polygon.use_smooth = True
            if hasattr(obj, '__setitem__'):
                obj['lumenwake_original_botanical_mesh'] = True
                obj['foliage_material_role'] = material.name if hasattr(material, 'name') else str(material)
            result.append(obj)
        return obj


def _ground(terrain, x, y):
    return float(terrain(x, y))


def _allowed(x, y, radius, variant, exclusions, path_guard=True):
    if (x / 111.0) ** 2 + (y / 108.0) ** 2 > 0.88:
        return False
    for cx, cy, cr in exclusions:
        if (x - cx) ** 2 + (y - cy) ** 2 < (cr + radius) ** 2:
            return False
    # Ship-pulled connection lanes are authored empty, with generous side room.
    if abs(x) > 59 and abs(y) < 8 + radius:
        return False
    if abs(y) > 59 and abs(x) < 8 + radius:
        return False
    if variant == 'hero' and path_guard:
        dx, dy = x + 15, y + 12
        ellipse_fraction = sqrt((dx / 38) ** 2 + (dy / 30) ** 2)
        radial_distance = sqrt(dx * dx + dy * dy)
        loop_distance = (radial_distance * abs(1 - 1 / ellipse_fraction)
                         if ellipse_fraction > 0.00001 else 30)
        if loop_distance < 3.0 + radius:
            return False
        # The northward observatory walk and south-east cottage approach.
        if _segment_distance((x, y), (-15, 15), (-24, 46)) < 3.3 + radius:
            return False
        if _segment_distance((x, y), (12, -40), (35, -42)) < 3.3 + radius:
            return False
    return True


def _segment_distance(point, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    denom = max(dx * dx + dy * dy, 0.00001)
    t = min(1, max(0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / denom))
    return sqrt((point[0] - a[0] - t * dx) ** 2 + (point[1] - a[1] - t * dy) ** 2)


def _tree_base(terrain, x, y, height, seed, wood, variant='cotton'):
    """Curved bark trunk, fluted collar, branching boughs and grounded roots."""
    rng = Random(seed)
    ground = _ground(terrain, x, y)
    lean = rng.uniform(-0.7, 0.7)
    sway = rng.uniform(-0.6, 0.6)
    base_radius = height * (0.058 if variant == 'pine' else 0.073)
    main = [(x, y, ground - 0.10),
            (x + lean * 0.30, y + sway * 0.25, ground + height * 0.13),
            (x + lean, y + sway, ground + height * 0.33),
            (x + lean * 0.5, y + sway * 0.4, ground + height * 0.53),
            (x + lean * 0.8, y - sway * 0.25, ground + height * 0.78)]
    wood.tube(main, [base_radius * 1.35, base_radius, base_radius * 0.80,
                     base_radius * 0.57, base_radius * 0.18], sides=11)
    # Every root follows the local terrain, including hillside trees.
    for i in range(5):
        angle = i * 2 * pi / 5 + rng.uniform(-0.20, 0.20)
        reach = base_radius * rng.uniform(2.3, 3.8)
        ex, ey = x + cos(angle) * reach, y + sin(angle) * reach
        middle = (x + cos(angle) * reach * 0.52,
                  y + sin(angle) * reach * 0.52)
        wood.tube([(x, y, ground + base_radius * 0.75),
                   (middle[0], middle[1], _ground(terrain, *middle) + base_radius * 0.18),
                   (ex, ey, _ground(terrain, ex, ey) + 0.018)],
                  [base_radius * 0.48, base_radius * 0.23, 0.035], sides=7)
    return ground, main, base_radius


def _cotton_tree(api, terrain, x, y, height, spread, seed, name, objects,
                 golden=False):
    """Original broadleaf: lifted crown, scalloped umbrella, visible forked limbs."""
    rng = Random(seed)
    wood, shade, mid, light = _Mesh(), _Mesh(), _Mesh(), _Mesh()
    ground, main, radius = _tree_base(terrain, x, y, height, seed, wood)
    branches = []
    rotation = rng.uniform(-pi, pi)
    for i in range(5):
        angle = rotation + i * 2 * pi / 5 + rng.uniform(-0.20, 0.20)
        reach = spread * rng.uniform(0.62, 0.87)
        end = (x + cos(angle) * reach, y + sin(angle) * reach,
               ground + height * rng.uniform(0.68, 0.84))
        elbow = (x + cos(angle) * reach * 0.52, y + sin(angle) * reach * 0.52,
                 ground + height * (0.64 + 0.02 * (i % 3)))
        wood.tube([main[2], elbow, end], [radius * 0.45, radius * 0.29, radius * 0.08], sides=8)
        branches.append((angle, end))
        # Low asymmetric lobes expose airy gaps between branching silhouettes.
        lobe = (end[0], end[1], end[2] + height * 0.015)
        mid.cushion(lobe, (spread * 0.47, spread * 0.43, height * 0.17),
                    seed + i * 71, rings=6, sides=14)
        shade.cushion((end[0] * 0.18 + x * 0.82, end[1] * 0.18 + y * 0.82,
                       ground + height * 0.66),
                      (spread * 0.51, spread * 0.50, height * 0.12),
                      seed + i * 13, rings=5, sides=12)
    light.cushion((x - spread * 0.12, y + spread * 0.09, ground + height * 0.90),
                  (spread * 0.70, spread * 0.65, height * 0.16), seed + 519,
                  rings=6, sides=16)
    light.cushion((x + spread * 0.43, y - spread * 0.26, ground + height * 0.83),
                  (spread * 0.47, spread * 0.42, height * 0.12), seed + 851,
                  rings=5, sides=12)
    # Individual folded leaves edge the crown; they read clearly at a close camera.
    for i in range(24):
        angle = rotation + i * 2.39996
        branch = branches[i % 5][1]
        root = (branch[0] + cos(angle) * spread * 0.36,
                branch[1] + sin(angle) * spread * 0.32,
                branch[2] + height * rng.uniform(-0.02, 0.12))
        layer = light if i % 3 else mid
        layer.blade(root, (cos(angle), sin(angle), rng.uniform(0.12, 0.45)),
                    rng.uniform(0.75, 1.35), rng.uniform(0.30, 0.51), bend=-0.18,
                    roll=rng.uniform(-0.45, 0.45))
    mats = api['materials']
    wood.emit(api, name + '_living_bark_and_roots', mats['wood'], objects)
    shade.emit(api, name + '_canopy_shadows', mats['leaf_dark'], objects, smooth=False)
    mid.emit(api, name + '_scalloped_boughs', mats['leaf_gold' if golden else 'leaf_sage'], objects,
             smooth=False)
    light.emit(api, name + '_lifted_crown_and_leaf_tips',
               mats['leaf_sage' if golden else 'leaf_gold'], objects, smooth=False)


def _pine_tree(api, terrain, x, y, height, spread, seed, name, objects):
    """Tall sailpine: spiral whorls of folded fans with daylight between tiers."""
    rng = Random(seed)
    wood, shade, mid, tips = _Mesh(), _Mesh(), _Mesh(), _Mesh()
    ground, main, radius = _tree_base(terrain, x, y, height, seed, wood, 'pine')
    wood.tube([main[-2], main[-1], (x, y, ground + height)],
              [radius * 0.56, radius * 0.18, 0.045], sides=9)
    phase = rng.uniform(-pi, pi)
    for tier in range(7):
        fraction = tier / 6
        level = ground + height * (0.25 + fraction * 0.65)
        reach = spread * (1 - fraction * 0.78)
        count = 5 if tier < 4 else 4
        for i in range(count):
            angle = phase + i * 2 * pi / count + tier * 0.63
            start = (x + cos(angle) * radius * 0.2,
                     y + sin(angle) * radius * 0.2, level)
            end = (x + cos(angle) * reach * 0.87,
                   y + sin(angle) * reach * 0.87, level - reach * 0.14)
            wood.tube([start, _lerp(start, end, 0.56), end],
                      [radius * 0.19, radius * 0.10, 0.025], sides=6)
            layer = shade if (tier + i) % 3 == 0 else mid
            layer.fan(start, (cos(angle), sin(angle), 0), reach,
                      reach * rng.uniform(0.67, 0.90), reach * 0.29, seed + i)
            # Serrated spear tips alternate their catch-light across the spiral.
            if i % 2 == 0:
                for finger in (-1, 0, 1):
                    a = angle + finger * 0.15
                    leaf_start = _lerp(start, end, 0.70)
                    tips.blade(leaf_start, (cos(a), sin(a), 0.2),
                               reach * 0.35, reach * 0.18, bend=-0.32)
    tips.blade((x, y, ground + height * 0.90), (0.1, 0.08, 1),
               height * 0.12, spread * 0.29, bend=0.03)
    mats = api['materials']
    wood.emit(api, name + '_tapered_bark', mats['wood'], objects)
    shade.emit(api, name + '_folded_shadow_fans', mats['leaf_dark'], objects, smooth=False)
    mid.emit(api, name + '_spiral_sage_whorls', mats['leaf_sage'], objects, smooth=False)
    tips.emit(api, name + '_sunlit_spear_tips', mats['leaf_gold'], objects, smooth=False)


def _willow_tree(api, terrain, x, y, height, spread, seed, name, objects):
    """Water willow with arching limbs and cascades of separately folded leaves."""
    rng = Random(seed)
    wood, crown, ribbons, bright = _Mesh(), _Mesh(), _Mesh(), _Mesh()
    ground, main, radius = _tree_base(terrain, x, y, height, seed, wood)
    phase = rng.uniform(-pi, pi)
    for arm in range(6):
        angle = phase + arm * 2 * pi / 6
        reach = spread * rng.uniform(0.60, 0.90)
        end = (x + cos(angle) * reach, y + sin(angle) * reach,
               ground + height * rng.uniform(0.74, 0.88))
        arch = (x + cos(angle) * reach * 0.50,
                y + sin(angle) * reach * 0.50, ground + height * 0.83)
        wood.tube([main[2], arch, end],
                  [radius * 0.42, radius * 0.23, 0.075], sides=8)
        crown.cushion((arch[0], arch[1], arch[2] + height * 0.035),
                      (spread * 0.43, spread * 0.38, height * 0.12), seed + arm * 33,
                      rings=5, sides=12)
        for curtain in range(3):
            offset = (curtain - 1) * 0.20
            a = angle + offset
            top = (end[0] + cos(a + pi / 2) * offset * spread,
                   end[1] + sin(a + pi / 2) * offset * spread, end[2])
            fall = height * rng.uniform(0.29, 0.46)
            middle = (top[0] + cos(a) * 0.50, top[1] + sin(a) * 0.50,
                      top[2] - fall * 0.46)
            bottom = (top[0] + cos(a) * 0.33, top[1] + sin(a) * 0.33,
                      top[2] - fall)
            wood.tube([top, middle, bottom], [0.038, 0.024, 0.008], sides=5)
            for i in range(8):
                t = (i + 0.5) / 8
                root = _lerp(top, middle, t * 2) if t < 0.5 else _lerp(middle, bottom, (t - 0.5) * 2)
                side = -1 if i % 2 else 1
                leaf_angle = a + side * pi / 3
                layer = bright if (i + curtain + arm) % 4 == 0 else ribbons
                layer.blade(root, (cos(leaf_angle) * 0.40,
                                   sin(leaf_angle) * 0.40, -1),
                            rng.uniform(0.65, 1.05), rng.uniform(0.17, 0.26),
                            bend=0.18, roll=side * 0.30)
    mats = api['materials']
    wood.emit(api, name + '_arching_bark_and_curtain_stems', mats['wood_light'], objects)
    crown.emit(api, name + '_airy_crown', mats['leaf_sage'], objects, smooth=False)
    ribbons.emit(api, name + '_falling_leaf_curtains', mats['leaf_dark'], objects, smooth=False)
    bright.emit(api, name + '_golden_curtain_tips', mats['leaf_gold'], objects, smooth=False)


def _flower_patch(api, terrain, center, extent, count, seed, name, objects,
                  variant, exclusions, primary='flower_coral'):
    """Mixed meadow: three-layer petals, nectar cups, stems and basal rosettes."""
    rng = Random(seed)
    stems, leaves, outer, inner, nectar = (_Mesh() for _ in range(5))
    x, y = center
    planted = 0
    for index in range(count):
        # Golden-angle drift keeps spacing organic without uniform dot scatter.
        angle = index * 2.39996 + seed * 0.031
        radius = sqrt((index + 0.6) / count) * extent
        px = x + cos(angle) * radius * rng.uniform(0.80, 1.07)
        py = y + sin(angle) * radius * rng.uniform(0.78, 1.05)
        if not _allowed(px, py, 0.13, variant, exclusions):
            continue
        ground = _ground(terrain, px, py)
        if ground < 8.2:
            continue
        height = rng.uniform(0.56, 1.20)
        lean = (rng.uniform(-0.13, 0.13), rng.uniform(-0.13, 0.13), 0)
        tip = (px + lean[0], py + lean[1], ground + height)
        stems.tube([(px, py, ground - 0.025),
                    (px + lean[0] * 0.4, py + lean[1] * 0.4, ground + height * 0.52), tip],
                   [0.037, 0.026, 0.015], sides=5)
        flower_size = rng.uniform(0.35, 0.53)
        petals = 7 if index % 3 else 6
        rotation = rng.uniform(-pi, pi)
        for p in range(petals):
            a = rotation + p * 2 * pi / petals
            outer.blade(tip, (cos(a), sin(a), rng.uniform(0.06, 0.18)),
                        flower_size, flower_size * 0.65, bend=0.26)
            # Smaller inner petals make blossoms read as flowers, never dots.
            b = a + pi / petals
            inner.blade(_add(tip, (0, 0, 0.03)), (cos(b), sin(b), 0.20),
                        flower_size * 0.64, flower_size * 0.44, bend=0.36)
        nectar.cushion(_add(tip, (0, 0, 0.04)),
                       (flower_size * 0.22, flower_size * 0.22, flower_size * 0.11),
                       seed + index, rings=4, sides=8)
        for leaf_index in range(3):
            a = rotation + leaf_index * 2.2
            root = (px, py, ground + 0.09 + leaf_index * height * 0.16)
            leaves.blade(root, (cos(a), sin(a), 0.34),
                         rng.uniform(0.40, 0.66), rng.uniform(0.19, 0.28), bend=-0.11)
        planted += 1
    mats = api['materials']
    stems.emit(api, name + '_living_stems', mats['leaf_dark'], objects)
    leaves.emit(api, name + '_folded_rosette_leaves', mats['leaf_sage'], objects)
    outer.emit(api, name + '_outer_petals', mats[primary], objects)
    inner_material = 'flower_ivory' if primary != 'flower_ivory' else 'flower_coral'
    inner.emit(api, name + '_layered_inner_petals', mats[inner_material], objects)
    nectar.emit(api, name + '_nectar_cups', mats['leaf_gold'], objects)
    return planted


def _undergrowth(api, terrain, center, extent, count, seed, name, objects,
                 variant, exclusions):
    """Original curled ferns, paired pinnae and weaving grass ribbons."""
    rng = Random(seed)
    stems, shade, light = _Mesh(), _Mesh(), _Mesh()
    fern_count = 0
    x, y = center
    for index in range(count):
        a = index * 2.39996 + seed * 0.012
        radius = extent * sqrt((index + 0.8) / max(count, 1))
        px, py = x + cos(a) * radius, y + sin(a) * radius
        if not _allowed(px, py, 0.28, variant, exclusions):
            continue
        ground = _ground(terrain, px, py)
        if ground < 8.2:
            continue
        fern_count += 1
        for frond in range(5):
            angle = a + frond * 2 * pi / 5 + rng.uniform(-0.14, 0.14)
            reach = rng.uniform(1.1, 1.8)
            height = rng.uniform(0.8, 1.35)
            origin = (px, py, ground + 0.07)
            p1 = (px + cos(angle) * reach * 0.23,
                  py + sin(angle) * reach * 0.23, ground + height * 0.72)
            p2 = (px + cos(angle) * reach * 0.70,
                  py + sin(angle) * reach * 0.70, ground + height)
            p3 = (px + cos(angle) * reach,
                  py + sin(angle) * reach, ground + height * 0.88)
            stems.tube([origin, p1, p2, p3], [0.031, 0.025, 0.017, 0.006], sides=5)
            for pair in range(6):
                t = (pair + 0.7) / 7
                if t < 0.33:
                    root = _lerp(origin, p1, t / 0.33)
                elif t < 0.72:
                    root = _lerp(p1, p2, (t - 0.33) / 0.39)
                else:
                    root = _lerp(p2, p3, (t - 0.72) / 0.28)
                leaf_length = reach * (0.32 - 0.19 * t)
                for side in (-1, 1):
                    leaf_angle = angle + side * (1.13 - t * 0.28)
                    layer = light if (pair + frond) % 3 == 0 else shade
                    layer.blade(root, (cos(leaf_angle), sin(leaf_angle), 0.20),
                                leaf_length, leaf_length * 0.39,
                                bend=-0.08, roll=side * 0.12)
            light.blade(p2, (cos(angle), sin(angle), -0.05), reach * 0.33,
                        reach * 0.11, bend=-0.16)
        # A curled fiddlehead is a real tapering spiral, not a bead on a stem.
        curl = []
        for j in range(13):
            t = j / 12
            if t < 0.50:
                curl.append((px + 0.12, py - 0.09, ground + 0.08 + t * 1.6))
            else:
                theta = (t - 0.5) * 3.6 * pi
                cr = 0.20 * (1 - (t - 0.5) * 1.6)
                curl.append((px + 0.12 + cos(theta) * cr,
                             py - 0.09, ground + 0.82 + sin(theta) * cr))
        stems.tube(curl, [0.03 * (1 - j / 17) for j in range(13)], sides=6)
    # Thin ribbons have distinct broad bases and curved tapered tips.
    for index in range(count * 7):
        angle = rng.uniform(-pi, pi)
        radius = extent * sqrt(rng.random())
        px, py = x + cos(angle) * radius, y + sin(angle) * radius
        if not _allowed(px, py, 0.12, variant, exclusions):
            continue
        z = _ground(terrain, px, py) - 0.005
        if z < 8.2:
            continue
        lean = rng.uniform(-pi, pi)
        height = rng.uniform(0.42, 0.96)
        layer = light if index % 4 == 0 else shade
        layer.blade((px, py, z), (cos(lean) * 0.28, sin(lean) * 0.28, 1),
                    height, rng.uniform(0.07, 0.13), bend=-0.28,
                    roll=rng.uniform(-0.3, 0.3))
    mats = api['materials']
    stems.emit(api, name + '_frond_ribs_and_fiddleheads', mats['leaf_dark'], objects)
    shade.emit(api, name + '_paired_pinnae_and_grass', mats['leaf_sage'], objects)
    light.emit(api, name + '_lightcatching_leaf_edges', mats['leaf_gold'], objects)
    return fern_count


# Each tuple is (species, x, y, height, spread).  Composition is authored, not a
# random occupancy fill.  Tall trees back the landmark; broad crowns frame the
# village; open southern shore and cardinal connection lanes remain visible.
_HERO_TREES = (
    ('pine', -68, 66, 22.5, 5.5), ('pine', -57, 76, 25.0, 5.0),
    ('pine', -80, 54, 20.0, 5.7), ('pine', -43, 76, 21.2, 4.7),
    ('pine', -81, 38, 23.3, 5.6), ('pine', -92, 49, 18.5, 4.7),
    ('cotton', -62, 50, 15.6, 6.7), ('cotton', -47, 60, 13.8, 6.0),
    ('cotton', -74, -30, 16.1, 7.2), ('cotton', -65, -44, 12.8, 6.0),
    ('cotton', -86, -22, 14.2, 6.1), ('cotton', -78, -51, 17.5, 7.5),
    ('gold', -60, -59, 12.5, 5.8), ('gold', -43, -68, 11.8, 5.4),
    ('cotton', 36, 69, 16.9, 7.0), ('cotton', 48, 76, 14.2, 6.2),
    ('cotton', 66, 58, 18.0, 7.4), ('cotton', 73, 42, 16.2, 6.8),
    ('gold', 59, 32, 13.3, 5.8), ('cotton', 80, 22, 14.5, 6.1),
    ('gold', 47, 52, 12.4, 5.7), ('cotton', 81, -37, 15.0, 6.2),
    ('cotton', 72, -57, 17.4, 7.4), ('gold', 72, -70, 12.5, 5.8),
    ('cotton', 89, -51, 13.8, 6.0), ('cotton', 66, -21, 15.3, 6.7),
    ('gold', 55, -83, 11.8, 5.5), ('cotton', 28, -78, 14.4, 6.1),
    ('cotton', 18, 21, 12.2, 5.3), ('gold', 38, 15, 11.8, 5.3),
    ('cotton', -51, 17, 15.7, 6.4), ('cotton', -58, -29, 13.2, 5.7),
    ('gold', -47, -48, 11.5, 5.2), ('cotton', -71, 17, 15.4, 6.2),
    ('pine', -91, 22, 19.4, 4.8), ('gold', 30, 46, 12.0, 5.5),
    ('cotton', 87, 39, 14.0, 6.0), ('cotton', -32, -76, 13.7, 6.1),
    ('willow', 19, -11, 13.6, 5.4), ('willow', -49, -9, 14.2, 5.7),
    ('willow', -23, -57, 12.4, 5.2), ('willow', 27, -28, 13.1, 5.3),
    # Second artist pass: three outer framing groves, with open shore between.
    # Their unequal heights extend the skyline rather than make a perimeter wall.
    ('cotton', -78, -65, 18.4, 7.8), ('gold', -49, -84, 13.4, 5.8),
    ('cotton', -84, -41, 15.8, 6.5), ('gold', -35, -90, 12.2, 5.3),
    ('pine', 81, 60, 20.4, 5.4), ('cotton', 87, 47, 17.1, 7.1),
    ('gold', 70, 73, 12.8, 5.8), ('cotton', -81, 29, 15.9, 6.7),
    ('pine', -94, 35, 19.2, 4.6), ('gold', -32, 88, 14.0, 6.3),
)

_TEMPLATE_TREES = (
    ('gold', 43, 44, 11.4, 5.2), ('cotton', 55, 52, 13.8, 5.8),
    ('gold', 68, 42, 10.8, 4.9), ('gold', 48, 65, 12.2, 5.5),
    ('cotton', 64, 65, 14.6, 6.3), ('gold', 78, 57, 11.1, 5.0),
    ('gold', 78, 28, 10.2, 4.8), ('cotton', 32, 70, 13.2, 5.8),
    ('gold', 39, 27, 10.8, 4.9), ('gold', 57, 28, 12.0, 5.1),
    ('pine', -73, 54, 19.7, 4.9), ('pine', -58, 70, 22.2, 5.5),
    ('pine', -83, 35, 18.5, 4.7), ('cotton', -59, 47, 14.6, 6.2),
    ('gold', -40, 62, 11.2, 5.2), ('cotton', -40, 39, 12.5, 5.5),
    ('cotton', -70, -37, 14.0, 6.0), ('gold', -60, -57, 11.7, 5.4),
    ('cotton', -42, -69, 13.8, 6.0), ('gold', -82, -48, 10.8, 4.8),
    ('gold', 56, -68, 12.4, 5.6), ('cotton', 76, -49, 15.3, 6.4),
    ('gold', 78, -30, 11.3, 5.0), ('willow', -28, -23, 12.6, 5.4),
    ('willow', -20, 22, 13.2, 5.5), ('cotton', 29, -74, 13.0, 5.6),
)

_HERO_FLOWERS = (
    (-30, -48, 3.6, 27, 'flower_coral'),
    (-14, -51, 3.0, 24, 'flower_ivory'),
    (4, -48, 3.7, 31, 'flower_lavender'),
    (25, -38, 3.2, 26, 'flower_coral'),
    (29, -7, 3.1, 25, 'flower_ivory'),
    (12, 22, 3.7, 32, 'flower_lavender'),
    (-39, 23, 3.5, 27, 'flower_coral'),
    (-60, -12, 3.2, 25, 'flower_lavender'),
    (-42, -42, 3.4, 28, 'flower_ivory'),
    (26, -54, 3.1, 25, 'flower_coral'),
    (55, -51, 3.6, 30, 'flower_lavender'),
    (59, -16, 3.0, 23, 'flower_ivory'),
    (-5, 46, 3.2, 25, 'flower_lavender'),
    (31, 60, 3.0, 24, 'flower_coral'),
    (-63, 35, 2.8, 21, 'flower_ivory'),
    (-73, -65, 4.4, 36, 'flower_lavender'),
    (78, 55, 4.3, 34, 'flower_ivory'),
    (-79, 27, 4.0, 33, 'flower_coral'),
    (-40, -86, 4.2, 35, 'flower_ivory'),
)

_TEMPLATE_FLOWERS = (
    (30, 43, 3.0, 24, 'flower_ivory'),
    (52, 38, 3.4, 28, 'flower_coral'),
    (72, 67, 3.0, 24, 'flower_lavender'),
    (-48, 50, 3.4, 28, 'flower_lavender'),
    (-32, 29, 3.2, 25, 'flower_ivory'),
    (-59, -45, 3.5, 29, 'flower_coral'),
    (-38, -58, 3.0, 25, 'flower_ivory'),
    (64, -52, 3.4, 28, 'flower_lavender'),
    (23, -56, 3.0, 24, 'flower_coral'),
    (-37, -6, 3.0, 23, 'flower_ivory'),
)

_HERO_FERNS = ((-58, 9, 4.4, 5), (-67, -42, 4.6, 5),
               (59, 39, 4.5, 5), (79, 31, 3.8, 4),
               (-48, 63, 4.4, 5), (-70, 56, 4.7, 5),
               (78, -65, 4.0, 4), (-43, -37, 3.5, 4),
               (18, 12, 3.8, 4), (-84, 26, 3.7, 4),
               (37, 71, 3.7, 4), (32, -81, 3.6, 4),
               (-77, -59, 4.8, 6), (75, 64, 4.6, 5),
               (-87, 36, 4.4, 5), (-45, -81, 4.6, 5))

_TEMPLATE_FERNS = ((-67, 52, 4.2, 5), (-43, 40, 3.6, 4),
                   (61, 60, 4.0, 4), (73, 36, 3.7, 4),
                   (-66, -55, 4.3, 5), (65, -61, 4.0, 4),
                   (-23, 31, 3.5, 4), (-36, -26, 3.7, 4))


def build_foliage(api, terrain, variant='hero', exclusions=None):
    """Build the curated planting into the caller's active collection.

    ``hero`` selects the sanctuary.  ``template`` (and any other variant value)
    selects the lower, orchard-focused Commons composition.  Existing geometry,
    materials, objects, collections and files are never removed or overwritten.
    """
    exclusions = list(exclusions or [])
    is_hero = variant == 'hero'
    objects = []
    tree_specs = _HERO_TREES if is_hero else _TEMPLATE_TREES
    flower_specs = _HERO_FLOWERS if is_hero else _TEMPLATE_FLOWERS
    fern_specs = _HERO_FERNS if is_hero else _TEMPLATE_FERNS
    seed = 741021 if is_hero else 841024
    counts = {'cotton': 0, 'gold': 0, 'pine': 0, 'willow': 0,
              'flowers': 0, 'ferns': 0, 'excluded_tree_positions': [],
              'submerged_tree_positions': []}
    prefix = 'Lumenwake' if is_hero else 'Riverjoin'
    for index, (species, x, y, height, spread) in enumerate(tree_specs):
        # Willow collars are slim.  Their crowns intentionally hang over water.
        clearance = 0.35 if species == 'willow' else 1.55
        if not _allowed(x, y, clearance, variant, exclusions):
            counts['excluded_tree_positions'].append([species, x, y])
            continue
        if _ground(terrain, x, y) < 8.2:
            counts['submerged_tree_positions'].append([species, x, y])
            continue
        name = '{}_{}_{}'.format(prefix, species, str(index + 1).zfill(2))
        tree_seed = seed + index * 173
        if species == 'pine':
            _pine_tree(api, terrain, x, y, height, spread, tree_seed, name, objects)
        elif species == 'willow':
            _willow_tree(api, terrain, x, y, height, spread, tree_seed, name, objects)
        else:
            _cotton_tree(api, terrain, x, y, height, spread, tree_seed, name, objects,
                         golden=(species == 'gold'))
        counts[species] += 1
    for index, (x, y, extent, count, color) in enumerate(flower_specs):
        counts['flowers'] += _flower_patch(
            api, terrain, (x, y), extent, count, seed + 9000 + index * 89,
            '{}_Meadow_{:02d}'.format(prefix, index + 1), objects,
            variant, exclusions, primary=color)
    for index, (x, y, extent, count) in enumerate(fern_specs):
        counts['ferns'] += _undergrowth(
            api, terrain, (x, y), extent, count, seed + 18000 + index * 109,
            '{}_FernUnderstory_{:02d}'.format(prefix, index + 1), objects,
            variant, exclusions)
    counts['trees'] = sum(counts[k] for k in ('cotton', 'gold', 'pine', 'willow'))
    counts['objects'] = len(objects)
    counts['authored_tree_positions'] = len(tree_specs)
    counts['flower_patch_positions'] = len(flower_specs)
    counts['fern_patch_positions'] = len(fern_specs)
    counts['species'] = {
        'cotton': 'scalloped cottoncrown broadleaf with fluted roots and airy boughs',
        'gold': 'smaller sunleaf orchard tree with folded golden foliage',
        'pine': 'spiral sailpine with thick scalloped branch fans',
        'willow': 'arching water willow with cascading folded leaves',
    }
    closeups = ([
        {'name': 'Pondside willow and layered meadow', 'position_xy': [19, -42],
         'target_xy': [-2, -23], 'eye_height': 4.0, 'target_height': 7.0},
        {'name': 'Sailpine woodland and fern fronds', 'position_xy': [-52, 33],
         'target_xy': [-72, 58], 'eye_height': 3.0, 'target_height': 9.0},
        {'name': 'Village flowers beneath cottoncrowns', 'position_xy': [40, -61],
         'target_xy': [67, -42], 'eye_height': 2.8, 'target_height': 6.0},
    ] if is_hero else [
        {'name': 'Commons orchard canopy and petal beds', 'position_xy': [27, 36],
         'target_xy': [57, 53], 'eye_height': 3.0, 'target_height': 6.0},
        {'name': 'Commons nursery forest edge', 'position_xy': [-36, 33],
         'target_xy': [-63, 58], 'eye_height': 3.0, 'target_height': 7.0},
    ])
    return {'objects': objects, 'summary': counts, 'closeup_views': closeups}
