# All-life progression and minigames

Creatures and plants in a player's world mature, earn what they live through, and carry it forward.
The mechanics registry already points at the maturity track (flora stages), the breeding and genome
inputs (egg hatch pools and creature families), and the evolved-form axes (dragon element, form,
variant). No XP curve is chosen here. Owner tuning stays open.

The plan file named beside this page is not in this tree. This page records step 3, which is.

## Step 3 — one activity result, credited once

Fishing, egg hatching, arcade cabinets, sports and mazes all end with a result. What Life Learns
needs one shape for "this activity finished with this outcome for this subject", and a receipt so
the same result credits that subject exactly once when it is replayed, retried or delivered twice.
The credit key is `(activityId, attemptId, subjectId)`. A second delivery of that triple does not
teach the lesson again.

- Contract: `docs/contracts/activity-result-v1/LEARNED-ENVELOPE.md`
- Core: `com.daedalus.world.activity.learned` (`ActivityResult`, `ActivityCredit`, `ActivityResultReceipt`)
- First wired game: Prismheart pond fishing, `PrismPondFishing`, reading `data/rpg/prism-fish.json`

A later minigame adds an adapter that builds the same envelope. It does not invent a second one.
The receipt records the lesson. It does not score it.
