// SPDX-License-Identifier: MIT

package com.daedalus.world.retro;

import com.daedalus.world.retro.RetroRealm.Entry;
import com.daedalus.world.retro.RetroRealm.Zone;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Encounter zones (ADR-052): which monsters roam where, how many come together, and how often they find you.
 *
 * <p>The field is cut into rings around the portal (the further from home, the tougher), with the hills, the
 * forests and the swamp keeping their own tables wherever they are; each cave floor has its own. Weights carry the
 * rarity: a lucky drip turns up about once in fifty fights in the middle ring and is worth more than twenty slimes.
 * {@code rate} is the average number of steps between fights; forests, hills and swamps count a step and a half
 * (the core applies that).
 */
public final class RetroEncounters {

    public static final char NEAR = '0';
    public static final char MIDDLE = '1';
    public static final char FAR = '2';
    public static final char HILLS = '3';
    public static final char SWAMP = '4';
    public static final char FOREST = '5';
    public static final char CAVE1 = '6';
    public static final char CAVE2 = '7';
    public static final char CAVE3 = '8';

    private RetroEncounters() {
    }

    /** Every zone the realm uses. */
    public static List<Zone> zones() {
        List<Zone> z = new ArrayList<>();
        z.add(new Zone(NEAR, 22, List.of(
                new Entry(RetroMonster.BLIGHT_SLIME, 50, 1, 3),
                new Entry(RetroMonster.DUST_WISP, 30, 1, 2),
                new Entry(RetroMonster.PUFFCAP, 20, 1, 2))));
        z.add(new Zone(MIDDLE, 20, List.of(
                new Entry(RetroMonster.BLIGHT_SLIME, 20, 2, 3),
                new Entry(RetroMonster.DUST_WISP, 20, 1, 3),
                new Entry(RetroMonster.PUFFCAP, 15, 1, 2),
                new Entry(RetroMonster.SHARDBACK, 20, 1, 2),
                new Entry(RetroMonster.EMBER_WISP, 12, 1, 2),
                new Entry(RetroMonster.BOG_SLIME, 10, 1, 2),
                new Entry(RetroMonster.LUCKY_DRIP, 2, 1, 1))));
        z.add(new Zone(FAR, 18, List.of(
                new Entry(RetroMonster.SHARDBACK, 18, 1, 3),
                new Entry(RetroMonster.EMBER_WISP, 18, 1, 3),
                new Entry(RetroMonster.GLASSBACK, 14, 1, 2),
                new Entry(RetroMonster.SHADECAP, 14, 1, 2),
                new Entry(RetroMonster.STARE_ORB, 12, 1, 2),
                new Entry(RetroMonster.MOSS_KNIGHT, 10, 1, 1),
                new Entry(RetroMonster.LUCKY_DRIP, 3, 1, 2),
                new Entry(RetroMonster.STONE_KNIGHT, 3, 1, 1))));
        z.add(new Zone(HILLS, 16, List.of(
                new Entry(RetroMonster.SHARDBACK, 40, 1, 3),
                new Entry(RetroMonster.GLASSBACK, 15, 1, 2),
                new Entry(RetroMonster.MOSS_KNIGHT, 8, 1, 1),
                new Entry(RetroMonster.LUCKY_DRIP, 2, 1, 1))));
        z.add(new Zone(SWAMP, 14, List.of(
                new Entry(RetroMonster.BLIGHT_SLIME, 25, 2, 3),
                new Entry(RetroMonster.BOG_SLIME, 35, 1, 3),
                new Entry(RetroMonster.PUFFCAP, 15, 1, 3),
                new Entry(RetroMonster.SHADECAP, 15, 1, 2))));
        z.add(new Zone(FOREST, 20, List.of(
                new Entry(RetroMonster.PUFFCAP, 35, 1, 3),
                new Entry(RetroMonster.DUST_WISP, 25, 1, 2),
                new Entry(RetroMonster.GLOOMWING, 25, 1, 3),
                new Entry(RetroMonster.SHADECAP, 10, 1, 1))));
        z.add(new Zone(CAVE1, 14, List.of(
                new Entry(RetroMonster.GLOOMWING, 35, 1, 3),
                new Entry(RetroMonster.SHARDBACK, 25, 1, 2),
                new Entry(RetroMonster.BOG_SLIME, 20, 1, 2),
                new Entry(RetroMonster.STARE_ORB, 15, 1, 1),
                new Entry(RetroMonster.LUCKY_DRIP, 3, 1, 1))));
        z.add(new Zone(CAVE2, 13, List.of(
                new Entry(RetroMonster.GLOOMWING, 20, 2, 3),
                new Entry(RetroMonster.STARE_ORB, 22, 1, 2),
                new Entry(RetroMonster.GLASSBACK, 20, 1, 2),
                new Entry(RetroMonster.MOSS_KNIGHT, 18, 1, 2),
                new Entry(RetroMonster.LUCKY_DRIP, 4, 1, 2))));
        z.add(new Zone(CAVE3, 12, List.of(
                new Entry(RetroMonster.STONE_KNIGHT, 25, 1, 2),
                new Entry(RetroMonster.MOSS_KNIGHT, 25, 1, 2),
                new Entry(RetroMonster.STARE_ORB, 20, 1, 3),
                new Entry(RetroMonster.GLASSBACK, 20, 1, 3),
                new Entry(RetroMonster.LUCKY_DRIP, 5, 1, 2))));
        return z;
    }

    /**
     * Roll one fight in {@code zone}, the way the core does: a leader by weight, a group of its kind, and one time in
     * three a stranger from the same table joins (never past three monsters).
     */
    public static List<RetroMonster> roll(Zone zone, SplittableRandom rng) {
        List<RetroMonster> group = new ArrayList<>();
        Entry lead = pick(zone, rng);
        int n = lead.min() + rng.nextInt(lead.max() - lead.min() + 1);
        for (int i = 0; i < n; i++) {
            group.add(lead.monster());
        }
        if (group.size() < 3 && rng.nextInt(3) == 0) {
            group.add(pick(zone, rng).monster());
        }
        return group;
    }

    static Entry pick(Zone zone, SplittableRandom rng) {
        int r = rng.nextInt(zone.totalWeight());
        for (Entry e : zone.entries()) {
            r -= e.weight();
            if (r < 0) {
                return e;
            }
        }
        throw new IllegalStateException("weights did not add up");
    }
}
