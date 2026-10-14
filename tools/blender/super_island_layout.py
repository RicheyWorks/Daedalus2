"""Geometry-only layouts for four or more distinct connected island plots.

No Blender dependency or import-time operations. Plot labels remain unchanged;
they describe authoring members and do not allocate deeds or authorize a tug.
Coordinates are metres: east=X, north=Y, up=Z. Plot roots have Z=0, while
connection decks share the supplied datum. The default four-member layout puts
roots at (+/-128, +/-128, 0) with 16 m connector spans.
"""

import math
from numbers import Real


SCHEMA = "daedalus.super-island.authoring/v1"
MINIMUM_PLOTS = 4
WALK_WIDTH_M = 8.0
_SOCKETS = (
    ("E", 1, 0),
    ("N", 0, 1),
    ("W", -1, 0),
    ("S", 0, -1),
)


def _members(plot_ids, minimum=MINIMUM_PLOTS):
    if isinstance(plot_ids, (str, bytes)):
        raise ValueError("plot_ids must be an iterable of distinct plot labels")
    try:
        members = list(plot_ids)
    except TypeError as error:
        raise ValueError("plot_ids must be an iterable of plot labels") from error
    if len(members) < minimum:
        if minimum == MINIMUM_PLOTS:
            raise ValueError("a Super Island requires four or more distinct plots")
        raise ValueError("an island group requires at least one distinct plot")
    for member in members:
        if not isinstance(member, str) or not member or member != member.strip():
            raise ValueError("each plot label must be a nonblank string without edge whitespace")
        if any(ord(character) < 32 for character in member):
            raise ValueError("plot labels must not contain control characters")
    if len(set(members)) != len(members):
        raise ValueError("an island group cannot repeat a plot label")
    return members


def is_super_island(plot_ids):
    """Return whether distinct members meet the four-island count threshold.

    One island and ordinary two/three-island groups return False. This is a
    count predicate only: the caller must separately establish connectivity.
    Label validation is the same as for layouts; no member identity is changed.
    """
    return len(_members(plot_ids, minimum=1)) >= MINIMUM_PLOTS


def _finite(name, value):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(name + " must be a finite real number")
    try:
        result = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(name + " must be a finite real number") from error
    if not math.isfinite(result):
        raise ValueError(name + " must be a finite real number")
    return result


def _profile(pitch, span, datum):
    pitch = _finite("pitch", pitch)
    span = _finite("span", span)
    datum = _finite("datum", datum)
    if pitch <= 0:
        raise ValueError("pitch must be positive")
    if span < WALK_WIDTH_M or span >= pitch:
        raise ValueError("span must fit an 8 m walkway and be smaller than pitch")
    return pitch, span, datum


def _cells(cells, count):
    if isinstance(cells, (str, bytes)):
        raise ValueError("cells must contain one integer (east, north) pair per plot")
    try:
        supplied = list(cells)
    except TypeError as error:
        raise ValueError("cells must contain integer (east, north) pairs") from error
    if len(supplied) != count:
        raise ValueError("cells must contain exactly one pair per plot")
    positions = []
    for cell in supplied:
        if not isinstance(cell, (list, tuple)) or len(cell) != 2:
            raise ValueError("each cell must be an integer (east, north) pair")
        if any(isinstance(axis, bool) or not isinstance(axis, int) for axis in cell):
            raise ValueError("cell coordinates must be integers")
        positions.append(tuple(cell))
    if len(set(positions)) != count:
        raise ValueError("two distinct plots cannot occupy the same authoring cell")
    return positions


def _measure(value, pitch):
    try:
        result = float(value) * pitch
    except (OverflowError, ValueError) as error:
        raise ValueError("the supplied cell extent exceeds finite authoring coordinates") from error
    if not math.isfinite(result):
        raise ValueError("the supplied cell extent exceeds finite authoring coordinates")
    return result


def _point(east, north, up):
    result = [float(east), float(north), float(up)]
    if not all(math.isfinite(axis) for axis in result):
        raise ValueError("layout would produce a nonfinite coordinate")
    return result


def _layout(members, cells, pitch, span, datum):
    lookup = {cell: index for index, cell in enumerate(cells)}
    adjacency = {member: [] for member in members}
    edges = []
    for index, (east, north) in enumerate(cells):
        # East/north only: every undirected cardinal edge occurs exactly once.
        for from_side, to_side, dx, dy in (("E", "W", 1, 0), ("N", "S", 0, 1)):
            other = lookup.get((east + dx, north + dy))
            if other is None:
                continue
            edges.append((index, other, from_side, to_side, dx, dy))
            adjacency[members[index]].append(members[other])
            adjacency[members[other]].append(members[index])

    visited = set()
    pending = [members[0]]
    while pending:
        member = pending.pop()
        if member in visited:
            continue
        visited.add(member)
        pending.extend(neighbour for neighbour in adjacency[member] if neighbour not in visited)
    if len(visited) != len(members):
        raise ValueError("all Super Island plots must belong to one connected cardinal graph")

    minimum_east = min(cell[0] for cell in cells)
    maximum_east = max(cell[0] for cell in cells)
    minimum_north = min(cell[1] for cell in cells)
    maximum_north = max(cell[1] for cell in cells)
    east_extent = _measure(maximum_east - minimum_east, pitch)
    north_extent = _measure(maximum_north - minimum_north, pitch)
    cell_width = _finite("cell footprint width", east_extent + pitch)
    cell_depth = _finite("cell footprint depth", north_extent + pitch)
    land_width = _finite("land envelope width", east_extent + span)
    land_depth = _finite("land envelope depth", north_extent + span)
    reach = span / 2.0
    plots = []
    socket_world = {}
    for member, (east, north) in zip(members, cells):
        # Centre the occupied bounding box, including incomplete final rows.
        # Subtract integer minima before conversion to avoid huge common offsets.
        x = _measure(east - minimum_east, pitch) - east_extent / 2.0
        y = _measure(north - minimum_north, pitch) - north_extent / 2.0
        sockets = []
        for side, dx, dy in _SOCKETS:
            local = _point(dx * reach, dy * reach, datum)
            world = _point(x + local[0], y + local[1], datum)
            socket_world[(member, side)] = world
            sockets.append({
                "side": side,
                "position": local,
                "worldPosition": world,
                "outward": [dx, dy, 0],
                "clearWidth": WALK_WIDTH_M,
                "walkwayDatum": datum,
            })
        plots.append({
            "plot": member,
            "cell": [east, north],
            "position": _point(x, y, 0.0),
            "sockets": sockets,
        })

    gap = pitch - span
    connectors = []
    for index, other, from_side, to_side, dx, dy in edges:
        first, second = members[index], members[other]
        start = socket_world[(first, from_side)]
        end = socket_world[(second, to_side)]
        connectors.append({
            "plots": [first, second],
            "sides": [from_side, to_side],
            "start": list(start),
            "end": list(end),
            "position": _point(
                start[0] / 2.0 + end[0] / 2.0,
                start[1] / 2.0 + end[1] / 2.0,
                datum,
            ),
            "direction": [dx, dy, 0],
            "orientation": "east-west" if dx else "north-south",
            "length": gap,
            "gap": gap,
            "walkWidth": WALK_WIDTH_M,
            "kind": "bridge",
        })

    return {
        "schema": SCHEMA,
        "stage": "AUTHORING_GEOMETRY_ONLY",
        "definition": "four or more distinct connected island plots",
        "memberIDs": list(members),
        "plotCount": len(members),
        "pitchMetres": pitch,
        "spanMetres": span,
        "walkwayDatumMetres": datum,
        "walkWidthMetres": WALK_WIDTH_M,
        "socketGapMetres": gap,
        "coordinates": "east-north-up-metres",
        "plots": plots,
        "connectors": connectors,
        "graph": {
            "connected": True,
            "adjacency": adjacency,
            "edgeCount": len(connectors),
        },
        "bounds": {
            "cellFootprintSize": [cell_width, cell_depth],
            "landEnvelopeSize": [land_width, land_depth],
            "minimum": [-land_width / 2.0, -land_depth / 2.0],
            "maximum": [land_width / 2.0, land_depth / 2.0],
        },
    }


def layout_plots(plot_ids, columns=2, pitch=256, span=240, datum=10):
    """Return a centred, connected row-major Super Island authoring layout.

    Labels are retained in input order. The last row can be incomplete; every
    member still connects through cardinal neighbours. Four members with the
    defaults produce roots (-128,-128), (128,-128), (-128,128), (128,128).
    Five/six members fit two columns; nine members can use columns=3.
    Invalid labels, dimensions or column counts raise ValueError.
    """
    members = _members(plot_ids)
    if isinstance(columns, bool) or not isinstance(columns, int) or columns <= 0:
        raise ValueError("columns must be a positive integer")
    pitch, span, datum = _profile(pitch, span, datum)
    cells = [(index % columns, index // columns) for index in range(len(members))]
    result = _layout(members, cells, pitch, span, datum)
    result["arrangement"] = "row-major"
    result["columns"] = min(columns, len(members))
    result["rows"] = (len(members) + columns - 1) // columns
    return result


def layout_cells(plot_ids, cells, pitch=256, span=240, datum=10):
    """Return a centred layout for explicitly supplied integer authoring cells.

    Cell order corresponds to label order. Duplicate cells and disconnected
    groups raise ValueError. Negative cells are valid local authoring inputs;
    these coordinates neither modify nor validate a live realm placement.
    """
    members = _members(plot_ids)
    pitch, span, datum = _profile(pitch, span, datum)
    positions = _cells(cells, len(members))
    result = _layout(members, positions, pitch, span, datum)
    result["arrangement"] = "manual-cells"
    return result
