// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import com.daedalus.world.companion.TonicBottler.Tier;

import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * G196 The Ark Cellar: one daily ledger for an ark's cistern water and its tonic cellar.
 *
 * <p>Rain and the ark spring fill the cistern (spilling over its cap), the crew drinks first,
 * then each planned bottling draws water by tier (G45 {@link Tier} T1-T4). A bottling that would
 * pull the cistern below the reserve is refused. Bottles leave the shelf once older than their
 * tier's {@link Tier#shelfDays()}. Plain data in, plain data out; no randomness inside.
 */
public final class ArkCellar {

    /** Quest id for the Daedalus quest hook. */
    public static final String QUEST_ID = "q_ark_cellar";

    private static final double EPS = 1e-9;

    public record Rules(double cisternCapL, double springLPerDay, double rainLPerDay,
                        double crewLPerDay, double reserveL, Map<Tier, Double> waterPerBottleL) {
        public Rules {
            if (cisternCapL <= 0 || springLPerDay < 0 || rainLPerDay < 0 || crewLPerDay < 0
                    || reserveL < 0 || reserveL > cisternCapL) {
                throw new IllegalArgumentException("bad cellar rules");
            }
            EnumMap<Tier, Double> w = new EnumMap<>(Tier.class);
            for (Tier t : Tier.values()) {
                Double v = Objects.requireNonNull(waterPerBottleL.get(t), "water for " + t);
                if (v <= 0) {
                    throw new IllegalArgumentException("water per bottle must be > 0");
                }
                w.put(t, v);
            }
            waterPerBottleL = Collections.unmodifiableMap(w);
        }

        /** Default ark: 400 L cistern, 20 L/day spring, 60 L more on rainy days, 25 L crew, 80 L reserve. */
        public static Rules defaults() {
            return new Rules(400, 20, 60, 25, 80,
                    Map.of(Tier.T1, 0.5, Tier.T2, 0.5, Tier.T3, 0.75, Tier.T4, 1.0));
        }
    }

    /** One day's weather and bottling plan (bottles per tier). */
    public record Day(boolean rain, Map<Tier, Integer> bottlings) {
        public Day {
            EnumMap<Tier, Integer> b = new EnumMap<>(Tier.class);
            for (Map.Entry<Tier, Integer> e : bottlings.entrySet()) {
                if (e.getValue() < 0) {
                    throw new IllegalArgumentException("negative bottling");
                }
                b.put(e.getKey(), e.getValue());
            }
            bottlings = Collections.unmodifiableMap(b);
        }

        public static Day dry() {
            return new Day(false, Map.of());
        }
    }

    public record Lot(Tier tier, int bottledDay) { }

    public record State(double cisternL, List<Lot> cellar) {
        public State {
            if (cisternL < 0) {
                throw new IllegalArgumentException("cistern < 0");
            }
            cellar = List.copyOf(cellar);
        }

        public int onShelf(int minLevel) {
            int n = 0;
            for (Lot l : cellar) {
                if (l.tier().level() >= minLevel) {
                    n++;
                }
            }
            return n;
        }
    }

    public record DayReport(int day, State state, double inflowL, double spilledL, double crewL,
                            double bottlingL, int bottled, int refused, int expired,
                            boolean belowReserve) { }

    public record QuestResult(String questId, boolean passed, int bottlesOnShelf, List<DayReport> log) {
        public QuestResult {
            log = List.copyOf(log);
        }
    }

    private final Rules rules;

    public ArkCellar(Rules rules) {
        this.rules = Objects.requireNonNull(rules);
    }

    public Rules rules() {
        return rules;
    }

    public State start(double cisternL) {
        return new State(Math.max(0, Math.min(cisternL, rules.cisternCapL())), List.of());
    }

    public DayReport day(State s, int day, Day d) {
        double inflow = rules.springLPerDay() + (d.rain() ? rules.rainLPerDay() : 0);
        double filled = s.cisternL() + inflow;
        double spilled = Math.max(0, filled - rules.cisternCapL());
        double water = filled - spilled;
        double crew = Math.min(water, rules.crewLPerDay());
        water -= crew;

        List<Lot> cellar = new ArrayList<>();
        int expired = 0;
        for (Lot l : s.cellar()) {
            if (day - l.bottledDay() > l.tier().shelfDays()) {
                expired++;
            } else {
                cellar.add(l);
            }
        }
        double bottlingL = 0;
        int bottled = 0;
        int refused = 0;
        for (Tier t : Tier.values()) {
            int n = d.bottlings().getOrDefault(t, 0);
            double per = rules.waterPerBottleL().get(t);
            for (int i = 0; i < n; i++) {
                if (water - per >= rules.reserveL() - EPS) {
                    water -= per;
                    bottlingL += per;
                    bottled++;
                    cellar.add(new Lot(t, day));
                } else {
                    refused++;
                }
            }
        }
        water = Math.max(0, water);
        return new DayReport(day, new State(water, cellar), inflow, spilled, crew, bottlingL,
                bottled, refused, expired, water < rules.reserveL() - EPS);
    }

    /**
     * Quest q_ark_cellar: run the plan from day 0; pass when the cistern never ends a day below
     * reserve and the shelf holds at least {@code target} bottles of tier level {@code minLevel}+.
     */
    public QuestResult quest(double startL, List<Day> plan, int target, int minLevel) {
        State s = start(startL);
        List<DayReport> log = new ArrayList<>();
        boolean ok = true;
        for (int i = 0; i < plan.size(); i++) {
            DayReport r = day(s, i, plan.get(i));
            log.add(r);
            ok &= !r.belowReserve();
            s = r.state();
        }
        int shelf = s.onShelf(minLevel);
        return new QuestResult(QUEST_ID, ok && shelf >= target, shelf, log);
    }
}
