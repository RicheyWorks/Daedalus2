# SPDX-License-Identifier: MIT
"""DSB 1 (island streaming budget manifest) in plain Python, a third port of
DaedalusStreamingBudgetCore.h / StreamingBudget.java (ADR-063, disk-saver).
test_dsb.py replays engines/unreal/core-test/streaming_budget_parity.txt through it, so Python = Java = C++.
Integers only; all or nothing; canonical write sorts by id."""
MAX_ISLANDS = 20000
MAX_CM = 1_000_000_000
MAX_KIB = 100_000_000
MAX_LINE = 512
ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")


class DsbError(ValueError):
    pass


def _integer(s, allow_neg, lo, hi):
    i, neg = 0, False
    if allow_neg and s.startswith("-"):
        neg, i = True, 1
    if i >= len(s) or len(s) - i > 12:
        return None
    if s[i] == "0" and len(s) - i > 1:
        return None
    if neg and len(s) - i == 1 and s[i] == "0":
        return None
    if any(c < "0" or c > "9" for c in s[i:]):
        return None
    v = int(s[i:])
    v = -v if neg else v
    return v if lo <= v <= hi else None


def parse(text):
    """Return a list of (id, x, y, ram, disk) in file order, or raise DsbError('line N: why')."""
    lines = text.split("\n")
    header, seen, out = False, set(), []
    for n, raw in enumerate(lines, 1):
        l = raw[:-1] if raw.endswith("\r") else raw
        if len(l) > MAX_LINE:
            raise DsbError(f"line {n}: line too long")
        t = l.replace("\t", " ").split()
        if not t or t[0].startswith("#"):
            continue
        if not header:
            if len(t) == 2 and t[0] == "DSB":
                if t[1] != "1":
                    raise DsbError(f"line {n}: unsupported version {t[1]}")
                header = True
                continue
            raise DsbError(f"line {n}: expected 'DSB 1'")
        if t[0] != "island":
            raise DsbError(f"line {n}: unknown record {t[0]}")
        if len(t) != 10 or (t[2], t[4], t[6], t[8]) != ("x", "y", "ram", "disk"):
            raise DsbError(f"line {n}: expected 'island <id> x <cm> y <cm> ram <kib> disk <kib>'")
        iid = t[1]
        if not iid or len(iid) > 64 or any(c not in ID_CHARS for c in iid):
            raise DsbError(f"line {n}: bad island id")
        if iid in seen:
            raise DsbError(f"line {n}: duplicate island {iid}")
        seen.add(iid)
        x = _integer(t[3], True, -MAX_CM, MAX_CM)
        if x is None:
            raise DsbError(f"line {n}: bad x")
        y = _integer(t[5], True, -MAX_CM, MAX_CM)
        if y is None:
            raise DsbError(f"line {n}: bad y")
        ram = _integer(t[7], False, 1, MAX_KIB)
        if ram is None:
            raise DsbError(f"line {n}: bad ram")
        disk = _integer(t[9], False, 1, MAX_KIB)
        if disk is None:
            raise DsbError(f"line {n}: bad disk")
        if len(out) >= MAX_ISLANDS:
            raise DsbError(f"line {n}: too many islands")
        out.append((iid, x, y, ram, disk))
    if not header:
        raise DsbError("line 1: empty")
    return out


def write(islands):
    """Canonical text: header, islands sorted by id (byte order), single spaces, LF."""
    o = ["DSB 1\n"]
    for iid, x, y, ram, disk in sorted(islands, key=lambda i: i[0].encode()):
        o.append(f"island {iid} x {x} y {y} ram {ram} disk {disk}\n")
    return "".join(o)


def pick(islands, vx, vy, load_cm, unload_cm, ram_budget, was_resident=()):
    """Nearest-first resident set under a RAM budget with load/unload hysteresis. Returns (flags, ram, disk, count)."""
    load2 = load_cm * load_cm
    u = max(load_cm, unload_cm)
    unload2 = u * u
    want = []
    for i, (_, x, y, _, _) in enumerate(islands):
        d = (x - vx) ** 2 + (y - vy) ** 2
        was = i < len(was_resident) and was_resident[i]
        if d <= load2 or (was and d <= unload2):
            want.append((d, i))
    want.sort()
    res = [False] * len(islands)
    ram = disk = count = 0
    for _, i in want:
        if islands[i][3] > ram_budget - ram:
            continue
        res[i] = True
        ram += islands[i][3]
        disk += islands[i][4]
        count += 1
    return res, ram, disk, count


def bits(flags):
    return "".join("1" if f else "0" for f in flags)
