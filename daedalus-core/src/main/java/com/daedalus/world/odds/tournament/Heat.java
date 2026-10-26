// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.tournament;

import com.daedalus.world.fishing.AnglerSkill;
import com.daedalus.world.fishing.Conditions;
import com.daedalus.world.fishing.FishSpecies;
import com.daedalus.world.fishing.FishTable;
import com.daedalus.world.odds.OddsRng;
import java.util.Objects;

/**
 * One heat of the Squall Cup. Each angler gets the same number of casts; every cast draws a fish from the G07 table
 * under the cup's sky and lands it when the angler's strike beats the fish's window. A heat scores the summed market
 * price of the catch. Ties go to sudden-death casts, then to the higher seed (the lower index).
 */
public final class Heat {

    /** Sudden-death casts tried before a tie falls to the seed. */
    public static final int SUDDEN_DEATH_CASTS = 5;

    private final FishTable table;
    private final Conditions sky;
    private final int casts;

    public Heat(FishTable table, Conditions sky, int casts) {
        this.table = Objects.requireNonNull(table, "table");
        this.sky = Objects.requireNonNull(sky, "sky");
        if (casts < 1) {
            throw new IllegalArgumentException("casts must be >= 1: " + casts);
        }
        this.casts = casts;
    }

    public int casts() {
        return casts;
    }

    /** The value of one cast: the fish's price when landed, else zero. */
    int cast(AnglerSkill skill, OddsRng rng) {
        FishSpecies fish = table.pick(rng.nextDouble(), sky);
        return rng.chance(skill.catchChance(sky.window(fish))) ? fish.price() : 0;
    }

    /** One angler's heat total over {@link #casts()} casts. */
    public int score(AnglerSkill skill, OddsRng rng) {
        int total = 0;
        for (int i = 0; i < casts; i++) {
            total += cast(skill, rng);
        }
        return total;
    }

    /** Exact expected heat total: casts times the sum over fish of bite odds, catch odds and price. */
    public double expectedScore(AnglerSkill skill) {
        double perCast = 0;
        for (FishSpecies fish : table.fish()) {
            double bite = table.biteChance(fish.name(), sky);
            perCast += bite * skill.catchChance(sky.window(fish)) * fish.price();
        }
        return perCast * casts;
    }

    /**
     * Plays a heat between a higher seed and a lower seed.
     *
     * @return true when the higher seed wins
     */
    public boolean higherSeedWins(Angler higher, Angler lower, OddsRng rng) {
        int a = score(higher.skill(), rng);
        int b = score(lower.skill(), rng);
        for (int i = 0; i < SUDDEN_DEATH_CASTS && a == b; i++) {
            a += cast(higher.skill(), rng);
            b += cast(lower.skill(), rng);
        }
        return a >= b;
    }
}
