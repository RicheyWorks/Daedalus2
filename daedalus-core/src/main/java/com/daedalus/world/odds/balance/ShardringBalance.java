// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.balance;

import com.daedalus.world.odds.OddsRng;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Shardring Resonance (tools/minigames/prism_shard.py, branch grok/prism-shard-minigame commit 35634971) re-played
 * on {@link OddsRng}. Rules and constants are copied from that source: ring of empty facets, one hue drawn per turn,
 * a circular run of 3+ same hue clears and scores run^2 x chain, every 3rd resonance of a hue adds 25 and clears one
 * random filled facet, a full ring loses and an empty pouch wins. The player is the source's own {@code greedy_move};
 * with probability {@code slip} a turn goes to a uniformly random empty facet instead.
 */
public final class ShardringBalance implements BalanceGame {

    static final int RUN = 3;
    static final int SPIRIT_EVERY = 3;
    static final int SPIRIT_BONUS = 25;
    /** {facets, hues, shards} per difficulty, as in the source. */
    private static final int[][] CONFIG = {{14, 3, 60}, {10, 3, 50}, {8, 3, 40}};
    static final List<String> NAMES = List.of("easy", "normal", "hard");

    private final double slip;

    public ShardringBalance() {
        this(0.0);
    }

    public ShardringBalance(double slip) {
        this.slip = slip;
    }

    @Override
    public String id() {
        return "shardring";
    }

    @Override
    public List<String> difficulties() {
        return NAMES;
    }

    @Override
    public boolean supports(String difficulty) {
        return NAMES.contains(difficulty);
    }

    @Override
    public SessionOutcome play(String difficulty, OddsRng rng) {
        return playConfig(CONFIG[NAMES.indexOf(difficulty)], rng);
    }

    /** Shipped {facets, hues, shards} for a difficulty (a copy). */
    static int[] shipped(String difficulty) {
        return CONFIG[NAMES.indexOf(difficulty)].clone();
    }

    /** Plays one session with explicit {facets, hues, shards}; used by {@link BalanceTuner}. */
    SessionOutcome playConfig(int[] cfg, OddsRng rng) {
        int n = cfg[0];
        int hues = cfg[1];
        int pouch = cfg[2];
        int[] ring = new int[n];
        java.util.Arrays.fill(ring, -1);
        int[] resonance = new int[hues];
        long score = 0;
        int chain = 0;
        int current = pick(rng, hues);
        int next = pick(rng, hues);
        while (true) {
            int facet = rng.chance(slip) ? randomEmpty(ring, rng) : greedy(ring, current);
            ring[facet] = current;
            pouch--;
            Set<Integer> run = runAt(ring, facet);
            long gained = 0;
            if (run.size() >= RUN) {
                chain++;
                gained = (long) run.size() * run.size() * chain;
                for (int j : run) {
                    ring[j] = -1;
                }
                resonance[current]++;
                if (resonance[current] % SPIRIT_EVERY == 0) {
                    gained += SPIRIT_BONUS;
                    List<Integer> filled = new ArrayList<>();
                    for (int j = 0; j < n; j++) {
                        if (ring[j] >= 0) {
                            filled.add(j);
                        }
                    }
                    if (!filled.isEmpty()) {
                        ring[filled.get(pick(rng, filled.size()))] = -1;
                    }
                }
            } else {
                chain = 0;
            }
            score += gained;
            current = next;
            next = pick(rng, hues);
            if (emptyCount(ring) == 0) {
                return new SessionOutcome(false, score);
            }
            if (pouch <= 0) {
                return new SessionOutcome(true, score);
            }
        }
    }

    static int pick(OddsRng rng, int k) {
        return (int) (rng.nextDouble() * k);
    }

    static Set<Integer> runAt(int[] ring, int i) {
        int n = ring.length;
        int hue = ring[i];
        Set<Integer> run = new HashSet<>();
        run.add(i);
        for (int step = 1; step >= -1; step -= 2) {
            int j = Math.floorMod(i + step, n);
            while (ring[j] == hue && !run.contains(j)) {
                run.add(j);
                j = Math.floorMod(j + step, n);
            }
        }
        return run;
    }

    /** The source's greedy_move: max key (resonates, run size, -index). */
    static int greedy(int[] ring, int hue) {
        int best = -1;
        int bestSize = -1;
        for (int i = 0; i < ring.length; i++) {
            if (ring[i] >= 0) {
                continue;
            }
            ring[i] = hue;
            int size = runAt(ring, i).size();
            ring[i] = -1;
            if (size > bestSize) {
                best = i;
                bestSize = size;
            }
        }
        return best;
    }

    private static int randomEmpty(int[] ring, OddsRng rng) {
        int[] empty = new int[ring.length];
        int k = 0;
        for (int i = 0; i < ring.length; i++) {
            if (ring[i] < 0) {
                empty[k++] = i;
            }
        }
        return empty[pick(rng, k)];
    }

    private static int emptyCount(int[] ring) {
        int c = 0;
        for (int h : ring) {
            if (h < 0) {
                c++;
            }
        }
        return c;
    }
}
