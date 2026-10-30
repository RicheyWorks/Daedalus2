# SPDX-License-Identifier: MIT
"""G581 DiskSaver seed and draw spec: golden draw sequences and a pure-Python reference.

docs/islands/DISKSAVER-SEED-SPEC.md describes how the DiskSaver tools seed Python's random.Random
and which draws they make, so their seeded layouts can be reproduced outside Python. This script
backs that spec:

* SpecRandom is a pure-Python implementation of the spec (MT19937 init_by_array, genrand,
  random(), getrandbits, _randbelow, randrange, randint, choice, shuffle, sample). It never calls
  the random module. Every golden line is checked against both CPython's random.Random and SpecRandom.
* The golden file engines/unreal/core-test/disksaver_seed_spec_parity.txt holds the draw sequences.
  Spec cases use small, big and negative seeds. Tool cases record the first draws of every DiskSaver
  tool that uses random, on the real tools/world_census fixtures and the shipped configs.
  The tools are run unchanged; only this script swaps a recording random.Random into their module
  while it runs.

  python tools/streaming/disksaver_seed_spec.py            # print the golden file
  python tools/streaming/disksaver_seed_spec.py --check    # exit 1 if the checked-in file is stale
  python tools/streaming/disksaver_seed_spec.py --write    # rewrite it

Golden lines: `C name` starts a case, `K hex` is the sha256 key bytes (tool cases), `S n` is the
integer passed to random.Random (hex, with a leading '-' when negative), then pairs of `D op args`
and `O result`. Ops: u32 (getrandbits(32)), random (the 53-bit integer a*2^26+b behind random()),
bits k, below n (_randbelow), range a b step, int a b, choice n (the index), shuffle n (the
permutation of range(n)), sample n k (the indices), skip m (m u32 draws, result = the last one).
An argument that Python refuses gives `O error <ExceptionName>` and draws nothing.
"""
import dataclasses
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import census_budget as cb  # noqa: E402

ROOT = cb.ROOT
GOLDEN = os.path.join(ROOT, "engines", "unreal", "core-test", "disksaver_seed_spec_parity.txt")
TRACE_CAP = 400  # draws recorded per tool case (a prefix of the tool's full sequence)
M32 = 0xFFFFFFFF


# ---------------------------------------------------------------- reference implementation (no random module)
class SpecRandom:
    """The spec in plain Python: CPython's random.Random for int seeds, as DiskSaver uses it."""

    N, M = 624, 397

    def __init__(self, seed):
        n = abs(seed)
        key = []
        while n:
            key.append(n & M32)
            n >>= 32
        self.words = 0
        self._init_by_array(key or [0])

    def _init_genrand(self, s):
        mt = [0] * self.N
        mt[0] = s
        for i in range(1, self.N):
            mt[i] = (1812433253 * (mt[i - 1] ^ (mt[i - 1] >> 30)) + i) & M32
        self.mt, self.mti = mt, self.N

    def _init_by_array(self, key):
        self._init_genrand(19650218)
        mt, i, j = self.mt, 1, 0
        for _ in range(max(self.N, len(key))):
            mt[i] = ((mt[i] ^ ((mt[i - 1] ^ (mt[i - 1] >> 30)) * 1664525)) + key[j] + j) & M32
            i, j = i + 1, j + 1
            if i >= self.N:
                mt[0], i = mt[self.N - 1], 1
            if j >= len(key):
                j = 0
        for _ in range(self.N - 1):
            mt[i] = ((mt[i] ^ ((mt[i - 1] ^ (mt[i - 1] >> 30)) * 1566083941)) - i) & M32
            i += 1
            if i >= self.N:
                mt[0], i = mt[self.N - 1], 1
        mt[0] = 0x80000000

    def u32(self):
        mt = self.mt
        if self.mti >= self.N:
            for k in range(self.N):
                y = (mt[k] & 0x80000000) | (mt[(k + 1) % self.N] & 0x7FFFFFFF)
                mt[k] = mt[(k + self.M) % self.N] ^ (y >> 1) ^ (0x9908B0DF if y & 1 else 0)
            self.mti = 0
        y = mt[self.mti]
        self.mti += 1
        y ^= y >> 11
        y ^= (y << 7) & 0x9D2C5680
        y ^= (y << 15) & 0xEFC60000
        y ^= y >> 18
        self.words += 1
        return y

    def random53(self):
        a, b = self.u32() >> 5, self.u32() >> 6
        return a * 67108864 + b  # random() == this / 2**53

    def random(self):
        return self.random53() / 9007199254740992.0

    def getrandbits(self, k):
        if k < 0:
            raise ValueError("number of bits must be non-negative")
        if k == 0:
            return 0
        if k <= 32:
            return self.u32() >> (32 - k)
        r, shift = 0, 0
        while k > 0:
            w = self.u32()
            if k < 32:
                w >>= 32 - k
            r |= w << shift
            shift += 32
            k -= 32
        return r

    def randbelow(self, n):
        if n <= 0:
            raise ValueError("randbelow needs n > 0")  # CPython's _randbelow(0) never returns; callers guard
        k = n.bit_length()
        r = self.getrandbits(k)
        while r >= n:
            r = self.getrandbits(k)
        return r

    def randrange(self, start, stop=None, step=1):
        if stop is None:
            if start > 0:
                return self.randbelow(start)
            raise ValueError("empty range for randrange()")
        width = stop - start
        if step == 1:
            if width > 0:
                return start + self.randbelow(width)
            raise ValueError("empty range for randrange()")
        if step > 0:
            n = (width + step - 1) // step
        elif step < 0:
            n = (width + step + 1) // step
        else:
            raise ValueError("zero step for randrange()")
        if n <= 0:
            raise ValueError("empty range for randrange()")
        return start + step * self.randbelow(n)

    def randint(self, a, b):
        return self.randrange(a, b + 1)

    def choice_index(self, n):
        if n <= 0:
            raise IndexError("Cannot choose from an empty sequence")
        return self.randbelow(n)

    def shuffle_perm(self, n):
        x = list(range(n))
        for i in range(n - 1, 0, -1):
            j = self.randbelow(i + 1)
            x[i], x[j] = x[j], x[i]
        return x

    @staticmethod
    def setsize(k):
        s = 21
        if k > 5:
            p = 1
            while p < 3 * k:
                p *= 4
            s += p  # == 4 ** ceil(log(3k, 4)): 3k is never a power of 4
        return s

    def sample_indices(self, n, k):
        if not 0 <= k <= n:
            raise ValueError("Sample larger than population or is negative")
        out = [0] * k
        if n <= self.setsize(k):
            pool = list(range(n))
            for i in range(k):
                j = self.randbelow(n - i)
                out[i] = pool[j]
                pool[j] = pool[n - i - 1]
        else:
            seen = set()
            for i in range(k):
                j = self.randbelow(n)
                while j in seen:
                    j = self.randbelow(n)
                seen.add(j)
                out[i] = j
        return out


# ---------------------------------------------------------------- ops on either generator
def run_op(r, op, a, spec):
    """Result text of one op on random.Random (spec=False) or SpecRandom (spec=True)."""
    try:
        if op == "u32":
            v = r.u32() if spec else r.getrandbits(32)
        elif op == "random":
            v = r.random53() if spec else int(r.random() * 9007199254740992)
        elif op == "bits":
            v = r.getrandbits(a[0])
        elif op == "below":
            if a[0] <= 0:
                raise ValueError("below")  # never sent to CPython: its _randbelow(0) loops forever
            v = r.randbelow(a[0]) if spec else r._randbelow(a[0])
        elif op == "range":
            v = r.randrange(a[0], a[1], a[2])
        elif op == "int":
            v = r.randint(a[0], a[1])
        elif op == "choice":
            v = r.choice_index(a[0]) if spec else r.choice(range(a[0]))
        elif op == "shuffle":
            if spec:
                v = r.shuffle_perm(a[0])
            else:
                v = list(range(a[0]))
                r.shuffle(v)
        elif op == "sample":
            v = r.sample_indices(a[0], a[1]) if spec else r.sample(range(a[0]), a[1])
        elif op == "skip":
            v = 0
            for _ in range(a[0]):
                v = r.u32() if spec else r.getrandbits(32)
        else:
            raise AssertionError(op)
    except (ValueError, IndexError) as e:
        return "error " + type(e).__name__
    return " ".join(map(str, v)) if isinstance(v, list) else str(v)


def seed_text(s):
    return ("-" if s < 0 else "") + format(abs(s), "x")


# ---------------------------------------------------------------- recording Random for the tools
class _Rec(random.Random):
    """random.Random that logs each top-level call as an op; results are exactly what the tool gets."""

    last = None

    def __init__(self, x=None):
        super().__init__(x)
        self.seed_int, self.ops, self.depth = x, [], 0
        _Rec.last = self

    def _log(self, op, args, res):
        if not self.depth:
            self.ops.append((op, args, res))

    def getrandbits(self, k):
        # Overriding random() alone would make Random.__init_subclass__ switch _randbelow to the
        # float-based _randbelow_without_getrandbits; overriding getrandbits too keeps CPython's path.
        return super().getrandbits(k)

    def random(self):
        v = super().random()
        self._log("random", (), str(int(v * 9007199254740992)))
        return v

    def randrange(self, start, stop=None, step=1):
        self.depth += 1
        try:
            v = super().randrange(start, stop, step)
        finally:
            self.depth -= 1
        self._log("range", (0, start, 1) if stop is None else (start, stop, step), str(v))
        return v

    def randint(self, a, b):
        self.depth += 1
        try:
            v = super().randint(a, b)
        finally:
            self.depth -= 1
        self._log("int", (a, b), str(v))
        return v

    def choice(self, seq):
        self.depth += 1
        try:
            i = super().choice(range(len(seq)))
        finally:
            self.depth -= 1
        self._log("choice", (len(seq),), str(i))
        return seq[i]

    def shuffle(self, x):
        self.depth += 1
        try:
            p = list(range(len(x)))
            super().shuffle(p)
        finally:
            self.depth -= 1
        old = list(x)
        x[:] = [old[i] for i in p]
        self._log("shuffle", (len(x),), " ".join(map(str, p)))

    def sample(self, population, k):
        self.depth += 1
        try:
            idx = super().sample(range(len(population)), k)
        finally:
            self.depth -= 1
        pop = list(population)
        self._log("sample", (len(pop), k), " ".join(map(str, idx)))
        return [pop[i] for i in idx]


def traced(mod, fn):
    """(seed int, ops) of the random.Random the tool builds inside fn(); the tool runs unchanged."""
    saved = mod.random
    mod.random = types.SimpleNamespace(Random=_Rec)
    _Rec.last = None
    try:
        fn()
    finally:
        mod.random = saved
    return _Rec.last.seed_int, _Rec.last.ops


# ---------------------------------------------------------------- cases
SPEC_OPS = ([("u32", ())] * 6 + [("random", ())] * 3 +
            [("bits", (k,)) for k in (0, 1, 7, 31, 32, 33, 53, 64)] +
            [("below", (n,)) for n in (1, 2, 3, 5, 26, 1000, 2 ** 31, 2 ** 31 + 1, 2 ** 32 - 1, 2 ** 32, 10 ** 12, 2 ** 63 - 1)] +
            [("range", r) for r in ((0, 10, 1), (-5, 5, 1), (0, 100, 7), (100, 0, -7), (-2 ** 61, 2 ** 61, 1), (3, 3, 1), (0, 10, 0), (5, 0, 1))] +
            [("int", r) for r in ((0, 0), (-25, 25), (1, 3), (0, 255), (3, 2))] +
            [("choice", (n,)) for n in (1, 4, 26, 0)] +
            [("shuffle", (n,)) for n in (0, 1, 2, 6, 26)] +
            [("sample", s) for s in ((5, 0), (5, 5), (40, 5), (40, 6), (21, 2), (22, 2), (84, 6), (85, 6), (86, 6), (1000, 12), (3, 4))] +
            [("skip", (620,))] + [("u32", ())] * 6 + [("random", ())] * 2)

SPEC_SEEDS = (0, 1, 7, 42, -42, 2 ** 31 - 1, 2 ** 32 - 1, 2 ** 32, 2 ** 64 - 1, 10 ** 30, 2 ** 255 + 12345,
              2 ** 256 - 1, 2 ** (32 * 700) - 3)


def real_census():
    """The real tools/world_census census, built the same way disksaver_cpp_parity.py builds it."""
    fix = os.path.join(ROOT, "tools", "world_census", "fixtures")
    with tempfile.TemporaryDirectory() as t:
        out = os.path.join(t, "c")
        subprocess.run([sys.executable, "-B", "-m", "tools.world_census", os.path.join(fix, "alpha.json"),
                        os.path.join(fix, "beta.json"), "--snapshot-date", "2026-10-26", "--bindings",
                        os.path.join(fix, "bindings.json"), "--output-dir", out], cwd=ROOT, check=True,
                       capture_output=True)
        with open(os.path.join(out, "census.json"), encoding="utf-8") as f:
            return json.load(f)


def _census(date, worlds):
    return {"format": "daedalus-world-census", "version": 1, "count_semantics": "asset-definitions", "snapshot_date": date,
            "worlds": [{"id": w, "islands": [{"slot": sl, "asset_definitions": n} for sl, n in isl]} for w, isl in worlds]}


# synthetic censuses: 7 islands (every tool lays them out) and 14 (tools with a smaller cap refuse and are skipped)
SYN = {"syn7": _census("2026-10-29", [("north", [(1, 3), (2, 40), (5, 7)]), ("south", [(0, 12), (3, 90)]), ("west", [(0, 0), (8, 5)])]),
       "syn14": _census("2026-10-30", [("big", [(i, (i * 37) % 101) for i in range(9)]), ("east", [(i, 10 * i + 1) for i in range(5)])])}


def tool_cases():
    """[(name, key bytes or None, mod, fn)] for every DiskSaver tool that draws from random."""
    import belfry_changes as bch, boom_defence as bd, bottle_census as bcs, census_riddles as cr  # noqa: E401
    import channel_dash as cd, fleet_soundings as fs, harbour_cryptogram as hc, last_crate as lc  # noqa: E401
    import lighthouse_leases as ll, manifest_match as mm, quay_duel as qd, quayside_shove as qs  # noqa: E401
    import rope_run as rr, sack_chute as sc, salvage_sale as ss, seal_roll as sr, smugglers_island as si  # noqa: E401
    import tide_clocks as tc, tide_lock as tl, tidemark_chunks as tm, tram_shunt as ts  # noqa: E401
    import twin_pilots as tp, watchfires as wf  # noqa: E401
    doc = real_census()
    with open(cb.DEFAULT_CONFIG, encoding="utf-8-sig") as f:
        bcfg = json.load(f)
    layout = [("census_riddles", cr, lambda s, d: cr.draw(d, bcfg, s, 5)), ("last_crate", lc, lambda s, d: lc.stack(d, s)),
              ("quay_duel", qd, lambda s, d: qd.quay(d, s)), ("fleet_soundings", fs, lambda s, d: fs.generate(d, s)),
              ("harbour_cryptogram", hc, lambda s, d: hc.make(d, s)), ("smugglers_island", si, lambda s, d: si.setup(d, s)),
              ("tide_lock", tl, lambda s, d: tl.boats(d, s)), ("watchfires", wf, lambda s, d: wf.chart(d, s)),
              ("manifest_match", mm, lambda s, d: mm.layout(d, s)), ("twin_pilots", tp, lambda s, d: tp.chart(d, s)),
              ("quayside_shove", qs, lambda s, d: qs.yard(d, s)), ("sack_chute", sc, lambda s, d: sc.chute(d, s)),
              ("seal_roll", sr, lambda s, d: sr.quay(d, s)), ("channel_dash", cd, lambda s, d: cd.lanes_for(d, s)),
              ("boom_defence", bd, lambda s, d: bd.chart(d, s)), ("salvage_sale", ss, lambda s, d: ss.sale(d, s)),
              ("rope_run", rr, lambda s, d: rr.quay(d, s)), ("belfry_changes", bch, lambda s, d: bch.ring(d, s)),
              ("tram_shunt", ts, lambda s, d: ts.train(d, s))]
    out = []
    for name, mod, fn in layout:
        for s in (0, 1, 7, 42, -3):
            out.append((f"{name}_seed{s}", mod, lambda fn=fn, s=s: fn(s, doc), True))
        for cname, cdoc in SYN.items():
            for s in (0, 42):
                out.append((f"{name}_{cname}_seed{s}", mod, lambda fn=fn, s=s, d=cdoc: fn(s, d), True))

    def cfg(rel):
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            return json.load(f)
    sims = [("tide_clocks", tc, "tide-clocks-v1.json", lambda c: tc.run(c)),
            ("lighthouse_leases", ll, "lighthouse-leases-v1.json", lambda c: ll.run(c)),
            ("tidemark_chunks", tm, "tidemark-chunks-v1.json", lambda c: tm.saves(c)),
            ("bottle_census", bcs, "bottle-census-v1.json", lambda c: bcs.run(c))]
    for name, mod, rel, fn in sims:
        real = mod.validate(cfg("data/islands/disk-saver/" + rel))
        for s in sorted({real.seed, 1, 7, 42}):
            c = dataclasses.replace(real, seed=s)
            out.append((f"{name}_seed{s}", mod, lambda fn=fn, c=c: fn(c), False))
    return out


def key_for(mod, fn):
    """The sha256 key bytes a layout tool hashes: captured from hashlib.sha256 while fn() runs."""
    seen = []
    real = mod.hashlib
    mod.hashlib = types.SimpleNamespace(sha256=lambda b=b"": (seen.append(bytes(b)), real.sha256(b))[1])
    try:
        traced(mod, fn)
    finally:
        mod.hashlib = real
    return seen[0]


def check_line(rng, spec, op, args, want):
    got_py, got_spec = run_op(rng, op, args, False), run_op(spec, op, args, True)
    if not got_py == got_spec == want:
        raise AssertionError(f"{op} {args}: python {got_py!r} spec {got_spec!r} recorded {want!r}")


def lines():
    out = ["# disksaver seed spec v1: written by tools/streaming/disksaver_seed_spec.py; do not edit",
           "# spec: docs/islands/DISKSAVER-SEED-SPEC.md"]
    for k in range(6, 100001):  # the integer setsize form equals CPython's float log form
        assert SpecRandom.setsize(k) == 21 + 4 ** math.ceil(math.log(k * 3, 4)), k
    for s in SPEC_SEEDS:
        out += [f"C spec_seed_{seed_text(s)[:24]}", f"S {seed_text(s)}"]
        rng, spec = random.Random(s), SpecRandom(s)
        for op, args in SPEC_OPS:
            want = run_op(rng, op, args, False)
            got = run_op(spec, op, args, True)
            assert got == want, (s, op, args, got, want)
            out += ["D " + " ".join([op] + [str(a) for a in args]), "O " + want]
    for name, mod, fn, keyed in tool_cases():
        try:
            seed, ops = traced(mod, fn)
        except Exception as e:  # a synthetic census over the tool's own cap: the tool refuses before seeding
            if type(e).__module__ == mod.__name__ and _Rec.last is None:
                continue
            raise
        out.append(f"C tool_{name}")
        if keyed:
            key = key_for(mod, fn)
            assert int(hashlib.sha256(key).hexdigest(), 16) == seed, name
            out.append("K " + key.hex())
        out.append(f"S {seed_text(seed)}")
        out.append(f"# {len(ops)} draws; {min(len(ops), TRACE_CAP)} recorded")
        rng, spec = random.Random(seed), SpecRandom(seed)
        for op, args, res in ops[:TRACE_CAP]:
            check_line(rng, spec, op, args, res)
            out += ["D " + " ".join([op] + [str(a) for a in args]), "O " + res]
    return out


def main(argv):
    text = "\n".join(lines()) + "\n"
    if "--write" in argv:
        with open(GOLDEN, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return 0
    if "--check" in argv:
        try:
            with open(GOLDEN, encoding="utf-8") as f:
                ok = f.read() == text
        except OSError:
            ok = False
        print("disksaver seed spec " + ("up to date" if ok else "STALE (rerun --write)"))
        return 0 if ok else 1
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
