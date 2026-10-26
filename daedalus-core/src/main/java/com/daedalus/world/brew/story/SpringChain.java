// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.story;

import com.daedalus.world.brew.BrewBench;
import com.daedalus.world.colony.PlotState;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * The island springs, in the order the water comes back. Every spring runs cloudy ({@link BrewBench#RAW_WATER})
 * until a restored seed-song tune is sung into it; each restored tune purifies the NEXT cloudy spring in the chain,
 * after which it runs clean ({@link BrewBench#WATER}). Drawing is once per event id.
 */
public final class SpringChain {
    public static final int MAX_SPRINGS = 32;

    /** One spring: id, display name and units of water per draw. */
    public record Spring(String id, String name, int yield) {
        public Spring {
            if (id == null || id.isBlank() || name == null || yield <= 0) {
                throw new IllegalArgumentException("spring needs id, name and positive yield");
            }
        }
    }

    public enum Outcome { CLEAN, CLOUDY, DUPLICATE, UNKNOWN_SPRING, IGNORED }

    /** Result of one draw: what landed in the plot store and how much. */
    public record Draw(Outcome outcome, String item, int amount) {
    }

    private final List<Spring> springs;
    private final Map<String, String> purifiedBy = new LinkedHashMap<>();
    private final Set<String> events = new HashSet<>();

    public SpringChain(List<Spring> springs) {
        if (springs == null || springs.isEmpty() || springs.size() > MAX_SPRINGS) {
            throw new IllegalArgumentException("one to " + MAX_SPRINGS + " springs");
        }
        Set<String> ids = new HashSet<>();
        springs.forEach(s -> {
            if (!ids.add(s.id())) {
                throw new IllegalArgumentException("duplicate spring " + s.id());
            }
        });
        this.springs = List.copyOf(springs);
    }

    /** The default chain of Youtube Master Island: twelve springs, one per ark record, uphill from the homestead. */
    public static SpringChain island() {
        String[] names = {"Homestead Well", "Reed Seep", "Ferry Steps", "Goat Ledge", "Old Ark Keel", "Bell Hollow",
            "Mist Stair", "Lantern Pool", "Broken Choir", "Cloudfoot", "Needle Falls", "Summit Basin"};
        List<Spring> out = new ArrayList<>();
        for (int i = 0; i < names.length; i++) {
            out.add(new Spring("spring_" + (i + 1), names[i], 4 + i / 3));
        }
        return new SpringChain(out);
    }

    public List<Spring> springs() {
        return springs;
    }

    /** The next cloudy spring, or null when every spring runs clean. */
    public Spring nextCloudy() {
        for (Spring s : springs) {
            if (!purifiedBy.containsKey(s.id())) {
                return s;
            }
        }
        return null;
    }

    /** Sings a restored tune into the next cloudy spring; returns that spring, or null if all are clean. */
    Spring purifyNext(String tuneName) {
        Spring s = nextCloudy();
        if (s != null) {
            purifiedBy.put(s.id(), tuneName);
        }
        return s;
    }

    public boolean clean(String springId) {
        return purifiedBy.containsKey(springId);
    }

    /** Which tune purified a spring, or null. */
    public String purifiedBy(String springId) {
        return purifiedBy.get(springId);
    }

    public int cleanCount() {
        return purifiedBy.size();
    }

    /** Draws once at a spring into the plot store: clean water if purified, raw (cloudy) water otherwise. */
    public Draw draw(String eventId, String springId, PlotState plot) {
        if (eventId == null || eventId.isBlank() || eventId.length() > 128 || plot == null) {
            return new Draw(Outcome.IGNORED, null, 0);
        }
        Spring s = springs.stream().filter(x -> x.id().equals(springId)).findFirst().orElse(null);
        if (s == null) {
            return new Draw(Outcome.UNKNOWN_SPRING, null, 0);
        }
        if (!events.add(eventId)) {
            return new Draw(Outcome.DUPLICATE, null, 0);
        }
        boolean isClean = clean(s.id());
        String item = isClean ? BrewBench.WATER : BrewBench.RAW_WATER;
        plot.add(item, s.yield());
        return new Draw(isClean ? Outcome.CLEAN : Outcome.CLOUDY, item, s.yield());
    }
}
