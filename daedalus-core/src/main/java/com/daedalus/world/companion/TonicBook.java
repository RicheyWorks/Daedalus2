// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.TreeSet;

/**
 * Kennel Isle's trough-brew pet tonics, loaded from {@code tools/islands/kennel-isle/tonics.json} (version 1).
 * The book is the single rule source: which herb sets make which tonic, and how coat pattern, drinker,
 * stage and charm scale it. {@link TonicBrewer} turns a recipe into a concrete, scaled brew.
 */
public final class TonicBook {
    /** One stat change: {@code op} is "add" or "mul". */
    public record Mod(String stat, String op, double value) {
    }

    /** One precomputed recipe from the book. Herb order never matters. */
    public record Recipe(String id, String name, List<String> herbs, String family, String shape, String finish,
                         int durationSec, String mode, List<Mod> mods, List<String> grants, double breedChancePct) {
        /** Defensive copies keep the book immutable. */
        public Recipe {
            herbs = List.copyOf(herbs);
            mods = List.copyOf(mods);
            grants = List.copyOf(grants);
        }
    }

    private final int maxHerbs;
    private final int decayDrinks;
    private final int decayMinutes;
    private final Map<String, String> herbRoles;
    private final Map<String, Recipe> byKey;
    private final Map<String, Map<String, Double>> coat;
    private final Map<String, Double> drinker;
    private final Map<Integer, Double> stageBonus;
    private final double charmMatching;

    private TonicBook(int maxHerbs, int decayDrinks, int decayMinutes, Map<String, String> herbRoles,
                      Map<String, Recipe> byKey, Map<String, Map<String, Double>> coat, Map<String, Double> drinker,
                      Map<Integer, Double> stageBonus, double charmMatching) {
        this.maxHerbs = maxHerbs;
        this.decayDrinks = decayDrinks;
        this.decayMinutes = decayMinutes;
        this.herbRoles = herbRoles;
        this.byKey = byKey;
        this.coat = coat;
        this.drinker = drinker;
        this.stageBonus = stageBonus;
        this.charmMatching = charmMatching;
    }

    /** Loads the book from a tonics.json file. */
    public static TonicBook load(Path file) throws IOException {
        return parse(Files.readString(file, StandardCharsets.UTF_8));
    }

    /** Parses tonics.json text. Rejects unknown versions and recipes that name unknown herbs. */
    @SuppressWarnings("unchecked")
    public static TonicBook parse(String json) {
        Map<String, Object> root = (Map<String, Object>) MiniJson.parse(json);
        if (num(root, "version") != 1) {
            throw new IllegalArgumentException("tonics json: unsupported version " + root.get("version"));
        }
        Map<String, Object> vessel = (Map<String, Object>) root.get("vessel");
        Map<String, Object> decay = (Map<String, Object>) vessel.get("decay");
        Map<String, String> roles = new LinkedHashMap<>();
        ((Map<String, Object>) root.get("herbs")).forEach((k, v) -> roles.put(k, (String) ((Map<String, Object>) v).get("role")));
        Map<String, Recipe> recipes = new LinkedHashMap<>();
        for (Object o : (List<Object>) root.get("recipes")) {
            Map<String, Object> r = (Map<String, Object>) o;
            List<String> herbs = new ArrayList<>();
            for (Object h : (List<Object>) r.get("herbs")) {
                if (!roles.containsKey((String) h)) {
                    throw new IllegalArgumentException("tonics json: recipe " + r.get("id") + " names unknown herb " + h);
                }
                herbs.add((String) h);
            }
            List<Mod> mods = new ArrayList<>();
            for (Object m : (List<Object>) r.get("mods")) {
                Map<String, Object> mm = (Map<String, Object>) m;
                mods.add(new Mod((String) mm.get("stat"), (String) mm.get("op"), num(mm, "value")));
            }
            List<String> grants = new ArrayList<>();
            if (r.get("grants") != null) {
                for (Object g : (List<Object>) r.get("grants")) {
                    grants.add((String) g);
                }
            }
            double breed = r.get("breedChancePct") == null ? 0 : num(r, "breedChancePct");
            Recipe rec = new Recipe((String) r.get("id"), (String) r.get("name"), herbs, (String) r.get("family"),
                (String) r.get("shape"), (String) r.get("finish"), (int) num(r, "durationSec"), (String) r.get("mode"),
                mods, grants, breed);
            if (recipes.put(key(herbs), rec) != null) {
                throw new IllegalArgumentException("tonics json: duplicate herb set " + herbs);
            }
        }
        Map<String, Object> st = (Map<String, Object>) root.get("strength");
        Map<String, Map<String, Double>> coat = new LinkedHashMap<>();
        ((Map<String, Object>) st.get("coat")).forEach((k, v) -> {
            Map<String, Double> m = new LinkedHashMap<>();
            ((Map<String, Object>) v).forEach((kk, vv) -> m.put(kk, (Double) vv));
            coat.put(k, m);
        });
        Map<String, Double> drinker = new LinkedHashMap<>();
        ((Map<String, Object>) st.get("drinker")).forEach((k, v) -> drinker.put(k, (Double) v));
        Map<Integer, Double> stage = new LinkedHashMap<>();
        ((Map<String, Object>) st.get("stageBonus")).forEach((k, v) -> stage.put(Integer.parseInt(k), (Double) v));
        double charm = num((Map<String, Object>) st.get("charm"), "matchingCharmSlot");
        return new TonicBook((int) num(vessel, "maxHerbs"), (int) num(decay, "drinks"), (int) num(decay, "minutes"),
            Collections.unmodifiableMap(roles), Collections.unmodifiableMap(recipes), coat, drinker, stage, charm);
    }

    private static double num(Map<String, Object> m, String k) {
        Object v = m.get(k);
        if (!(v instanceof Double d)) {
            throw new IllegalArgumentException("tonics json: missing number " + k);
        }
        return d;
    }

    private static String key(Collection<String> herbs) {
        return String.join("+", new TreeSet<>(herbs));
    }

    /** Finds the recipe for a set of herbs in any order; empty when the trough would fizzle. */
    public Optional<Recipe> recipe(Collection<String> herbs) {
        if (herbs.isEmpty() || herbs.size() > maxHerbs || new TreeSet<>(herbs).size() != herbs.size()) {
            return Optional.empty();
        }
        return Optional.ofNullable(byKey.get(key(herbs)));
    }

    /** All recipes, in file order. */
    public List<Recipe> recipes() {
        return List.copyOf(byKey.values());
    }

    /** Herb name to role (base, heart, finish). */
    public Map<String, String> herbRoles() {
        return Map.copyOf(herbRoles);
    }

    /** Most herbs one trough brew takes. */
    public int maxHerbs() {
        return maxHerbs;
    }

    /** Drinks a brew lasts before it is spent. */
    public int decayDrinks() {
        return decayDrinks;
    }

    /** Minutes a brew lasts before it goes flat. */
    public int decayMinutes() {
        return decayMinutes;
    }

    double coatMultiplier(String coatPattern, String shape) {
        Map<String, Double> m = coat.getOrDefault(coatPattern, coat.get("None"));
        return m.getOrDefault(shape == null ? "burst" : shape.toLowerCase(Locale.ROOT), 1.0);
    }

    double drinkerMultiplier(String drinkerKind) {
        Double d = drinker.get(drinkerKind);
        return d != null ? d : drinker.getOrDefault("other", 1.0);
    }

    double stageMultiplier(int stage) {
        return stageBonus.getOrDefault(stage, 1.0);
    }

    double charmMultiplier(boolean matchingCharm) {
        return matchingCharm ? charmMatching : 1.0;
    }
}
