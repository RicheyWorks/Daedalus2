#!/usr/bin/env python3
"""Execute the pinned, original Python care/ribbon rules without Qt or installs.

python -B pet_care_source_oracle.py --source-root /path/to/computerpets --check
Omit --check to generate the sibling pet_care_parity.txt fixture.
The source checkout is read only; bytecode writing is disabled before importing it.
This oracle covers numeric Rui care, poses/commands, object spawns and ribbon
transitions. Dialogue selection, Qt drawing and persistence are separate scope.
Source app.py calls integer-rounded decay every 33 ms. Preserve that quirk;
do not silently introduce fractional accumulation in the portable core.
"""
import argparse
import hashlib
import importlib
import io
import itertools
from pathlib import Path
import random
import sys

sys.dont_write_bytecode = True
COMMIT = "8394667521edb4e2876658eae61b4aaee3145567"
PINS = {
    "client/computerpets_client/__init__.py": "3bd459bb2fcf7c40145d46263bb6fbe649557eb0",
    "client/computerpets_client/life.py": "0d8ba442d02bb8b9a313e85bba6f27e62ec735b6",
    "client/computerpets_client/play.py": "f5b237577ab0ef447172b9fe4a1c68fda74f1967",
    "client/computerpets_client/species.py": "9c045c3625b380cebe9422e760db0a6be68d0c6b",
    "client/computerpets_client/hours.py": "1e81c3d08a7e6e0ed293a31091c6af9dc3a435ec",
    "client/computerpets_client/hive.py": "e670eefe6d51bd599c42cd2c3746750a9dd34697",
    "client/computerpets_client/paths.py": "3d66261f994718906f23b6907d915535f28e53bf",
    "client/computerpets_client/line_picker.py": "6d008d5780219b954601f9dbe880661468e72f25",
    "client/computerpets_client/shed.py": "862900615f5a4e665df4d4b7eb641d62610fc075",
    "client/computerpets_client/app.py": "3c00198e737779c899e6f9abd9f666bad9121a97",
    "client/tests/test_care.py": "0ef7134b4510db5ddceaa38a6402e904b0f255d8",
    "client/tests/test_play.py": "5b441472924bbd75c407190173c1329fd0a00da1",
}
POSES = ("idle", "walk", "sit", "eat", "sleep", "play")
COMMANDS = ("idle", "eat", "play", "hide", "enter", "sit", "sleep", "talk")
ACTIONS = ("feed", "treat", "play", "hide", "call", "clean", "medicine", "rest", "bath", "talk", "praise")
ACTS = ("none", "play", "snack", "hide", "idle")


def blob_hash(path):
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def number(n):
    return format(n, ".17g") if isinstance(n, float) else str(int(n))


def state_row(s):
    values = [s.hunger, s.mood, s.energy, s.hygiene, s.health, s.bond,
              s.sick, s.hidden, POSES.index(s.anim), s.last_tick, len(s.mess)]
    for obj in s.mess:
        values.extend((obj.id, obj.x))
    values.append(len(s.gifts))
    for obj in s.gifts:
        values.extend((obj.id, obj.x))
    return " ".join(number(v) for v in values)


class Tape:
    def __init__(self, values):
        self.values = values
        self.used = 0

    def random(self):
        value = self.values[self.used]
        self.used += 1
        return value


def generate(source):
    for path, expected in PINS.items():
        actual = blob_hash(source / path)
        if actual != expected:
            raise RuntimeError(f"Pinned source mismatch: {path}: {actual} != {expected}")
    sys.path.insert(0, str(source / "client"))
    life = importlib.import_module("computerpets_client.life")
    play = importlib.import_module("computerpets_client.play")
    picker = importlib.import_module("computerpets_client.line_picker")
    shed = importlib.import_module("computerpets_client.shed")
    hours = importlib.import_module("computerpets_client.hours")
    output = io.StringIO()
    output.write("PETCARE 1\n")
    output.write(f"# source https://github.com/RicheyWorks/computerpets/tree/{COMMIT}\n")
    for path, sha in PINS.items():
        output.write(f"# blob {sha} {path}\n")
    output.write("# Executed original Python rules; dialogue/shed/hive/persistence excluded.\n")
    output.write("# Numeric rounding at each decay call is intentional source parity.\n")
    count = 0

    def row(*values):
        nonlocal count
        output.write(" ".join(str(v) for v in values) + "\n")
        count += 1

    def reset_picker():
        picker.set_line_picker_for_tests(picker.LinePicker(random=lambda: 0.0, now=lambda: 1700))

    samples = [life.CareState()]
    for edge, sick, hidden in itertools.product((0, 1, 17, 18, 21, 22, 24, 31, 32, 40, 41, 42, 64, 65, 99, 100), (False, True), (False, True)):
        samples.append(life.CareState(hunger=edge, mood=edge, energy=edge, hygiene=edge,
                                      health=edge, bond=edge, sick=sick, hidden=hidden, anim="walk", last_tick=1300,
                                      mess=[life.MessPile(9, 21.25)], gifts=[shed.Coat(11, 28.5, "gift")]))
    seeded = random.Random(427)
    for _ in range(40):
        samples.append(life.CareState(**dict(zip(("hunger", "mood", "energy", "hygiene", "health", "bond"),
                                                  [seeded.randrange(101) for _ in range(6)])),
                                      sick=bool(seeded.randrange(2)), hidden=bool(seeded.randrange(2)),
                                      anim=seeded.choice(POSES), last_tick=1700))
    for before in samples:
        for index, name in enumerate(ACTIONS):
            reset_picker()
            result = getattr(life, "apply_" + name)(before)
            row("A", index, state_row(before), state_row(result.state), POSES.index(result.anim), COMMANDS.index(result.cmd))
        row("V", state_row(before), before.vitals())
        for ident in (9, 77):
            result = life.pick_mess(before, ident)
            row("M", ident, state_row(before), state_row(result.state), POSES.index(result.anim), COMMANDS.index(result.cmd))

    decay_cases = []
    for dt, resting, hidden, sick in itertools.product((-100, 0, 1, 33, 108000, 162000, 216000, 252000, 120000, 180000,
                                                        10800000, 21600000, 50400000, 129600000), (False, True), (False, True), (False, True)):
        decay_cases.append((life.CareState(energy=40, hidden=hidden, sick=sick), dt, resting, [0.9] * 4))
    for hygiene, health, hunger, bond in itertools.product((17, 18, 40, 41, 42), (31, 32, 64, 65), (17, 18), (24, 25)):
        decay_cases.append((life.CareState(hygiene=hygiene, health=health, hunger=hunger, bond=bond), 120000, False,
                            [0, 0.25, 0, 0.75]))
    for mess_count, gift_count, probability in itertools.product((0, 4, 5), (0, 1, 2), (0, 0.199999, 0.2, 0.349999, 0.35, 0.9)):
        decay_cases.append((life.CareState(hygiene=20, bond=25,
                                          mess=[life.MessPile(100 + i, 22 + i) for i in range(mess_count)],
                                          gifts=[shed.Coat(200 + i, 33 + i, "gift") for i in range(gift_count)]),
                            120000, False, [probability] * 4))
    for before, dt, resting, tape_values in decay_cases:
        tape = Tape(tape_values)
        result = life.decay(before, dt, rng=tape, now=1700, key="red_panda", resting=resting)
        row("D", dt, 1700, int(resting), len(tape_values), *map(number, tape_values), state_row(before), state_row(result), tape.used)

    # Explicit one-hour frame sequence: do not accidentally change source cadence/rounding.
    before = life.CareState()
    after = before
    for _ in range(109090):
        after = life.decay(after, 33, rng=Tape([0.9, 0.9]), now=1700, key="red_panda", resting=False)
    row("S", 109090, 33, state_row(before), state_row(after))

    for value in (-100, -0.5, 0, 0.5, 1.5, 2.5, 21.5, 22.5, 77.5, 78.5, 99.5, 100.5, 500):
        row("C", number(value), life.clamp(value))
    for hour in range(-1, 25):
        row("R", hour, int(hours.is_resting_hour("red_panda", hour)))

    for taken, cmd, mark, on_care, via in itertools.product((False, True),
            ("idle", "wander", "seek", "leave", "play", "eat", "enter", "other"),
            (None, "lure", "treat"), (False, True), ("catch", "arrive")):
        chase = play.PlayChase(taken, cmd, mark)
        result = play.play_hop(chase, via, on_care)
        row("H", int(taken), cmd, mark or "-", int(on_care), 0 if via == "catch" else 1,
            ACTS.index(result.act), int(result.next.taken), result.next.cmd, result.next.mark or "-",
            result.apply_play, result.persist_play, result.issue_play, result.issue_eat)
    for vias, on_care in itertools.product((("catch", "arrive"), ("arrive", "catch"), ("catch", "catch", "arrive", "arrive")), (False, True)):
        result = play.play_chase(vias, play.PlayChase(False, "seek", "lure"), on_care)
        row("Q", int(on_care), len(vias), *(0 if v == "catch" else 1 for v in vias),
            *(ACTS.index(a) for a in result.acts), int(result.taken), result.cmd, result.mark or "-",
            result.apply_play, result.persist_play, result.issue_play, result.issue_eat)
    output.write(f"END {count}\n")
    return output.getvalue(), count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("pet_care_parity.txt"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generated, count = generate(args.source_root.resolve())
    if args.check:
        if args.output.read_text(encoding="utf-8") != generated:
            raise RuntimeError("Source oracle fixture differs; regenerate only after reviewing source changes")
        print(f"PASS pinned Python source oracle: {count} cases; fixture matches")
    else:
        args.output.write_text(generated, encoding="utf-8", newline="\n")
        print(f"WROTE {count} original Python oracle cases to {args.output}")


if __name__ == "__main__":
    main()
