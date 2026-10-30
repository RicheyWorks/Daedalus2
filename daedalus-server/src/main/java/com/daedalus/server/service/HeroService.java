// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.world.WorldId;
import com.daedalus.world.adventure.FoeKind;
import com.daedalus.world.adventure.Hero;
import com.daedalus.world.adventure.HeroRules;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.function.LongSupplier;

/**
 * Every adventurer's progress (ADR-037), one hero per person across all worlds, saved beside the worlds as
 * {@code heroes.daeh}: {@code name exp attack magic life beaten} per line. The server owns experience: a
 * client reports which foe it beat, and the server adds that foe's experience from its own table. A client
 * may not report beating foes faster than a sword can swing.
 */
@Service
public class HeroService {

    /** The quickest two foes can fall to one sword: a thrust, its recovery, and the next thrust. */
    public static final long MIN_BETWEEN_MS = 350;

    /** A hero after a request, and what happened: BEAT, TOO_FAST, RAISED, NOT_ENOUGH, FELL, HEALED, BAD_ACTOR. */
    public record HeroWrite(String result, Hero hero) {
    }

    private final Path file;
    private final TreeMap<String, Hero> heroes = new TreeMap<>();
    private final Map<String, Long> lastBeat = new HashMap<>();
    private final Object lock = new Object();
    private LongSupplier clock = System::currentTimeMillis;

    @Autowired
    public HeroService(WorldHub hub) {
        this(hub.get(WorldId.ZERO.value()).file().resolveSibling("heroes.daeh"));
    }

    public HeroService(Path file) {
        this.file = file;
        load();
    }

    public void useClock(LongSupplier clock) {
        this.clock = clock;
    }

    static boolean badName(String name) {
        return name == null || name.isBlank() || name.length() > 64 || !name.trim().matches("[A-Za-z0-9._@-]+");
    }

    /** The hero of this name: their saved progress, or a fresh hero. Null for a name that cannot be one. */
    public Hero hero(String name) {
        if (badName(name)) {
            return null;
        }
        synchronized (lock) {
            return heroes.getOrDefault(name.trim(), Hero.fresh(name.trim()));
        }
    }

    public HeroWrite beat(String name, FoeKind foe) {
        if (badName(name)) {
            return new HeroWrite("BAD_ACTOR", null);
        }
        synchronized (lock) {
            String n = name.trim();
            long now = clock.getAsLong();
            Long last = lastBeat.get(n);
            Hero h = heroes.getOrDefault(n, Hero.fresh(n));
            if (last != null && now - last < MIN_BETWEEN_MS) {
                return new HeroWrite("TOO_FAST", h);
            }
            lastBeat.put(n, now);
            h = h.beat(foe);
            heroes.put(n, h);
            persist();
            return new HeroWrite("BEAT", h);
        }
    }

    public HeroWrite raise(String name, HeroRules.Stat stat) {
        if (badName(name)) {
            return new HeroWrite("BAD_ACTOR", null);
        }
        synchronized (lock) {
            String n = name.trim();
            Hero h = heroes.getOrDefault(n, Hero.fresh(n));
            if (!h.canRaise(stat)) {
                return new HeroWrite("NOT_ENOUGH", h);
            }
            h = h.raise(stat);
            heroes.put(n, h);
            persist();
            return new HeroWrite("RAISED", h);
        }
    }

    public HeroWrite fall(String name) {
        if (badName(name)) {
            return new HeroWrite("BAD_ACTOR", null);
        }
        synchronized (lock) {
            String n = name.trim();
            Hero h = heroes.getOrDefault(n, Hero.fresh(n)).fall();
            heroes.put(n, h);
            persist();
            return new HeroWrite("FELL", h);
        }
    }

    private void load() {
        if (!Files.exists(file)) {
            return;
        }
        try {
            for (String line : Files.readAllLines(file, StandardCharsets.UTF_8)) {
                String t = line.strip();
                if (t.isEmpty() || t.startsWith("#")) {
                    continue;
                }
                String[] p = t.split("\\s+");
                if (p.length != 6 || badName(p[0])) {
                    throw new IOException("Bad hero row: " + t);
                }
                heroes.put(p[0], new Hero(p[0], Integer.parseInt(p[1]), Integer.parseInt(p[2]), Integer.parseInt(p[3]),
                        Integer.parseInt(p[4]), Integer.parseInt(p[5])));
            }
        } catch (IOException | IllegalArgumentException e) {
            throw new IllegalStateException("Cannot read heroes " + file, e);
        }
    }

    private void persist() {
        List<String> rows = new ArrayList<>();
        rows.add("# Daedalus heroes (ADR-037): name exp attack magic life beaten");
        for (Hero h : heroes.values()) {
            rows.add(h.name() + " " + h.exp() + " " + h.attack() + " " + h.magic() + " " + h.life() + " " + h.beaten());
        }
        try {
            Path tmp = file.resolveSibling(file.getFileName() + ".tmp");
            Files.write(tmp, rows, StandardCharsets.UTF_8);
            Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException e) {
            throw new UncheckedIOException("Cannot persist heroes " + file, e);
        }
    }
}
