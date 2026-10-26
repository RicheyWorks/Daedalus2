# Kennel Isle: Pack Order (contest gap G26)

Owner: art-master-flex. Story plus the mechanic it runs on. Water side: [KENNEL-QUIET-SPRING.md](KENNEL-QUIET-SPRING.md) (G17).

- Mechanic: `daedalus-core/src/main/java/com/daedalus/world/companion/KennelPantry.java` (daily food ledger + quest check), rules in `data/islands/kennel-food-v1.json`, tests in `KennelPantryTest` (10 tests).
- Source rules: `tools/islands/kennel-isle/ISLAND.md` s3 (goats, hay, kibble) and s5 (`F1_MilkPail` -> `F2_KibbleBin` -> `Feed_0..3`). Until now they were editor tags only.

## Rules
Each hay-fed goat gives 1.5 L of milk. Each watered Starkibble plant gives 1 Starkibble. The kibble bin turns 1 L of milk + 1 Starkibble into 4 portions, as many batches as both allow. Milk spoils at day's end; kibble and Starkibble keep. Four bowls hold 3 portions each (12 a day). Rations: Cane Corso 2, dog 1, pup 1. Pets eat in pack order: the Corso first, then dogs, then pups. Anyone who misses a full ration goes up a hunger stage (10% stat drain per stage, up to 50%), and a full meal resets it.

## Lore
The Cane Corso was on Kennel Isle before anyone else, guarding the spring like it was still on a curb waiting for pickup, and the pack formed around it. So the Corso eats first, and nobody on the island argues. The keepers learned the hard way that when the bin runs short, it's the pups at the back of the line who go without. Starkibble was a weed until someone noticed the dogs digging it up. Now it's half of every meal and the "heart" of the Bond tonic.

## Quest: Pack Order
A storm scatters the herd and the pantry is empty. For three days, feed the pack (Tank the Corso, Rex, Bo and Pip the pup) with whatever goats you can find and feed.
- Goal: nobody goes hungry on any of the three days.
- The math: the pack eats 5 portions a day. One goat (1.5 L, 1 batch, 4 portions) leaves Pip hungry. Two hay-fed goats (3 batches, 12 portions) pass, and the extra carries over. Goats without hay give nothing. Milk without Starkibble is spilled.

## NPC lines
- **Marrow, old Ark keeper** (start): "Storm took the goats up the ridge. Bin's empty. The pack doesn't care whose fault it is. Find milk."
- **Pip, kennel kid** (Pip hungry): "Tank ate, Rex ate, Bo ate... Pip always eats last. That's not fair, is it?"
- **Marrow** (on the order): "Corso first. Always. He held the spring when there was nobody here to hold it for."
- **Marrow** (goat with no hay): "A goat on an empty belly gives you a look, not milk."
- **Marrow** (pass): "Three days, full bowls, and a little left over. That's a kennel. Go scratch Tank behind the ears; he counted every portion."
- **Marrow** (fail): "Somebody at the back went without. Tomorrow, two goats and hay first."

## Later (editor)
Bin and bowl actors (`F2_KibbleBin`, `Feed_0..3`) call the ledger; queued in BOARD\UNREAL-QUEUE.md.
