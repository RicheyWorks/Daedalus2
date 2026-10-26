// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.breeding;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Maps a G28 pup {@link Coat} to the blender-team material instance for the Mob_CorsoPup coat slot. The table is the
 * {@code lookup} block of {@code Mob_CorsoPup.coat_variants.json} (schema bb-material-variants/1), keyed
 * {@code <coatKey>/<COLOUR>[/Storm]} where coatKey is the TuringCoat line ({@code Spots}, {@code Stripes},
 * {@code Labyrinth}, {@code None}). The pattern itself is grown by the parent material from the G21 field; the
 * instance only carries colour and storm streak.
 */
public final class CoatVariants {

    /** Classpath resource holding the delivered variant table. */
    public static final String RESOURCE = "Mob_CorsoPup.coat_variants.json";

    private static final Pattern LOOKUP = Pattern.compile("\"lookup\"\\s*:\\s*\\{([^}]*)\\}");
    private static final Pattern PAIR = Pattern.compile("\"([^\"]+)\"\\s*:\\s*\"([^\"]+)\"");

    private final Map<String, String> table;

    private CoatVariants(Map<String, String> table) {
        this.table = Collections.unmodifiableMap(table);
    }

    /** Parses the {@code lookup} block of a bb-material-variants JSON document. */
    public static CoatVariants fromJson(String json) {
        Objects.requireNonNull(json, "json");
        Matcher block = LOOKUP.matcher(json);
        if (!block.find()) {
            throw new IllegalArgumentException("no lookup block in coat variant table");
        }
        Map<String, String> table = new LinkedHashMap<>();
        Matcher pair = PAIR.matcher(block.group(1));
        while (pair.find()) {
            table.put(pair.group(1), pair.group(2));
        }
        if (table.isEmpty()) {
            throw new IllegalArgumentException("empty lookup block in coat variant table");
        }
        return new CoatVariants(table);
    }

    /** Loads the table shipped next to this class. */
    public static CoatVariants load() {
        try (InputStream in = CoatVariants.class.getResourceAsStream(RESOURCE)) {
            if (in == null) {
                throw new IllegalStateException("missing resource " + RESOURCE);
            }
            return fromJson(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    /** The lookup key for a coat: {@code <coatKey>/<COLOUR>} plus {@code /Storm} when storm-marked. */
    public static String key(Coat coat) {
        String base = coat.pattern().coatKey() + "/" + coat.colour().name();
        return coat.stormMarked() ? base + "/Storm" : base;
    }

    public int size() {
        return table.size();
    }

    /** The material instance for a coat, if the table has one. */
    public Optional<String> find(Coat coat) {
        return Optional.ofNullable(table.get(key(coat)));
    }

    /** The material instance for a coat; throws when the table has no entry. */
    public String material(Coat coat) {
        return find(coat).orElseThrow(() -> new IllegalArgumentException("no coat variant for " + key(coat)));
    }

    /** True when every coat G28 can produce has a material. */
    public boolean coversAllCoats() {
        for (Coat.Pattern p : Coat.Pattern.values()) {
            for (Coat.Colour c : Coat.Colour.values()) {
                if (!table.containsKey(key(new Coat(p, c, false))) || !table.containsKey(key(new Coat(p, c, true)))) {
                    return false;
                }
            }
        }
        return true;
    }

    /** Chance of each material instance from a cross: the G28 cross table summed per material. */
    public Map<String, Double> materialOdds(Genotype mother, Genotype father) {
        Map<String, Double> out = new LinkedHashMap<>();
        for (Map.Entry<Coat, Double> e : CoatOdds.cross(mother, father).entrySet()) {
            out.merge(material(e.getKey()), e.getValue(), Double::sum);
        }
        return out;
    }

    /** The material each pup of a seeded G28 litter spawns with, in birth order. */
    public List<String> litterMaterials(Genotype mother, Genotype father, long seed, int size) {
        return CoatOdds.litter(mother, father, seed, size).stream().map(g -> material(g.coat())).toList();
    }
}
