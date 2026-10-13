from keystone_beaver import outcome, best_dams
GOAL = dict(min_h=1.55, min_old=30)
def ok(o): return o["H"] >= GOAL["min_h"] and o["old_growth"] >= GOAL["min_old"]
def test_no_dams_too_simple(): assert not ok(outcome([]))
def test_dams_by_the_oaks_drown_them(): assert outcome([(2, 8), (4, 8)])["old_growth"] < 30
def test_too_many_dams_fail(): assert not ok(outcome([(7, 6), (10, 6), (9, 2)]))
def test_two_well_placed_dams_pass(): assert ok(outcome([(7, 6), (10, 6)]))
def test_naive_even_spacing_fails(): assert not ok(outcome(best_dams(2)))
