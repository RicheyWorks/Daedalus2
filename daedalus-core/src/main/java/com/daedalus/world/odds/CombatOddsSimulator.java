// SPDX-License-Identifier: MIT

package com.daedalus.world.odds;

import java.util.List;
import java.util.Objects;

/**
 * The Combat Odds Engine: a deterministic Monte Carlo encounter simulator. Each trial is an event-driven fight in
 * continuous time (every fighter swings on its own cooldown, with a random phase), and the run aggregates the trials
 * into an {@link OddsReport}. Offline and pure: it never runs in a frame path, never calls the network, and the same
 * (encounter, seed, trials) gives the same report on any JVM.
 *
 * <p>Model: foes whose order {@code attacks} shoot the player; the player shoots foes by the encounter's
 * {@link TargetPolicy}. The fight is a WIN when no attacking foe is left standing (units that retreat or hold are not
 * threats), a LOSS when the player's health reaches zero, and a DRAW when {@code maxSeconds} runs out first.
 */
public final class CombatOddsSimulator {

    public static final int MAX_TRIALS = 1_000_000;
    /** 97.5th percentile of the standard normal: the 95% two-sided interval. */
    static final double Z95 = 1.959963984540054;

    public enum Outcome { WIN, LOSS, DRAW }

    /** One finished trial. */
    record Trial(Outcome outcome, double seconds, double healthLost, int foesDowned) {
    }

    private CombatOddsSimulator() {
    }

    /** Run {@code trials} fights with win/lose payoffs. */
    public static OddsReport run(Encounter encounter, long seed, int trials) {
        return run(encounter, seed, trials, Payoffs.WIN_LOSE);
    }

    public static OddsReport run(Encounter encounter, long seed, int trials, Payoffs payoffs) {
        Objects.requireNonNull(encounter, "encounter");
        Objects.requireNonNull(payoffs, "payoffs");
        if (trials < 1 || trials > MAX_TRIALS) {
            throw new IllegalArgumentException("trials must be 1.." + MAX_TRIALS);
        }
        int wins = 0;
        int losses = 0;
        int draws = 0;
        double[] winTimes = new double[trials];
        double[] lossTimes = new double[trials];
        double[] lost = new double[trials];
        double[] values = new double[trials];
        long downed = 0;
        for (int i = 0; i < trials; i++) {
            Trial t = simulateOnce(encounter, OddsRng.forTrial(seed, i));
            switch (t.outcome()) {
                case WIN -> winTimes[wins++] = t.seconds();
                case LOSS -> lossTimes[losses++] = t.seconds();
                case DRAW -> draws++;
                default -> throw new IllegalStateException("unknown outcome");
            }
            lost[i] = t.healthLost();
            values[i] = payoffs.value(t.outcome(), t.healthLost());
            downed += t.foesDowned();
        }
        double pWin = (double) wins / trials;
        double[] wilson = wilson(wins, trials);
        Summary health = Summary.of(lost, trials);
        double[] ev = meanInterval(values);
        return new OddsReport(seed, trials, wins, losses, draws, pWin, wilson[0], wilson[1],
                Summary.of(winTimes, wins), Summary.of(lossTimes, losses), health,
                health.mean() / encounter.player().health(), (double) downed / trials, ev[0], ev[1], ev[2]);
    }

    /** Wilson score interval for {@code k} successes in {@code n} trials: {low, high}. Honest near 0 and 1. */
    static double[] wilson(int k, int n) {
        double p = (double) k / n;
        double z2 = Z95 * Z95;
        double denom = 1 + z2 / n;
        double centre = (p + z2 / (2.0 * n)) / denom;
        double half = Z95 * Math.sqrt(p * (1 - p) / n + z2 / (4.0 * n * n)) / denom;
        return new double[] {Math.max(0, centre - half), Math.min(1, centre + half)};
    }

    /** {mean, low, high} of a sample, normal approximation on the standard error. */
    static double[] meanInterval(double[] v) {
        Summary s = Summary.of(v, v.length);
        double half = Z95 * s.stdDev() / Math.sqrt(v.length);
        return new double[] {s.mean(), s.mean() - half, s.mean() + half};
    }

    /** One fight. All randomness comes from {@code rng}, drawn in a fixed order. */
    static Trial simulateOnce(Encounter e, OddsRng rng) {
        Combatant player = e.player();
        List<Encounter.Foe> foes = e.foes();
        int n = foes.size();
        double[] hp = new double[n];
        double[] next = new double[n];
        boolean[] up = new boolean[n];
        int threats = 0;
        for (int i = 0; i < n; i++) {
            Encounter.Foe f = foes.get(i);
            hp[i] = f.stats().health();
            double phase = rng.nextDouble();
            if (f.profile().attacks() && !f.profile().leaves()) {
                up[i] = true;
                threats++;
                next[i] = f.profile().startDelay() + f.stats().cooldown() * phase;
            } else {
                next[i] = Double.POSITIVE_INFINITY;
            }
        }
        double playerNext = player.cooldown() * rng.nextDouble();
        if (threats == 0) {
            return new Trial(Outcome.WIN, 0, 0, 0);
        }
        double playerHp = player.health();
        int downed = 0;
        while (true) {
            int who = -1;                       // -1 is the player; ties go to the player, then the lowest index
            double t = playerNext;
            for (int i = 0; i < n; i++) {
                if (up[i] && next[i] < t) {
                    t = next[i];
                    who = i;
                }
            }
            if (t > e.maxSeconds()) {
                return new Trial(Outcome.DRAW, e.maxSeconds(), player.health() - playerHp, downed);
            }
            if (who < 0) {
                int target = pick(e.policy(), foes, hp, up, player.armor());
                Encounter.Foe f = foes.get(target);
                if (rng.chance(player.accuracy())) {
                    double dmg = player.damage() * (rng.chance(player.critChance()) ? player.critMultiplier() : 1.0);
                    hp[target] -= Combatant.afterArmor(dmg, f.stats().armor()) * f.profile().incomingMultiplier();
                    if (hp[target] <= 0) {
                        up[target] = false;
                        downed++;
                        if (--threats == 0) {
                            return new Trial(Outcome.WIN, t, player.health() - playerHp, downed);
                        }
                    }
                }
                playerNext += player.cooldown();
            } else {
                Encounter.Foe f = foes.get(who);
                Combatant c = f.stats();
                if (rng.chance(c.accuracy() * f.profile().accuracyMultiplier())) {
                    double dmg = c.damage() * (rng.chance(c.critChance()) ? c.critMultiplier() : 1.0);
                    playerHp -= Combatant.afterArmor(dmg, player.armor());
                    if (playerHp <= 0) {
                        return new Trial(Outcome.LOSS, t, player.health(), downed);
                    }
                }
                next[who] += c.cooldown();
            }
        }
    }

    /** The index of the live threat the player shoots next. At least one is up when this is called. */
    private static int pick(TargetPolicy policy, List<Encounter.Foe> foes, double[] hp, boolean[] up, double playerArmor) {
        int best = -1;
        double bestKey = 0;
        for (int i = 0; i < foes.size(); i++) {
            if (!up[i]) {
                continue;
            }
            double key = switch (policy) {
                case FIRST_LISTED -> -i;
                case LOWEST_HEALTH -> -hp[i];
                case HIGHEST_THREAT -> foes.get(i).stats().expectedDps(playerArmor) * foes.get(i).profile().accuracyMultiplier();
            };
            if (best < 0 || key > bestKey) {
                best = i;
                bestKey = key;
            }
        }
        return best;
    }
}