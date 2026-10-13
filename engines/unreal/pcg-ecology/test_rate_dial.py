from rate_dial import dial_state
def test_ends_fail_middle_passes():
    assert not dial_state(0.0)["pass"] and not dial_state(1.0)["pass"] and dial_state(0.1)["pass"]
def test_clamps(): assert dial_state(-3)["rate"] == 0.0 and dial_state(9)["rate"] == 0.32
