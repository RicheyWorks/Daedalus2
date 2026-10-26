// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * Kennel Isle's fresh-water loop as a daily ledger (contest gap G17), from {@code data/islands/kennel-water-v1.json}.
 * Pure and deterministic.
 *
 * <p>Each day: raw water (spring unless silted, rain catchers on rainy days, hauled well buckets) passes the sand and
 * charcoal filter up to its daily capacity (a clogged filter passes nothing drinkable); the solar still adds distilled
 * water on sunny days without the filter. Drinkable water fills the cistern (overflow spills). Animals then drink from
 * the troughs; if the cistern can't cover everyone, each gets the same share of its need, and anyone short goes up one
 * thirst stage (stats drain {@code thirstDrainPctPerStage} per stage up to the cap). A full drink resets thirst.
 * Herbs are watered last from what is left.
 *
 * <p>Quest "The Quiet Spring" ({@link #quietSpring}): the spring is silted and the cistern drained; keep every animal
 * watered through the dry days with the backups alone.
 */
public final class KennelWaterLoop {
    public record Rules(double springLPerDay, int rainCatchers, double rainLPerTick, int rainTicksPerRainyDay,
                        double stillLPerSunnyDay, double wellBucketL, int wellMaxHaulsPerDay, double filterLPerDay,
                        double cisternL, double herbLPerPlantPerDay, Map<String, Double> needs,
                        int drainPerStage, int drainCap, int questDryDays, double questStartCisternL) {
        public Rules {
            needs = Collections.unmodifiableMap(new TreeMap<>(needs));
            if (cisternL <= 0 || filterLPerDay < 0 || drainPerStage < 0 || drainCap < 0 || questDryDays < 1) {
                throw new IllegalArgumentException("bad kennel water rules");
            }
        }
    }

    /** One day's weather and keeper choices. */
    public record Day(boolean rain, boolean sunny, boolean springSilted, boolean filterClogged, int wellHauls) {
        public static Day dry(int wellHauls) {
            return new Day(false, true, true, false, wellHauls);
        }
    }

    /** One animal on the island. {@code kind} must be in the needs table. */
    public record Animal(String name, String kind) { }

    public record State(double cisternL, Map<String, Integer> thirst) {
        public State {
            thirst = Collections.unmodifiableMap(new TreeMap<>(thirst));
        }

        public int drainPct(Rules r, String animal) {
            return Math.min(r.drainCap(), r.drainPerStage() * thirst.getOrDefault(animal, 0));
        }
    }

    public record DayReport(State state, double inflowL, double spilledL, double drunkL, double herbL,
                            List<String> thirsty) {
        public DayReport {
            thirsty = List.copyOf(thirsty);
        }
    }

    private final Rules r;

    public KennelWaterLoop(Rules rules) {
        this.r = rules;
    }

    public Rules rules() {
        return r;
    }

    public static KennelWaterLoop load(Path p) throws IOException {
        return parse(Files.readString(p, StandardCharsets.UTF_8));
    }

    @SuppressWarnings("unchecked")
    public static KennelWaterLoop parse(String json) {
        Map<String, Object> m = (Map<String, Object>) MiniJson.parse(json);
        if (!(m.get("version") instanceof Number v) || v.intValue() != 1) {
            throw new IllegalArgumentException("kennel water version must be 1");
        }
        Map<String, Object> s = (Map<String, Object>) m.get("sources");
        Map<String, Object> q = (Map<String, Object>) m.get("quest");
        Map<String, Double> needs = new LinkedHashMap<>();
        for (Map.Entry<String, Object> e : ((Map<String, Object>) m.get("needsLPerDay")).entrySet()) {
            needs.put(e.getKey(), ((Number) e.getValue()).doubleValue());
        }
        return new KennelWaterLoop(new Rules(n(s, "springLPerDay"), (int) n(s, "rainCatchers"), n(s, "rainLPerTick"),
            (int) n(s, "rainTicksPerRainyDay"), n(s, "stillLPerSunnyDay"), n(s, "wellBucketL"),
            (int) n(s, "wellMaxHaulsPerDay"), n(m, "filterLPerDay"), n(m, "cisternL"), n(m, "herbLPerPlantPerDay"),
            needs, (int) n(m, "thirstDrainPctPerStage"), (int) n(m, "thirstDrainCapPct"), (int) n(q, "dryDays"),
            n(q, "startCisternL")));
    }

    private static double n(Map<String, Object> m, String k) {
        if (!(m.get(k) instanceof Number x)) {
            throw new IllegalArgumentException("kennel water missing number " + k);
        }
        return x.doubleValue();
    }

    public State start(double cisternL) {
        return new State(Math.max(0, Math.min(r.cisternL(), cisternL)), Map.of());
    }

    /** Daily water need of the whole roster (litres). */
    public double need(List<Animal> animals) {
        double t = 0;
        for (Animal a : animals) {
            t += needOf(a);
        }
        return t;
    }

    private double needOf(Animal a) {
        Double n = r.needs().get(a.kind());
        if (n == null) {
            throw new IllegalArgumentException("unknown animal kind " + a.kind());
        }
        return n;
    }

    public DayReport day(State s, Day d, List<Animal> animals, int herbPlants) {
        int hauls = Math.max(0, Math.min(r.wellMaxHaulsPerDay(), d.wellHauls()));
        double raw = (d.springSilted() ? 0 : r.springLPerDay())
            + (d.rain() ? r.rainCatchers() * r.rainLPerTick() * r.rainTicksPerRainyDay() : 0)
            + hauls * r.wellBucketL();
        double filtered = d.filterClogged() ? 0 : Math.min(raw, r.filterLPerDay());
        double inflow = filtered + (d.sunny() ? r.stillLPerSunnyDay() : 0);
        double cistern = s.cisternL() + inflow;
        double spilled = Math.max(0, cistern - r.cisternL());
        cistern -= spilled;

        double need = need(animals);
        double share = need == 0 ? 1 : Math.min(1, cistern / need);
        double drunk = need * share;
        cistern -= drunk;
        Map<String, Integer> thirst = new TreeMap<>(s.thirst());
        List<String> thirsty = new ArrayList<>();
        for (Animal a : animals) {
            if (share < 1 - 1e-9) {
                thirst.merge(a.name(), 1, Integer::sum);
                thirsty.add(a.name());
            } else {
                thirst.remove(a.name());
            }
        }
        double herb = Math.min(cistern, herbPlants * r.herbLPerPlantPerDay());
        cistern -= herb;
        return new DayReport(new State(cistern, thirst), inflow, spilled, drunk, herb, thirsty);
    }

    public record QuestResult(String questId, boolean passed, int days, List<DayReport> log) {
        public QuestResult {
            log = List.copyOf(log);
        }
    }

    /**
     * "The Quiet Spring": spring silted, filter clean, no rain, sunny, cistern starts at the quest level. The keeper
     * chooses well hauls per day ({@code haulPlan}, last value repeats). Passes when nobody is thirsty on any dry day.
     */
    public QuestResult quietSpring(List<Animal> animals, int herbPlants, List<Integer> haulPlan) {
        if (haulPlan.isEmpty()) {
            throw new IllegalArgumentException("haul plan is empty");
        }
        State s = start(r.questStartCisternL());
        List<DayReport> log = new ArrayList<>();
        boolean ok = true;
        for (int i = 0; i < r.questDryDays(); i++) {
            int hauls = haulPlan.get(Math.min(i, haulPlan.size() - 1));
            DayReport rep = day(s, Day.dry(hauls), animals, herbPlants);
            log.add(rep);
            ok &= rep.thirsty().isEmpty();
            s = rep.state();
        }
        return new QuestResult("kennel_quiet_spring", ok, r.questDryDays(), log);
    }

    /** Fewest daily well hauls that pass the quest for this roster (or -1 if even the maximum fails). */
    public int minHauls(List<Animal> animals, int herbPlants) {
        for (int h = 0; h <= r.wellMaxHaulsPerDay(); h++) {
            if (quietSpring(animals, herbPlants, List.of(h)).passed()) {
                return h;
            }
        }
        return -1;
    }
}
