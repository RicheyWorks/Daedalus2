# Kennel Isle trough -> tonic engine contract (art-master-flex)

Original Java engine: art-master-flex. Java endpoint/contract: team-codex (Astra), per the active two-team lanes. Native/Unreal execution: unreal-team (Claude).

The implemented endpoint and authoritative multiline TONIC 1 grammar are documented in
[contracts/tonic-v1](contracts/tonic-v1/README.md), with exact HTTP success/refusal fixtures.
It is a pure host-authorized calculation, not an inventory or trough-decay transaction.

## Java API (daedalus-core, `com.daedalus.world.companion`)
- `TonicBook.load(Path tools/islands/kennel-isle/tonics.json)`: 100 recipes, 12 herbs, max 3 herbs.
- `TonicBrewer.brew(Collection<String> herbs, String coat, String drinker, int stage, boolean charm)` -> `Optional<Brew>`.
- `TonicBrewer.brew(..., long seed)` -> `Optional<RolledBrew(brew, secondRoll)>`: Labyrinth coat gets a deterministic 10% second roll (factor x2, capped at 2). Seed = e.g. trough actor id ^ brew tick.
- `Brew(recipe, factor, mods[stat, op add|mul, value], durationSec)`; `TroughBrew` tracks decay (3 drinks / 10 min).
- coat: Spots | Stripes | Labyrinth | None. drinker: `cane_corso` (1.0), `packMember` (0.5), other.

## Unreal side (Island_AMF)
- Trough actor: tag `Brew_Trough` (+ `Tonic_*` data tags). Herbs: `Prop_Herb_AMF_*` with `Herb_Source` and `Tonic_Herb_<Name>`.
- Proposed call: on interact, collect up to 3 `Tonic_Herb_<Name>` from deposited herbs, call brew(herbs, pet coat, drinker kind, stage, charm, seed), apply mods to the companion for durationSec.
- Transport: POST `/api/v1/kennel/brew`, JSON inputs and text/plain TONIC 1 output. The final multiline contract carries mode, grants and breeding chance as well as scaled modifiers; the former one-line suggestion is superseded.

## Native side (art-master-flex, Oct 18): the trough calls Java

Files (all in `engines/unreal/DaedalusLink`, plain-C++ core + thin Unreal layer, new files only):

| File | What |
|---|---|
| `Public/DaedalusTonicCore.h` | No Unreal types. TONIC 1 request writer (byte-exact with `barkbalm-request.json`, signed 64-bit seed kept exact), strict all-or-nothing reply parser with the contract bounds (4096 B / 512 B line / 64-char ids / 32 mods / 32 grants), trough state (3 herbs, steep, 3 drinks or 10 min), per-pet effect ledger, seed derivation, drinker-from-tags. |
| `Public/DaedalusTonic.h`, `Private/DaedalusTonic.cpp` | `UDaedalusBrewTroughComponent`, `UDaedalusTonicEffects`, `UDaedalusTonicSubsystem`, console `daedalus.tonic.steep` / `daedalus.tonic.status`. |
| `core-test/tonic_core_test.cpp` | Checks the core against `docs/contracts/tonic-v1` fixtures (g++/clang, ASan+UBSan in CI). |

Flow (no level edit needed; the subsystem adds the component to the placed `Brew_Trough` actor at BeginPlay, preferring the one tagged `Interact_Brew`):

1. `DepositHerbActor(plant)` / `DepositHerb("Barkbalm")` reads `Tonic_Herb_<Name>` (max 3, no duplicates).
2. `Interact(player)` **steeps**: one `POST /api/v1/kennel/brew` with the herbs, the Corso as the reference drinker and a host-chosen seed. HTTP 200 + a valid TONIC 1 reply locks the herbs and starts the trough (3 drinks, flat after 10 min). Any refusal (422 no recipe, 400, 401/403, 429, timeout, bad reply) keeps the herbs and spends nothing.
3. A pet **drinks** (`Drink(pet)`, or automatically when a tagged pet is within `Reach` and `bAutoDrink`): one more POST with *that pet's* coat / drinker kind / stage / charm, seed = `DeriveSeed(troughName, steepNo, drinkNo)`. The reply is applied once to the pet's `UDaedalusTonicEffects`; a failed or refused drink gives the drink back.
4. `UDaedalusTonicEffects` holds the mods (`GetStat(stat, base)` = (base + adds) x muls), grants (`HasGrant("swim")`, `livestockWaterCross`) and breed chance until `durationSec`; the same recipe refreshes instead of stacking; `pulse` tonics hand their mods out once through `OnTonicPulse`.
5. Credentials are never saved: `ConfigureSession(origin, token)` or the environment variables `DAEDALUS_KENNEL_ORIGIN` / `DAEDALUS_KENNEL_TOKEN` (https anywhere, http only to 127.0.0.1; the server must have `daedalus.kennel.host-subject` set to that token's subject). Redirects are refused. The calls are asynchronous (off the game thread).

Who is a pet (tags the Kennel Isle scripts / a later editor pass set): `AMF_Companion` + `Cane_Corso` (editor labels containing `CaneCorso` also work), `Pack_Member`, `Coat_Spots` | `Coat_Stripes` | `Coat_Labyrinth`, `Stage_2` | `Stage_3`, `Tonic_Charm`. Untagged animals count as `other`, coat `None`, stage 1.

Still open (needs the editor, ask codex-play-guard for editor time): tag the placed pets with `Cane_Corso` / `Coat_*` / `Stage_*` so coat scaling is visible, and a PIE run of `daedalus.tonic.steep Barkbalm Pawmint` against a Java host.
