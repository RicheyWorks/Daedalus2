#!/usr/bin/env python3
"""Siltlane rules twin and golden fixture.

The playable rules live in DaedalusSiltlaneCore.h. This module is the fixture
beside that core: it deals the same xorshift stream the core uses (not
CPython random) and writes engines/unreal/core-test/siltlane_parity.txt.

  python tools/minigames/siltlane_parity.py --check
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "engines/unreal/core-test/siltlane_parity.txt"


class Rng:
    def __init__(self):
        self.state = 730

    def seed(self, value):
        self.state = value if value else 1

    def next(self):
        s = self.state & 0xFFFFFFFF
        s ^= (s << 13) & 0xFFFFFFFF
        s ^= s >> 17
        s ^= (s << 5) & 0xFFFFFFFF
        self.state = s & 0xFFFFFFFF
        return self.state

    def mint(self, low, high):
        if high <= low:
            return low
        return low + self.next() % (high - low + 1)


class Stone:
    def __init__(self, lane, row):
        self.lane = lane
        self.row = row


class Core:
    def __init__(self):
        self.option = 0
        self.course = 3
        self.lane = 1
        self.passed = 0
        self.lost = False
        self.cleared = False
        self.fall_every = 12
        self.spawn_every = 24
        self.tick = 0
        self.was_left = False
        self.was_right = False
        self.stones = []
        self.rng = Rng()
        self.seed = 730
        self.difficulty = "normal"

    def target(self):
        table = {"easy": (6, 4), "hard": (10, 6)}
        course, practice = table.get(self.difficulty, (8, 5))
        return practice if self.option == 1 else course

    def spawn_row(self):
        return 6 if self.difficulty == "hard" else 7

    def apply_pace(self):
        if self.difficulty == "easy":
            self.fall_every, self.spawn_every = 20, 36
        elif self.difficulty == "hard":
            self.fall_every, self.spawn_every = 8, 14
        else:
            self.fall_every, self.spawn_every = 12, 24

    def deal(self):
        self.course = 2 if self.option == 1 else 3
        self.lane = 0 if self.option == 1 else 1
        self.passed = 0
        self.lost = False
        self.cleared = False
        self.tick = 0
        self.was_left = self.was_right = False
        self.stones = []
        self.rng.seed(self.seed)
        self.apply_pace()

    def reset(self, seed):
        self.seed = seed if seed else 1
        self.deal()

    def set_option(self, value, seed):
        if value < 0 or value > 1:
            return False
        self.option = value
        self.seed = seed if seed else 1
        self.deal()
        return True

    def set_difficulty(self, name):
        if name not in ("easy", "normal", "hard"):
            return False
        self.difficulty = name
        self.apply_pace()
        if self.passed >= self.target():
            self.cleared = True
        return True

    def over(self):
        return self.lost or self.cleared

    def closest(self):
        best = 99
        for stone in self.stones:
            if stone.lane == self.lane and 0 <= stone.row < best:
                best = stone.row
        return best

    def fall(self):
        for stone in self.stones:
            stone.row -= 1
        for stone in self.stones:
            if stone.row == 0 and stone.lane == self.lane:
                self.lost = True
                return
        kept = []
        for stone in self.stones:
            if stone.row >= 0:
                kept.append(stone)
            elif self.passed < self.target():
                self.passed += 1
                if self.passed >= self.target():
                    self.cleared = True
        self.stones = kept

    def spawn(self):
        lane = self.rng.mint(0, self.course - 1)
        if self.difficulty == "easy" and self.course > 1 and lane == self.lane:
            lane = (lane + 1) % self.course
        self.stones.append(Stone(lane, self.spawn_row()))

    def step(self, left, right):
        if self.over():
            return
        if left and not self.was_left and self.lane > 0:
            self.lane -= 1
        elif right and not self.was_right and self.lane < self.course - 1:
            self.lane += 1
        self.was_left = bool(left)
        self.was_right = bool(right)
        self.tick += 1
        if self.tick % self.fall_every == 0:
            self.fall()
        if not self.over() and self.tick % self.spawn_every == 0:
            self.spawn()

    def note(self):
        if self.cleared:
            return "The runner cleared the silt course; passed " + str(self.passed)
        if self.lost:
            return "The silt caught the runner; passed " + str(self.passed)
        return "Lane " + str(self.lane) + "; passed " + str(self.passed) + " of " + str(self.target())


def dodge(core):
    """Move toward the lane whose nearest stone is farther away, releasing held keys."""
    def nearest(lane):
        best = 99
        for stone in core.stones:
            if stone.lane == lane and stone.row >= 0 and stone.row < best:
                best = stone.row
        return best

    here = nearest(core.lane)
    safest = max(range(core.course), key=nearest)
    if safest == core.lane or here == 99:
        return "."
    choice = "L" if safest < core.lane else "R"
    if choice == "L" and core.was_left:
        return "."
    if choice == "R" and core.was_right:
        return "."
    return choice


def apply_move(core, move):
    core.step(move == "L", move == "R")


def trace(seed, option, difficulty, policy, limit):
    core = Core()
    core.set_difficulty(difficulty)
    core.set_option(option, seed)
    lines = [f"RUN {seed} {option} {difficulty}"]
    for _ in range(limit):
        if core.over():
            break
        move = policy(core)
        apply_move(core, move)
        lines.append(f"{move} {core.lane} {core.passed} {int(core.lost)} {int(core.cleared)}")
    return lines, core


def fixture_text():
    stand, _ = trace(730, 0, "normal", lambda _c: ".", 200)
    clear, _ = trace(730, 1, "normal", dodge, 800)
    hard, _ = trace(730, 0, "hard", dodge, 800)
    lines = ["# siltlane-parity-v1", *stand, *clear, *hard, ""]
    return "\n".join(lines)


def improvements():
    """Forty small checks. Each one names the improvement it locks."""
    gaps = []

    def expect(ok, what):
        if not ok:
            gaps.append(what)

    fresh = Core()
    fresh.reset(730)
    expect(fresh.lane == 1 and fresh.fall_every == 12 and fresh.spawn_every == 24 and fresh.target() == 8, "01 fresh normal course")
    expect(fresh.note() == "Lane 1; passed 0 of 8", "02 opening note names the target")
    note = fresh.note()
    expect(fresh.set_difficulty("hard") and fresh.fall_every == 8 and fresh.spawn_every == 14 and fresh.passed == 0 and fresh.lane == 1, "03 hard pace keeps the run")
    expect(fresh.note() == "Lane 1; passed 0 of 10", "04 hard note names ten stones")
    expect(fresh.note() != note, "05 the note follows the target")
    expect(fresh.set_difficulty("easy") and fresh.fall_every == 20 and fresh.spawn_every == 36 and fresh.target() == 6, "06 easy pace and six-stone clear")
    expect(not fresh.set_difficulty("legendary") and fresh.difficulty == "easy", "07 unknown difficulty is refused")
    practice = Core()
    expect(practice.set_option(1, 730) and practice.course == 2 and practice.lane == 0 and practice.target() == 5, "08 practice is two lanes and five stones")
    expect(not practice.set_option(2, 730) and practice.option == 1, "09 option 2 is refused")
    expect(practice.set_option(0, 730) and practice.course == 3 and practice.target() == 8 and practice.lane == 1, "10 option 0 restores three lanes")
    zero, one = Core(), Core()
    zero.reset(0)
    one.reset(1)
    for _ in range(30):
        zero.step(False, False)
        one.step(False, False)
    expect(zero.lane == one.lane and zero.passed == one.passed and zero.tick == one.tick, "11 seed 0 matches seed 1")
    edge = Core()
    edge.reset(730)
    edge.step(False, True)
    edge.step(False, False)
    edge.step(False, True)
    edge.step(False, False)
    edge.step(False, True)
    expect(edge.lane == 2, "12 the right edge stops at lane 2")
    practice.reset(730)
    practice.set_option(1, 730)
    practice.step(False, True)
    practice.step(False, False)
    practice.step(False, True)
    expect(practice.lane == 1, "13 practice stops at lane 1")
    hold = Core()
    hold.reset(730)
    hold.step(True, False)
    hold.step(True, False)
    expect(hold.lane == 0, "14 a held left press moves once")
    hold.step(False, False)
    hold.step(False, True)
    hold.step(False, True)
    expect(hold.lane == 1, "15 a held right press moves once")
    both = Core()
    both.reset(730)
    both.step(True, True)
    expect(both.lane == 0, "16 left wins when both directions are held")
    opened = Core()
    opened.reset(730)
    expect(opened.closest() == 99, "17 closest starts empty")
    stand, stood = trace(730, 0, "normal", lambda _c: ".", 200)
    expect(stood.lost and not stood.cleared, "18 standing still loses")
    expect(stood.passed < stood.target(), "19 a loss scores below the target")
    expect("caught" in stood.note(), "20 the loss note names the catch")
    stood.reset(730)
    expect(stood.passed == 0 and stood.lane == 1 and not stood.over(), "21 restart clears the loss")
    mid = Core()
    mid.reset(4)
    guard = 0
    while mid.passed == 0 and not mid.over() and guard < 400:
        apply_move(mid, dodge(mid))
        guard += 1
    passed = mid.passed
    lane = mid.lane
    expect(passed > 0 and mid.set_difficulty("hard") and mid.passed == passed and mid.lane == lane, "22 difficulty keeps a pass already scored")
    _lines, cleared = trace(730, 1, "normal", dodge, 800)
    expect(cleared.cleared and not cleared.lost, "23 practice seed 730 can clear")
    expect(cleared.passed == cleared.target(), "24 a clear scores exactly the target")
    expect("cleared" in cleared.note(), "25 the clear note names the course")
    expect(cleared.passed <= cleared.target(), "26 the score never passes the target")
    cleared.reset(730)
    expect(not cleared.over() and cleared.passed == 0, "27 retry after a clear starts over")
    fuzz_ok = True
    for seed in range(1, 21):
        core = Core()
        core.reset(seed)
        for _ in range(250):
            if core.over():
                break
            apply_move(core, dodge(core))
            if not 0 <= core.lane < core.course or core.passed > core.target():
                fuzz_ok = False
        if core.passed > core.target():
            fuzz_ok = False
    expect(fuzz_ok, "28 twenty seeds stay in lane and under the target")
    text = fixture_text()
    expect(text.startswith("# siltlane-parity-v1\n"), "29 the fixture has a header")
    expect("RUN 730 0 normal" in text and "RUN 730 1 normal" in text and "RUN 730 0 hard" in text, "30 the fixture has stand, practice and hard runs")
    easy = Core()
    easy.set_difficulty("easy")
    easy.reset(730)
    seen = False
    for _ in range(80):
        if easy.stones:
            seen = all(s.lane != 1 or easy.difficulty != "easy" for s in easy.stones if s.row == easy.spawn_row())
            break
        easy.step(False, False)
    expect(seen, "31 easy does not drop the first stone on the opening lane")
    hard = Core()
    hard.set_difficulty("hard")
    hard.reset(730)
    row_seen = None
    for _ in range(40):
        if hard.stones:
            row_seen = hard.stones[0].row
            break
        hard.step(False, False)
    expect(row_seen == 6, "32 hard stones start one row closer")
    normal = Core()
    normal.reset(730)
    normal_row = None
    for _ in range(40):
        if normal.stones:
            normal_row = normal.stones[0].row
            break
        normal.step(False, False)
    expect(normal_row == 7, "33 a normal stone starts on row 7")
    expect(hard.fall_every < normal.fall_every, "34 hard falls faster than normal")
    easy_pace = Core()
    easy_pace.set_difficulty("easy")
    easy_pace.reset(1)
    normal_pace = Core()
    normal_pace.reset(1)
    expect(easy_pace.fall_every > normal_pace.fall_every > hard.fall_every, "35 easy falls slower than normal slower than hard")
    expect(easy_pace.spawn_every > normal_pace.spawn_every > hard.spawn_every, "36 easy spawns less often than normal less often than hard")
    frozen = Core()
    frozen.reset(730)
    for _ in range(400):
        if frozen.lost:
            break
        frozen.step(False, False)
    lane_at_loss = frozen.lane
    frozen.step(True, False)
    expect(frozen.lost and frozen.lane == lane_at_loss, "37 a step after the loss does not move")
    again_a, again_b = Core(), Core()
    again_a.reset(42)
    again_b.reset(42)
    for _ in range(40):
        again_a.step(False, True)
        again_b.step(False, True)
    expect(again_a.lane == again_b.lane and again_a.passed == again_b.passed and len(again_a.stones) == len(again_b.stones), "38 the same seed replays")
    expect(cleared.spawn_row() == 7 and hard.spawn_row() == 6, "39 spawn row follows difficulty")
    expect(len(stand) > 10 and len(_lines) > 10, "40 both traces record more than a handful of steps")
    return gaps


def main():
    gaps = improvements()
    text = fixture_text()
    if "--check" in sys.argv:
        found = FIXTURE.read_text(encoding="utf-8") if FIXTURE.exists() else ""
        if found != text:
            gaps.append("siltlane_parity.txt is stale; run python tools/minigames/siltlane_parity.py")
    else:
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(text, encoding="utf-8", newline="\n")
    for gap in gaps:
        print("FAIL:", gap)
    print("siltlane parity ok" if not gaps else f"{len(gaps)} gap(s)")
    return 1 if gaps else 0


if __name__ == "__main__":
    sys.exit(main())
