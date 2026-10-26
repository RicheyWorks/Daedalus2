# SPDX-License-Identifier: MIT
"""Place the Prismheart waystones on the demo world map at build time (contest G10, disk-saver).

    place(world, walkable, entries) -> [{"id", "bit", "name", "lore", "near", "x", "y"}]

Each waystone stands one step off the road from its landmark: the landmark's exit tile is the one just south of it
(where the game puts you when you leave), and the waystone goes on the first tile reached from that exit, in a fixed
breadth-first order (east, west, south, north), that is walkable, not a landmark, reachable on foot from the Town,
and not already taken. Deterministic: the same map gives the same spots. Raises ValueError with a reason when a
waystone cannot be placed or the data would not fit the WAY1 save string (see waystones.js)."""
import re
from collections import deque

MAX_BIT = 30
ORDER = ((1, 0), (-1, 0), (0, 1), (0, -1))
ENTERABLE = ("Cave", "Castle", "Shrine", "Town")


def find(world, name):
    return next(((x, y) for y, r in enumerate(world) for x, c in enumerate(r) if c == name), None)


def foot_reach(world, walkable):
    start = find(world, "Town")
    if start is None:
        raise ValueError("world map has no Town")
    seen, q = {start}, deque([start])
    while q:
        x, y = q.popleft()
        for dx, dy in ORDER:
            n = (x + dx, y + dy)
            if 0 <= n[1] < len(world) and 0 <= n[0] < len(world[0]) and n not in seen and (walkable.get(world[n[1]][n[0]]) or world[n[1]][n[0]] in ENTERABLE):
                seen.add(n)
                q.append(n)
    return seen


def validate_entries(entries):
    ids, bits = set(), set()
    for e in entries:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,31}", str(e.get("id", ""))):
            raise ValueError("waystone: bad id %r" % e.get("id"))
        if not isinstance(e.get("bit"), int) or isinstance(e.get("bit"), bool) or not 0 <= e["bit"] <= MAX_BIT:
            raise ValueError("waystone %s: bad bit %r" % (e["id"], e.get("bit")))
        if e["id"] in ids:
            raise ValueError("waystone: duplicate id %s" % e["id"])
        if e["bit"] in bits:
            raise ValueError("waystone: duplicate bit %d" % e["bit"])
        if not e.get("name"):
            raise ValueError("waystone %s: no name" % e["id"])
        ids.add(e["id"])
        bits.add(e["bit"])


def place(world, walkable, entries, landmarks=None, avoid=()):
    validate_entries(entries)
    reach = foot_reach(world, walkable)
    landmarks = set(landmarks or ())
    taken, out = set((int(x), int(y)) for x, y in avoid), []
    h, w = len(world), len(world[0])

    def ok(p):
        x, y = p
        c = world[y][x]
        return p in reach and walkable.get(c) and c not in landmarks and p not in taken

    for e in entries:
        lm = find(world, e["near"])
        if lm is None:
            raise ValueError("waystone %s: landmark %s is not on the world map" % (e["id"], e["near"]))
        exit_ = (lm[0], lm[1] + 1)
        if not (0 <= exit_[1] < h) or exit_ not in reach:
            raise ValueError("waystone %s: %s has no exit reachable on foot" % (e["id"], e["near"]))
        seen, q, spot = {exit_}, deque([exit_]), None
        while q and spot is None:
            x, y = q.popleft()
            for dx, dy in ORDER:
                n = (x + dx, y + dy)
                if 0 <= n[1] < h and 0 <= n[0] < w and n not in seen and n in reach:
                    seen.add(n)
                    if n != exit_ and ok(n):
                        spot = n
                        break
                    q.append(n)
        if spot is None:
            raise ValueError("waystone %s: no free walkable tile near %s" % (e["id"], e["near"]))
        taken.add(spot)
        out.append({"id": e["id"], "bit": e["bit"], "name": e["name"], "lore": e.get("lore", ""), "near": e["near"], "x": spot[0], "y": spot[1]})
    return out
