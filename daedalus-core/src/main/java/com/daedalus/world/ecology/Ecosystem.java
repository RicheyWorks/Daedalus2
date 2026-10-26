// SPDX-License-Identifier: MIT

package com.daedalus.world.ecology;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.SplittableRandom;
import java.util.TreeMap;

/**
 * Every island's community, stepped together one ecological day at a time (ADR-022).
 *
 * <p><b>Natural dispersal.</b> After the Shattering, only kinds that cross open sky alone reach a
 * new island without an ark. Each day every dispersing kind present anywhere sends drifters to every
 * other island with chance {@code DRIFT · e^(−distance / REACH)} — the c·e^(−distance) of
 * MacArthur–Wilson. A thin <b>wild-sky rain</b> also brings dispersers from the whole canon, so
 * even an isolated, empty island slowly gains wings and spores — at {@link #WILD_RAIN} a day for an
 * island of {@link #REF_AREA} habitat cells, more for a bigger one: a bigger island is a bigger
 * target (the target effect). Kinds that cannot fly arrive only by ark (ADR-023).
 *
 * <p><b>Local extinction</b> is MacArthur–Wilson's e/area: each kind on an island is wiped out on a
 * given day with chance {@link #CATASTROPHE}·{@link #REF_AREA}/area (storms, disease, a bad
 * season), capped at {@link #MAX_CATASTROPHE}. Together the two give the species–area relationship;
 * the first version had neither and big and small islands ended up equally rich (ADR-022).
 */
public final class Ecosystem {

    public static final double DRIFT = 0.08;
    public static final double REACH = 120.0;
    public static final double WILD_RAIN = 0.15;
    public static final double DRIFTERS = 2.0;
    public static final double REF_AREA = 1000.0;
    public static final double CATASTROPHE = 0.004;
    public static final double MAX_CATASTROPHE = 0.2;

    /** An island as the ecosystem sees it: its living space and where it sits. */
    public record Isle(int slot, Habitat habitat, double x, double z) {
    }

    private final SpeciesCanon canon;
    private final TreeMap<Integer, Isle> isles = new TreeMap<>();
    private final TreeMap<Integer, Community> communities = new TreeMap<>();
    private long day;

    public Ecosystem(SpeciesCanon canon) {
        this.canon = canon;
    }

    public void addIsle(Isle isle) {
        isles.put(isle.slot(), isle);
        communities.computeIfAbsent(isle.slot(), s -> new Community());
    }

    public Community community(int slot) {
        return communities.get(slot);
    }

    public Isle isle(int slot) {
        return isles.get(slot);
    }

    public Map<Integer, Community> communities() {
        return Collections.unmodifiableMap(communities);
    }

    public long day() {
        return day;
    }

    public void setDay(long day) {
        this.day = day;
    }

    /** What one day did, for the trace and the realm: arrivals by drift and kinds lost, per island. */
    public record DayReport(long day, Map<Integer, List<String>> drifted, Map<Integer, List<String>> rained,
                            Map<Integer, List<String>> lost) {

        /** Copy on construct, lists and all: a report is a record of a day, not a live view. */
        public DayReport {
            drifted = frozen(drifted);
            rained = frozen(rained);
            lost = frozen(lost);
        }

        private static Map<Integer, List<String>> frozen(Map<Integer, List<String>> m) {
            Map<Integer, List<String>> out = new TreeMap<>();
            if (m != null) {
                m.forEach((k, v) -> out.put(k, List.copyOf(v)));
            }
            return Collections.unmodifiableMap(out);
        }
    }

    /** Daily chance a kind on an island of this habitat is wiped out locally. */
    public static double catastrophe(Habitat h) {
        return Math.min(MAX_CATASTROPHE, CATASTROPHE * REF_AREA / Math.max(1.0, h.area()));
    }

    /** Daily chance the wild sky drops a disperser on an island of this habitat. */
    public static double rain(Habitat h) {
        return Math.min(1.0, WILD_RAIN * h.area() / REF_AREA);
    }

    /** Step every island one day. {@code seed} is the world's ecology seed. */
    public DayReport step(long seed) {
        day++;
        SplittableRandom rng = new SplittableRandom(seed * 0x9E3779B97F4A7C15L + day);
        Map<Integer, List<String>> drifted = new TreeMap<>();
        Map<Integer, List<String>> rained = new TreeMap<>();
        Map<Integer, List<String>> lost = new TreeMap<>();
        List<Species> dispersers = new ArrayList<>();
        for (Species s : canon.all()) {
            if (s.disperses()) {
                dispersers.add(s);
            }
        }
        for (Isle to : isles.values()) {
            Community home = communities.get(to.slot());
            List<String> came = new ArrayList<>();
            for (Isle from : isles.values()) {
                if (from.slot() == to.slot()) {
                    continue;
                }
                double chance = DRIFT * Math.exp(-Math.hypot(from.x() - to.x(), from.z() - to.z()) / REACH);
                for (Map.Entry<String, Double> e : communities.get(from.slot()).abundance().entrySet()) {
                    Species s = canon.byKey(e.getKey());
                    if (s != null && s.disperses() && rng.nextDouble() < chance
                            && home.arrive(s, DRIFTERS, to.habitat()) > 0) {
                        came.add(s.key());
                    }
                }
            }
            if (!came.isEmpty()) {
                drifted.put(to.slot(), came);
            }
            if (rng.nextDouble() < rain(to.habitat()) && !dispersers.isEmpty()) {
                Species s = dispersers.get(rng.nextInt(dispersers.size()));
                if (home.arrive(s, DRIFTERS, to.habitat()) > 0) {
                    rained.put(to.slot(), List.of(s.key()));
                }
            }
        }
        for (Isle isle : isles.values()) {
            Community c = communities.get(isle.slot());
            List<String> gone = new ArrayList<>();
            double wipe = catastrophe(isle.habitat());
            for (String key : new ArrayList<>(c.abundance().keySet())) {
                if (rng.nextDouble() < wipe) {
                    c.put(key, 0);
                    gone.add(key);
                }
            }
            gone.addAll(c.day(canon, isle.habitat(), rng.nextLong()));
            if (!gone.isEmpty()) {
                lost.put(isle.slot(), gone);
            }
        }
        return new DayReport(day, drifted, rained, lost);
    }
}
