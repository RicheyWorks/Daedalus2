"""Per-island seeded flora layer (board #1 support).
token_id -> deterministic island ecology profile -> ecology_rules layout.
Each island gets its own disturbance age (succession stage), stream course and seed,
so the flora mix differs per token but obeys the same ecological rules."""
import hashlib, math, random
import ecology_rules as er

def profile(token_id):
    h = int(hashlib.sha256(f"daedalus-island-{token_id}".encode()).hexdigest(), 16)
    r = random.Random(h)
    years = round(math.exp(r.uniform(math.log(3), math.log(250))), 1)  # log-uniform: young scrub .. old forest
    a = r.uniform(0, math.pi)                                          # stream bearing
    off = r.uniform(-25, 25)
    cx, cy = 50 + off * math.cos(a + math.pi / 2), 50 + off * math.sin(a + math.pi / 2)
    stream = [(cx + t * math.cos(a) + 4 * math.sin(t / 9), cy + t * math.sin(a)) for t in range(-70, 71, 5)]
    gaps = [(r.uniform(10, 90), r.uniform(10, 90), r.uniform(6, 14), round(r.uniform(1, 12), 1)) for _ in range(r.randint(0, 2))]
    return {"token": token_id, "seed": h % 2**31, "years": years, "stream": stream, "gaps": gaps}

def generate(token_id, **kw):
    p = profile(token_id)
    old, oldg = er.STREAM_POINTS, list(er.DISTURBANCES)
    er.STREAM_POINTS = p["stream"]; er.DISTURBANCES[:] = p["gaps"]
    try:
        out = er.generate(seed=p["seed"], years=p["years"], **kw)
    finally:
        er.STREAM_POINTS = old; er.DISTURBANCES[:] = oldg
    return p, out

def mix(placed):
    c = {}
    for q in placed:
        n = q["species"] if isinstance(q, dict) else q[0]
        c[n] = c.get(n, 0) + 1
    return c

if __name__ == "__main__":
    ok = True
    profs = [profile(t) for t in range(1, 6)]
    ok &= profile(3) == profile(3)
    ok &= len({p["years"] for p in profs}) == 5
    mixes = []
    for t in (1, 2, 3):
        p, out = generate(t)
        placed = out[0] if isinstance(out, tuple) else out
        m = mix(placed); mixes.append(m)
        print(f"token {t}: years={p['years']} n={len(placed)} {m}")
    ok &= mixes[0] != mixes[1] != mixes[2]
    print("PASS" if ok else "FAIL")

