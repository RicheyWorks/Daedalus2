// SPDX-License-Identifier: MIT

package com.daedalus.world.retro;

import com.daedalus.world.retro.RetroRealm.Loot;

import java.util.List;
import java.util.SplittableRandom;

/**
 * Loot tables (ADR-052): what a chest can hold at each depth of the realm, by weight. Rolled once, when the realm is
 * generated, so a seed always hides the same treasure in the same chest, and the server can prove every chest is
 * reachable before anyone opens one.
 *
 * <p>Tier 1 is near home (town storerooms); tier 2 the cave's upper floors and the castle treasury; tier 3 the cave's
 * depths. The deeper the tier, the more gold, the rarer the gear, and the likelier a chest bites back.
 */
public final class RetroLoot {

    /** One row of a table: a weight, and either a gold range, an item, or a mimic. */
    public record Row(int weight, int goldMin, int goldMax, RetroItem item, RetroMonster mimic) {
        static Row gold(int weight, int min, int max) {
            return new Row(weight, min, max, null, null);
        }

        static Row item(int weight, RetroItem item) {
            return new Row(weight, 0, 0, item, null);
        }

        static Row mimic(int weight, RetroMonster m) {
            return new Row(weight, 0, 0, null, m);
        }
    }

    private static final List<Row> TIER1 = List.of(
            Row.gold(36, 10, 40),
            Row.item(18, RetroItem.HERB),
            Row.item(10, RetroItem.ANTIDOTE),
            Row.item(10, RetroItem.TORCH),
            Row.item(12, RetroItem.BRONZE_KEY),
            Row.item(6, RetroItem.CLUB),
            Row.item(5, RetroItem.LEATHER_VEST),
            Row.item(3, RetroItem.WINGS));

    private static final List<Row> TIER2 = List.of(
            Row.gold(30, 40, 150),
            Row.item(10, RetroItem.HERB),
            Row.item(10, RetroItem.TONIC),
            Row.item(10, RetroItem.BRONZE_KEY),
            Row.item(6, RetroItem.COPPER_SWORD),
            Row.item(4, RetroItem.CHAIN_MAIL),
            Row.item(4, RetroItem.MIGHT_SEED),
            Row.item(4, RetroItem.LIFE_SEED),
            Row.item(5, RetroItem.STAR_SHARD),
            Row.item(2, RetroItem.EMBER_BLADE),
            Row.item(2, RetroItem.SHARD_MAIL),
            Row.mimic(13, RetroMonster.GNASHBOX));

    private static final List<Row> TIER3 = List.of(
            Row.gold(25, 150, 400),
            Row.item(10, RetroItem.TONIC),
            Row.item(15, RetroItem.STAR_SHARD),
            Row.item(8, RetroItem.EMBER_BLADE),
            Row.item(8, RetroItem.SHARD_MAIL),
            Row.item(5, RetroItem.MIGHT_SEED),
            Row.item(5, RetroItem.LIFE_SEED),
            Row.item(10, RetroItem.IRON_AXE),
            Row.mimic(14, RetroMonster.GNASHBOX));

    private RetroLoot() {
    }

    /** The table for a tier, 1 to 3. */
    public static List<Row> table(int tier) {
        return switch (tier) {
            case 1 -> TIER1;
            case 2 -> TIER2;
            case 3 -> TIER3;
            default -> throw new IllegalArgumentException("loot tiers are 1 to 3, not " + tier);
        };
    }

    /** Roll one chest of {@code tier}. */
    public static Loot roll(int tier, SplittableRandom rng) {
        List<Row> t = table(tier);
        int total = t.stream().mapToInt(Row::weight).sum();
        int pick = rng.nextInt(total);
        for (Row r : t) {
            pick -= r.weight();
            if (pick < 0) {
                if (r.mimic() != null) {
                    return Loot.mimic(r.mimic());
                }
                if (r.item() != null) {
                    return Loot.item(r.item());
                }
                return Loot.gold(r.goldMin() + rng.nextInt(r.goldMax() - r.goldMin() + 1));
            }
        }
        throw new IllegalStateException("weights did not add up");
    }

    /** Roll a chest that is never a mimic (for chests the story needs to be real). */
    public static Loot rollHonest(int tier, SplittableRandom rng) {
        Loot l = roll(tier, rng);
        while (l.kind() == Loot.Kind.MIMIC) {
            l = roll(tier, rng);
        }
        return l;
    }
}
