// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.parlay;

import com.daedalus.world.fishing.AnglerSkill;
import com.daedalus.world.fishing.Conditions;
import com.daedalus.world.fishing.FishSpecies;
import com.daedalus.world.fishing.FishTable;
import com.daedalus.world.fishing.FishingOdds;
import com.daedalus.world.odds.OddsRng;
import java.util.ArrayList;
import java.util.List;

/**
 * The Odds Keeper's chalkboard at the OddsReaper Island inn. Each island day the keeper chalks up seeded Storm Parlay
 * tickets: 1 to {@code maxLegs} named catches priced from the true {@link FishingOdds} for that day's sky, offered at
 * fair odds less a house edge of at most {@value #HOUSE_EDGE}. The same (island seed, day) always gives the same board,
 * so every player on the island reads the same chalk. Long shots below {@value #MIN_PROBABILITY} are wiped and redrawn.
 */
public final class ParlayBoard {

    /** The keeper's largest cut: 5%. Players are told; the offer is never worse than 95% of fair. */
    public static final double HOUSE_EDGE = 0.05;
    /** Tickets less likely than this are not chalked (the keeper will not sell a 1-in-10,000 dream). */
    public static final double MIN_PROBABILITY = 1e-4;
    /** Redraws allowed per ticket before the board gives up on that slot. */
    static final int MAX_REDRAWS = 64;

    private ParlayBoard() {
    }

    /**
     * The board for one island day.
     *
     * @param table      the fish that bite at the inn's spot today
     * @param islandSeed the island's seed
     * @param day        island day number (>= 0)
     * @param sky        today's conditions (a storm is what brings the crowds)
     * @param reference  the angler skill tickets are priced for (the keeper uses {@link AnglerSkill#STEADY})
     * @param tickets    how many tickets to chalk (1-12)
     * @param maxLegs    longest parlay (1-4)
     */
    public static List<ParlayTicket> daily(FishTable table, long islandSeed, int day, Conditions sky, AnglerSkill reference,
                                           int tickets, int maxLegs) {
        if (day < 0) {
            throw new IllegalArgumentException("day must be >= 0, got " + day);
        }
        if (tickets < 1 || tickets > 12) {
            throw new IllegalArgumentException("tickets must be 1-12, got " + tickets);
        }
        if (maxLegs < 1 || maxLegs > 4) {
            throw new IllegalArgumentException("maxLegs must be 1-4, got " + maxLegs);
        }
        FishingOdds.Breakdown odds = FishingOdds.exact(table, sky, reference);
        List<FishSpecies> fish = table.fish();
        OddsRng rng = OddsRng.forTrial(islandSeed, day);
        double edge = HOUSE_EDGE * rng.nextDouble();
        List<ParlayTicket> out = new ArrayList<>();
        for (int n = 0; n < tickets; n++) {
            for (int tries = 0; tries < MAX_REDRAWS; tries++) {
                int legCount = 1 + (int) (rng.nextDouble() * maxLegs);
                List<String> legs = new ArrayList<>();
                double p = 1;
                for (int k = 0; k < legCount; k++) {
                    String name = fish.get((int) (rng.nextDouble() * fish.size())).name();
                    legs.add(name);
                    p *= odds.catchShare(name);
                }
                if (p >= MIN_PROBABILITY) {
                    double offered = Math.max(1.0, (1 - edge) / p);
                    out.add(new ParlayTicket("D" + day + "-T" + (n + 1), day, sky, legs, p, offered));
                    break;
                }
            }
        }
        return out;
    }
}
