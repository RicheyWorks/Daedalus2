// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.rope;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 24 of the Youtube Master Island story, "The Rope Market" (quest {@code q_rope_market}). A harbour market buys
 * rope by the piece at a price per length. The player cuts the whole coil; the sale is rich when the pieces fetch the
 * most possible. {@link #bestPrice()} is exact rod-cutting DP and {@link #bestCuts()} walks it back.
 */
public final class RopeMarket {
    public static final String QUEST_ID = "q_rope_market";
    public static final int PIECES_TO_CUT = 3;

    public enum Outcome { CUT, JOINED, TOO_LONG, NOT_CUT, UNKNOWN, RICH, THIN, ROPE_LEFT, DUPLICATE, IGNORED }

    private final int coil;
    private final int[] price;
    private final int[] best;
    private final int[] firstCut;
    private final List<Integer> pieces = new ArrayList<>();
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("cut", "piece", PIECES_TO_CUT),
            new QuestProgress.Step("sell", "rich", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private Outcome last;

    /** {@code prices[k-1]} is what the market pays for one piece of length k, for k = 1..coil. */
    public RopeMarket(int coil, List<Integer> prices) {
        if (coil <= 0 || prices.size() != coil || prices.stream().anyMatch(p -> p < 0)) {
            throw new IllegalArgumentException("need a price for every length 1.." + coil);
        }
        this.coil = coil;
        price = new int[coil + 1];
        for (int k = 1; k <= coil; k++) {
            price[k] = prices.get(k - 1);
        }
        best = new int[coil + 1];
        firstCut = new int[coil + 1];
        for (int n = 1; n <= coil; n++) {
            for (int k = 1; k <= n; k++) {
                if (price[k] + best[n - k] > best[n] || firstCut[n] == 0) {
                    best[n] = Math.max(best[n], price[k] + best[n - k]);
                    if (best[n] == price[k] + best[n - k]) {
                        firstCut[n] = k;
                    }
                }
            }
        }
    }

    /** A seeded market: a 6-12 length coil, prices rising by 0-4 per length with the odd bargain length. */
    public static RopeMarket seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x209EL);
        int coil = 6 + rng.nextInt(7);
        List<Integer> prices = new ArrayList<>();
        int p = 0;
        for (int k = 1; k <= coil; k++) {
            p += rng.nextInt(5);
            prices.add(p + (rng.nextInt(4) == 0 ? 3 : 0));
        }
        return new RopeMarket(coil, prices);
    }

    public int coil() {
        return coil;
    }

    public int price(int length) {
        return length >= 1 && length <= coil ? price[length] : 0;
    }

    /** The most the whole coil can fetch. */
    public int bestPrice() {
        return best[coil];
    }

    /** One best set of piece lengths. */
    public List<Integer> bestCuts() {
        List<Integer> out = new ArrayList<>();
        for (int n = coil; n > 0; n -= firstCut[n]) {
            out.add(firstCut[n]);
        }
        return out;
    }

    public List<Integer> pieces() {
        return List.copyOf(pieces);
    }

    public int left() {
        return coil - pieces.stream().mapToInt(Integer::intValue).sum();
    }

    public int value() {
        return pieces.stream().mapToInt(this::price).sum();
    }

    public QuestProgress quest() {
        return quest;
    }

    public Outcome last() {
        return last;
    }

    private Outcome guard(String eventId) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        return events.contains(eventId) ? Outcome.DUPLICATE : null;
    }

    /** Cuts one piece of the given length off what's left of the coil. */
    public Outcome cut(String eventId, int length) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (length < 1 || length > coil) {
            return Outcome.UNKNOWN;
        }
        if (length > left()) {
            return Outcome.TOO_LONG;
        }
        events.add(eventId);
        pieces.add(length);
        last = null;
        quest.apply(eventId, "cut", "piece");
        return Outcome.CUT;
    }

    /** Splices a cut piece back onto the coil. */
    public Outcome join(String eventId, int length) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (!pieces.remove(Integer.valueOf(length))) {
            return Outcome.NOT_CUT;
        }
        events.add(eventId);
        last = null;
        return Outcome.JOINED;
    }

    /** Sells the pieces: ROPE_LEFT while coil remains, RICH at the best price, else THIN. */
    public Outcome sell(String eventId) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (left() > 0) {
            return Outcome.ROPE_LEFT;
        }
        events.add(eventId);
        last = value() == bestPrice() ? Outcome.RICH : Outcome.THIN;
        if (last == Outcome.RICH) {
            quest.apply(eventId, "sell", "rich");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once a sale was rich. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperRopeLines.THANKS;
        }
        return KeeperRopeLines.line(this);
    }
}
