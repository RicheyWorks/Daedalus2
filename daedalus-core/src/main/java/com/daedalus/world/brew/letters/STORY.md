# Letters by Ark: Youtube Master Island, chapter 10 (youtube-master, contest G97)

Chapters 1-9: melody brewing (G25), mended records and clean springs (G33), the record hunt (G46), choir stones
(G53), the first week home (G62), the record exchange (G66), the root cellar (G73), the homecoming supper (G85) and
the thirteenth song (G94). Chapter 10 (suggested by buffffff, #49578) writes to the islands beyond the shelf.

## Story

With the arks flying again, Fisher Dov opens an ark post on the dock. The supper guests all have old friends on
far islands they haven't heard from since the sky fell: Harbourmaster Nell at Kelp Harbour (Dov's), Smith Arlo at
Cinder Reach (Mason Hale's), Lampwright Suse on the Glass Shoals (Aunt Brine's) and Orchard-keeper Bram at the Far
Orchard (Keeper Oriel's). A letter goes better with a sealed jar from the cellar. But the runs are long, three days
a leg, and every squall or debris strike holds the ark two days more; a jar that turns on the way does more harm
than no jar at all. The Odds Keeper's underwriter (G80) will quote cover for a run, paid in salt; a covered jar
that spoils is made right. Every jar that lands good brings a reply on the return ark, and when it comes, the
supper guest who wrote reads it out.

## Beats, mechanics and tests (`LettersByArkTest`)

| Beat | Mechanic in code | Test |
|---|---|---|
| Four far islands, each an old friend of a supper guest, on ark routes of 1-4 legs | `Destination.island()` (G47 `ArkRoute` / `RouteLeg` / `Hazard`, read-only), `voyageDays` = 3 per leg | `farIslandsRoutesAndUnderwriterQuotes` |
| The underwriter quotes cover by route and sky | `quote` = G80 `ArkPolicy(route, sky, 1 per crate).premium(0.20)` (read-only) | `farIslandsRoutesAndUnderwriterQuotes` |
| A sealed jar leaves the cellar unopened; you need the jar, a known island and salt for cover | `RootCellar.dispatch` (G73, additive), `ship` guards | `shipGuardsAndSealedJarsLeaveWithoutSoaking` |
| Shelf life has to beat the voyage; good +2 (favourite +1), spoiled -2 | `Parcel.arrivesGood` (last good day >= arrival day), `nextDay` regard | `shelfLifeMustBeatTheVoyage` |
| Cover is paid in salt and refunds a spoiled parcel's regard | `ship(cover=true)`, covered spoil = 0 | `coverIsPaidInSaltAndRefundsASpoiledParcel` |
| Each run is one seeded voyage; rough runs strike more and run late | `ArkRoute.sail` with `OddsRng(seed, parcel)`, +2 days per strike | `voyagesAreSeededAndRougherRunsStrikeMore` |
| Quest `q_letters_by_ark`: ship four, three land good, two replies, then Dov; replies unlock the supper guest's epilogue | PORT09-twin `colony.QuestProgress` (ship parcel x4, arrive_good x3, reply letter x2, talk dov), `epilogue(guestId)` | `questShipFourThreeLandGoodTwoRepliesThenDovAndTheSupperEpilogue` |

One clock: `LettersByArk.nextDay` also ends the cellar's day, so jars keep spoiling on the shelf while parcels sail.

## Lines (`ReplyLines`)

- Dov, greeting: "The arks are running again. Seal a jar, write a letter, and I'll see it gets there. Mind the long
  runs: a jar that turns on the way does more harm than no jar at all."
- Shipping: "3 more parcels to send. Cover the long runs if you've the salt."
- Waiting: "4 parcels still afloat. The arks are slow; the jars aren't."
- Replies: "Letters come back on the return ark. 2 more to wait for."
- Quest done: "Letters from every run. The far islands know the homestead's name now."
- After: "There's always an ark going somewhere. Bring a jar."
- Supper guest epilogue: "A letter came from Harbourmaster Nell! I thought they'd gone down with the sky."

## Editor later (UNREAL-QUEUE)

Ark post on the dock (parcel crate, letter desk, route board showing voyage days and the underwriter's quote),
far-island NPC portraits on the reply letters, and the epilogue bark on the supper guests. Source-only here.
