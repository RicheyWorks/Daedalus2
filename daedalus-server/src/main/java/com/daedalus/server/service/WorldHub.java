// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.world.WorldId;
import com.daedalus.world.WorldStyle;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * Every world this server mounts (ADR-030). World Zero is the Spring {@link WorldService} bean and is
 * always first; every other world is its own {@link WorldService} with its own DAEW file and
 * sidecars beside World Zero's ({@code <id>.daew}, {@code <id>.daew.islands}, …), publishing on the
 * same event stream so STOMP frames reach {@code /topic/world/<id>/…}. The registry — id, style, seed,
 * title — persists as {@code worlds.registry} beside World Zero's file; worlds regrow from it on boot.
 */
@Service
public class WorldHub {

    public static final int MAX_WORLDS = 16;
    private static final Pattern ID = Pattern.compile("^[a-z0-9](?:[a-z0-9-]{1,30})[a-z0-9]$");

    /** A mounted world as the registry remembers it. */
    public record WorldEntry(String id, WorldStyle style, long seed, String title) {
    }

    /** Outcome of {@link #create}: CREATED, EXISTS, BAD_ID, BAD_TITLE, STYLE_NOT_READY or FULL. */
    public record WorldWrite(String result, WorldEntry world) {
    }

    private final WorldService zero;
    private final ApplicationEventPublisher publisher;
    private final Map<String, WorldEntry> entries = new LinkedHashMap<>();
    private final Map<String, WorldService> mounted = new LinkedHashMap<>();
    private final Object lock = new Object();

    public WorldHub(WorldService zero, ApplicationEventPublisher publisher) {
        this.zero = zero;
        this.publisher = publisher;
        entries.put(WorldId.ZERO.value(), new WorldEntry(WorldId.ZERO.value(), WorldStyle.SKY_ISLANDS, 0, "World Zero"));
        mounted.put(WorldId.ZERO.value(), zero);
        load();
    }

    /** A hub over World Zero alone, for code and tests that never mount another world. */
    public static WorldHub of(WorldService zero) {
        return new WorldHub(zero, event -> { });
    }

    /** The world with this id, or null when none is mounted. */
    public WorldService get(String id) {
        synchronized (lock) {
            return id == null ? null : mounted.get(id);
        }
    }

    /** World Zero, or the world {@code id} names when it is mounted (callers then 404 on null reads). */
    public WorldService resolve(String id) {
        WorldService w = get(id);
        return w == null ? zero : w;
    }

    public List<WorldEntry> worlds() {
        synchronized (lock) {
            return List.copyOf(entries.values());
        }
    }

    public List<WorldService> services() {
        synchronized (lock) {
            return List.copyOf(mounted.values());
        }
    }

    /**
     * Mount a new world. A sky-islands world is born with one island grown from its seed, so it is
     * never an empty sky; a Parcels world with its district laid out (ADR-033); a Bricks world with
     * its baseplate, spawn, runway and obby (ADR-034); a Gallery City with its streets and galleries (ADR-035). Styles whose generator
     * has not shipped answer STYLE_NOT_READY (ADR-029).
     */
    public WorldWrite create(String id, WorldStyle style, long seed, String title) {
        synchronized (lock) {
            if (id == null || !ID.matcher(id).matches()) {
                return new WorldWrite("BAD_ID", null);
            }
            String name = title == null ? "" : title.strip();
            if (name.isEmpty() || name.length() > 48 || name.chars().anyMatch(Character::isISOControl)) {
                return new WorldWrite("BAD_TITLE", null);
            }
            if (entries.containsKey(id)) {
                return new WorldWrite("EXISTS", entries.get(id));
            }
            if (style == null || !style.ready()) {
                return new WorldWrite("STYLE_NOT_READY", null);
            }
            if (entries.size() >= MAX_WORLDS) {
                return new WorldWrite("FULL", null);
            }
            WorldEntry entry = new WorldEntry(id, style, seed, name);
            WorldService world = mount(entry);
            if (style == WorldStyle.SKY_ISLANDS && world.islands(id).isEmpty()) {
                world.raiseIsland(id, seed, 18);
            } else if (style == WorldStyle.PARCELS) {
                world.raiseDistrict(id, seed);
            } else if (style == WorldStyle.BRICKS) {
                world.raiseBricks(id, seed);
            } else if (style == WorldStyle.GALLERY) {
                world.raiseGallery(id, seed);
            } else if (style == WorldStyle.LABYRINTH) {
                world.raiseLabyrinth(id, seed);
            }
            entries.put(id, entry);
            persist();
            return new WorldWrite("CREATED", entry);
        }
    }

    /** Outcome of {@link #openGate}: OPENED with both gate indexes, or why not. */
    public record GateWrite(String result, int fromGate, int toGate) {
    }

    /**
     * Open a pair of sky gates between two worlds (ADR-031): one in each world's clouds, past its
     * rainbow, each leading to the other. Results: OPENED, SAME_WORLD, NO_SUCH_WORLD, ALREADY_LINKED,
     * FULL (a world has no free gate). Both gates are built or neither is.
     */
    public GateWrite openGate(String fromId, String toId) {
        synchronized (lock) {
            WorldService a = mounted.get(fromId);
            WorldService b = mounted.get(toId);
            if (a == null || b == null) {
                return new GateWrite("NO_SUCH_WORLD", -1, -1);
            }
            if (fromId.equals(toId)) {
                return new GateWrite("SAME_WORLD", -1, -1);
            }
            if (a.hasGateTo(fromId, toId) || b.hasGateTo(toId, fromId)) {
                return new GateWrite("ALREADY_LINKED", -1, -1);
            }
            int ga = a.freeGate(fromId);
            int gb = b.freeGate(toId);
            if (ga < 0 || gb < 0) {
                return new GateWrite("FULL", -1, -1);
            }
            if (!a.addGate(fromId, ga, toId, gb)) {
                return new GateWrite("FULL", -1, -1);
            }
            if (!b.addGate(toId, gb, fromId, ga)) {
                a.dropGate(fromId, ga);
                return new GateWrite("FULL", -1, -1);
            }
            return new GateWrite("OPENED", ga, gb);
        }
    }

    /** The title a world goes by, or its id when it is not mounted. */
    public String title(String id) {
        synchronized (lock) {
            WorldEntry e = entries.get(id);
            return e == null ? id : e.title();
        }
    }

    /** The style of a mounted world, or null. */
    public com.daedalus.world.WorldStyle style(String id) {
        synchronized (lock) {
            WorldEntry e = entries.get(id);
            return e == null ? null : e.style();
        }
    }

    private WorldService mount(WorldEntry entry) {
        Path file = zero.file().resolveSibling(entry.id() + ".daew");
        WorldService world = new WorldService(file, new WorldId(entry.id()), publisher);
        world.useDayLength(zero.dayLength());
        world.useStyle(entry.style(), entry.seed());
        mounted.put(entry.id(), world);
        return world;
    }

    Path registryFile() {
        return zero.file().resolveSibling("worlds.registry");
    }

    private void load() {
        Path f = registryFile();
        if (!Files.exists(f)) {
            return;
        }
        try {
            for (String line : Files.readAllLines(f, StandardCharsets.UTF_8)) {
                String t = line.strip();
                if (t.isEmpty() || t.startsWith("#")) {
                    continue;
                }
                String[] p = t.split("\\s+", 4);
                if (p.length != 4 || !ID.matcher(p[0]).matches()) {
                    throw new IOException("Bad world registry row: " + t);
                }
                WorldEntry e = new WorldEntry(p[0], WorldStyle.valueOf(p[1]), Long.parseLong(p[2]), p[3]);
                entries.put(e.id(), e);
                mount(e);
            }
        } catch (IOException | IllegalArgumentException e) {
            throw new IllegalStateException("Cannot read world registry " + f, e);
        }
    }

    private void persist() {
        Path f = registryFile();
        List<String> rows = new ArrayList<>();
        rows.add("# Daedalus worlds (ADR-030): id style seed title. World Zero is implicit.");
        for (WorldEntry e : entries.values()) {
            if (!WorldId.ZERO.value().equals(e.id())) {
                rows.add(e.id() + " " + e.style() + " " + e.seed() + " " + e.title());
            }
        }
        try {
            Path tmp = f.resolveSibling(f.getFileName() + ".tmp");
            Files.write(tmp, rows, StandardCharsets.UTF_8);
            Files.move(tmp, f, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException e) {
            throw new UncheckedIOException("Cannot persist world registry " + f, e);
        }
    }
}
