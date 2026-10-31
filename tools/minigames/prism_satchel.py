#!/usr/bin/env python3
"""Prism Satchel and Warden Trials: one shard wallet and one mastery ladder shared by every Prismheart game.

A finished game pays hued Prism Shards into the satchel: a win pays a base by difficulty (easy 1, normal 2,
hard 3) plus score // divisor (capped), a loss pays half of that score share, a perfect run pays a bonus, and
each new Warden seal the run earns pays one more. Every shard is the game's home hue (ember, tide, verdant, gale,
umbra). Spending shards is checked (never below zero); counts stop at COUNT_MAX so a save always reloads.

Warden Trials rank each game's best run with seals, in order: Ember (finish a game; an attempt mark, not mastery,
so mastered() skips it), Tide (win), Verdant (win on
normal or hard), Gale (win on hard), Umbra (win on hard at the game's par) and Heartglass (win on hard at the
game's heartglass par, or a perfect run where the game has one). Pars come from the Fair Par table (pythagoras,
FAIRPAR02); changing a par changes the parity fixture.

All math is integer; nothing is random. The save is a short text line, strictly parsed. Python is the rules
authority; DaedalusPrismSatchelCore.h must match it byte for byte (prism_satchel_parity.txt).
"""
import sys

HUES = ("ember", "tide", "verdant", "gale", "umbra")
SEALS = ("none", "ember", "tide", "verdant", "gale", "umbra", "heartglass")
DIFFICULTIES = ("easy", "normal", "hard")
WIN_BASE = {"easy": 1, "normal": 2, "hard": 3}
SCORE_CAP = 4  # most shards a run's score can add
PERFECT_BONUS = 2
SAVE_TAG = "PRISMSATCHEL1"
SAVE_MAX = 4096  # characters; anything longer is not a satchel
COUNT_MAX = 999_999_999  # shard counts and runs stop here, so every satchel still fits its 9-digit save fields

# game id -> (home hue, score divisor, umbra par, heartglass par or "perfect"). Pars are the Fair Par table
# (engines/unreal/core-test/prism_fair_par_parity.txt, docs/mechanics/FAIRPAR02) on hard: umbra = silver, heartglass = gold;
# where hard has no par (silver 0: the bot never wins) normal is used. test_prism_satchel pins this against the table.
PAYOUTS = {
    "shardring": ("tide", 60, 188, 215),
    "lumenpath": ("ember", 50, 140, 180),
    "wardens_accord": ("tide", 15, 60, 65),
    "facetlock": ("gale", 40, 130, 160),
    "prismvault": ("umbra", 40, 100, 200),
    "shardfall": ("ember", 12, 34, 38),
    "prismcairn": ("verdant", 35, 105, 105),
    "spiritkite": ("gale", 8, 22, 25),
    "shadewatch": ("umbra", 40, 148, 163),
    "glimmerloom": ("tide", 50, 120, 135),
    "glowmoss": ("verdant", 12, 29, "perfect"),
}


def seal_for(game, difficulty, score, won, perfect=False):
    """Index into SEALS for one finished run (Warden Trials)."""
    _, _, umbra_par, heart_par = PAYOUTS[game]
    if not won:
        return SEALS.index("ember")
    if difficulty != "hard":
        return SEALS.index("verdant") if difficulty == "normal" else SEALS.index("tide")
    if heart_par == "perfect":
        heart = perfect
    else:
        heart = score >= heart_par
    if heart:
        return SEALS.index("heartglass")
    return SEALS.index("umbra") if score >= umbra_par else SEALS.index("gale")


def check_result(game, difficulty, score, won, perfect):
    if game not in PAYOUTS:
        raise ValueError(f"unknown game {game!r}")
    if difficulty not in DIFFICULTIES:
        raise ValueError(f"unknown difficulty {difficulty!r}")
    if not isinstance(score, int) or isinstance(score, bool) or score < 0:
        raise ValueError("score must be a whole number >= 0")
    if not isinstance(won, bool) or not isinstance(perfect, bool) or (perfect and not won):
        raise ValueError("won and perfect are true or false, and only a win can be perfect")


class Satchel:
    def __init__(self):
        self.shards = {h: 0 for h in HUES}
        self.runs = 0
        self.seals = {}  # game id -> best seal index

    def record(self, game, difficulty, score, won, perfect=False):
        """Pay one finished run into the satchel. Returns (shards paid, home hue, seal index, new seal levels)."""
        check_result(game, difficulty, score, won, perfect)
        hue, divisor, _, _ = PAYOUTS[game]
        share = score // divisor
        pay = WIN_BASE[difficulty] + min(SCORE_CAP, share) if won else min(SCORE_CAP // 2, share // 2)
        if perfect:
            pay += PERFECT_BONUS
        seal = seal_for(game, difficulty, score, won, perfect)
        gained = max(0, seal - self.seals.get(game, 0))
        pay += gained
        if gained:
            self.seals[game] = seal
        self.shards[hue] = min(COUNT_MAX, self.shards[hue] + pay)
        self.runs = min(COUNT_MAX, self.runs + 1)
        return pay, hue, seal, gained

    def spend(self, cost):
        """Take shards out; ValueError when the cost is malformed or the satchel is short (nothing is taken)."""
        if not isinstance(cost, dict) or not cost or any(h not in HUES for h in cost):
            raise ValueError("a cost names one or more hues")
        if any(not isinstance(n, int) or isinstance(n, bool) or n < 1 for n in cost.values()):
            raise ValueError("each hue in a cost needs a whole number of shards >= 1")
        short = [h for h in HUES if cost.get(h, 0) > self.shards[h]]
        if short:
            raise ValueError("satchel is short of " + ", ".join(short))
        for h, n in cost.items():
            self.shards[h] -= n

    def mastered(self):
        """Games with a seal past Ember. Ember only marks a finished attempt (a loss earns it), so mastery counts skip it."""
        return sum(1 for s in self.seals.values() if s >= SEALS.index("tide"))

    def heartglass(self):
        """Games with a Heartglass seal (unlocks Spirit Boons later)."""
        return sum(1 for s in self.seals.values() if s == SEALS.index("heartglass"))

    def to_text(self):
        shards = ",".join(str(self.shards[h]) for h in HUES)
        seals = ",".join(f"{g}:{s}" for g, s in sorted(self.seals.items()))
        return f"{SAVE_TAG};{shards};{self.runs};{seals}"

    @classmethod
    def from_text(cls, text):
        """Strict parse of to_text(); ValueError names what is wrong."""
        if not isinstance(text, str) or len(text) > SAVE_MAX:
            raise ValueError("not a satchel save")
        parts = text.strip().split(";")
        if len(parts) != 4 or parts[0] != SAVE_TAG:
            raise ValueError(f"satchel saves start with {SAVE_TAG} and have 4 parts")
        counts = parts[1].split(",")
        if len(counts) != len(HUES) or not all(c.isdigit() and len(c) <= 9 for c in counts):
            raise ValueError("satchel shards must be 5 whole numbers")
        if not parts[2].isdigit() or len(parts[2]) > 9:
            raise ValueError("satchel runs must be a whole number")
        s = cls()
        s.shards = {h: int(c) for h, c in zip(HUES, counts)}
        s.runs = int(parts[2])
        for item in parts[3].split(",") if parts[3] else []:
            game, _, seal = item.partition(":")
            if game not in PAYOUTS or game in s.seals or not seal.isdigit() or not 1 <= int(seal) < len(SEALS):
                raise ValueError(f"bad seal entry {item!r}")
            s.seals[game] = int(seal)
        if s.to_text() != text.strip():
            raise ValueError("satchel save is not in canonical order")
        return s


def main(argv=None):
    s = Satchel()
    for game in sorted(PAYOUTS):
        print(game, s.record(game, "hard", PAYOUTS[game][2], True))
    print(s.to_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
