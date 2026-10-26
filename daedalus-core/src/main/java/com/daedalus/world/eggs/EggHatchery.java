// SPDX-License-Identifier: MIT

package com.daedalus.world.eggs;

import com.daedalus.world.companion.MiniJson;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.TreeMap;

/**
 * Egg hatching minigame core (PORT06 / WZ24, contest gap G06). Pure, JDK-only and deterministic: the same egg,
 * seed and care actions always give the same hatchling.
 *
 * <p>Rules come from {@code data/eggs/egg-hatch-v1.json}: the egg table is exported from Claude's
 * {@code tools/blender/voxel_eggs.py manifest()} (type, shell pattern, rarity, hatch pool by creature family) and the
 * {@code care} block adds the nest rules. Each care tick the keeper sets the nest warmth and may turn the egg.
 * A tick inside the warm band adds one growth point (two if the egg was turned); a tick outside the band is a chill,
 * and every {@code chillPenaltyEvery} chills cost one point (never below the start of the current stage). The egg goes
 * Intact -> Cracked -> Hatching at the stage thresholds and hatches at {@code hatchAt}.
 *
 * <p>Daedalus tie-in: the shell pattern decides the hatchling's coat (speckle/dots -> Spots, stripe/bands/zigzag ->
 * Stripes, marble/spiral -> Labyrinth, solid/facet -> None), which is the exact coat key the Kennel Isle
 * {@link com.daedalus.world.companion.TonicBrewer} reads, so a hatchling can drink trough tonics the moment it joins
 * the companion roster.
 */
public final class EggHatchery {
    public enum Stage { INTACT, CRACKED, HATCHING, HATCHED }

    /** One egg type from the manifest. */
    public record EggType(String name, String pattern, String rarity, Map<String, Integer> hatchPool) {
        public EggType {
            Objects.requireNonNull(name);
            Objects.requireNonNull(pattern);
            Objects.requireNonNull(rarity);
            hatchPool = Collections.unmodifiableMap(new TreeMap<>(hatchPool));
            if (hatchPool.isEmpty()) {
                throw new IllegalArgumentException("egg " + name + " has an empty hatch pool");
            }
        }
    }

    /** Nest rules. */
    public record Care(double warmMin, double warmMax, int crackAt, int hatchingAt, int hatchAt,
                       int chillPenaltyEvery, double shinyOdds, double perfectCareShinyMultiplier) {
        public Care {
            if (!(warmMin < warmMax) || !(0 < crackAt && crackAt < hatchingAt && hatchingAt < hatchAt)
                || chillPenaltyEvery < 1 || shinyOdds < 0 || shinyOdds > 1 || perfectCareShinyMultiplier < 1) {
                throw new IllegalArgumentException("bad egg care rules");
            }
        }
    }

    /** One keeper action for a tick. */
    public record CareAction(double warmth, boolean turned) { }

    /** Immutable egg state. */
    public record EggState(EggType type, long seed, Stage stage, int growth, int chills, int ticks, int turns,
                           Hatchling hatchling) {
        public boolean hatched() {
            return stage == Stage.HATCHED;
        }
    }

    /** What came out. {@code coat} is a TonicBrewer coat key. */
    public record Hatchling(String egg, String family, String coat, boolean shiny, String rarity, int careTicks,
                            boolean perfectCare) { }

    private final Map<String, EggType> eggs;
    private final Care care;

    public EggHatchery(Map<String, EggType> eggs, Care care) {
        if (eggs.isEmpty()) {
            throw new IllegalArgumentException("no eggs");
        }
        this.eggs = Collections.unmodifiableMap(new TreeMap<>(eggs));
        this.care = Objects.requireNonNull(care);
    }

    public static EggHatchery load(Path file) throws IOException {
        return parse(Files.readString(file, StandardCharsets.UTF_8));
    }

    @SuppressWarnings("unchecked")
    public static EggHatchery parse(String json) {
        Map<String, Object> root = (Map<String, Object>) MiniJson.parse(json);
        if (((Number) root.get("version")).intValue() != 1) {
            throw new IllegalArgumentException("egg-hatch version must be 1");
        }
        Map<String, Object> c = (Map<String, Object>) root.get("care");
        Care care = new Care(num(c, "warmMin"), num(c, "warmMax"), (int) num(c, "crackAt"),
            (int) num(c, "hatchingAt"), (int) num(c, "hatchAt"), (int) num(c, "chillPenaltyEvery"),
            num(root, "shiny_odds"), num(c, "perfectCareShinyMultiplier"));
        Map<String, EggType> eggs = new LinkedHashMap<>();
        for (Map.Entry<String, Object> e : ((Map<String, Object>) root.get("eggs")).entrySet()) {
            Map<String, Object> v = (Map<String, Object>) e.getValue();
            Map<String, Integer> pool = new LinkedHashMap<>();
            for (Map.Entry<String, Object> h : ((Map<String, Object>) v.get("hatch")).entrySet()) {
                int w = ((Number) h.getValue()).intValue();
                if (w <= 0) {
                    throw new IllegalArgumentException("egg " + e.getKey() + " weight must be > 0");
                }
                pool.put(h.getKey(), w);
            }
            eggs.put(e.getKey(), new EggType(e.getKey(), (String) v.get("pattern"), (String) v.get("rarity"), pool));
        }
        return new EggHatchery(eggs, care);
    }

    private static double num(Map<String, Object> m, String k) {
        Object v = m.get(k);
        if (!(v instanceof Number n)) {
            throw new IllegalArgumentException("egg-hatch missing number " + k);
        }
        return n.doubleValue();
    }

    public Map<String, EggType> eggs() {
        return eggs;
    }

    public Care care() {
        return care;
    }

    /** A fresh, intact egg. */
    public EggState start(String eggType, long seed) {
        EggType t = eggs.get(eggType);
        if (t == null) {
            throw new IllegalArgumentException("unknown egg " + eggType);
        }
        return new EggState(t, seed, Stage.INTACT, 0, 0, 0, 0, null);
    }

    /** Applies one care tick. A hatched egg is returned unchanged. */
    public EggState tick(EggState s, CareAction a) {
        if (s.hatched()) {
            return s;
        }
        boolean warm = a.warmth() >= care.warmMin() && a.warmth() <= care.warmMax();
        int growth = s.growth();
        int chills = s.chills();
        if (warm) {
            growth += a.turned() ? 2 : 1;
        } else {
            chills++;
            if (chills % care.chillPenaltyEvery() == 0) {
                growth = Math.max(stageFloor(s.stage()), growth - 1);
            }
        }
        int ticks = s.ticks() + 1;
        int turns = s.turns() + (a.turned() ? 1 : 0);
        Stage stage = stageFor(growth);
        Hatchling h = null;
        if (stage == Stage.HATCHED) {
            h = hatch(s.type(), s.seed(), ticks, chills == 0);
        }
        return new EggState(s.type(), s.seed(), stage, growth, chills, ticks, turns, h);
    }

    /** Runs a whole care plan; stops early once hatched. */
    public EggState run(EggState s, List<CareAction> plan) {
        for (CareAction a : plan) {
            if (s.hatched()) {
                break;
            }
            s = tick(s, a);
        }
        return s;
    }

    Stage stageFor(int growth) {
        if (growth >= care.hatchAt()) {
            return Stage.HATCHED;
        }
        if (growth >= care.hatchingAt()) {
            return Stage.HATCHING;
        }
        if (growth >= care.crackAt()) {
            return Stage.CRACKED;
        }
        return Stage.INTACT;
    }

    private int stageFloor(Stage st) {
        return switch (st) {
            case INTACT -> 0;
            case CRACKED -> care.crackAt();
            case HATCHING -> care.hatchingAt();
            case HATCHED -> care.hatchAt();
        };
    }

    Hatchling hatch(EggType t, long seed, int ticks, boolean perfect) {
        String family = rollFamily(t, seed);
        double odds = Math.min(1.0, care.shinyOdds() * (perfect ? care.perfectCareShinyMultiplier() : 1.0));
        boolean shiny = unit(mix(seed ^ 0x5EEDL, t.name().hashCode() * 31L + 7)) < odds;
        return new Hatchling(t.name(), family, coatFor(t.pattern()), shiny, t.rarity(), ticks, perfect);
    }

    /** Weighted family roll; deterministic per (egg, seed). */
    public static String rollFamily(EggType t, long seed) {
        int total = 0;
        for (int w : t.hatchPool().values()) {
            total += w;
        }
        long r = Long.remainderUnsigned(mix(seed, t.name().hashCode()), total);
        List<String> keys = new ArrayList<>(t.hatchPool().keySet());
        for (String k : keys) {
            r -= t.hatchPool().get(k);
            if (r < 0) {
                return k;
            }
        }
        return keys.get(keys.size() - 1);
    }

    /** Shell pattern -> TonicBrewer coat key. */
    public static String coatFor(String pattern) {
        return switch (pattern) {
            case "speckle", "dots" -> "Spots";
            case "stripe", "bands", "zigzag" -> "Stripes";
            case "marble", "spiral" -> "Labyrinth";
            default -> "None";
        };
    }

    static long mix(long a, long b) {
        long z = a * 0x9E3779B97F4A7C15L + b;
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        return z ^ (z >>> 31);
    }

    static double unit(long z) {
        return (z >>> 11) * 0x1.0p-53;
    }
}
