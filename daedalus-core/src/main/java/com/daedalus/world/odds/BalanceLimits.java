// SPDX-License-Identifier: MIT

package com.daedalus.world.odds;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * The balance band an adaptive encounter must stay inside: the player's win probability between {@code minPWin} and
 * {@code maxPWin}, the median time-to-kill under {@code maxMedianTtk} seconds, and the mean health lost under
 * {@code maxHealthLostFraction} of the player's health.
 *
 * <p>The check is honest about noise: a limit is VIOLATED only when the whole 95% interval is outside it; a point
 * estimate outside the band with an interval that still reaches in is a WARNING that more trials are needed.
 */
public record BalanceLimits(double minPWin, double maxPWin, double maxMedianTtk, double maxHealthLostFraction) {

    /** A fair fight: 40-85% win chance, over in a minute, costing at most 80% of health on average. */
    public static final BalanceLimits FAIR = new BalanceLimits(0.40, 0.85, 60, 0.80);

    public BalanceLimits {
        if (!(minPWin >= 0 && maxPWin <= 1 && minPWin <= maxPWin)) {
            throw new IllegalArgumentException("need 0 <= minPWin <= maxPWin <= 1");
        }
        if (!(maxMedianTtk > 0) || !(maxHealthLostFraction > 0)) {
            throw new IllegalArgumentException("maxMedianTtk and maxHealthLostFraction must be above 0");
        }
    }

    /** The verdict: violations (certain), warnings (inconclusive), and ok when there are no violations. */
    public record Verdict(boolean ok, List<String> violations, List<String> warnings) {
        public Verdict {
            violations = List.copyOf(violations);
            warnings = List.copyOf(warnings);
        }
    }

    public Verdict check(OddsReport r) {
        List<String> bad = new ArrayList<>();
        List<String> warn = new ArrayList<>();
        if (r.pWinHigh() < minPWin) {
            bad.add(f("too hard: P(win) %.3f, 95%% CI [%.3f, %.3f] is below the %.3f floor", r.pWin(), r.pWinLow(),
                    r.pWinHigh(), minPWin));
        } else if (r.pWin() < minPWin) {
            warn.add(f("P(win) %.3f is below the %.3f floor but the CI [%.3f, %.3f] reaches it: run more trials",
                    r.pWin(), minPWin, r.pWinLow(), r.pWinHigh()));
        }
        if (r.pWinLow() > maxPWin) {
            bad.add(f("too easy: P(win) %.3f, 95%% CI [%.3f, %.3f] is above the %.3f ceiling", r.pWin(), r.pWinLow(),
                    r.pWinHigh(), maxPWin));
        } else if (r.pWin() > maxPWin) {
            warn.add(f("P(win) %.3f is above the %.3f ceiling but the CI [%.3f, %.3f] reaches it: run more trials",
                    r.pWin(), maxPWin, r.pWinLow(), r.pWinHigh()));
        }
        if (r.winTtk().n() > 0 && r.winTtk().p50() > maxMedianTtk) {
            bad.add(f("too slow: median time-to-kill %.1fs is above %.1fs", r.winTtk().p50(), maxMedianTtk));
        }
        if (r.meanHealthLostFraction() > maxHealthLostFraction) {
            bad.add(f("too punishing: mean health lost %.0f%% is above %.0f%%", 100 * r.meanHealthLostFraction(),
                    100 * maxHealthLostFraction));
        }
        return new Verdict(bad.isEmpty(), bad, warn);
    }

    private static String f(String fmt, Object... args) {
        return String.format(Locale.ROOT, fmt, args);
    }
}