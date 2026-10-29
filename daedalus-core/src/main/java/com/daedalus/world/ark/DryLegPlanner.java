// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import com.daedalus.world.ark.ArkCellar.Day;
import com.daedalus.world.ark.ArkCellar.DayReport;
import com.daedalus.world.ark.ArkCellar.QuestResult;
import com.daedalus.world.ark.ArkCellar.State;
import com.daedalus.world.companion.TonicBottler.Tier;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Random;

/**
 * G201 The Dry Leg: plan an ark leg's tonic bottling against a rain forecast so the cistern never
 * ends a day below reserve, bottling as much as the leg allows.
 *
 * <p>Each day the planner bottles the largest count whose draw keeps that day and every later day
 * (with no further bottling) at or above reserve. Feasibility is checked by replaying the
 * {@link ArkCellar} ledger itself, so plan and ledger can never disagree. Bottling early only
 * lowers later overflow spill, so the earliest-first choice is optimal for a single tier.
 */
public final class DryLegPlanner {

    public static final String QUEST_ID = "q_dry_leg";

    public record Plan(Tier tier, List<Integer> bottlesPerDay, int total, List<Day> days) {
        public Plan {
            bottlesPerDay = List.copyOf(bottlesPerDay);
            days = List.copyOf(days);
        }
    }

    private final ArkCellar cellar;

    public DryLegPlanner(ArkCellar cellar) {
        this.cellar = Objects.requireNonNull(cellar);
    }

    /** Seeded rain forecast; {@code rainPct} in [0, 100]. */
    public static List<Boolean> forecast(long seed, int days, int rainPct) {
        if (days < 0 || rainPct < 0 || rainPct > 100) {
            throw new IllegalArgumentException("bad forecast");
        }
        Random rnd = new Random(seed);
        List<Boolean> f = new ArrayList<>(days);
        for (int i = 0; i < days; i++) {
            f.add(rnd.nextInt(100) < rainPct);
        }
        return f;
    }

    /** Turns per-day counts into ledger days for one tier. */
    public static List<Day> days(List<Boolean> rain, Tier tier, List<Integer> counts) {
        if (rain.size() != counts.size()) {
            throw new IllegalArgumentException("forecast and plan lengths differ");
        }
        List<Day> out = new ArrayList<>(rain.size());
        for (int i = 0; i < rain.size(); i++) {
            out.add(new Day(rain.get(i), Map.of(tier, counts.get(i))));
        }
        return out;
    }

    /** True when the plan never ends a day below reserve and every bottle is accepted. */
    public boolean safe(double startL, List<Day> plan) {
        State s = cellar.start(startL);
        for (int i = 0; i < plan.size(); i++) {
            DayReport r = cellar.day(s, i, plan.get(i));
            if (r.belowReserve() || r.refused() > 0) {
                return false;
            }
            s = r.state();
        }
        return true;
    }

    public Plan plan(double startL, List<Boolean> rain, Tier tier) {
        double per = cellar.rules().waterPerBottleL().get(tier);
        int kMax = (int) Math.floor(cellar.rules().cisternCapL() / per);
        State s = cellar.start(startL);
        List<Integer> counts = new ArrayList<>();
        for (int d = 0; d < rain.size(); d++) {
            int lo = 0;
            int hi = kMax;
            if (!feasible(s, d, rain, tier, 0)) {
                hi = 0;
            }
            while (lo < hi) {
                int mid = (lo + hi + 1) >>> 1;
                if (feasible(s, d, rain, tier, mid)) {
                    lo = mid;
                } else {
                    hi = mid - 1;
                }
            }
            counts.add(lo);
            s = cellar.day(s, d, new Day(rain.get(d), Map.of(tier, lo))).state();
        }
        int total = counts.stream().mapToInt(Integer::intValue).sum();
        return new Plan(tier, counts, total, days(rain, tier, counts));
    }

    private boolean feasible(State s, int d, List<Boolean> rain, Tier tier, int k) {
        DayReport r = cellar.day(s, d, new Day(rain.get(d), Map.of(tier, k)));
        if (r.belowReserve() || r.refused() > 0) {
            return false;
        }
        State t = r.state();
        for (int e = d + 1; e < rain.size(); e++) {
            DayReport f = cellar.day(t, e, new Day(rain.get(e), Map.of()));
            if (f.belowReserve()) {
                return false;
            }
            t = f.state();
        }
        return true;
    }

    /** Quest q_dry_leg: the planned leg must pass the G196 cellar quest with {@code target} bottles. */
    public QuestResult quest(double startL, List<Boolean> rain, Tier tier, int target) {
        Plan p = plan(startL, rain, tier);
        QuestResult q = cellar.quest(startL, p.days(), target, tier.level());
        return new QuestResult(QUEST_ID, q.passed(), q.bottlesOnShelf(), q.log());
    }
}
