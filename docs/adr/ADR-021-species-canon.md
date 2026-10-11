# ADR-021: The species canon

**Status:** Accepted
**Date:** 2026-10-10
**Deciders:** RicheyWorks

## Question

Arks carry animals to repopulate the shattered islands (ADR-019). Which animals? The world needs a
species pool before it can have an ecology, and a pool is only useful if every kind says where on an
island it can live, how it breeds, and whether it can cross the sky without an ark.

## Decision

**The pool is the ComputerPets canon.** All 221 kinds from `web/src/lib/pets/catalog.ts` — key,
name, rarity, temperament — in catalog order. ComputerPets stays the owner of identity; Daedalus adds
ecology.

**Ecology is assigned by explicit tables, not guesses.** `tools/canon/build_species.py` names every
kind in exactly one guild and one size class; a kind the tables do not name stops the build (it did
on the first run: all the marine kinds were missing a size). The script writes
`daedalus-core/src/main/resources/com/daedalus/world/ecology/species.tsv`, which core loads with no
JSON dependency.

| Guild | Kinds | Lives on |
|---|---|---|
| MEADOW | 76 | grass and scrub |
| POND | 43 | the pond and stream |
| CANOPY | 31 | trees |
| MARINE | 31 | nothing yet — the sea fell away in the Shattering |
| STARBORN | 22 | the crystals under the islands — they fell with the meteor (dragons, Living Crystal, Methane Floater…) |
| DECOMPOSER | 18 | soil and deadwood |

- **Strategy** is a rule, pinned by a test on every row: TINY/SMALL and all decomposers are
  r-selected; MEDIUM, LARGE and rooted (SESSILE) kinds are K-selected. 130 R, 91 K.
- **Dispersal**: 57 kinds cross open sky alone (wings, spores, wind-borne cells). The other 164 need
  an ark — which is the story: arks carry those who cannot fly.

**`GET /api/v1/species`** (public) serves the canon with guild counts. The realm gets a bestiary:
one chip per guild, tap to list its kinds with size, strategy and whether they need an ark.

## Open decision for the owner

ComputerPets is "All rights reserved"; Daedalus is MIT. This slice copies species names and
temperaments (not art, dialogue or code) into an MIT repository. That is the owner's call to make
explicit — relicense the canon data, keep Daedalus private, or swap in neutral names.

## Verified

Core: 221 kinds in catalog order, all four rarities, every guild populated, spot classifications
(goldfish POND, barn owl CANOPY, fly agaric DECOMPOSER, Earth Dragon STARBORN, octopus MARINE),
the strategy rule on every row, malformed and duplicate rows refused with a line number. Server:
`/species` serves 221 with exact guild counts; prod posture table. Browser: the realm loads the
whole canon and the STARBORN chip lists 22 kinds.

## Held

- MARINE kinds have no habitat until an island grows a sky lake.
