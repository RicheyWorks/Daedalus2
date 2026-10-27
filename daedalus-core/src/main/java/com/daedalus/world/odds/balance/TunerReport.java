// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.balance;

import com.daedalus.world.odds.OddsRng;
import java.util.ArrayList;
import java.util.List;

/** Offline entry point: prints the tuner's suggested settings for Shardring and Cairnwell (docs/mechanics). */
public final class TunerReport {

    public static final long SEED = 195L;
    public static final int SEARCH_TRIALS = 300;
    public static final int CONFIRM_TRIALS = 4000;
    public static final long MAX_SESSIONS = 2_000_000L;

    private TunerReport() {
    }

    /** Shardring knobs {facets, hues, shards} around the source's DIFFICULTY table; greedy player, no slip. */
    public static TunableGame shardring() {
        ShardringBalance sim = new ShardringBalance();
        return new TunableGame() {
            @Override
            public String id() {
                return sim.id();
            }

            @Override
            public List<String> difficulties() {
                return ShardringBalance.NAMES;
            }

            @Override
            public List<Knob> knobs() {
                return List.of(new Knob("facets", 8, 16, 1), new Knob("hues", 2, 5, 1),
                        new Knob("shards", 20, 60, 10));
            }

            @Override
            public int[] shipped(String difficulty) {
                return ShardringBalance.shipped(difficulty);
            }

            @Override
            public SessionOutcome play(int[] knobs, OddsRng rng) {
                return sim.playConfig(knobs, rng);
            }
        };
    }

    /**
     * Cairnwell knobs {cols, rows, dropEvery} around Option 0/1; default player (20 layers to win, 6-tick reaction,
     * 25% slip). "easy" is the practice well (Option 1); "hard" has no shipped well, so the tuner proposes one.
     */
    public static TunableGame cairnwell() {
        CairnwellBalance sim = new CairnwellBalance();
        return new TunableGame() {
            @Override
            public String id() {
                return sim.id();
            }

            @Override
            public List<String> difficulties() {
                return CairnwellBalance.NAMES;
            }

            @Override
            public List<Knob> knobs() {
                return List.of(new Knob("cols", 3, 8, 1), new Knob("rows", 4, 10, 1),
                        new Knob("dropEvery", 6, 28, 2));
            }

            @Override
            public int[] shipped(String difficulty) {
                return CairnwellBalance.shipped(difficulty);
            }

            @Override
            public SessionOutcome play(int[] knobs, OddsRng rng) {
                return sim.playConfig(knobs, rng);
            }
        };
    }

    public static List<Suggestion> runAll(long seed) {
        BalanceTuner tuner = new BalanceTuner(new BalanceCheck(), SEARCH_TRIALS, CONFIRM_TRIALS, MAX_SESSIONS);
        List<Suggestion> all = new ArrayList<>();
        all.addAll(tuner.tune(shardring(), seed));
        all.addAll(tuner.tune(cairnwell(), seed));
        return all;
    }

    public static void main(String[] args) {
        for (Suggestion s : runAll(SEED)) {
            System.out.println(s);
        }
    }
}
