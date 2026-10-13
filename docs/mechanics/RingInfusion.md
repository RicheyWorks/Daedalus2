# Ring Infusion

Claim: team-codex / Sol Island / Sol Reach in the existing Portal Realm.

Three ordered herbs form a ring. Matching endpoint essences seal it; the centre selects
an existing same-essence effect from `data/herbs/combos.json`. Distinct outer and middle
essences double duration. Matching all three retains normal duration. A successful brew
consumes the three actual herb units and one clean water atomically. Invalid recipes or
insufficient ingredients consume nothing. Discovery is saved in the journal.

This is a positional closure puzzle, distinct from Buff's stacked herbs, Prometheus's
harmonic chords and Pootscoot's hydraulic phase routing. Six original herbs have distinct
silhouettes: Dawnleaf, Rillprism, Cinderbud, Stillmoss, Stridefern and Clearbell.

## Adventure: The Keeper's Broken Circle

The waterworks keeper remembers a garden carried aboard an ark after the impact. Its
three-part seal is broken. The keeper's clue is: "The beginning returns at the end; the
middle tells the spring what to remember."

1. **Restore the waterworks.** Draw dirty well water and filter it. Actual filtration
   records the quest fact; merely visiting the well does not advance the stage.
2. **Discover the ring.** Find herbs across the garden. Dawnleaf–Rillprism–Dawnleaf
   demonstrates a doubled cool effect. A valid brew records discovery and advancement.
3. **Feed the keeper.** Water and feed the livestock, then cook egg, milk and clean water
   into Sol Custard. Actual cooking advances the stage.
4. **Beyond the arch.** `portal_ready` lets an integration caller open the existing
   seeded Portal Realm journey. Reuse its party, dungeon keys, battles and persistence.

NFT connection: store the journal under the player's existing island/deed identity and
realm seed. The land NFT identifies the fragment; it does not grant free herbs or food.
This is a persistence integration proposal, not a new contract, mint or ownership claim.
The current rules do not implement wallet authentication or on-chain writes.

## Implementation and proof

`tools/islands/sol/sol_rules.py` implements resource consumption, discovery, quest facts,
stage calculation and save/restore. Tests cover actual action-driven progression and
failure atomicity. The farm is a portable reference; runtime interaction, journal UI
and portal gating await the shared homestead integration and a granted editor turn.
500 art variants are READY; no in-world feature or contest score is claimed yet.
