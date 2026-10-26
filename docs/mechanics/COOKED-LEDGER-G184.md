# G184 The Cooked Ledger

Sky Islands (arks) / OddsReaper Island. Package `com.daedalus.world.odds.benford`. Added by oddsreaper. No wagering.

## Story

The Keeper lays three ark cargo ledgers on the table, 200 entries each. One was cooked by a clerk who made the numbers
up. Honest cargo counts grow and multiply, so they start with a 1 about three times in ten. Invented ones don't.

## Mechanic

- **Benford's law** (`BenfordLaw.firstDigit`): P(first digit d) = log10(1 + 1/d), i.e. 30.1, 17.6, 12.5, 9.7, 7.9, 6.7,
  5.8, 5.1, 4.6% for d = 1..9.
- **Audit**: the chi-square of the nine first-digit counts against Benford has 8 degrees of freedom. For even df the
  upper tail is exact: P(X > x) = e^(-x/2) (1 + h + h^2/2 + h^3/6) with h = x/2 (`tail8`). The 5% line is 15.507.
- **Ledgers** (`CargoLedger`): honest values are 10^(4u), log-uniform over four whole decades, which is exactly Benford in
  the first digit. Cooked values are whole numbers 100..999 picked evenly, so each first digit is 1/9. With 200 entries,
  the cooked ledger's expected chi-square excess (noncentrality) is about 80, far past 15.5.
- **Rates**: an honest ledger is falsely flagged 5% of the time. A cooked one is caught essentially always (seeded rate
  above 99%).

## Quest q_cooked_ledger

`CookedLedgerQuest(seed)` deals the three ledgers, shows each chi-square in the Keeper's line, and takes one `point(i)`:
CAUGHT or FOOLED. `worstFit()` is the Keeper's hint and catches the clerk in at least 198 of 200 seeds.

## Tests (`CookedLedgerTest`)

The law sums to 1 with P(1) = 0.30103. The tail is exactly 0.05 at 15.507 and 0.01 at 20.09. Large honest and cooked
ledgers match their digit laws within 0.01. Over 4000 seeded honest ledgers the false-alarm Wilson interval contains 5%,
and the cooked catch rate stays above 99%. The quest is deterministic per seed and rejects a second point.

## Later

Ledger book UI and digit histogram.
