// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.breeding;

import java.util.Locale;

/**
 * The Odds Keeper's third quest, "The Stormcoat": raise a storm-marked Turing-coat pup. Before each pairing she tells
 * the player the true odds; the quest is done the first time a storm-marked pup is born. Mutable, one per save.
 */
public final class StormcoatQuest {

    private int litters;
    private int pups;
    private boolean done;

    /** What the Keeper says before a pairing. */
    public static String advice(Genotype mother, Genotype father) {
        double p = CoatOdds.stormMarkedChance(mother, father);
        if (p == 0) {
            return "Those two will never throw a stormcoat. Look for a carrier.";
        }
        return String.format(Locale.ROOT, "%s with %s: %.1f%% of pups come storm-marked, about one in %d.", mother, father,
                100 * p, Math.round(1 / p));
    }

    /** Records a born litter. Returns true when this litter finishes the quest. */
    public boolean record(Iterable<Genotype> litter) {
        litters++;
        boolean finished = false;
        for (Genotype g : litter) {
            pups++;
            if (!done && g.coat().stormMarked()) {
                done = true;
                finished = true;
            }
        }
        return finished;
    }

    public boolean done() {
        return done;
    }

    public int litters() {
        return litters;
    }

    public int pups() {
        return pups;
    }
}
