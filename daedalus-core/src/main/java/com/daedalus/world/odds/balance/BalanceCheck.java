// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.balance;

import com.daedalus.world.odds.Intervals;
import com.daedalus.world.odds.OddsRng;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Seeded difficulty balance check. Plays {@code trials} sessions per difficulty (trial {@code t} uses
 * {@link OddsRng#forTrial(long, long)}, so results do not depend on run order), then flags modes whose 95% Wilson
 * interval falls wholly outside their band, and harder modes that are clearly easier than a softer one.
 */
public final class BalanceCheck {

    private final Map<String, BalanceBand> bands = new HashMap<>();
    private final BalanceBand fallback;

    /** Default bands: easy 60-98%, normal 30-90%, hard 10-75%; any other name 10-95%. */
    public BalanceCheck() {
        this(new BalanceBand(0.10, 0.95));
        band("easy", new BalanceBand(0.60, 0.98));
        band("normal", new BalanceBand(0.30, 0.90));
        band("hard", new BalanceBand(0.10, 0.75));
    }

    public BalanceCheck(BalanceBand fallback) {
        this.fallback = fallback;
    }

    /** Sets the band for one difficulty name. */
    public BalanceCheck band(String difficulty, BalanceBand band) {
        bands.put(difficulty, band);
        return this;
    }

    public BalanceBand bandFor(String difficulty) {
        return bands.getOrDefault(difficulty, fallback);
    }

    /** Simulates every difficulty of {@code game} and returns flagged results, softest first. */
    public List<ModeResult> run(BalanceGame game, long seed, int trials) {
        if (trials < 1) {
            throw new IllegalArgumentException("trials must be >= 1: " + trials);
        }
        List<ModeResult> out = new ArrayList<>();
        for (String d : game.difficulties()) {
            if (!game.supports(d)) {
                ModeResult missing = new ModeResult(game.id(), d, 0, 0, 0, new double[] {0, 0});
                missing.flag(BalanceFlag.MISSING_MODE);
                out.add(missing);
                continue;
            }
            long modeSeed = seed ^ (d.hashCode() * 0x9E3779B97F4A7C15L);
            int wins = 0;
            double scoreSum = 0;
            for (int t = 0; t < trials; t++) {
                SessionOutcome o = game.play(d, OddsRng.forTrial(modeSeed, t));
                if (o.won()) {
                    wins++;
                }
                scoreSum += o.score();
            }
            out.add(new ModeResult(game.id(), d, trials, wins, scoreSum / trials, Intervals.wilson(wins, trials)));
        }
        flag(out);
        return out;
    }

    /** Applies band and monotonic flags to results listed softest first. Public so other runners can reuse it. */
    public void flag(List<ModeResult> softestFirst) {
        for (int i = 0; i < softestFirst.size(); i++) {
            ModeResult r = softestFirst.get(i);
            if (r.trials() == 0) {
                continue;
            }
            BalanceBand b = bandFor(r.difficulty());
            if (r.high() < b.floor()) {
                r.flag(BalanceFlag.TOO_HARD);
            }
            if (r.low() > b.ceiling()) {
                r.flag(BalanceFlag.TOO_EASY);
            }
            for (int j = 0; j < i; j++) {
                ModeResult softer = softestFirst.get(j);
                if (softer.trials() > 0 && r.low() > softer.high()) {
                    r.flag(BalanceFlag.NOT_MONOTONIC);
                }
            }
        }
    }
}
