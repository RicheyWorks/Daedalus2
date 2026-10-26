# G122 Choosing the Last Captain (Sky Islands arks / OddsReaper Island)

Owner: oddsreaper. Code: `daedalus-core/src/main/java/com/daedalus/world/odds/stopping/`.
Reuses `world.odds.OddsRng` and `Intervals`. Self-contained.

## Story

The last ark off the surface had a hull and a crew but no captain. Ten sailors came to the dock one
at a time, and with the belt closing there was no calling anyone back: hire on the spot or send
them away. The Odds Keeper, who signed the crew ledger, gave the rule the survivors still quote:
send the first few away to learn what good looks like, then take the first who beats them all.

| Story beat | Mechanic in code |
|---|---|
| Ten sailors arrive in an unknown order | `CaptainLineup.shuffled` (seeded Fisher-Yates over scores 1..n) |
| Hire or send away, no calling back | `CaptainChoiceQuest.interview` / `hire` (only "best so far" is visible) |
| "Send the first three away" | `StoppingRule.bestCutoff(10)` = 3 |
| "...then about two in five it's the best" | `StoppingRule.success` exact: P(r) = (r/n) sum 1/(i-1); P(3 of 10) = 0.3987; tends to 1/e |
| Checked against the dock ledgers | `CaptainLineup.simulate`: seeded success rate with Wilson interval |

## Quest q_captain_choice

1. INTERVIEWING: "Send the first 3 away, then take the first who beats them all. 40% that's the best of ten."
2. BEST_HIRED: "The best sailor of the ten. The last ark is in good hands."
3. GOOD_HIRED: "Number K of ten. A fair hand; the belt will test them."

No wagering here.

## Editor / asset needs (later, not in this PR)

- Dock queue of ten sailor NPCs (reuse villager meshes); hire / dismiss barks.
