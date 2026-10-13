# Daedalus game mechanics — director review edition

**Prepared for Richey · 2026-10-13 · Review proposal v1**

Read alongside [Storyline](STORYLINE.md), [Source reconciliation](SOURCE-RECONCILIATION.md), and the searchable [complete item and asset register](ITEM-REGISTER.md). This is a consolidated design for review, not a declaration that every feature is playable. Existing source files and item workbooks remain unchanged.

## 1. The game we are building

Daedalus is a shattered planet whose surviving fragments sustain different communities and different kinds of games. The player makes a fragment livable, learns its rules, gains companions and the means to travel, then follows a distinctive rainbow into another realm. A successful expedition brings home knowledge, relationships and whatever goods that realm's travel rules permit.

The central motivation is **making a broken world reachable and worth living in**. Combat protects journeys; crafting equips them; farming sustains them; music remembers them; mazes conceal the remains of the old world. The strongest rewards should demonstrate mastery of these relationships rather than merely demand a larger kill count.

### Reading the decisions

- **Confirmed**: a direct user instruction, including the current conversation. These outrank older documents when they conflict.
- **Existing**: a rule, implementation or intention found in a named source. This does not itself establish current live proof.
- **Proposed**: a developed addition or reconciliation for Richey's review. It is not approved canon or an instruction to silently change runtime behavior.

Evidence levels remain separate: a catalog entry, a Blender asset, an imported Unreal asset, a tested rule, and a demonstrated player action are five different things. The review's source audit records those distinctions.

### Design commitments

1. **Every realm is its own game.** It has its own item catalog, equipment, activities, rules, visual language and progression.
2. **Familiar controls, distinct contents.** Inventory tab navigation is consistent across realms; appearance, categories, contents and available actions fit the current realm.
3. **Travel is discovered in the world.** Players find a realm's unique rainbow by the small traces of its dust in distant clouds.
4. **Quiet visual guidance.** Occasional distant twinkles invite attention. Avoid a constant sparkling overlay, saturated fog or an unavoidable glowing path.
5. **Reusable systems, observable outcomes.** Extend existing world, creature, recipe, travel, save and jukebox systems. A usable feature must produce a visible result and survive save/load where applicable.
6. **Original fiction and presentation.** The Portal Realm uses the approachable quest structure of early console RPGs, party development and discovery-led exploration. Existing franchises are creative references, not Daedalus character names or copied settings.

## 2. The play loops and what they accomplish

| Loop | Player sequence | Persistent result | Story purpose |
|---|---|---|---|
| Home fragment | Find clean water → grow/feed → harvest/process → improve shelter and tools | A more dependable home and known recipes | The impact's survivors gain a future |
| Expedition | Notice a clue → prepare → navigate → overcome threat/puzzle → return | Discoveries, opened routes, earned goods | Reconnect isolated communities |
| Realm crossing | Follow dust → identify rainbow → reach its gate → inspect destination rules → cross | Discovered route and separate realm progress | Different fragments preserved different ways of life |
| Companion care | Meet → help/feed → earn trust → travel together | Relationship and permitted abilities | Life carried by arks is a responsibility |
| Restoration | Diagnose a real shortage → supply or repair → verify recovery | Changed settlement state and NPC memory | The player changes conditions rather than collecting arbitrary errands |
| Mastery | Learn local grammar → combine skills → solve exceptional encounter | A memorable ability, landmark or legendary reward | Expertise connects the world's systems |

**Proposed first-session pacing:** offer safe movement, drinking and inventory in the opening minutes; one meaningful repair and one companion encounter before the first combat gate; reveal a rainbow clue early but let the player prepare before reaching it. These are pacing targets, not timed penalties or a requirement to finish every island before exploring.

## 3. M01 — world structure, islands and realm identity

**Existing:** the story describes one immense planet broken by an impact, with fragments inside a globe-like sky, arks between them and space exploration reserved for a later phase. Seeded terrain and the realm registry already exist. See [REALMS](../REALMS.md), the shared STORY snapshot in the source audit and ADR-029/030.

**Reconciliation:** distinguish a **realm** (a ruleset/game), a **world instance** (a seeded or hosted instance of that ruleset), an **island/district** (a place inside it), and an **asset variant** (a visual representation). Sol Reach is a district associated with the Portal Realm, not automatically a new engine. The contest's several-hundred-meter show islands are not evidence that the normal generated start island has that size.

**Proposed:** each realm declares a small profile: identity, art theme, item namespace, permitted player actions, progression model, entrance/exit rules, companion representation and save version. A distinct island mechanic can live inside an existing realm without copying its inventory or travel implementation.

**Acceptance:** the same player can enter two genuinely different realms, recognize the change, return, and retain each realm's correct state. A realm swap cannot overwrite the other realm's bag or quest flags.

## 4. M02 — rainbow discovery and travel

**Confirmed:** every realm's rainbow is unique. Players find it through traces of its dust colors in nearby clouds; distant twinkles remain restrained. The realm lies at the end of its rainbow.

**Existing:** ADR-031 already provides paired sky gates, cloud berths and flying mounts. Its identical rainbow plan is older than the current unique-rainbow requirement. ADR-052 also uses PORTAL cubes for the 8-bit experience.

**Proposed encounter sequence:**

1. **Glimpse.** A few colored points briefly catch the light in a distant cloud. Ordinary clouds remain dominant.
2. **Recognition.** A second cloud repeats the same color family and recognizable swirl or cloud silhouette. The player can infer a direction without following a continuous particle line.
3. **Approach.** The signature becomes readable: larger cloud shoulders, finer dust arcs, or a restrained pastel shimmer. A unicorn can face or walk toward the next clue.
4. **Threshold.** The rainbow and gate reveal the destination's identity. The player can inspect realm rules and arrange equipment before crossing.
5. **Arrival.** A safe berth and return route prevent arrival into an unplayable fall, combat trap or stranded state.

A destination's motif must be stable enough to learn. Weather may alter visibility, but should not quietly change a rainbow's destination. Proposed accessibility options add a soft chime, a shape cue and an optional discovered-route journal; avoid making color or hearing the sole channel. Reduced-effects mode retains the clue while removing glitter motion.

**Proposed consistency rule:** all new inter-realm routes require discovering their rainbow. Existing island PORTAL cubes become access points associated with a discovered rainbow, or remain explicitly local portals. Richey should choose this reconciliation before old portals are changed. Returning along a known route may be made easier, but no undiscovered-realm menu shortcut is assumed.

**Acceptance:** from a natural viewpoint, a player notices the clue without a marker, follows at least two environmental hints, identifies the correct destination and returns successfully. Test day, night, bad weather and reduced-effects mode. No claim that this trail exists today.

## 5. M03 — inventory and items across realms

**Confirmed:** the shared tab pattern is inspired by ARC Raiders. Its controls remain familiar, while the realm supplies its look and its actual items. Category names are not forced to be identical across different games.

**Proposed layout:** a visible tab strip, an item grid/list, a selected-item detail panel, and a short action row. Mouse, keyboard and controller reach the same actions. Remember selection and scroll per tab; changing a filter never consumes, equips or transfers an item. Explain disabled actions, show stack count and relevant condition, and distinguish a quest object from a consumable.

Examples: the Portal Realm may expose Bag, Equipment and Key Items; a farming fragment may expose Tools, Harvest, Food and Care; a vehicle-heavy realm may expose Parts, Cargo and Equipment. These are examples pending the realm's actual catalog, not a universal taxonomy.

**Existing capacity conflict:** shared `data/inventory/inventory.json` specifies 30 slots, eight hotbar positions, default stack 64 and tools stack one. ADR-052's retro party has a shared 12-slot bag. Keep both rules scoped to their realm; the new tabs do not magically expand either capacity.

**Proposed transfer policy:** preserve player identity, travel discoveries and story memory across realms. Keep equipment and consumable inventories realm-scoped by default. A destination may explicitly recognize a carried companion or convert a permitted item through a documented mapping. Never delete unsupported gear on crossing, silently turn it into currency, or duplicate it. Deed ownership and the right to use an item in a different game's combat are separate concepts.

**Acceptance:** equip/use/store/sort a real item, fill a bag, cross realms and return, then reload the save. Verify counts, equipment, selection and any permitted transfer receipt. Decide an overflow rule per realm; the existing generic pickup-on-full rule should not scatter a legendary quest reward into an unsafe sea.

## 6. M04 — survival, water and the living settlement

**Existing:** clean water connects thirst, cooking, livestock and herbs. Shared data includes springs, dirty wells, rain catchers, salt water, boiling, filtering and distillation. Some island definitions intentionally differ. The Living World service already models a keeper, a finite cistern and a dry spell; that limited service is not a complete universal economy.

**Player actions:** identify a source, draw water, treat it if required, store/distribute it, drink or consume it in a recipe. Show quality at collection and at use. A well's quality follows its specific source definition; do not assume every well is clean because one island's well is.

**Existing draft balance:** shared hunger drains at 0.05/s, thirst at 0.08/s, with sprint multipliers. A drink restores 35 thirst. From the draft starting thirst of 80, idle depletion takes about 16 minutes 40 seconds. That gives a reason to prepare, but these are data values, not a recommendation to impose survival drain inside every other genre.

**Proposed experience:** early water is reachable without a long forced expedition; scarcity becomes interesting when choosing irrigation, treatment, storage and travel supplies. A repair quest changes actual flow or available reserves, with an NPC response after recovery. A decorative pipe is not enough. Offline catch-up must be bounded and its consequences explained; pet loss while absent needs a separate approved policy.

**Acceptance:** drawing and delivery reduce the actual source reserve; treatment transforms the correct quantity; a thirsty animal ceases production; replenishment resumes it without an infinite catch-up reward. Failure or retry must not consume twice.

## 7. M05 — gathering, crafting and the economy

**Existing:** the shared working economy has 29 logical item IDs, 14 recipes and ten stations; its storyline describes forage → processing → ore → refining → tools, ark parts and pet gear. These are much fewer than the art catalog's visual assets. The source audit preserves that distinction.

**Proposed item definition:** every usable item needs a realm-qualified gameplay ID, display name, tab/category, stack and equipment rules, acquisition source, valid targets, effect, duration/cooldown where relevant, consumption/repair rules, save representation and an art binding. A mesh with “tonic” in its name does not establish those facts.

**Crafting transaction:** choose a recipe/station → preview costs and outputs → validate ownership, capacity, resources and station state → consume and grant once → update the journal. Failed preconditions consume nothing. Timed crafts persist start/progress/result without generating another output on reconnect. Quantities, variants and cosmetic skins are separate.

**Progression:** wood/fiber makes basic tools and rigging; ore and fuel unlock metalwork; refined material improves expeditions and repairs. Reuse the existing 14 recipes first. Add a recipe only when its result has a real consumer, use or sink. Trade routes should solve differences between island supplies, rather than give every settlement an identical shop.

**Proposal:** trade essential surplus, repair tools and improve transport before introducing market speculation. Player-facing economic consequences stay separate from blockchain ownership/deployment work. No assumption that all crafted items are on-chain, or that owning a token supplies free resources.

**Acceptance:** one complete chain, such as hardwood → charcoal → smelted metal → useful repair, is playable and persistent. Test insufficient fuel, full inventory and an interrupted craft.

## 8. M06 — local herb systems, kept distinct

The islands already have several original recipe grammars. Preserve their identities, share the common consumption/effect infrastructure, and teach each grammar through its story. Values below are source rules or design descriptions, not proof of every station in Play.

| Place / source | What the player learns | Existing rule | Proposed story payoff |
|---|---|---|---|
| Sol Reach / Ring Infusion | Position and closure | Three ordered herbs; matching ends close the ring, center determines effect; distinct outer/center doubles duration; valid brew consumes actual herbs and clean water | Repair a spring seal and earn the Keeper's trust |
| Orrery Reach | Time and constellation | 24 hourly blooms; one-herb tea, paired constellation brew, day/night eclipse combinations; clean water | Recover charts and restore the telescope |
| Kennel Isle | Care and compatibility | Up to three herbs, 100 canonical recipes; coat/drinker/stage/charm matter; TONIC 1 includes modifiers, grants, mode and breeding chance | Keep a companion expedition-ready |
| Buffffff Island | Layer order | Up to six layers; bottom/top fuse, middle extends duration; water/honey sealing; ordinary seventh layer spoils | Sustain a herd through hardship |
| Prometheus | Harmony | Pitch relationships form herb chords; island song and creature calls share a genetic theme | Restore a listening garden |
| Recording Isle | Melody | Ordered rising/falling/arch/valley contours; returning cadence purifies | Recover a voyage's forgotten song |
| Blender Boss Island | Spatial planning | Core gives strength, weave adds an effect, drift extends duration | Restore water to the spiral workshop |
| Tideglass / Pootscoot | Hydraulic routing | Hydraulic/phase-routing concept noted in existing sources; exact rule must come from its owner | Make a reliable crossing from failing channels |
| Pythagoras | Succession | Maintain pioneer, meadow, scrub and climax stages; stages supply different herbs | Wake the Climax Seed and move acorns by ark |
| Hephaestus | Tempering | Magma favors strength, spring favors duration; dual quench within ten seconds gives dual effect | Repair hull rivets while keeping the pens watered |
| OddsReaper | Probability | Guaranteed base plus chance-driven jackpot; parlay, caps and reroll exceptions are explicit in current JSON | Learn risk through a recoverable experiment |
| DiskSaver | Resource balance | Named teas, drying/compression and a balance of water, animals and herbs | Recover a keeper's memory while maintaining supplies |

**Reconciliations:** Buff's later catalyst proposal allows a special over-six effect, while the basic rule spoils at seven. Treat catalyst use as an explicit exception needing a recipe, not an accidental blanket removal of the limit. OddsReaper's newer data corrects its older “flat +20% for every herb” story; caps and rerolls produce different expectations. Audio AUD 1 currently transports ambience/calls/cues, not herb-chord gameplay. Do not present it as a implemented brewing endpoint.

**Proposed shared feedback:** show ingredients in spatial/order form, let the player read the pattern, and save successful discoveries. Preserve intentionally different failure rules: Sol rejects without consumption; generic murky brews and Buff's spoiled overstack have different outcomes. State them before a player commits.

**Acceptance:** perform one correct recipe, one incorrect recipe and one save/reload for each enabled station, checking actual effects and resource changes. A recipe calculation endpoint alone does not prove inventory consumption or effect application.

## 9. M07 — combat, party development and enemy intelligence

**Existing:** the Portal Realm has a hero/sage/scout party, turn-based commands, levels, gear, spells, ambush tables and dungeon guardians. The 3D world has its own real-time weapons and tactics work. Both can share content concepts without sharing timing or balance rules.

**Portal Realm direction:** simple readable choices, a dangerous field beyond a safe town, clues that reward attention, a party whose members solve different problems, and equipment that changes decisions. Retain FIGHT/SPELL/ITEM/DEFEND/RUN, consumable key tiers, placed story keys and generated but finishable dungeons. The existing castle and three-floor cave provide the first complete adventure; do not replace them with an unconnected new campaign.

**Proposed discovery additions:** recognizable landmarks at route branches, clues grounded in the generated map, optional shortcuts opened by knowledge or equipment, and repeatable signs of danger before a difficult region. Combat teaches threats before combining them. Critical progression never depends on a rare random drop.

**Real-time direction:** local C++ handles immediate movement, hit reactions and combat; Java may select slower squad intentions from known state. Enemies should communicate readable actions, not punish the player using invisible knowledge. Preserve the existing adaptive director rather than write another combat brain. Remote director failure must not freeze a fight.

**Acceptance:** a new player can understand why they lost; defensive actions matter; a forced-disconnect test leaves a safe fallback; local and remote evidence are reported separately. “12/12 tactics” from a team report is evidence for that scenario, not certification of every combat feature.

## 10. M08 — ecology, livestock, pets and memory

**Existing:** arks move finite living populations; habitat governs settlement. Food/water loops and inherited coats/songs already have their own data and engines. Pythagoras's succession work, the limited Living World keeper simulation and companion care are related but different layers.

**Proposed player-facing integration:** show which need is blocking an animal's production, which habitat a transported species needs, and how a repair changed a settlement. A pet's inherited coat is an identity, not a dyeable equipment skin. Cosmetic equipment can change without rewriting the genome.

Memory begins with a few concrete facts: you delivered water, restored a route, protected a herd, or helped an ark land. NPCs can greet you accordingly and offer a relevant follow-up. Do not require continuous language-model calls to maintain these facts. Drought, shortages and restoration quests should follow actual resource state.

**Open boundary:** ordinary livestock mortality, pet death, companion recovery and unicorn protection are not interchangeable. Existing island drafts disagree about death after neglect. Proposed default for review: named companions withdraw or require recovery rather than permanently vanish during an offline absence; livestock policy remains realm-specific and explicit.

**Acceptance:** supply and population totals are conserved across an ark voyage; no animals are copied. An NPC remembers a verified action after restart. A blocked action explains habitat or resource requirements.

## 11. M09 — unicorn helpers, groups and the mountain alpha

**Confirmed:** unicorn NPCs help, defend and point the player in the right direction. Half the unicorns encountered are intended to be in male-female pairs. Other groups are female-only; no male-only groups. Ordinary packs can reach eight, but that size is rare. Ordinary unicorns fear burning bulls; the alpha in the mountains is exempt.

**Current art:** 500 static variants have been built from the shared horse, with ten palettes and fifty proportions per palette. Each is 1,016 triangles. There are no skeletal animations or implemented behavior merely because these files exist.

**Current content assignment, not a final spawn algorithm:** 250 individuals occupy 125 mixed pairs; the remaining 250 are female, including ordinary herds and the twelve-member exception. The art's alpha is provisionally a female in the eight-member herd. The user did not specify alpha sex or a particular model. Keep the distinction visible.

**Proposed state priority:**

1. Ordinary unicorn sees a threatening burning bull → interrupt guidance/ordinary defense and seek a reachable safe route with its group.
2. Mountain alpha sees the same threat → remain composed and protect a safe approach; its exact attack/ward behavior is proposed, not specified.
3. Other immediate threat to the player → defend within a bounded range, then regroup.
4. Safe player requests direction → face the correct route, move to a short visible waypoint, look back and wait.
5. No request/threat → graze, socialize and remain available.

No group teleports the player to an undiscovered realm. Guidance does not require the player to capture, purchase or harm a unicorn. Failed navigation chooses a safe waiting point instead of leading someone over an edge. Fear should read as an intentional exception, with animation, distance and a brief journal explanation; it should not look like broken ally AI.

**Proposed population model:** pairs and herds are persistent social groups, not a random sex reroll each time the camera looks away. The 500 models are a catalog, not 500 simultaneously active AI. Spawn nearby groups from habitat budgets and preserve identity as they stream out.

**Decision needed:** does “50 percent” mean individual unicorns seen over time, or half of encounters being mixed pairs? The current art follows individuals. Real encounter weights must be tuned after that decision; a catalog fraction cannot prove a play-session probability.

## 12. M10 — ten burning bulls and the herd of twelve

**Confirmed reward condition:** drive ten burning bulls into the sea and find a pack of twelve unicorns to receive a chest full of the game's strongest legendary items. The twelve is an explicit exceptional herd above the normal eight limit. Under the current grouping rule it is female-only.

**Proposed quest title:** *The Last Ember, the Twelve Lights*. Story treatment appears in [Storyline](STORYLINE.md). The conditions are fixed; the presentation and reward names below are proposals.

**Playable sequence:** learn why ordinary unicorns retreat → seek the mountain alpha → learn a safe herding route → redirect burning bulls along several coastal routes → discover the twelve and claim their chest. Do not require ten identical short runs through the same corridor. The sea remains the actual goal; a pond, a kill or a despawn is not substituted.

**Proposed bull outcome:** seawater extinguishes the unnatural fire and the bull survives on a safe shore. This connects the task to restoration and avoids asking the player to destroy the creatures they are learning to help. It is a story proposal for review, not an already confirmed rule.

**Quest state:** locked/rumored → discovered → progressing, with a set of unique credited bull IDs and a separate herd-discovery flag → eligible when both conditions hold → chest awarded. Finding the herd first should record discovery and provide a clue, not permanently fail the quest. The chest becomes available on the next valid meeting after ten credits; the exact presentation is for review.

**Credit rules proposed:** the authoritative host verifies a qualifying burning bull, player participation in its drive, and its sea arrival. Repeated sea entries by one bull count once. Death, teleport/debug spawning and another player's unrelated event grant nothing by default. Co-op contribution rules require a deliberate choice; proximity alone is not assumed sufficient. Persist the count and discovery separately across sessions.

**Proposed chest composition:** one exceptional weapon, one protective item, one traversal/reconnaissance relic and one companion-support relic, all valid in this quest's realm. Suggested identities are *Dawnwake* (turn a defensive opening into a sweeping counter), *Twelvefold Mantle* (survive a lethal mistake and rally), *Prism Spur* (a powerful contextual traverse), and *Keeper's Bell* (call a protective unicorn response). Names, slots, exact quantities, damage and cooldowns are unapproved. They must feel stronger than ordinary rewards; do not quietly reduce the user's “best items” ask to cosmetic loot.

Protect other realms through explicit transfer rules rather than secretly weakening the reward. The chest cannot overwrite equipment or lose items when the bag is full: proposed protected reward storage retains unclaimed contents. Grant and claim are persistent, idempotent operations; the default proposal is one award per character/realm until repeatability is decided.

**Acceptance:** test 9/10 versus 10/10, herd discovery in either order, ordinary pack of eight versus the designated twelve, duplicate bull events, reconnect, full inventory and two simultaneous claim requests. Then show the player obtaining and actually using the legendary items. A counter or a spawned chest mesh alone is insufficient.

### Ordinary unicorn quests

**Confirmed:** players can complete quests for unicorns and earn rewards. Proposed quests in Storyline section 8 include restoring drinking water, reuniting a separated pair, restoring grazing habitat and learning a rainbow route. Give each a real completion fact, realm-valid item reward and persistent receipt. Ordinary quests complement the legendary chain; they do not replace its ten-bull and twelve-herd conditions. Repeatable supplies should respond to actual need, not permit endless rewards for empty interactions.

## 13. M11 — quests, dialogue and discovery

**Existing:** seven-step onboarding, named quests in `data/quests/quests.json`, Sol's action-based Broken Circle, Orrery's Keeper's Logbook and the succession chapters already provide material. Preserve their identities while fitting them into the campaign.

**Proposed quest format:** an observable world need, a clear verb, tracked prerequisites, a real consequence, a recovery path and a reward. Dialogue explains why; interaction verifies what happened. “Visit the filter” is not “purify water.” “Own a herb” is not “brew correctly.” Every progression-critical clue should be available through more than one understandable route, such as dialogue plus an environmental diagram.

Keep optional local stories optional. Players may see the main rainbow arc without mastering every herb language. Use a story journal with current intent, learned clues and the last relevant NPC; avoid filling it with hundreds of uncurated asset names. Repeatable jobs should describe actual demand, with caps and recovery so players cannot manufacture an endless shortage reward.

## 14. M12 — sound, weather and presentation

**Existing:** use the touring jukebox, existing realm cue vocabulary, creature-call synthesis and biome ambience. AUD 1 carries a musical cue, ambience layers and PCS 1 call parameters. Pootscoot is implementing the native consumer. Track selection and genotype music remain existing jukebox responsibilities.

**Proposed direction:** each realm's rainbow shares a restrained visual motif with a short audio motif. It is occasionally recognizable, never a constant loud waypoint beacon. A unicorn's warning can briefly interrupt calm ambience when a burning bull approaches. The alpha's presence changes the response from panic to steadiness, not necessarily the overall music volume.

Town, exploration, cave and combat cues change with meaningful state; don't restart the track every poll. Music must be independently adjustable from effects and dialogue. Required clues remain usable while muted. Loading, unavailable audio bindings and jukebox outages cannot stall gameplay.

## 15. M13 — progression, defeat and persistence

Each realm defines its own experience, equipment strength and failure consequences. Preserve the Portal Realm's existing defeat behavior separately from the survival draft's no-inventory-drop respawn. A common UI can communicate both without merging their rules.

**Proposed shared progress:** a travel journal records discovered rainbows, relationships and major restoration decisions. Realm saves retain inventory, opened chests, local quests, companion state and locations. Completions that grant things use persistent receipts. A lost response should be safely retried; it must not grant twice or consume again.

Capacity upgrades, new routes, better knowledge and reliable allies supplement combat strength. The legendary chest is a late mastery reward, not the tutorial's mandatory equipment. Further moons and space are a future hook, not required scope for the first complete campaign.

## 16. Account for the existing items before authoring more

### M14 — Dungeon Master inside the Labyrinth

**Confirmed:** integrate the existing AI Dungeon Master game into Daedalus's already planned dungeon/maze realm, prepare a C++ bridge and Blender art, and hand the tested slice to Claude for Unreal.

**Located:** `RicheyWorks/ai-dungeon-master`, also in the local projects folder. The GitHub baseline inspected is `9dadff2f69eb4e8d504f0044130b5fada6f74f43`; the local checkout is older and has unrelated edits. The current `/v2/status` and `/v2/action` return version-one typed JSON envelopes. Authenticated sessions select isolated engines; unauthenticated calls share a default engine. This matters for a realm integration and is not inferred from the older README.

**Proposed division:** existing Daedalus maze generation and native movement build the room; Dungeon Master supplies party/quest status, available choices, remembered narrative and turn outcomes. The UI displays offered choices rather than sending arbitrary commands. Narration describes authoritative results; it cannot independently grant loot or change the Unreal world. Bind a reviewed scene/event ID to a room response instead of parsing free-form prose as an instruction.

**First C++ slice:** explicit configured service/session, bounded status decoding, one pending request, stale-response rejection, only currently advertised choice labels, retained last valid display on failure, and no automatic replay of a possibly committed action. No session creation, reset, save deletion, pack upload or model-key configuration is needed for the first consumer. The pilot is one party in one Labyrinth session; multiplayer world consequences need their own authoritative mapping.

**First Blender slice:** a small reusable encounter kit built from existing dungeon art where available: a narrator lectern, route marker, choice plinths, archive/reward anchor and a portal frame. Each has a named role; no wall kit is duplicated merely to inflate asset count. The delivery manifest records exports and what remains unimplemented.

**Acceptance:** show a real Dungeon Master status, choose a real offered action, display the resulting party/quest state, preserve the previous state on refusal, and prove that a late response from a previous connection cannot overwrite the current session. Link the chosen event to one visible room response in Play. Server rewards and inventory transfer remain separate, reviewed transactions.

The workbook snapshot contains **10,862 unique asset names**. A second tracker contains **763 explicit mechanic descriptions**, of which **752** exactly match the master names. Eleven tracker entries are absent from MASTER; 500 new unicorn variants are outside both sheets. The accompanying register therefore accounts for **11,373 distinct art IDs**, without pretending they are 11,373 usable gameplay items.

| Catalog group | MASTER entries | Proposed mechanical treatment |
|---|---:|---|
| Fauna/livestock | 2,895 | Group variants under species/archetypes; bind AI, habitat, care and products deliberately |
| Props (other) | 1,465 | Separate decoration from interactable machinery; not every prop needs a mechanic |
| Flora | 1,423 | Bind harvest/regrowth stages or explicitly label decorative |
| Herbs | 1,265 | Bind to the correct island grammar; preserve ingredient IDs across visual growth stages |
| Water | 953 | Distinguish source, treatment, storage, transport and vessel roles |
| Food/crops | 679 | Define edible state, inputs, growth, spoilage and outputs |
| Ores/materials | 635 | Define acquisition tier and an actual crafting consumer |
| Items (other) | 339 | Resolve realm, inventory category and action before activation |
| Chests/containers | 228 | Define capacity, ownership and reward semantics separately from mesh size |
| Vehicles/arks | 208 | Bind transport ability, route, cargo and boarding state |
| Buildings | 191 | Distinguish habitat, workshop, shop and decoration |
| NFT landmarks | 158 | Present identity/lore; do not assume they grant gameplay power |
| Weapons/armor | 134 | Bind equipment slots, combat rules, tier and repair semantics per realm |
| Tools | 120 | Bind allowed targets, speed/tier and durability where used |
| Sky | 87 | Separate scenery from weather effects and navigable gateways |
| Other | 82 | Owner classification required before gameplay use |
| **Total** | **10,862** | Complete source enumeration in the register |

New ideas should normally consume these assets and systems. Create new art only for an identifiable missing silhouette, interaction or story identity. The legendary chest needs its own item definitions and distinctive presentation; a renamed ordinary sword without a new ability would not fulfill the reward promise.

## 17. Build sequence and review gates

| Slice | Concrete player outcome | Reuse first | Done when |
|---|---|---|---|
| A. Content identity | A real item displays correct details in two realm inventories | Existing catalogs, inventory cores and HUD | Counts/save/load/filter/equip pass in both realms |
| B. First home | Player drinks, makes one repair and completes a real recipe | Sol rules, water/crafting, current NPCs | Action changes resources and NPC response persistently |
| C. First rainbow | Player follows subtle dust, reaches the right gate and returns | Paired gates, mounts, Sky Director | Correct destination, safe arrival, readable quiet clues |
| D. First unicorn | One mixed pair guides and defends; fears the burning bull | Shipped horse/unicorn art, creature rendering/navigation | Player-visible states and safe group navigation |
| E. Mountain exception | Player recognizes the alpha and learns herding | Same NPC system with explicit role override | Ordinary fear and alpha response differ reliably |
| F. Legendary quest | Ten distinct drives and the twelve herd yield usable best-tier gear | Quest/save/inventory transaction systems | All credit/reward tests plus a complete Play demonstration |
| G. Wider network | Several local arcs reconnect communities | Existing island-specific mechanics and jukebox | Route, consequence and return trip matter in each arc |

Java owns durable world/quest decisions and reusable calculations; native Unreal C++ owns immediate movement, animation, interaction and presentation. Blender supplies reusable art. Shared fixtures define boundaries. Owner assignments and current claims belong to the team board, not to an invented parallel management system in this document.

## 18. Decisions for Richey's review

| Decision | Recommended review choice | What it controls |
|---|---|---|
| Campaign premise | Reconnect and sustain the fragments; do not physically reassemble the planet in phase one | Main story stakes and ending |
| Old local portals | Keep them as local/discovered-rainbow access points | Compatibility with built Portal Realm entrances |
| Unicorn 50% | Measure individuals encountered, matching current content assignment | Spawn weighting and encounter accounting |
| Mountain alpha | Keep sex/name open; current female assignment is provisional | Character design, not general herd rules |
| Bull fate | Fire extinguished, animal survives | Quest tone and completion visuals |
| Legendary chest | One persistent award per character/realm, protected storage; contents subject to review | Reward exploitation, co-op and item definitions |
| Cross-realm items | Explicit opt-in transfers, otherwise preserve separate bags | Balance and loss/duplication prevention |
| Defeat and companions | Realm-specific player defeat; recoverable named companions proposed | Stakes without accidental offline loss |
| Main-path breadth | One complete home → rainbow → realm → return arc before multiplying realms | Production order and proof quality |

The proposed story supplies concrete missions, characters and consequences for these mechanics. Richey's decisions should be incorporated here first, then translated into small owned builds and observable acceptance tests.
