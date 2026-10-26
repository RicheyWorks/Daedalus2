# Choir Stones: Youtube Master Island, chapter 4 (youtube-master, contest G53)

Chapter 1 (G25) taught the island to brew by melody, chapter 2 (G33) mended the arks' records and cleared the
springs, chapter 3 (G46) brought the scattered records home across the rope bridges. Chapter 4 is about keeping
those bridges.

## Story

The shelf never stopped settling after the asteroid. Every night it shakes, and every shake chews at the rope
bridges that tie the fragments to the homestead. Three bad nights and a rope snaps; a fragment on the far side is
cut off, with its spring and whatever records still lie there.

Mason Hale cut keel blocks for the arks before the fall. She found that a stone carved with a mended seed-song
hums, and rope near a humming stone stops fraying: the old songs were written to steady the seed vaults on the
voyage, and they steady the shelf too. A stronger brew of the tune (a higher tier) hums farther. But blank stones
are scarce and each mended record can only be carved once, so you have to choose where the shelf needs the song
most, and re-string the ropes the shaking still wins.

## Beats, mechanics and tests (`ChoirStonesTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| Ropes fray each shake and snap at zero; rope from the store re-strings them | `BridgeLedger` (strength 3, `fray`, `restring` costs 2 `rope`, `cutOff` = fragments with no intact route home) | `bridgesFraySnapAndRestringWithRope` |
| Only a mended record (G33) and a blank stone make a choir stone; one per record, one per fragment | `ChoirStones.carve` uses `SeedSongSpring.isRestored`, spends `choir_stone_blank` | `onlyAMendedRecordAndABlankStoneMakeAChoirStone` |
| A stronger brew hums farther | `ChoirStones.range(tier)`: T1 1, T2-T3 2, T4 3 bridges (tier from the G25 brew) | `humRangeComesFromTheBrewTier` |
| A humming rope never frays | `humming(bridge)`; the nightly tremor skips humming bridges | `aHummingBridgeNeverFrays` (20 seeded shelves x 40 nights) |
| The shaking is seeded and an unguarded shelf breaks | `night(n)`: `1 + fragments/4` seeded frays, once per night | `tremorsAreSeededAndUnguardedShelvesFallApart` |
| Quest `q_choir_stones`: carve 2 stones, hold 3 nights with nothing cut off, tell Mason Hale | PORT09-twin `colony.QuestProgress` steps carve x2, hold night x3, talk mason_hale x1; reward claimable once | `questCarveTwoHoldThreeNightsTellTheMason` |
| Hale tells you what the shake cost | `MasonLines.line` | `theMasonNamesWhatTheShakeCutOff` |

The map is the G46 `hunt.FragmentMap`, so the same bridges the player walked to find the records are the ones the
stones protect.

## Mason Hale's lines

- Greeting: "Feel that? The shelf shakes every night, and the ropes can't take it forever. Bring me a song you've
  mended and a blank stone, and I'll make it hum."
- One stone: "One stone humming. One more and the ropes near it might just hold."
- Cut off: "Last night's shake cut off 2 fragments. Re-string the snapped ropes, and put a stone where the shaking
  keeps winning."
- Holding: "The ropes held 3 nights. Keep the stones singing."
- Quest done: "Three nights and not one fragment lost. The stones remember what the arks sang. Take this chisel;
  it's yours now."

Editor later (UNREAL-QUEUE): choir stone props and fraying/snapped rope-bridge states can call this rule set through
the server; no editor work was done here.
