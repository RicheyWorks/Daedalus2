# DiskSaver Island: Salvage Sale (G563)

A sealed-bid auction against a deterministic rival. Auctioneer Barnaby sells the census salvage
on the quay.

`tools/streaming/salvage_sale.py` reads a world census (the `tools/world_census` output,
read-only). Every island (up to six) puts up one lot, and spare lots pad the sale to five. Lots
are sold in label order. A lot's value is 3 + its asset count mod 5, plus a seeded 0 to 4. You
and the Broker each start with a third of the total value in coin. Python dev tooling only; nothing
runs inside Unreal.

You write one sealed bid per lot. The Broker's rule is public: half the lot's value (rounded
down), plus 3 for every lot it has lost so far, capped by the coin it has left. The higher bid
wins and pays its own bid, and a tie goes to the Broker. Your score is the value you win.

Because the Broker gets hungrier each time it loses, early wins make later lots dearer. Par is
the best score possible, found by an exact search over (lot, your coin, Broker coin, lots it
has lost). The tests check it against a brute force over every win-or-pass plan.
`greedy_value` shows the trap: winning every lot you can afford.

```
python tools/streaming/salvage_sale.py census.json --seed 7                    # the lots and par
python tools/streaming/salvage_sale.py census.json --seed 7 --bids 0,5,0,7,0
python tools/streaming/salvage_sale.py census.json --seed 7 --auto
```

| verdict | meaning |
|---|---|
| `shrewd` | par value won |
| `fair` | at least half of par |
| `fleeced` | less than half of par |

Exit 2 refuses the wrong number of bids, a non-number, a bid above your coin, or a census with
no islands. CI (`.github/workflows/salvage-sale.yml`) runs the tests, including the real census
fixtures, and plays the seed-7 sale. Hook: `data/islands/disk-saver/salvage-sale-v1.json`.
