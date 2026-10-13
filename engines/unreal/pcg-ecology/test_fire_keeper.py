from fire_keeper import fire_regime, best_rate
def test_no_fire_is_monoculture(): assert fire_regime(0.0) == 0.0
def test_hump_shape():
    lo, mid, hi = fire_regime(0.005), fire_regime(0.03), fire_regime(0.32)
    assert mid > lo and mid > hi
def test_best_rate_is_intermediate():
    for s in range(3): assert 0.01 <= best_rate(seed=s) <= 0.08
