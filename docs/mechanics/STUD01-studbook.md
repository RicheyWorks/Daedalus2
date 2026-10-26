# STUD01 — Studbook (contest G163)

*Code: `daedalus-core/src/main/java/com/daedalus/world/battlefield/FounderDrift.java` (tests: `FounderDriftTest`, 10).*

## Story

Before keeper Ilsa Marr can let the sky-cranes go (CRANE01), she has to breed them. The ark aviary was founded with
**twenty cranes** and has twenty places. Every chick gets half its genes from each parent, chosen by chance, and in a
small flock chance throws genes away a little every generation. Lose enough of them and the birds are inbred, and inbred
cranes die young on the marsh. Ilsa's studbook is how she fights it: who breeds, how many of each sex, and whether to
borrow cranes from the other arks.

## Quest `q_studbook`: "Twenty Places, Twenty Generations"

1. For each of 20 generations, pick how many cocks and hens are raised (`breed(gen, cocks, hens)`, total at most 20).
   The default is 10 and 10.
2. Choose how many migrant cranes a generation the other arks lend (`migrants(k)`, 40 in total over the run).
3. Run the studbook (`run()`). Ilsa reads the retained gene diversity:
   - **DIVERSE**: at least 85% of the founders' diversity is left.
   - **THINNING**: at least 70%.
   - **INBRED**: less.
4. The flock then flies to the marsh. Inbreeding F = 1 − retained lowers survival to `0.75 · exp(−0.2·F)`
   (`Report.marsh(AlleeRelease.Settings)`), and G142's Allee release runs with that survival.

Results with the defaults over 100 seeds (marsh = all 40 released in year 0):

| Studbook | Mean retained | Expected (1 − 1/2Ne)^t | DIVERSE / THINNING / INBRED | Marsh ESTABLISHED |
|---|---|---|---|---|
| 10 + 10 every generation | 0.610 | 0.603 | 0 / 0 / 100 | 3 |
| 2 cocks + 18 hens | 0.267 | 0.248 | 0 / 0 / 100 | 0 |
| one pair in generation 5 | 0.480 | 0.464 | 0 / 0 / 100 | 0 |
| 1 migrant a generation | 0.830 | — | 27 / 73 / 0 | 44 |
| 2 migrants a generation | 0.904 | — | 97 / 3 / 0 | 73 |
| (outbred, G142 default) | — | — | — | 90 |

The lessons are the classic ones: effective size is set by the rarer sex, a single bottleneck generation costs more than
many good ones repay, and about one migrant a generation is enough to stop a small flock drifting apart.

## Rules (seeded)

1. Founders: 20 cranes (first half cocks), 40 neutral loci, every allele copy unique, so founder diversity is
   1 − 1/40 = 0.975.
2. Each generation, each chick picks a random father among the previous cocks and a random mother among the hens, and
   inherits a random one of each parent's two copies at every locus.
3. Then `migrants` chicks are swapped for cranes with brand-new alleles.
4. Gene diversity is the mean over loci of 1 − Σp². Effective size `Ne = 4MF/(M+F)` (`effectiveSize`), across
   generations the harmonic mean (`harmonicMean`), and the no-migrant expectation is the product of (1 − 1/(2Ne))
   (`expectedRetained()`).

Every roll is a splitmix hash of (seed, generation, chick, locus, salt). `Settings.DEFAULT = (20, 20, 20, 40, 40, 0.2)`.

## What the tests pin

- Effective size and harmonic mean match the textbook (10+10 → 20, 2+18 → 7.2, harmonic of 20, 20, 2 → 5).
- Founders start with all alleles unique (diversity 0.975).
- Mean retained diversity over 100 seeds is within 0.05 of (1 − 1/2Ne)^t for the even, skewed and bottleneck studbooks.
- A skewed sex ratio costs more than 0.2 of diversity and one bottleneck pair more than 0.08. The plain studbook ends
  INBRED in every seed.
- One migrant a generation raises retained diversity by more than 0.15 and never ends INBRED. Two give DIVERSE in at
  least 90 of 100 seeds.
- Without migrants, alleles are only ever lost.
- On the marsh, the inbred flock establishes in at most 10 of 100 seeds, the two-migrant flock in at least 60.
- Survival falls with inbreeding, and `marsh()` changes nothing but survival.
- The same seed and plan give the same studbook, and over-capacity breeding, an overdrawn migrant pool and bad settings
  are refused.

## Host seam

- `FounderDrift.aviary(Settings, seed)`, then `breed(gen, cocks, hens)` and `migrants(k)` from Ilsa's studbook UI, then
  `run()`.
- `Report.generations()` drives the studbook ledger (diversity bar, allele count). `Report.outcome()` drives Ilsa's
  lines. `Report.marsh(AlleeRelease.Settings.DEFAULT)` hands the flock to CRANE01's release.
- Ties: the cranes are G142's. The migrants come over the ark routes (the arks chain), and the founders came out of
  VAULT01's ark seed-vault era.
- Assets: `Prop_Studbook_Ledger` (open ledger on a lectern with a diversity bar), `Prop_Leg_Band` (coloured crane leg
  band showing lineage), and reuse of `Mob_Sky_Crane` and the aviary (see UNREAL-QUEUE / BLENDER-ASKS).
