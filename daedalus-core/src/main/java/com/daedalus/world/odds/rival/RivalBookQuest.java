// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.rival;

import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.Set;

/**
 * Quest q_rival_book: a rival bookmaker sets up on the ark docks and prices the Keeper's boards (G47 routes, G35 cup).
 * The Keeper hands the player his fair chances and asks them to find every value line on the rival's book. Each call
 * is checked; {@link #MAX_MISCALLS} wrong calls end the quest. Calling every value line wins the Keeper's thanks and
 * {@link #REWARD} storm herbs (in-game only; no real-money wagering).
 */
public final class RivalBookQuest {

    public static final int MAX_MISCALLS = 2;
    public static final int REWARD = 15;
    /** Lines must beat the fair price by at least this edge to count as value. */
    public static final double MIN_EDGE = 0.02;

    /** Quest stages. */
    public enum Stage { SCANNING, EXPOSED, FOOLED }

    private final RivalBook book;
    private final Set<Integer> value = new HashSet<>();
    private final Set<Integer> found = new HashSet<>();
    private Stage stage;
    private int miscalls;

    public RivalBookQuest(double[] fairChances, RivalBook book) {
        this.book = Objects.requireNonNull(book, "book");
        List<ValueScan.Value> v = ValueScan.values(fairChances, book, MIN_EDGE);
        v.forEach(x -> value.add(x.outcome()));
        this.stage = value.isEmpty() ? Stage.EXPOSED : Stage.SCANNING;
    }

    public Stage stage() {
        return stage;
    }

    public int valueLines() {
        return value.size();
    }

    public int found() {
        return found.size();
    }

    public int miscalls() {
        return miscalls;
    }

    /**
     * The player calls outcome {@code i} as a value line.
     *
     * @return true if it is one (and new)
     */
    public boolean call(int i) {
        if (stage != Stage.SCANNING) {
            throw new IllegalStateException("quest over: " + stage);
        }
        Objects.checkIndex(i, book.size());
        boolean hit = value.contains(i) && found.add(i);
        if (!hit) {
            miscalls++;
            if (miscalls >= MAX_MISCALLS) {
                stage = Stage.FOOLED;
            }
        } else if (found.size() == value.size()) {
            stage = Stage.EXPOSED;
        }
        return hit;
    }

    /** Herbs paid: {@link #REWARD} when exposed with at least one value line found, else 0. */
    public int reward() {
        return stage == Stage.EXPOSED && !value.isEmpty() ? REWARD : 0;
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        return switch (stage) {
            case SCANNING -> String.format(Locale.ROOT,
                    "%d of his lines are soft and you have found %d. Check them against my chalk.",
                    value.size(), found.size());
            case EXPOSED -> value.isEmpty()
                    ? "Not a soft line on his slate today. Even a rival gets lucky."
                    : "Every soft line called. He will think twice before pricing my arks again.";
            case FOOLED -> "He priced you as well as the routes. Read the chalk, not his smile.";
        };
    }
}
