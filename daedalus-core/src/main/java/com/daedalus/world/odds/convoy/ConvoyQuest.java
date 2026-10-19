// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.convoy;

import com.daedalus.world.odds.OddsRng;
import java.util.List;
import java.util.Locale;
import java.util.Objects;

/**
 * Quest q_convoy_split: {@link #FLEET} arks must cross the belt and at least {@link #NEEDED} must arrive to seed the
 * island. Sail together for mutual aid, or split so one storm cannot take everyone? The player picks a split; the
 * Keeper chalks the exact chance and compares it with the best split. Within {@link #TOLERANCE} of the best earns his
 * nod; then the crossing sails once on a fresh seeded stream.
 */
public final class ConvoyQuest {

    public static final int FLEET = 6;
    public static final int NEEDED = 4;
    public static final double TOLERANCE = 0.01;

    /** Quest stages. */
    public enum Stage { PLANNING, CHOSEN, SEEDED, SHORT }

    private final ConvoyRisk risk;
    private final List<Integer> best;
    private final double bestChance;
    private Stage stage = Stage.PLANNING;
    private ConvoyPlan plan;
    private int arrived = -1;

    public ConvoyQuest(ConvoyRisk risk) {
        this.risk = Objects.requireNonNull(risk, "risk");
        List<Integer> b = null;
        double bc = -1;
        for (List<Integer> s : ConvoyPlan.splits(FLEET)) {
            double p = new ConvoyPlan(s, risk).atLeast(NEEDED);
            if (p > bc + 1e-12) {
                bc = p;
                b = s;
            }
        }
        this.best = b;
        this.bestChance = bc;
    }

    public Stage stage() {
        return stage;
    }

    /** The Keeper's best split (ties to the first found, largest convoys first). */
    public List<Integer> best() {
        return List.copyOf(best);
    }

    public double bestChance() {
        return bestChance;
    }

    /** Chooses a split; it must cover the whole fleet. */
    public double choose(List<Integer> split) {
        if (stage != Stage.PLANNING) {
            throw new IllegalStateException("already chosen: " + stage);
        }
        ConvoyPlan p = new ConvoyPlan(split, risk);
        if (p.arks() != FLEET) {
            throw new IllegalArgumentException("split must cover " + FLEET + " arks: " + split);
        }
        plan = p;
        stage = Stage.CHOSEN;
        return p.atLeast(NEEDED);
    }

    /** Whether the chosen split is within {@link #TOLERANCE} of the best chance. */
    public boolean wise() {
        return plan != null && plan.atLeast(NEEDED) >= bestChance - TOLERANCE;
    }

    /** Sails the crossing once; returns arks arrived. */
    public int sail(long seed) {
        if (stage != Stage.CHOSEN) {
            throw new IllegalStateException("choose a split first: " + stage);
        }
        arrived = plan.sail(new OddsRng(seed));
        stage = arrived >= NEEDED ? Stage.SEEDED : Stage.SHORT;
        return arrived;
    }

    public int arrived() {
        return arrived;
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        return switch (stage) {
            case PLANNING -> String.format(Locale.ROOT,
                    "Six arks, four must land. Best chalk: %s at %.0f%%. Together for aid, apart against the storm.",
                    best, bestChance * 100);
            case CHOSEN -> wise()
                    ? String.format(Locale.ROOT, "%s. The old captains would have split it the same.", plan.convoys())
                    : String.format(Locale.ROOT, "%s gives %.0f%%; the chalk had %.0f%%.",
                            plan.convoys(), plan.atLeast(NEEDED) * 100, bestChance * 100);
            case SEEDED -> String.format(Locale.ROOT, "%d arks landed. The island will grow again.", arrived);
            case SHORT -> String.format(Locale.ROOT, "Only %d landed. The belt kept the rest.", arrived);
        };
    }
}
