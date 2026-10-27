// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.balance;

import com.daedalus.world.odds.OddsRng;
import java.util.List;

/**
 * Reedbeat (DaedalusDesktopReedbeatCore.h on main) re-played tick by tick. Source constants: option 0 (mapped to
 * "normal") is 8 notes, a note every 36 ticks, an 8-tick strike window; option 1 (the practice round, mapped to "easy")
 * is 4 notes, every 40 ticks, an 18-tick window. The source ships no third option, so "hard" is reported as missing.
 * The first note opens at gap + (seed mod 5). A press inside the open window is a hit and schedules the next note; a
 * press outside it is a miss (the note stays scheduled); a window that closes unstruck is a miss and moves on. Three
 * misses lose; {@code total} hits win. Score is hits x 100. A press on the very tick the window closes therefore costs
 * two misses (the press, then the closed window), exactly as in the source.
 *
 * <p>Player model (anticipating tapper): the beat is regular, so the player aims every press at the centre of the
 * window with Gaussian timing error of {@code sigmaTicks} ticks (default 4 ticks, about 67 ms at 60 Hz). After an
 * early miss the player re-aims at the same window, never earlier than the next tick. The note gap does not change
 * this player's odds, so the tuner holds it at the source's 36 (or window + 4 if wider).
 */
public final class ReedbeatBalance implements BalanceGame, TunableGame {
    static final List<String> NAMES = List.of("easy", "normal", "hard");
    /** {total notes, window ticks, gap ticks} for "easy" (option 1) and "normal" (option 0). */
    private static final int[][] CONFIG = {{4, 18, 40}, {8, 8, 36}};
    static final int MAX_MISSES = 3;
    static final int HIT_POINTS = 100;

    private final double sigmaTicks;

    public ReedbeatBalance() {
        this(4.0);
    }

    public ReedbeatBalance(double sigmaTicks) {
        if (!(sigmaTicks >= 0)) {
            throw new IllegalArgumentException("sigmaTicks >= 0 required");
        }
        this.sigmaTicks = sigmaTicks;
    }

    @Override
    public String id() {
        return "reedbeat";
    }

    @Override
    public List<String> difficulties() {
        return NAMES;
    }

    @Override
    public boolean supports(String difficulty) {
        return "easy".equals(difficulty) || "normal".equals(difficulty);
    }

    @Override
    public SessionOutcome play(String difficulty, OddsRng rng) {
        if (!supports(difficulty)) {
            throw new IllegalArgumentException("Reedbeat ships no '" + difficulty + "' round");
        }
        return playConfig(CONFIG["easy".equals(difficulty) ? 0 : 1], rng);
    }

    @Override
    public List<Knob> knobs() {
        return List.of(new Knob("notes", 2, 12, 1), new Knob("window", 4, 24, 2));
    }

    @Override
    public int[] shipped(String difficulty) {
        if ("easy".equals(difficulty)) {
            return new int[] {CONFIG[0][0], CONFIG[0][1]};
        }
        return "normal".equals(difficulty) ? new int[] {CONFIG[1][0], CONFIG[1][1]} : null;
    }

    @Override
    public SessionOutcome play(int[] knobs, OddsRng rng) {
        return playConfig(new int[] {knobs[0], knobs[1], Math.max(36, knobs[1] + 4)}, rng);
    }

    /** Plays one round with explicit {total, window, gap}. */
    SessionOutcome playConfig(int[] cfg, OddsRng rng) {
        int total = cfg[0];
        int window = cfg[1];
        int gap = cfg[2];
        long seed = rng.nextLong() >>> 32;
        seed = seed == 0 ? 1 : seed;
        int clock = 0;
        int nextAt = gap + (int) (seed % 5);
        int hits = 0;
        int misses = 0;
        int target = aim(nextAt, window, clock, rng);
        while (true) {
            clock++;
            boolean open = clock >= nextAt && clock < nextAt + window;
            if (clock == target) {
                if (open) {
                    hits++;
                    if (hits >= total) {
                        return new SessionOutcome(true, (long) hits * HIT_POINTS);
                    }
                    nextAt += gap;
                } else if (++misses >= MAX_MISSES) {
                    return new SessionOutcome(false, (long) hits * HIT_POINTS);
                }
                target = aim(nextAt, window, clock, rng);
                continue;
            }
            if (clock >= nextAt + window) {
                if (++misses >= MAX_MISSES) {
                    return new SessionOutcome(false, (long) hits * HIT_POINTS);
                }
                nextAt += gap;
                target = aim(nextAt, window, clock, rng);
            }
        }
    }

    private int aim(int nextAt, int window, int clock, OddsRng rng) {
        double centre = nextAt + (window - 1) / 2.0;
        int t = (int) Math.round(centre + sigmaTicks * gaussian(rng));
        return Math.max(t, clock + 1);
    }

    /** Standard normal draw (Box-Muller) from {@link OddsRng}. */
    static double gaussian(OddsRng rng) {
        double u = 1.0 - rng.nextDouble();
        double v = rng.nextDouble();
        return Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2 * Math.PI * v);
    }
}
