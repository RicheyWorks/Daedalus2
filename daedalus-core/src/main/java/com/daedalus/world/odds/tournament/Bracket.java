// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.tournament;

import com.daedalus.world.odds.OddsRng;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/**
 * A single-elimination bracket in standard seeding (1 meets the last seed, the top two can only meet in the final).
 * Fields that are not a power of two are padded with byes, which go to the top seeds. Entrants are seeded in list
 * order: index 0 is the first seed.
 */
public final class Bracket {

    private final List<Angler> anglers;
    private final int[] slots;

    public Bracket(List<Angler> anglers) {
        Objects.requireNonNull(anglers, "anglers");
        if (anglers.size() < 2) {
            throw new IllegalArgumentException("a cup needs at least two anglers");
        }
        this.anglers = List.copyOf(anglers);
        int size = 1;
        while (size < anglers.size()) {
            size *= 2;
        }
        int[] order = seedOrder(size);
        this.slots = new int[size];
        for (int i = 0; i < size; i++) {
            slots[i] = order[i] < anglers.size() ? order[i] : -1;
        }
    }

    /** Standard bracket order of seed indices for a power-of-two field, e.g. 4 gives [0, 3, 1, 2]. */
    static int[] seedOrder(int size) {
        int[] order = {0};
        while (order.length < size) {
            int n = order.length * 2;
            int[] next = new int[n];
            for (int i = 0; i < order.length; i++) {
                next[2 * i] = order[i];
                next[2 * i + 1] = n - 1 - order[i];
            }
            order = next;
        }
        return order;
    }

    public List<Angler> anglers() {
        return anglers;
    }

    /** Number of rounds to crown a champion. */
    public int rounds() {
        return Integer.numberOfTrailingZeros(slots.length);
    }

    /** Number of byes handed out in round one. */
    public int byes() {
        return slots.length - anglers.size();
    }

    /** The first-round slot list; -1 marks a bye. */
    public List<Integer> firstRound() {
        List<Integer> out = new ArrayList<>(slots.length);
        for (int s : slots) {
            out.add(s);
        }
        return Collections.unmodifiableList(out);
    }

    /**
     * Plays the whole cup once.
     *
     * @return the survivors after each round; the last list holds only the champion's index
     */
    public List<List<Integer>> play(Heat heat, OddsRng rng) {
        Objects.requireNonNull(heat, "heat");
        List<List<Integer>> history = new ArrayList<>();
        int[] alive = slots.clone();
        while (alive.length > 1) {
            int[] next = new int[alive.length / 2];
            for (int i = 0; i < next.length; i++) {
                next[i] = match(heat, alive[2 * i], alive[2 * i + 1], rng);
            }
            List<Integer> round = new ArrayList<>(next.length);
            for (int s : next) {
                round.add(s);
            }
            history.add(Collections.unmodifiableList(round));
            alive = next;
        }
        return Collections.unmodifiableList(history);
    }

    /** Champion index of one full cup. */
    public int champion(Heat heat, OddsRng rng) {
        List<List<Integer>> history = play(heat, rng);
        return history.get(history.size() - 1).get(0);
    }

    private int match(Heat heat, int a, int b, OddsRng rng) {
        if (a < 0) {
            return b;
        }
        if (b < 0) {
            return a;
        }
        int hi = Math.min(a, b);
        int lo = Math.max(a, b);
        return heat.higherSeedWins(anglers.get(hi), anglers.get(lo), rng) ? hi : lo;
    }
}
