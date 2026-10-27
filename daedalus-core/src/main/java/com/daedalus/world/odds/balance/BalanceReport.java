// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.balance;

import java.util.ArrayList;
import java.util.List;

/** Offline entry point: prints the default balance check for every registered minigame adapter. */
public final class BalanceReport {

    /** Seed used by the published report in docs/mechanics. */
    public static final long SEED = 190L;
    public static final int TRIALS = 4000;

    private BalanceReport() {
    }

    /** Every adapter the report covers; add a new minigame here. */
    public static List<BalanceGame> games() {
        return List.of(new ShardringBalance(), new CairnwellBalance());
    }

    public static List<ModeResult> runAll(long seed, int trials) {
        BalanceCheck check = new BalanceCheck();
        List<ModeResult> all = new ArrayList<>();
        for (BalanceGame g : games()) {
            all.addAll(check.run(g, seed, trials));
        }
        return all;
    }

    public static void main(String[] args) {
        for (ModeResult r : runAll(SEED, TRIALS)) {
            System.out.println(r);
        }
    }
}
