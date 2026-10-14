"""Artist-authored architecture for Lumenwake and Riverjoin Commons.

This module is deliberately Blender-independent: the scene owner supplies the
primitive API and an actual terrain-height sampler. Dimensions are metres,
Z is up, boxes use full dimensions and sphere scales use radii. Windows, roof
ribs, deck boards and structural trim are compound meshes, not object clouds.

The paired-island composition keeps the central water garden clear and puts
doors, connected paths and porches at terrain height. It contains original
architecture only; the scene owner owns vegetation, ocean and towing sockets.
"""

from math import atan2, ceil, cos, hypot, pi, sin, sqrt


class _Mesh:
    """Small closed-shell mesh accumulator; each emitted object has one material."""

    def __init__(self):
        self.verts = []
        self.faces = []

    def shell(self, verts, faces):
        offset = len(self.verts)
        self.verts.extend(verts)
        self.faces.extend(tuple(offset + n for n in face) for face in faces)

    def prism(self, center, dims, angle=0.0):
        x, y, z = center
        a, b, c = (n * 0.5 for n in dims)
        ca, sa = cos(angle), sin(angle)
        verts = []
        for dx, dy, dz in ((-a, -b, -c), (a, -b, -c),
                           (a, b, -c), (-a, b, -c),
                           (-a, -b, c), (a, -b, c),
                           (a, b, c), (-a, b, c)):
            verts.append((x + dx * ca - dy * sa,
                          y + dx * sa + dy * ca, z + dz))
        self.shell(verts, ((0, 3, 2, 1), (4, 5, 6, 7),
                           (0, 1, 5, 4), (1, 2, 6, 5),
                           (2, 3, 7, 6), (3, 0, 4, 7)))

    def beam(self, start, end, width, depth=None):
        """Rectangular beam along any 3D vector, with stable perpendicular axes."""
        ax, ay, az = start
        bx, by, bz = end
        vx, vy, vz = bx - ax, by - ay, bz - az
        length = sqrt(vx * vx + vy * vy + vz * vz)
        if length < 0.0001:
            return
        vx, vy, vz = vx / length, vy / length, vz / length
        horizontal = sqrt(vx * vx + vy * vy)
        if horizontal < 0.0001:
            ux, uy, uz = 1.0, 0.0, 0.0
        else:
            ux, uy, uz = -vy / horizontal, vx / horizontal, 0.0
        wx, wy, wz = vy * uz - vz * uy, vz * ux - vx * uz, vx * uy - vy * ux
        half_u = width * 0.5
        half_w = (depth if depth is not None else width) * 0.5
        verts = []
        for point in (start, end):
            for du, dw in ((-half_u, -half_w), (half_u, -half_w),
                           (half_u, half_w), (-half_u, half_w)):
                verts.append((point[0] + ux * du + wx * dw,
                              point[1] + uy * du + wy * dw,
                              point[2] + uz * du + wz * dw))
        self.shell(verts, ((0, 3, 2, 1), (4, 5, 6, 7),
                           (0, 1, 5, 4), (1, 2, 6, 5),
                           (2, 3, 7, 6), (3, 0, 4, 7)))


class _Builder:
    def __init__(self, api, terrain, prefix):
        self.api = api
        self.terrain = terrain
        self.materials = api['materials']
        self.prefix = prefix
        self.objects = []
        self.placements = []
        self.routes = []

    def remember(self, obj, role='architecture'):
        if obj is not None:
            self.objects.append(obj)
            try:
                obj['lumenwake_role'] = role
                obj['authored_module'] = 'lumenwake_architecture'
            except (AttributeError, TypeError):
                pass
        return obj

    def box(self, name, loc, dims, material, bevel=0.12):
        return self.remember(self.api['box'](self.prefix + name, loc, dims,
                                           self.materials[material], bevel=bevel))

    def sphere(self, name, loc, radii, material, segments=16, rings=8):
        return self.remember(self.api['sphere'](self.prefix + name, loc, radii,
                                              self.materials[material],
                                              segments=segments, rings=rings))

    def cylinder(self, name, loc, radius, depth, material, vertices=20):
        return self.remember(self.api['cylinder'](self.prefix + name, loc, radius,
                                                depth, self.materials[material],
                                                vertices=vertices))

    def emit(self, name, geometry, material, role='architecture'):
        if not geometry.verts:
            return None
        obj = self.api['mesh'](self.prefix + name, geometry.verts, geometry.faces,
                               self.materials[material])
        return self.remember(obj, role)

    def sample_base(self, x, y, width, depth):
        samples = [self.terrain(x + dx * width, y + dy * depth)
                   for dx, dy in ((-.5, -.5), (.5, -.5), (.5, .5),
                                  (-.5, .5), (0, 0), (-.5, 0),
                                  (.5, 0), (0, -.5), (0, .5))]
        return max(samples) + .38, min(samples) - .5

    def footing(self, name, x, y, width, depth):
        floor, buried = self.sample_base(x, y, width, depth)
        self.box(name + '_fitted_stone_footing', (x, y, (floor + buried) * .5),
                 (width + .6, depth + .6, floor - buried), 'stone', .2)
        self.box(name + '_pale_threshold_course', (x, y, floor - .12),
                 (width + .9, depth + .9, .28), 'stone_light', .08)
        return floor

    def deck(self, name, x, y, width, depth, elevation=None):
        deck_z = elevation if elevation is not None else self.sample_base(x, y, width, depth)[0]
        structure, boards = _Mesh(), _Mesh()
        for px in (x - width * .43, x + width * .43):
            for py in (y - depth * .42, y + depth * .42):
                ground = self.terrain(px, py) - .25
                if deck_z > ground:
                    structure.prism((px, py, (ground + deck_z) * .5),
                                    (.42, .42, deck_z - ground))
        for py in (y - depth * .34, y + depth * .34):
            structure.prism((x, py, deck_z - .22), (width, .25, .3))
        count = max(2, int(ceil(depth / .52)))
        stride = depth / count
        for n in range(count):
            boards.prism((x, y - depth * .5 + (n + .5) * stride, deck_z),
                         (width, stride - .035, .19))
        self.emit(name + '_supported_joists', structure, 'wood')
        self.emit(name + '_individual_floorboards', boards, 'wood_light', 'walkable_deck')
        return deck_z + .1

    def route(self, name, points, width=3.3, minimum_z=10.24):
        """Continuous engineered walk: fitted stairs on land, piers over channels.

        A two-pass grade envelope keeps every deck node above the full corridor
        while limiting stairs to .43m rise/metre. This prevents channel samples
        producing disconnected treads, and gives bridges deliberate approaches.
        """
        boards, timber, foundations, rails = _Mesh(), _Mesh(), _Mesh(), _Mesh()
        nodes, corner_indices = [], []
        for segment, (start, end) in enumerate(zip(points[:-1], points[1:])):
            sx, sy = start
            ex, ey = end
            dx, dy = ex - sx, ey - sy
            distance = hypot(dx, dy)
            if distance < .001:
                continue
            count = max(1, int(ceil(distance / .58)))
            ux, uy = dx / distance, dy / distance
            if segment:
                corner_indices.append(len(nodes) - 1)
            for n in range(count + 1):
                if segment and not n:
                    continue
                t = n / count
                x, y = sx + dx * t, sy + dy * t
                grounds = [self.terrain(x, y),
                           self.terrain(x - uy * width * .48, y + ux * width * .48),
                           self.terrain(x + uy * width * .48, y - ux * width * .48)]
                z = max(grounds) + .27
                if minimum_z is not None:
                    z = max(z, minimum_z)
                nodes.append([x, y, z, self.terrain(x, y)])
        if len(nodes) < 2:
            return
        for order in (range(1, len(nodes)), range(len(nodes) - 2, -1, -1)):
            forward = order.step > 0
            for n in order:
                adjacent = n - 1 if forward else n + 1
                distance = hypot(nodes[n][0] - nodes[adjacent][0],
                                 nodes[n][1] - nodes[adjacent][1])
                nodes[n][2] = max(nodes[n][2], nodes[adjacent][2] - distance * .43)
        for n, (a, b) in enumerate(zip(nodes[:-1], nodes[1:])):
            dx, dy = b[0] - a[0], b[1] - a[1]
            distance = hypot(dx, dy)
            ux, uy = dx / distance, dy / distance
            angle = atan2(dy, dx) + pi * .5
            x, y = (a[0] + b[0]) * .5, (a[1] + b[1]) * .5
            z = max(a[2], b[2])
            ground = self.terrain(x, y)
            clearance = z - ground
            # Shallow tread joints are closed by actual vertical timber risers.
            boards.prism((x, y, z), (width, distance + .012, .17), angle)
            if abs(a[2] - b[2]) > .04:
                riser_height = abs(a[2] - b[2]) + .12
                boards.prism((b[0], b[1], z - riser_height * .5),
                             (width, .075, riser_height), angle)
            for side in (-1, 1):
                offset = side * width * .39
                timber.beam((a[0] - uy * offset, a[1] + ux * offset, a[2] -.29),
                             (b[0] - uy * offset, b[1] + ux * offset, b[2] -.29), .24, .34)
            if clearance < 1.45:
                lower = min(ground -.20, z -.23)
                foundations.prism((x, y, (z -.10 + lower) * .5),
                                   (width -.18, distance + .045, z -.10 - lower), angle)
            elif n % 5 == 0 or n in corner_indices:
                for side in (-1, 1):
                    px, py = x - uy * side * width * .38, y + ux * side * width * .38
                    buried = self.terrain(px, py) -.40
                    timber.prism((px, py, (buried + z -.20) * .5),
                                  (.31, .31, max(.25, z -.20 - buried)))
                timber.prism((x, y, z -.33), (width + .12, .24, .30), angle)
            # Bridge/stair rail is continuous; dry, level garden walks stay open.
            steep = abs(a[2] - b[2]) / distance > .10
            if clearance > .80 or steep:
                for side in (-1, 1):
                    offset = side * (width * .5 -.10)
                    pa = (a[0] - uy * offset, a[1] + ux * offset, a[2] + 1.05)
                    pb = (b[0] - uy * offset, b[1] + ux * offset, b[2] + 1.05)
                    rails.beam(pa, pb, .10)
                    rails.beam((pa[0], pa[1], pa[2] -.43),
                               (pb[0], pb[1], pb[2] -.43), .065)
                    if n % 4 == 0:
                        rails.prism((pa[0], pa[1], a[2] + .54), (.13, .13, 1.19))
        for n in corner_indices:
            x, y, z, _ = nodes[n]
            boards.prism((x, y, z + .10), (width + .08, width + .08, .17))
            timber.prism((x, y, z -.18), (width + .12, width + .12, .32))
        self.emit(name + '_continuous_treads_and_closed_risers', boards, 'wood_light', 'connected_route')
        self.emit(name + '_continuous_stringers_and_grounded_piers', timber, 'wood')
        self.emit(name + '_fitted_stone_stair_foundations', foundations, 'stone_light')
        self.emit(name + '_continuous_bridge_and_stair_handrails', rails, 'wood')
        self.routes.append({'name': name, 'points_xy': [list(p) for p in points],
                            'width_m': width, 'ground_following': True,
                            'maximum_stair_grade': .43, 'minimum_deck_z': minimum_z,
                            'structure': 'fitted_stair_base_or_supported_pier_boardwalk'})

    def steps(self, name, center, width, run, target_z, outward=(0, -1)):
        x, y = center
        ox, oy = outward
        ground = self.terrain(x + ox * run, y + oy * run)
        rise = max(.2, target_z - ground)
        count = max(2, int(ceil(rise / .28)))
        angle = atan2(oy, ox) + pi * .5
        mesh = _Mesh()
        for n in range(count):
            t = (n + .5) / count
            px, py = x + ox * run * t, y + oy * run * t
            top = target_z - rise * n / count
            lower = min(self.terrain(px, py) - .2, top - .18)
            mesh.prism((px, py, (top + lower) * .5),
                       (width, run / count + .035, top - lower), angle)
        self.emit(name + '_grounded_stair', mesh, 'stone_light', 'walkable_stair')


def _facade(center, horizontal, outward, u, v, z):
    return (center[0] + horizontal[0] * u + outward[0] * v,
            center[1] + horizontal[1] * u + outward[1] * v, center[2] + z)


def _arch_outline(width, height, base=0.0, segments=10):
    radius = width * .5
    spring = height - radius + base
    return [(-radius, base), (radius, base)] + [
        (radius * cos(pi * n / segments), spring + radius * sin(pi * n / segments))
        for n in range(segments + 1)]


def _arch_panel(mesh, center, horizontal, outward, width, height, depth, base=0.0):
    outline = _arch_outline(width, height, base)
    verts = [_facade(center, horizontal, outward, u, v, z)
             for v in (-depth * .5, depth * .5) for u, z in outline]
    n = len(outline)
    faces = [tuple(reversed(range(n))), tuple(range(n, n * 2))]
    faces.extend((i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n))
    mesh.shell(verts, faces)


def _arch_ring(mesh, center, horizontal, outward, width, height, thickness, depth):
    outer = _arch_outline(width, height)
    inner = _arch_outline(width - thickness * 2, height - thickness * 2,
                          base=thickness)
    n = len(outer)
    verts = []
    for v in (-depth * .5, depth * .5):
        for outline in (outer, inner):
            verts.extend(_facade(center, horizontal, outward, u, v, z)
                         for u, z in outline)
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.extend(((i, j, j + n, i + n),
                      (i + 2 * n, i + 3 * n, j + 3 * n, j + 2 * n),
                      (i, i + 2 * n, j + 2 * n, j),
                      (i + n, j + n, j + 3 * n, i + 3 * n)))
    mesh.shell(verts, [tuple(reversed(face)) for face in faces])


def _windows(builder, name, specs, frame='wood', shutters=False):
    glass, frames, sill, shutter_mesh = _Mesh(), _Mesh(), _Mesh(), _Mesh()
    for center, horizontal, outward, width, height in specs:
        _arch_panel(glass, center, horizontal, outward, width - .25,
                    height - .18, .10, .11)
        front = _facade(center, horizontal, outward, 0, .14, 0)
        _arch_ring(frames, front, horizontal, outward, width, height, .16, .18)
        bottom = _facade(center, horizontal, outward, 0, .15, .18)
        top = _facade(center, horizontal, outward, 0, .15, height - .17)
        frames.beam(bottom, top, .095)
        spring = height - width * .5
        frames.beam(_facade(center, horizontal, outward, -width * .43, .15, spring),
                    _facade(center, horizontal, outward, width * .43, .15, spring), .09)
        angle = atan2(horizontal[1], horizontal[0])
        sill.prism(_facade(center, horizontal, outward, 0, .16, -.09),
                   (width + .38, .56, .23), angle)
        if shutters:
            for sign in (-1, 1):
                u = sign * (width * .5 + .28)
                shutter_mesh.prism(_facade(center, horizontal, outward, u, .13, height * .43),
                                    (.43, .15, height * .84), angle)
                for z in (.22, height * .50, height * .72):
                    frames.prism(_facade(center, horizontal, outward, u, .25, z),
                                 (.42, .10, .07), angle)
    builder.emit(name + '_recessed_arch_glazing', glass, 'glass')
    builder.emit(name + '_arched_frames_and_mullions', frames, frame)
    builder.emit(name + '_carved_window_sills', sill, 'stone_light')
    builder.emit(name + '_open_cedar_shutters', shutter_mesh, 'wood_light')


def _door(builder, name, x, y, floor, width=1.65, height=3.25):
    panel, frame, studs = _Mesh(), _Mesh(), _Mesh()
    center, horizontal, outward = (x, y, floor), (1, 0), (0, -1)
    _arch_panel(panel, center, horizontal, outward, width, height, .22)
    _arch_ring(frame, (x, y - .17, floor), horizontal, outward,
               width + .34, height + .17, .16, .20)
    for n in range(6):
        studs.prism((x - width * .40 + n * width * .16, y - .145, floor + height * .40),
                    (.025, .04, height * .73))
    for height_ratio in (.23, .62):
        frame.prism((x, y - .17, floor + height * height_ratio),
                    (width * .86, .10, .10))
    builder.emit(name + '_arched_cedar_door', panel, 'wood_light')
    builder.emit(name + '_door_surround_and_straps', frame, 'wood')
    builder.emit(name + '_door_board_seams', studs, 'roof_dark')
    builder.sphere(name + '_brass_latch', (x + width * .29, y - .25, floor + 1.2),
                   (.105, .105, .105), 'brass', 10, 5)


def _gable_volume(x, y, floor, width, depth, eave, rise):
    profile = [(-width * .5, floor), (width * .5, floor),
               (width * .5, floor + eave), (0, floor + eave + rise),
               (-width * .5, floor + eave)]
    mesh = _Mesh()
    mesh.shell([(x + u, y + v, z) for v in (-depth * .5, depth * .5)
                for u, z in profile],
               ((0, 1, 2, 3, 4), (9, 8, 7, 6, 5),
                (5, 6, 1, 0), (6, 7, 2, 1), (7, 8, 3, 2),
                (8, 9, 4, 3), (9, 5, 0, 4)))
    return mesh


def _gable_roof(builder, name, x, y, z, width, depth, rise, material='roof'):
    roof, ribs, rim = _Mesh(), _Mesh(), _Mesh()
    half_w = width * .5
    half_d = depth * .5
    for side in (-1, 1):
        verts = [(x, y - half_d, z + rise), (x + side * half_w, y - half_d, z),
                 (x + side * half_w, y + half_d, z), (x, y + half_d, z + rise)]
        faces = ((0, 1, 2, 3), (7, 6, 5, 4),
                 (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0))
        if side < 0:
            faces = tuple(tuple(reversed(face)) for face in faces)
        roof.shell(verts + [(a, b, c - .24) for a, b, c in verts], faces)
        for n in range(max(5, int(depth / 1.0)) + 1):
            yy = y - half_d + depth * n / max(5, int(depth / 1.0))
            ribs.beam((x, yy, z + rise + .10),
                       (x + side * half_w, yy, z + .10), .10, .14)
        rim.beam((x + side * half_w, y - half_d, z),
                  (x + side * half_w, y + half_d, z), .23, .27)
        for yy in (y - half_d, y + half_d):
            rim.beam((x, yy, z + rise + .02), (x + side * half_w, yy, z + .02), .23)
    builder.emit(name + '_layered_pitched_roof', roof, material)
    builder.emit(name + '_raised_roof_seams', ribs, 'brass')
    builder.emit(name + '_carved_eaves_and_verge', rim, 'wood')
    builder.box(name + '_copper_ridge_cap', (x, y, z + rise + .17),
                (.34, depth + .25, .30), 'roof', .10)


def _lantern(builder, name, x, y, base_z, post=False):
    if post:
        builder.box(name + '_post', (x, y, base_z + 1.65), (.22, .22, 3.3), 'wood', .045)
        base_z += 2.95
    builder.box(name + '_warm_glass', (x, y, base_z + .29), (.44, .44, .58), 'glow', .035)
    metal = _Mesh()
    for dx in (-.255, .255):
        for dy in (-.255, .255):
            metal.prism((x + dx, y + dy, base_z + .29), (.055, .055, .64))
    metal.prism((x, y, base_z -.015), (.59, .59, .08))
    metal.prism((x, y, base_z + .63), (.64, .64, .11))
    builder.emit(name + '_brass_cage', metal, 'brass')
    builder.sphere(name + '_cap', (x, y, base_z + .72), (.36, .36, .16), 'roof', 12, 5)


def _planter(builder, name, x, y, width, depth, z=None, flowers='flower_coral'):
    floor = builder.terrain(x, y) if z is None else z
    builder.box(name + '_cedar_box', (x, y, floor + .35), (width, depth, .70), 'wood', .09)
    builder.box(name + '_soil', (x, y, floor + .72), (width -.17, depth -.17, .10), 'soil', .015)
    leaves, blossoms = _Mesh(), _Mesh()
    count = max(3, int(width * 1.1))
    for n in range(count):
        px = x - width * .40 + width * .80 * n / max(1, count - 1)
        py = y + sin(n * 2.1) * depth * .18
        stem_z = floor + .94 + (n % 3) * .07
        leaves.prism((px, py, floor + .90), (.08, .08, .37))
        leaves.prism((px + .13, py, floor + .93), (.31, .15, .09), .45)
        for petal in range(5):
            angle = petal * 2 * pi / 5
            blossoms.prism((px + .13 * cos(angle), py + .13 * sin(angle), stem_z + .16),
                           (.18, .14, .08), angle)
    builder.emit(name + '_stems_and_leaves', leaves, 'leaf_sage')
    builder.emit(name + '_five_petalled_blooms', blossoms, flowers)


def _cottage(builder, name, center, width, depth, style, roof_material):
    x, y = center
    floor = builder.footing(name, x, y, width, depth)
    eave = 5.5 if style != 'workshop' else 5.9
    rise = 4.5 if style == 'atelier' else (3.5 if style == 'workshop' else 4.2)
    builder.emit(name + '_plaster_gabled_envelope',
                  _gable_volume(x, y, floor, width, depth, eave, rise), 'wall')
    _gable_roof(builder, name, x, y, floor + eave, width + 1.35, depth + 1.4,
                 rise + .28, roof_material)
    timber = _Mesh()
    for dx in (-width * .5 -.04, width * .5 + .04):
        for dy in (-depth * .5 -.04, depth * .5 + .04):
            timber.prism((x + dx, y + dy, floor + eave * .5), (.28, .28, eave))
    for yy in (y - depth * .5 -.09, y + depth * .5 + .09):
        timber.prism((x, yy, floor + .43), (width + .24, .23, .25))
        timber.prism((x, yy, floor + eave -.05), (width + .25, .23, .22))
        timber.beam((x - width * .5, yy, floor + eave),
                     (x, yy, floor + eave + rise), .25)
        timber.beam((x + width * .5, yy, floor + eave),
                     (x, yy, floor + eave + rise), .25)
        timber.beam((x, yy, floor + eave), (x, yy, floor + eave + rise - .22), .20)
        timber.beam((x - width * .26, yy, floor + eave),
                     (x, yy, floor + eave + rise * .67), .18)
        timber.beam((x + width * .26, yy, floor + eave),
                     (x, yy, floor + eave + rise * .67), .18)
    for xx in (x - width * .5 -.08, x + width * .5 + .08):
        timber.prism((xx, y, floor + .43), (.23, depth, .25))
    builder.emit(name + '_visible_structural_half_timber', timber, 'wood')
    front_y = y - depth * .5 -.19
    _door(builder, name, x, front_y, floor)
    windows = [((x + sign * width * .29, front_y, floor + 1.55),
                (1, 0), (0, -1), 1.55, 2.75) for sign in (-1, 1)]
    windows += [((x, front_y, floor + eave + .60), (1, 0), (0, -1), 1.80, 2.40)]
    for sign in (-1, 1):
        for offset in (-depth * .25, depth * .25):
            windows.append(((x + sign * (width * .5 + .13), y + offset, floor + 1.60),
                            (0, sign), (sign, 0), 1.55, 2.55))
    _windows(builder, name, windows, shutters=True)
    porch_y = front_y - 1.8
    porch_floor = builder.deck(name + '_porch', x, porch_y, width * .82, 3.35, floor -.07)
    veranda = _Mesh()
    for px in (x - width * .34, x + width * .34):
        veranda.prism((px, porch_y - 1.45, floor + 1.68), (.26, .26, 3.36))
        veranda.beam((px, porch_y - 1.44, floor + 2.68),
                      (px, porch_y -.64, floor + 3.36), .19)
    veranda.prism((x, porch_y - 1.45, floor + 3.35), (width * .75, .29, .28))
    builder.emit(name + '_porch_posts_and_knee_braces', veranda, 'wood')
    awning = _Mesh()
    awning.shell([(x - width * .40, front_y + .18, floor + 4.02),
                  (x + width * .40, front_y + .18, floor + 4.02),
                  (x + width * .40, porch_y - 1.65, floor + 3.45),
                  (x - width * .40, porch_y - 1.65, floor + 3.45),
                  (x - width * .40, front_y + .18, floor + 3.85),
                  (x + width * .40, front_y + .18, floor + 3.85),
                  (x + width * .40, porch_y - 1.65, floor + 3.28),
                  (x - width * .40, porch_y - 1.65, floor + 3.28)],
                 ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
                  (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)))
    builder.emit(name + '_sheltered_veranda_roof', awning,
                  'roof_dark' if roof_material == 'roof' else 'roof')
    builder.steps(name + '_front', (x, porch_y - 1.78), 2.8, 2.8, porch_floor)
    _lantern(builder, name + '_door_lantern', x + 1.30, front_y -.42, floor + 2.55)
    for sign in (-1, 1):
        _planter(builder, name + ('_west_flowerbox' if sign < 0 else '_east_flowerbox'),
                  x + sign * width * .28, front_y -.58, 2.1, .75, floor + .50,
                  'flower_lavender' if style == 'home' else 'flower_coral')
    # A tall working chimney, collar and rain cap are part of the silhouette.
    chimney_x = x + width * .29
    chimney_y = y + depth * .18
    roof_at_chimney = floor + eave + rise * .42
    builder.box(name + '_coursed_chimney', (chimney_x, chimney_y, roof_at_chimney + 1.0),
                (1.4, 1.5, 3.4), 'stone_light', .10)
    builder.box(name + '_chimney_brick_band', (chimney_x, chimney_y, roof_at_chimney + 2.25),
                (1.56, 1.65, .27), 'roof', .05)
    builder.box(name + '_chimney_dark_flue', (chimney_x, chimney_y, roof_at_chimney + 2.73),
                (.90, 1.0, .42), 'roof_dark', .06)
    builder.box(name + '_chimney_weather_cap', (chimney_x, chimney_y, roof_at_chimney + 3.02),
                (1.72, 1.78, .27), 'stone_light', .05)
    builder.placements.append({'name': name, 'center_xy': [x, y], 'floor_z': floor,
                               'footprint_m': [width, depth], 'style': style,
                               'entrance_xy': [x, porch_y - 4.58]})
    return floor, (x, porch_y - 4.58)


def _dome(builder, name, x, y, base_z, radius, height, roof='roof'):
    mesh = _Mesh()
    segments = 24
    levels = 7
    for level in range(levels):
        theta = level / levels * pi * .5
        rr = radius * cos(theta)
        for segment in range(segments):
            angle = segment / segments * 2 * pi
            mesh.verts.append((x + rr * cos(angle), y + rr * sin(angle),
                               base_z + height * sin(theta)))
    for level in range(levels - 1):
        for segment in range(segments):
            nxt = (segment + 1) % segments
            a = level * segments + segment
            b = level * segments + nxt
            mesh.faces.append((a, b, b + segments, a + segments))
    apex = len(mesh.verts)
    mesh.verts.append((x, y, base_z + height))
    for segment in range(segments):
        a = (levels - 1) * segments + segment
        b = (levels - 1) * segments + (segment + 1) % segments
        mesh.faces.append((a, b, apex))
    # A lower flange conceals the roof/wall join; the ribs sit above the surface.
    builder.emit(name + '_segmented_copper_dome', mesh, roof)
    builder.cylinder(name + '_dome_drum_flange', (x, y, base_z -.09),
                     radius + .20, .32, 'brass', 24)
    ribs = _Mesh()
    for segment in range(12):
        angle = segment / 12 * 2 * pi
        points = []
        for level in range(levels + 1):
            theta = level / levels * pi * .5
            rr = radius * cos(theta) + .045
            points.append((x + rr * cos(angle), y + rr * sin(angle),
                           base_z + height * sin(theta) + .08))
        for a, b in zip(points[:-1], points[1:]):
            ribs.beam(a, b, .10)
    builder.emit(name + '_standing_seam_meridians', ribs, 'brass')
    builder.cylinder(name + '_apex_copper_finial', (x, y, base_z + height + .31),
                     .32, .55, 'brass', 12)


def _observatory(builder):
    name, x, y = 'Lumenwake_Observatory', -24.0, 46.0
    floor, buried = builder.sample_base(x, y, 19, 19)
    builder.cylinder(name + '_deep_fitted_terrace', (x, y, (floor + buried) * .5),
                     11.8, floor - buried, 'stone', 32)
    builder.cylinder(name + '_ivory_terrace_lip', (x, y, floor -.03),
                     12.0, .38, 'stone_light', 32)
    builder.cylinder(name + '_octagonal_lower_plinth', (x, y, floor + .40),
                     8.7, .8, 'stone_light', 16)
    builder.cylinder(name + '_ivory_observatory_drum', (x, y, floor + 6.35),
                     7.7, 11.5, 'cream', 24)
    for z, radius, depth in ((1.0, 7.85, .35), (4.1, 7.87, .25),
                              (10.7, 7.87, .27), (12.1, 8.05, .45)):
        builder.cylinder(name + '_carved_string_course_' + str(z),
                         (x, y, floor + z), radius, depth, 'stone_light', 24)
    pilasters, windows = _Mesh(), []
    for n in range(12):
        angle = n * 2 * pi / 12
        outward = (cos(angle), sin(angle))
        horizontal = (-sin(angle), cos(angle))
        wx, wy = x + outward[0] * 7.71, y + outward[1] * 7.71
        if n != 9:
            windows.append(((wx, wy, floor + 5.0), horizontal, outward, 2.08, 4.05))
        column_angle = angle + pi / 12
        cx, cy = x + 7.65 * cos(column_angle), y + 7.65 * sin(column_angle)
        pilasters.prism((cx, cy, floor + 6.8), (.27, .36, 10.2), column_angle + pi * .5)
    builder.emit(name + '_ivory_radial_pilasters', pilasters, 'stone_light')
    _windows(builder, name, windows, 'brass')
    _dome(builder, name, x, y, floor + 12.23, 8.6, 6.8)
    _door(builder, name, x, y - 7.70, floor + .84, 2.50, 4.2)
    # Entry loggia is structural, connected to the terrace and stair.
    porch_z = builder.deck(name + '_entry_loggia', x, y - 9.15, 7.0, 4.6, floor + .56)
    supports = _Mesh()
    for px in (x - 2.65, x + 2.65):
        supports.prism((px, y - 10.95, floor + 2.69), (.43, .43, 4.3))
        supports.beam((px, y - 10.94, floor + 3.46),
                       (px, y - 9.90, floor + 4.50), .27)
    builder.emit(name + '_loggia_cedar_columns', supports, 'wood')
    _gable_roof(builder, name + '_entry_loggia', x, y - 9.10,
                 floor + 4.56, 7.6, 5.05, 1.35, 'roof_dark')
    builder.steps(name + '_entry', (x - 3.60, y - 9.15), 2.9, 3.2, porch_z, (-1, 0))
    for sign in (-1, 1):
        _lantern(builder, name + ('_west_entry_light' if sign < 0 else '_east_entry_light'),
                   x + sign * 3.45, y - 10.15, floor + .68, True)
    # Distinct ivory lighthouse shares the observatory precinct, not a decorative mast.
    lx, ly = x + 14.8, y + 5.0
    lighthouse_floor, lighthouse_buried = builder.sample_base(lx, ly, 8.2, 8.2)
    builder.cylinder(name + '_beacon_fitted_foundation',
                     (lx, ly, (lighthouse_floor + lighthouse_buried) * .5),
                     4.5, lighthouse_floor - lighthouse_buried, 'stone', 16)
    builder.cylinder(name + '_beacon_ivory_shaft', (lx, ly, lighthouse_floor + 9.0),
                     2.65, 18.0, 'cream', 16)
    for z in (.28, 6.0, 12.0, 17.7):
        builder.cylinder(name + '_beacon_copper_band_' + str(z),
                         (lx, ly, lighthouse_floor + z), 2.74, .30, 'roof', 16)
    builder.cylinder(name + '_beacon_balcony', (lx, ly, lighthouse_floor + 18.15),
                     3.8, .42, 'stone_light', 24)
    builder.cylinder(name + '_beacon_lantern_room', (lx, ly, lighthouse_floor + 19.95),
                     2.47, 3.2, 'glass', 16)
    builder.cylinder(name + '_beacon_actual_light', (lx, ly, lighthouse_floor + 19.95),
                     .98, 2.05, 'glow', 16)
    cages, balcony = _Mesh(), _Mesh()
    for n in range(16):
        angle = n * 2 * pi / 16
        cages.prism((lx + 2.5 * cos(angle), ly + 2.5 * sin(angle), lighthouse_floor + 19.97),
                     (.11, .11, 3.30))
        point = (lx + 3.46 * cos(angle), ly + 3.46 * sin(angle), lighthouse_floor + 18.82)
        balcony.prism(point, (.12, .12, 1.28))
        next_angle = (n + 1) * 2 * pi / 16
        balcony.beam((point[0], point[1], lighthouse_floor + 19.44),
                      (lx + 3.46 * cos(next_angle), ly + 3.46 * sin(next_angle),
                       lighthouse_floor + 19.44), .10)
    builder.emit(name + '_beacon_lantern_vertical_mullions', cages, 'brass')
    builder.emit(name + '_beacon_walkable_balcony_rail', balcony, 'brass')
    _dome(builder, name + '_beacon', lx, ly, lighthouse_floor + 21.60, 3.08, 2.58, 'roof_dark')
    beacon_windows = []
    for z, angle in ((3.0, -pi * .5), (8.7, -.35), (13.4, pi * .55)):
        outward = (cos(angle), sin(angle))
        beacon_windows.append(((lx + 2.64 * outward[0], ly + 2.64 * outward[1],
                                lighthouse_floor + z), (-outward[1], outward[0]),
                               outward, .92, 1.90))
    _windows(builder, name + '_beacon', beacon_windows, 'brass')
    _door(builder, name + '_beacon', lx, ly - 2.68, lighthouse_floor + .13, 1.35, 2.85)
    builder.route(name + '_precinct_link', ((x + 9.0, y), (lx, ly - 4.1)), 2.7)
    builder.placements.append({'name': name, 'center_xy': [x, y],
                               'floor_z': floor, 'style': 'copper_observatory_and_ivory_beacon',
                               'landmark_height_m': max(floor + 19.6, lighthouse_floor + 24.8),
                               'entrance_xy': [x - 6.8, y - 9.15]})
    return (x - 6.8, y - 9.15)


def _market(builder, x, y):
    name = 'Lanterncourt_Market'
    floor = builder.deck(name, x, y, 14.0, 11.0)
    legs, shelves, cloth = _Mesh(), _Mesh(), _Mesh()
    for n in range(2):
        stall_x = x + (-4.5 if n == 0 else 4.5)
        for dx in (-2.0, 2.0):
            for dy in (-1.1, 1.1):
                legs.prism((stall_x + dx, y + dy, floor + 1.55), (.19, .19, 3.1))
        shelves.prism((stall_x, y, floor + 1.14), (4.0, 2.3, .21))
        shelves.prism((stall_x, y + .94, floor + .55), (4.0, .18, 1.1))
        cloth.shell([(stall_x - 2.25, y - 1.5, floor + 3.02),
                     (stall_x + 2.25, y - 1.5, floor + 3.02),
                     (stall_x + 2.25, y + 1.5, floor + 3.60),
                     (stall_x - 2.25, y + 1.5, floor + 3.60)], ((0, 1, 2, 3),))
        for crate_n in range(3):
            cx = stall_x - 1.35 + crate_n * 1.35
            builder.box(name + '_produce_crate_' + str(n) + '_' + str(crate_n),
                        (cx, y, floor + 1.48), (1.15, 1.2, .55), 'wood_light', .06)
            for fruit_n in range(4):
                builder.sphere(name + '_harvest_' + str(n) + '_' + str(crate_n) + '_' + str(fruit_n),
                               (cx -.33 + (fruit_n % 2) * .66,
                                y -.26 + (fruit_n // 2) * .52, floor + 1.90),
                               (.23, .23, .25), 'flower_coral' if n == 0 else 'leaf_gold', 8, 5)
    builder.emit(name + '_stall_cedar_posts', legs, 'wood')
    builder.emit(name + '_stall_counters', shelves, 'wood_light')
    builder.emit(name + '_sea_glass_canvas_awning', cloth, 'roof_dark')
    # Benches surround a grounded public hearth rather than filling the route.
    hx, hy = x + 11.0, y + 6.8
    hz = builder.terrain(hx, hy)
    builder.cylinder(name + '_public_hearth_stone_ring', (hx, hy, hz + .28), 1.65, .56, 'stone_light', 16)
    builder.cylinder(name + '_hearth_dark_basin', (hx, hy, hz + .59), 1.23, .11, 'roof_dark', 16)
    logs = _Mesh()
    logs.beam((hx - .88, hy -.37, hz + .73), (hx + .84, hy + .39, hz + .73), .26)
    logs.beam((hx - .68, hy + .64, hz + .85), (hx + .60, hy -.66, hz + .85), .26)
    builder.emit(name + '_actual_hearth_logs', logs, 'wood')
    for angle in (-.3, 1.0, 2.4, 3.7):
        bx, by = hx + 3.6 * cos(angle), hy + 3.6 * sin(angle)
        bench = _Mesh()
        zz = builder.terrain(bx, by)
        bench.prism((bx, by, zz + .86), (2.7, .68, .20), angle + pi * .5)
        for u in (-1, 1):
            px, py = bx - u * sin(angle), by + u * cos(angle)
            bench.prism((px, py, zz + .39), (.24, .38, .79), angle)
        builder.emit(name + '_hearth_bench_' + str(angle), bench, 'wood_light')
    for sign in (-1, 1):
        _lantern(builder, name + ('_west_lantern' if sign < 0 else '_east_lantern'),
                   x + sign * 7.0, y - 4.5, builder.terrain(x + sign * 7, y - 4.5), True)
    builder.steps(name + '_north', (x, y + 5.55), 4.0, 3.0, floor, (0, 1))
    builder.steps(name + '_south', (x, y - 5.55), 4.0, 3.0, floor, (0, -1))
    builder.steps(name + '_east', (x + 7.05, y), 3.1, 2.8, floor, (1, 0))
    builder.placements.append({'name': name, 'center_xy': [x, y], 'floor_z': floor,
                               'style': 'two_stall_market_and_public_hearth'})


def _atelier_annex(builder, center, floor):
    x, y = center
    name = 'Tideglass_Atelier_Sunroom'
    ax, ay = x + 9.4, y + 1.3
    ground = builder.terrain(ax, ay)
    builder.box(name + '_fitted_base', (ax, ay, (ground + floor) * .5),
                (5.3, 7.5, max(.4, floor - ground + .35)), 'stone_light', .1)
    builder.box(name + '_waist_wall', (ax, ay, floor + 1.0), (5.2, 7.4, 2.0), 'cream', .1)
    frames, glass = _Mesh(), _Mesh()
    for sign in (-1, 1):
        xx = ax + sign * 2.64
        for n in range(4):
            yy = ay - 2.9 + n * 1.94
            glass.prism((xx, yy, floor + 3.3), (.09, 1.69, 2.35))
            frames.prism((xx + sign * .07, yy + .88, floor + 3.3), (.14, .14, 2.6))
        frames.prism((xx + sign * .07, ay, floor + 2.06), (.16, 7.5, .18))
        frames.prism((xx + sign * .07, ay, floor + 4.54), (.16, 7.5, .18))
    builder.emit(name + '_real_glazed_walls', glass, 'glass')
    builder.emit(name + '_cedar_glazing_structure', frames, 'wood')
    _gable_roof(builder, name, ax, ay, floor + 4.7, 6.0, 8.3, 1.4, 'roof_dark')
    builder.placements.append({'name': name, 'center_xy': [ax, ay], 'floor_z': floor,
                               'style': 'connected_sea_glass_sunroom'})


def _round_turret(builder, name, center, floor):
    x, y = center
    builder.cylinder(name + '_ivory_hexagonal_turret', (x, y, floor + 3.65),
                     3.3, 7.3, 'cream', 12)
    builder.cylinder(name + '_turret_sill_band', (x, y, floor + 1.20),
                     3.4, .24, 'stone_light', 12)
    mesh = _Mesh()
    sides = 12
    verts = [(x + 3.85 * cos(n * 2 * pi / sides),
              y + 3.85 * sin(n * 2 * pi / sides), floor + 7.2) for n in range(sides)]
    verts.append((x, y, floor + 12.1))
    mesh.shell(verts, [(n, (n + 1) % sides, sides) for n in range(sides)])
    builder.emit(name + '_twelve_sided_cedar_spire', mesh, 'roof_dark')
    seams = _Mesh()
    for n in range(6):
        angle = n * 2 * pi / 6
        seams.beam((x + 3.85 * cos(angle), y + 3.85 * sin(angle), floor + 7.27),
                    (x, y, floor + 12.17), .11)
    builder.emit(name + '_turret_ridge_seams', seams, 'brass')
    windows = []
    for angle in (-pi * .5, 0, pi * .5, pi):
        outward = (cos(angle), sin(angle))
        windows.append(((x + 3.32 * outward[0], y + 3.32 * outward[1], floor + 2.15),
                        (-outward[1], outward[0]), outward, 1.24, 2.8))
    _windows(builder, name, windows, 'wood')


def _workshop_yard(builder, x, y, floor):
    name = 'Lanternwright_Working_Yard'
    builder.deck(name, x - 9.3, y, 5.8, 10.3, floor -.1)
    table = _Mesh()
    table.prism((x - 9.3, y + 1.8, floor + 1.05), (4.2, 1.5, .25))
    for dx in (-1.6, 1.6):
        for dy in (-.45, .45):
            table.prism((x - 9.3 + dx, y + 1.8 + dy, floor + .45), (.18, .18, .9))
    table.prism((x - 9.3, y + 2.50, floor + 2.25), (4.3, .19, 1.7))
    builder.emit(name + '_joinery_bench_and_tool_wall', table, 'wood_light')
    tools = _Mesh()
    for n in range(5):
        px = x - 10.9 + n * .78
        tools.prism((px, y + 2.33, floor + 2.25), (.07, .09, .82))
        tools.prism((px + .18, y + 2.27, floor + 2.67), (.52, .14, .19))
    builder.emit(name + '_working_hand_tools', tools, 'brass')
    for n in range(3):
        builder.cylinder(name + '_timber_stock_' + str(n),
                         (x - 9.3 + (n - 1) * 1.55, y - 2.5, floor + .87),
                         .61, 1.74, 'wood', 12)
    builder.placements.append({'name': name, 'center_xy': [x - 9.3, y],
                               'floor_z': floor, 'style': 'usable_joinery_bench'})


def _cistern(builder, center):
    x, y = center
    name = 'Riverjoin_Raincatch_Cistern'
    floor, buried = builder.sample_base(x, y, 7.7, 7.7)
    builder.cylinder(name + '_fitted_stone_ring', (x, y, (floor + buried) * .5),
                     4.2, floor - buried, 'stone', 16)
    builder.cylinder(name + '_cream_water_tank', (x, y, floor + 2.3),
                     3.1, 4.6, 'cream', 20)
    for z in (.42, 2.25, 4.35):
        builder.cylinder(name + '_copper_binding_' + str(z), (x, y, floor + z),
                         3.2, .22, 'brass', 20)
    _dome(builder, name, x, y, floor + 4.63, 3.35, 1.3, 'roof_dark')
    pipe = _Mesh()
    pipe.beam((x + 3.3, y, floor + 4.3), (x + 4.2, y, floor + 4.3), .18)
    pipe.beam((x + 4.2, y, floor + 4.3), (x + 4.2, y, floor + 1.5), .18)
    pipe.beam((x + 4.2, y, floor + 1.5), (x + 4.8, y, floor + 1.5), .18)
    builder.emit(name + '_visible_rainwater_spigot', pipe, 'brass')
    builder.box(name + '_stone_drinking_trough', (x + 4.75, y, floor + .55),
                (2.3, 1.4, .9), 'stone_light', .18)
    builder.box(name + '_trough_water', (x + 4.75, y, floor + 1.02),
                (1.90, 1.04, .06), 'water', .01)
    builder.placements.append({'name': name, 'center_xy': [x, y], 'floor_z': floor,
                               'style': 'shared_rainwater_cistern'})


def _boathouse(builder):
    x, y = 38.0, -38.0
    name = 'Riverjoin_Tugwright_Boathouse'
    floor, entrance = _cottage(builder, name, (x, y), 17.0, 12.0, 'workshop', 'roof_dark')
    # Low side annex carries the towing business without imposing a factory skyline.
    ax = x + 12.6
    builder.box(name + '_rope_loft_wall', (ax, y + 1.0, floor + 1.6),
                (7.9, 9.5, 3.2), 'wall', .12)
    _gable_roof(builder, name + '_rope_loft', ax, y + 1.0, floor + 3.3,
                 8.8, 10.3, 1.6, 'roof')
    _windows(builder, name + '_rope_loft',
               [((ax, y - 3.87, floor + .9), (1, 0), (0, -1), 2.7, 1.95)], 'wood')
    work_z = builder.deck(name + '_tug_repair_apron', x, y - 14.0, 18.0, 9.2, floor -.06)
    # A recognizable small hull on actual cradle beams is a repair vignette.
    hull = _Mesh()
    sections = [(-5.5, .25, .30), (-3.8, 1.9, 1.1),
                (2.4, 2.0, 1.15), (5.0, .90, .65)]
    verts = []
    for along, beam, keel in sections:
        verts.extend(((x + along, y - 14.1 - beam, work_z + 1.70),
                      (x + along, y - 14.1 + beam, work_z + 1.70),
                      (x + along, y - 14.1, work_z + .72 - keel * .16)))
    faces = [(2, 1, 0), (9, 10, 11)]
    for n in range(3):
        a, b = n * 3, (n + 1) * 3
        faces.extend(((a, b, b + 2, a + 2), (a + 2, b + 2, b + 1, a + 1)))
    hull.shell(verts, [tuple(reversed(face)) for face in faces])
    builder.emit(name + '_tug_hull_on_cradle', hull, 'roof_dark')
    cradle = _Mesh()
    for dx in (-2.8, 2.2):
        cradle.prism((x + dx, y - 14.1, work_z + .38), (.30, 5.0, .56))
    builder.emit(name + '_actual_repair_cradle', cradle, 'wood')
    builder.box(name + '_hull_inset_deck', (x -.1, y - 14.1, work_z + 1.63),
                (7.2, 2.6, .18), 'wood_light', .08)
    builder.box(name + '_tug_wheelhouse', (x + .9, y - 14.1, work_z + 2.47),
                (2.8, 2.4, 1.65), 'cream', .13)
    _gable_roof(builder, name + '_tug_wheelhouse', x + .9, y - 14.1,
                 work_z + 3.30, 3.2, 2.7, .38, 'roof')
    builder.box(name + '_tug_window', (x + .9, y - 15.35, work_z + 2.66),
                (1.75, .08, .74), 'glass', .04)
    builder.cylinder(name + '_tug_stack', (x + 2.35, y - 14.1, work_z + 3.68),
                     .28, 1.6, 'brass', 12)
    _workshop_yard(builder, x - 1.5, y + .5, floor)
    builder.routes.append({'name': name + '_working_apron', 'points_xy': [list(entrance), [x, y - 14]],
                            'width_m': 4.5, 'ground_following': False})
    return entrance


def _sunleaf_garden(builder):
    """Small, authored medicinal garden; the supported leaf fan is its skyline."""
    name, x, y = 'Sunleaf_Medicinal_Cloister', -43.0, -56.0
    floor = builder.footing(name, x, y, 11.4, 11.0)
    floor = builder.deck(name + '_garden_terrace', x, y, 11.4, 11.0, floor + .10)
    fence, pergola, bench = _Mesh(), _Mesh(), _Mesh()
    # Low garden boundary has real entrances through both end rails.
    for sign in (-1, 1):
        xx = x + sign * 5.5
        for n in range(8):
            yy = y - 5.05 + n * 10.1 / 7
            fence.prism((xx, yy, floor + .57), (.18, .18, 1.14))
        for zz in (.31, .83):
            fence.prism((xx, y, floor + zz), (.13, 10.3, .13))
        for yy in (y - 5.35, y + 5.35):
            fence.prism((x + sign * 3.62, yy, floor + .57), (3.58, .14, .14))
            for dx in (2.0, 3.8, 5.3):
                fence.prism((x + sign * dx, yy, floor + .50), (.15, .15, 1.0))
    builder.emit(name + '_low_open_cedar_fence', fence, 'wood_light')
    # A cool north-facing pergola shades a seat and the shared seed table.
    py = y + 3.0
    for dx in (-3.25, 3.25):
        for dy in (-1.55, 1.55):
            pergola.prism((x + dx, py + dy, floor + 1.93), (.27, .27, 3.86))
            pergola.beam((x + dx, py + dy, floor + 2.96),
                          (x + dx - (.76 if dx > 0 else -.76), py + dy, floor + 3.76), .18)
    for dy in (-1.68, 1.68):
        pergola.prism((x, py + dy, floor + 3.90), (7.4, .25, .29))
    for n in range(9):
        pergola.prism((x - 3.35 + n * .8375, py, floor + 4.08), (.20, 4.05, .23))
    builder.emit(name + '_real_pergola_posts_rafters_and_braces', pergola, 'wood')
    # Seat stays on the western wall, leaving the middle corridor playable.
    bench.prism((x - 1.95, py + .84, floor + .88), (2.45, .71, .22))
    bench.prism((x - 1.95, py + 1.11, floor + 1.29), (2.45, .16, .77))
    for dx in (-.87, .87):
        bench.prism((x - 1.95 + dx, py + .84, floor + .43), (.22, .47, .86))
    bench.prism((x + 1.85, py + .79, floor + 1.14), (1.8, 1.0, .21))
    for dx in (-.65, .65):
        bench.prism((x + 1.85 + dx, py + .79, floor + .56), (.18, .73, 1.12))
    builder.emit(name + '_gardener_bench_and_seed_table', bench, 'wood_light')
    # Original Sunleaf catcher: five gilded botanical blades on a real frame.
    fan, stems = _Mesh(), _Mesh()
    origin = (x, py - 1.69, floor + 4.10)
    for n in range(5):
        angle = .22 + n * (pi - .44) / 4
        reach = 2.35 if n in (1, 3) else 2.05
        ex, ez = cos(angle) * reach, sin(angle) * reach
        mid_x, mid_z = ex * .59, ez * .59
        half = .36 if n != 2 else .43
        outline = [(0, 0), (mid_x - sin(angle) * half, mid_z + cos(angle) * half),
                   (ex, ez), (mid_x + sin(angle) * half, mid_z - cos(angle) * half)]
        verts = [(origin[0] + dx, origin[1] + dy, origin[2] + dz)
                 for dy in (-.075, .075) for dx, dz in outline]
        fan.shell(verts, ((3, 2, 1, 0), (4, 5, 6, 7),
                          (1, 5, 4, 0), (2, 6, 5, 1), (3, 7, 6, 2), (0, 4, 7, 3)))
        stems.beam((origin[0], origin[1] -.11, origin[2]),
                    (origin[0] + ex * .86, origin[1] -.11, origin[2] + ez * .86), .055)
    builder.emit(name + '_five_gilded_sunleaf_blades', fan, 'leaf_gold')
    builder.emit(name + '_sunleaf_stems_and_seams', stems, 'brass')
    # Raised herbs read as garden beds, not scattered decorative dots.
    for side in (-1, 1):
        for row in range(2):
            bx, by = x + side * 3.85, y - .9 - row * 2.85
            bed_name = name + '_herb_bed_' + str(side) + '_' + str(row)
            _planter(builder, bed_name, bx, by, 2.35, 2.0, floor,
                      'flower_lavender' if row == 0 else 'flower_ivory')
            for n in range(2):
                builder.sphere(bed_name + '_rounded_medicinal_sage_' + str(n),
                               (bx - .49 + n * .98, by + .42, floor + 1.08),
                               (.58, .45, .43), 'leaf_sage', 10, 6)
    builder.steps(name + '_north_gate', (x, y + 5.6), 3.3, 3.0, floor, (0, 1))
    builder.steps(name + '_south_gate', (x, y - 5.6), 3.3, 2.4, floor, (0, -1))
    builder.route(name + '_pond_garden_spur', ((x, y + 8.6), (-42, -33), (-43, -20)), 2.7)
    _lantern(builder, name + '_garden_lantern', x + 5.35, y + 5.25, floor)
    builder.placements.append({'name': name, 'center_xy': [x, y], 'floor_z': floor,
                               'footprint_m': [11.4, 11.0],
                               'style': 'raised_medicinal_garden_and_sunleaf_pergola',
                               'entrance_xy': [x, y + 8.6]})


def build_architecture(api, terrain, variant='hero'):
    """Build one owned island's original architecture and connected village routes.

    ``hero`` is the copper/ivory Lumenwake destination. ``template`` and
    ``riverjoin`` select Riverjoin Commons, a lower, repeatable working island.
    Each return placement names a real scene assembly; all geometry is retained
    in ``objects`` for the root generator to assign collections or export layers.
    """
    if variant not in ('hero', 'template', 'riverjoin', 'RiverjoinCommons'):
        raise ValueError('Unknown architecture variant: ' + str(variant))
    builder = _Builder(api, terrain, 'LW_' if variant == 'hero' else 'RC_')
    if variant == 'hero':
        landmark_entrance = _observatory(builder)
        atelier_floor, atelier_entrance = _cottage(
            builder, 'Tideglass_Atelier', (35.0, -42.0), 13.8, 10.0, 'atelier', 'roof')
        _atelier_annex(builder, (35.0, -42.0), atelier_floor)
        workshop_floor, workshop_entrance = _cottage(
            builder, 'The_Lanternwright', (58.0, -30.0), 12.7, 11.0, 'workshop', 'roof_dark')
        _workshop_yard(builder, 58.0, -30.0, workshop_floor)
        home_floor, home_entrance = _cottage(
            builder, 'Sunpetal_House', (45.0, -62.0), 10.8, 9.0, 'home', 'roof_dark')
        _round_turret(builder, 'Sunpetal_House', (37.2, -60.0), home_floor)
        _market(builder, 33.5, -22.0)
        builder.route('Observatory_to_Lanterncourt',
                       (landmark_entrance, (-35.5, 29.5), (-45, 24), (-50, 17),
                        (-42, 13), (-32, 16), (-17, 15), (-3, 11), (13, 0),
                        (24, -11), (33.5, -13.45)), 3.6, minimum_z=10.24)
        builder.route('Lanterncourt_to_Atelier',
                       ((33.5, -30.55), (24.7, -35), (24.7, -49), atelier_entrance), 3.0)
        builder.route('Lanterncourt_to_Lanternwright',
                       ((43.35, -22), (48, -22), (66.5, -24), (68.2, -38), workshop_entrance), 3.0)
        builder.route('Village_to_Sunpetal',
                       (atelier_entrance, (29.0, -53), (27.0, -70), home_entrance), 3.0)
        builder.route('Sunpetal_to_Lanternwright',
                       (home_entrance, (61, -74), (69, -58), (68.2, -38)), 3.0)
        _planter(builder, 'Lanterncourt_Coral_Garden', 23.7, -26.4, 4.3, 1.9)
        _planter(builder, 'Lanterncourt_Ivory_Garden', 22.2, -17.5, 3.6, 1.7, flowers='flower_ivory')
        _sunleaf_garden(builder)
        bounds = [-50, -78, 73, 65]
    else:
        tug_entrance = _boathouse(builder)
        cottage_floor, cottage_entrance = _cottage(
            builder, 'Riverjoin_Orchardkeeper', (-38.0, 30.0), 12.2, 9.5, 'home', 'roof')
        _round_turret(builder, 'Riverjoin_Orchardkeeper', (-45.8, 31.7), cottage_floor)
        _cistern(builder, (-25.0, 38.0))
        builder.route('Riverjoin_Commons_Crossing',
                       (cottage_entrance, (-38, 14), (-19, 4), (1, -1), (21, -16), (27, -33),
                        (27, -49), tug_entrance), 3.5)
        builder.route('Riverjoin_Cistern_Link', ((-38, 24), (-27, 27), (-25, 33)), 2.4)
        # Exterior sockets and their long piers belong to the scene owner.
        # These explicit route mouths provide real common-ground endpoints.
        builder.route('Riverjoin_West_Plot_Route', ((-101, 0), (-78, 0), (-59, 7), (-38, 14)), 4.0)
        builder.route('Riverjoin_East_Plot_Route', ((101, 0), (79, 0), (60, -9), (21, -16)), 4.0)
        _planter(builder, 'Riverjoin_Orchard_Terrace', -49.0, 20.0, 4.9, 2.1,
                  flowers='flower_ivory')
        _planter(builder, 'Riverjoin_Working_Coral_Garden', 25.0, -52.0, 4.0, 1.8)
        bounds = [-104, -58, 104, 45]
    return {'objects': builder.objects, 'placements': builder.placements,
            'routes': builder.routes, 'bounds_xy': bounds,
            'variant': variant, 'central_pond_clearance_xy': [-15, -12]}
