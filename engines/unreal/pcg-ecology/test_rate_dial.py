from rate_dial import dial_state
def test_ends_fail_middle_passes():
    assert not dial_state(0.0)["pass"] and not dial_state(1.0)["pass"] and dial_state(0.1)["pass"]
def test_clamps(): assert dial_state(-3)["rate"] == 0.0 and dial_state(9)["rate"] == 0.32
from rate_dial import simulate_grid
def test_grid_no_fire_all_oak():
    g = simulate_grid(0.0); assert all(v == 3 for row in g for v in row)
def test_grid_wetland_cells_marked_and_unburnt():
    g = simulate_grid(0.5, wet=[(0, 0), (1, 0)]); assert g[0][0] == 4 and g[0][1] == 4
def test_grid_mid_rate_has_all_stages():
    vals = {v for row in simulate_grid(0.03) for v in row}; assert {0, 1, 2, 3} <= vals
