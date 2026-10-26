// SPDX-License-Identifier: MIT

package com.daedalus.world.ecology;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * The species canon (ADR-021): every kind the world knows, loaded once from
 * {@code species.tsv} on the classpath. Order is the catalog's, so an index is stable.
 */
public final class SpeciesCanon {

    private static final String RESOURCE = "/com/daedalus/world/ecology/species.tsv";
    private static final SpeciesCanon INSTANCE = load();

    private final List<Species> all;
    private final Map<String, Species> byKey;
    private final Map<Guild, List<Species>> byGuild;

    private SpeciesCanon(List<Species> all) {
        this.all = List.copyOf(all);
        Map<String, Species> keys = new LinkedHashMap<>();
        Map<Guild, List<Species>> guilds = new EnumMap<>(Guild.class);
        for (Guild g : Guild.values()) {
            guilds.put(g, new ArrayList<>());
        }
        for (Species s : all) {
            if (keys.put(s.key(), s) != null) {
                throw new IllegalStateException("Duplicate species key " + s.key());
            }
            guilds.get(s.guild()).add(s);
        }
        guilds.replaceAll((g, list) -> List.copyOf(list));
        this.byKey = Collections.unmodifiableMap(keys);
        this.byGuild = Collections.unmodifiableMap(guilds);
    }

    public static SpeciesCanon get() {
        return INSTANCE;
    }

    public List<Species> all() {
        return all;
    }

    public Species byKey(String key) {
        return byKey.get(key);
    }

    public List<Species> guild(Guild guild) {
        return byGuild.get(guild);
    }

    static SpeciesCanon parse(InputStream in) throws IOException {
        List<Species> rows = new ArrayList<>();
        try (BufferedReader r = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8))) {
            String line;
            int n = 0;
            while ((line = r.readLine()) != null) {
                n++;
                if (line.isBlank() || line.startsWith("#")) {
                    continue;
                }
                String[] f = line.split("\t", -1);
                if (f.length != 8 || f[6].length() != 1 || !"RK".contains(f[6])
                        || !("0".equals(f[7]) || "1".equals(f[7]))) {
                    throw new IOException("Bad species row " + n + ": " + line);
                }
                rows.add(new Species(f[0], f[1], f[2], f[3], Guild.valueOf(f[4]), f[5],
                        f[6].charAt(0), "1".equals(f[7])));
            }
        }
        return new SpeciesCanon(rows);
    }

    private static SpeciesCanon load() {
        try (InputStream in = SpeciesCanon.class.getResourceAsStream(RESOURCE)) {
            if (in == null) {
                throw new IllegalStateException("Species canon missing: " + RESOURCE);
            }
            return parse(in);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
