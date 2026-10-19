// SPDX-License-Identifier: MIT

package com.daedalus.world.activity;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Turns one finished cast at Windmere's pond into an activity result.
 * The bite roll stays in the pond demo. This adapter only accepts a cast the demo already finished,
 * checks the species against {@code data/rpg/prism-fish.json}, and credits one subject once.
 */
public final class PrismPondFishing {
    public static final String ACTIVITY_ID = "prismheart.pond-fishing";
    public static final String SCHEMA = "daedalus.rpg-fish/v1";
    public static final String REALM = "prism";
    public static final String GOT_AWAY = "IT GOT AWAY.";
    public static final String TOO_SOON = "TOO SOON. THE RIPPLE SCATTERS.";
    public static final String LESSON_RIPPLE = "ripple-scattered";
    public static final int MAX_JSON = 32768;
    public static final int MAX_SPECIES = 64;

    private static final Pattern SPECIES_NAME = Pattern.compile("^[A-Z][a-z]+( [A-Z][a-z]+){0,3}$");
    private static final Set<String> RARITIES = Set.of("COMMON", "UNCOMMON", "RARE", "LEGENDARY");
    private static final Set<String> ROOT_KEYS = Set.of("schema", "realm", "about", "fish");
    private static final Set<String> FISH_KEYS = Set.of(
            "name", "rarity", "weight", "window_s", "effect", "price", "note", "night_weight");

    private PrismPondFishing() {
    }

    /** One species in the pond table. */
    public record Species(String name, String rarity, int weight, double windowSeconds, String effect,
                          int price, String note, Integer nightWeight) {
        /** Reads every stock field so a catalog row cannot quietly drop one. */
        public String stockLine() {
            return name + "|" + rarity + "|" + weight + "|" + windowSeconds + "|" + effect + "|"
                    + price + "|" + note + "|" + nightWeight;
        }
    }

    /** The pond table, in file order. */
    public static final class Catalog {
        private final List<Species> fish;
        private final Map<String, Species> byName;

        private Catalog(List<Species> fish) {
            this.fish = List.copyOf(fish);
            Map<String, Species> map = new LinkedHashMap<>();
            for (Species species : this.fish) {
                if (map.putIfAbsent(species.name(), species) != null) {
                    throw new IllegalArgumentException("prism-pond: duplicate species " + species.name());
                }
            }
            this.byName = Map.copyOf(map);
        }

        public List<Species> fish() {
            return fish;
        }

        public Species require(String name) {
            Species species = byName.get(name);
            if (species == null) {
                throw new IllegalArgumentException("prism-pond: unknown species " + name);
            }
            return species;
        }
    }

    /**
     * A finished cast. {@code phase} and {@code message} are the demo's fields.
     * {@code species} is {@code fishing.fish.name} when the pond has chosen one, otherwise null.
     */
    public record Cast(String attemptId, String subjectId, ActivityResult.SubjectKind subjectKind,
                       String phase, String message, String species) {
    }

    /** Parses {@code data/rpg/prism-fish.json}. Unknown versions and unknown species fields are refused. */
    public static Catalog catalog(String json) {
        if (json == null) {
            throw new IllegalArgumentException("prism-pond: json is required");
        }
        if (json.length() > MAX_JSON) {
            throw new IllegalArgumentException("prism-pond: json exceeds " + MAX_JSON + " characters");
        }
        Object value;
        try {
            value = ActivityJson.parse(json);
        } catch (IllegalArgumentException ex) {
            throw new IllegalArgumentException("prism-pond: " + ex.getMessage(), ex);
        }
        Map<String, Object> root = object(value, "catalog");
        rejectUnknown(root.keySet(), ROOT_KEYS, "catalog");
        if (!SCHEMA.equals(text(root.get("schema"), "schema"))) {
            throw new IllegalArgumentException("prism-pond: schema must be " + SCHEMA);
        }
        if (!REALM.equals(text(root.get("realm"), "realm"))) {
            throw new IllegalArgumentException("prism-pond: realm must be " + REALM);
        }
        if (root.containsKey("about")) {
            ascii(root.get("about"), "about", 800);
        }
        if (!(root.get("fish") instanceof List<?> rows) || rows.isEmpty() || rows.size() > MAX_SPECIES) {
            throw new IllegalArgumentException("prism-pond: fish must be 1.." + MAX_SPECIES + " species");
        }
        List<Species> fish = new ArrayList<>();
        for (Object row : rows) {
            fish.add(species(row));
        }
        Catalog catalog = new Catalog(fish);
        for (Species species : catalog.fish()) {
            String line = species.stockLine();
            if (!line.startsWith(species.name() + "|") || !line.contains("|" + species.rarity() + "|")) {
                throw new IllegalArgumentException("prism-pond: stock line lost " + species.name());
            }
        }
        return catalog;
    }

    /** The caught banner the pond demo writes, with or without the first-time {@code NEW! } prefix. */
    public static String caughtBanner(Species species, boolean firstOfKind) {
        String body = "CAUGHT A " + species.name().toUpperCase(Locale.ROOT) + " (" + species.rarity() + ").";
        return firstOfKind ? "NEW! " + body : body;
    }

    /** Lesson token for a catalog species. {@code Pond Perch} becomes {@code pond-perch}. */
    public static String lesson(String speciesName) {
        return speciesName.toLowerCase(Locale.ROOT).replace(' ', '-');
    }

    /** Maps one finished cast onto a v1 envelope. Refuses a cast that is still in the water. */
    public static ActivityResult fromCast(Cast cast, Catalog catalog) {
        if (cast == null || catalog == null) {
            throw new IllegalArgumentException("prism-pond: cast and catalog are required");
        }
        if (cast.phase() == null || cast.message() == null) {
            throw new IllegalArgumentException("prism-pond: phase and message are required");
        }
        if (!"done".equals(cast.phase())) {
            throw new IllegalArgumentException("prism-pond: activity is not finished");
        }
        if (TOO_SOON.equals(cast.message())) {
            if (cast.species() != null) {
                throw new IllegalArgumentException("prism-pond: a scattered cast has no species");
            }
            return envelope(cast, ActivityResult.Outcome.FAILED, LESSON_RIPPLE, Map.of("finish", "too-soon"));
        }
        if (GOT_AWAY.equals(cast.message())) {
            Species species = caughtSpecies(cast, catalog);
            return envelope(cast, ActivityResult.Outcome.MISSED, lesson(species.name()), detail(species, "got-away"));
        }
        Species species = caughtSpecies(cast, catalog);
        String fresh = caughtBanner(species, true);
        String again = caughtBanner(species, false);
        if (!fresh.equals(cast.message()) && !again.equals(cast.message())) {
            throw new IllegalArgumentException("prism-pond: banner does not match " + species.name());
        }
        return envelope(cast, ActivityResult.Outcome.LEARNED, lesson(species.name()), detail(species, "caught"));
    }

    /** Builds the envelope and credits it. A second delivery of the same cast is refused. */
    public static ActivityResultReceipt credit(ActivityCredit credit, Cast cast, Catalog catalog) {
        return ActivityResultReceipt.issue(credit, fromCast(cast, catalog));
    }

    private static Species caughtSpecies(Cast cast, Catalog catalog) {
        if (cast.species() == null) {
            throw new IllegalArgumentException("prism-pond: species is required");
        }
        return catalog.require(cast.species());
    }

    private static ActivityResult envelope(Cast cast, ActivityResult.Outcome outcome, String learned,
                                           Map<String, String> detail) {
        return new ActivityResult(
                ActivityResult.VERSION, ACTIVITY_ID, cast.attemptId(), cast.subjectId(), cast.subjectKind(),
                outcome, learned, detail);
    }

    private static Map<String, String> detail(Species species, String finish) {
        return Map.of(
                "effect", species.effect(),
                "finish", finish,
                "rarity", species.rarity(),
                "species", species.name());
    }

    private static Species species(Object raw) {
        Map<String, Object> row = object(raw, "fish");
        rejectUnknown(row.keySet(), FISH_KEYS, "fish");
        for (String key : List.of("name", "rarity", "weight", "window_s", "effect", "price", "note")) {
            if (!row.containsKey(key)) {
                throw new IllegalArgumentException("prism-pond: fish missing " + key);
            }
        }
        String name = ascii(row.get("name"), "name", 48);
        if (!SPECIES_NAME.matcher(name).matches()) {
            throw new IllegalArgumentException("prism-pond: bad species name");
        }
        String rarity = ascii(row.get("rarity"), "rarity", 16);
        if (!RARITIES.contains(rarity)) {
            throw new IllegalArgumentException("prism-pond: bad rarity");
        }
        int weight = integer(row.get("weight"), "weight", 1, 10_000);
        double window = real(row.get("window_s"), "window_s");
        String effect = ascii(row.get("effect"), "effect", 48);
        int price = integer(row.get("price"), "price", 0, 1_000_000);
        String note = ascii(row.get("note"), "note", 120);
        Integer night = null;
        if (row.containsKey("night_weight")) {
            night = integer(row.get("night_weight"), "night_weight", 1, 10_000);
        }
        return new Species(name, rarity, weight, window, effect, price, note, night);
    }

    private static void rejectUnknown(Set<String> keys, Set<String> allowed, String where) {
        for (String key : keys) {
            if (!allowed.contains(key)) {
                throw new IllegalArgumentException("prism-pond: unknown " + where + " field " + key);
            }
        }
    }

    private static Map<String, Object> object(Object value, String what) {
        if (!(value instanceof Map<?, ?> raw)) {
            throw new IllegalArgumentException("prism-pond: " + what + " must be an object");
        }
        Map<String, Object> out = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : raw.entrySet()) {
            out.put((String) entry.getKey(), entry.getValue());
        }
        return out;
    }

    private static String text(Object raw, String field) {
        if (!(raw instanceof String value)) {
            throw new IllegalArgumentException("prism-pond: " + field + " must be a string");
        }
        return value;
    }

    private static String ascii(Object raw, String field, int max) {
        String value = text(raw, field);
        if (value.isEmpty() || value.length() > max) {
            throw new IllegalArgumentException("prism-pond: " + field + " must be 1.." + max + " characters");
        }
        for (int n = 0; n < value.length(); n++) {
            char c = value.charAt(n);
            if (c < 0x20 || c > 0x7E) {
                throw new IllegalArgumentException("prism-pond: " + field + " must be printable ASCII");
            }
        }
        return value;
    }

    private static int integer(Object raw, String field, int min, int max) {
        final long v;
        if (raw instanceof Long n) {
            v = n;
        } else if (raw instanceof Double n && n >= Long.MIN_VALUE && n <= Long.MAX_VALUE && n == Math.rint(n)) {
            v = n.longValue();
        } else {
            throw new IllegalArgumentException("prism-pond: " + field + " must be an integer");
        }
        if (v < min || v > max) {
            throw new IllegalArgumentException("prism-pond: " + field + " must be " + min + ".." + max);
        }
        return (int) v;
    }

    private static double real(Object raw, String field) {
        final double v;
        if (raw instanceof Long n) {
            v = n.doubleValue();
        } else if (raw instanceof Double n) {
            v = n;
        } else {
            throw new IllegalArgumentException("prism-pond: " + field + " must be a number");
        }
        if (!Double.isFinite(v) || v <= 0 || v > 60) {
            throw new IllegalArgumentException("prism-pond: " + field + " must be a finite number in (0, 60]");
        }
        return v;
    }
}
