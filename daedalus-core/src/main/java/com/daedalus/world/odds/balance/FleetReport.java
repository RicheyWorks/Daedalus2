// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.balance;

import java.util.ArrayList;
import java.util.List;

/**
 * G255 Balance Fleet: runs {@link BalanceCheck} and {@link BalanceTuner} over the desktop cabinets Reedbeat and
 * Beacon Sweep (and re-runs Shardring and Cairnwell through {@link TunerReport}). Reporting only: no game is edited.
 * {@code main} prints the tables quoted in docs/mechanics/BALANCE-FLEET-G255.md.
 */
public final class FleetReport {
    public static final long SEED = 255L;
    static final int CHECK_TRIALS = 2000;
    static final int SEARCH_TRIALS = 150;
    static final int CONFIRM_TRIALS = 1500;
    static final long MAX_SESSIONS = 200_000;

    private FleetReport() {
    }

    /** The new fleet adapters, in report order. */
    public static List<BalanceGame> games() {
        return List.of(new ReedbeatBalance(), new BeaconSweepBalance());
    }

    public static List<TunableGame> tunables() {
        return List.of(new ReedbeatBalance(), new BeaconSweepBalance());
    }

    public static List<ModeResult> checkAll(long seed) {
        BalanceCheck check = new BalanceCheck();
        List<ModeResult> out = new ArrayList<>();
        for (BalanceGame g : games()) {
            out.addAll(check.run(g, seed, CHECK_TRIALS));
        }
        return out;
    }

    public static List<Suggestion> tuneAll(long seed) {
        BalanceTuner tuner = new BalanceTuner(new BalanceCheck(), SEARCH_TRIALS, CONFIRM_TRIALS, MAX_SESSIONS);
        List<Suggestion> out = new ArrayList<>();
        for (TunableGame g : tunables()) {
            out.addAll(tuner.tune(g, seed));
        }
        return out;
    }

    public static void main(String[] args) {
        for (ModeResult r : checkAll(SEED)) {
            System.out.println(r);
        }
        for (Suggestion s : tuneAll(SEED)) {
            System.out.println(s);
        }
        for (ModeResult r : BalanceReport.runAll(BalanceReport.SEED, BalanceReport.TRIALS)) {
            System.out.println(r);
        }
        for (Suggestion s : TunerReport.runAll(TunerReport.SEED)) {
            System.out.println(s);
        }
    }
}
