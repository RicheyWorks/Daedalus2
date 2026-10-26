// SPDX-License-Identifier: MIT

package com.daedalus.world.retro;

import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;

/**
 * A whole 8-bit realm behind a portal (ADR-052), as the Java engines generate it: the maps, where every stair and
 * door leads, what is in every chest, which key opens which lock, who lives where and what they sell, which
 * monsters roam each zone and how often, and the guardian at the bottom of the cave.
 *
 * <p>The C++ core plays it; {@link RetroCodec} carries it there as text; {@link RetroProgress} proves it can be
 * finished.
 */
public record RetroRealm(long seed, String name, List<RetroMap> maps, List<Zone> zones, List<Link> links,
                         List<Chest> chests, List<Door> doors, List<Npc> npcs, List<Shop> shops, List<Boss> bosses,
                         Place spawn, Place portal, List<String> news, List<Land> lands) {

    public RetroRealm(long seed, String name, List<RetroMap> maps, List<Zone> zones, List<Link> links,
                      List<Chest> chests, List<Door> doors, List<Npc> npcs, List<Shop> shops, List<Boss> bosses,
                      Place spawn, Place portal, List<String> news) {
        this(seed, name, maps, zones, links, chests, doors, npcs, shops, bosses, spawn, portal, news, List.of());
    }

    public RetroRealm {
        maps = List.copyOf(maps);
        zones = List.copyOf(zones);
        links = List.copyOf(links);
        chests = List.copyOf(chests);
        doors = List.copyOf(doors);
        npcs = List.copyOf(npcs);
        shops = List.copyOf(shops);
        bosses = List.copyOf(bosses);
        news = List.copyOf(news);
        lands = List.copyOf(lands);
        java.util.Set<Integer> numbers = new java.util.HashSet<>();
        for (Land land : lands) {
            if (!numbers.add(land.number())) throw new IllegalArgumentException("duplicate land number");
            RetroMap map = maps.stream().filter(m -> m.id().equals(land.map())).findFirst()
                    .orElseThrow(() -> new IllegalArgumentException("land names unknown map"));
            if ((long) land.x() + land.width() > map.width() || (long) land.y() + land.height() > map.height()) {
                throw new IllegalArgumentException("land outside map");
            }
        }
        Objects.requireNonNull(spawn);
        Objects.requireNonNull(portal);
    }

    /** A tile of one map. */
    public record Land(int number, String map, int x, int y, int width, int height, String owner) {
        public Land {
            if (number < 0 || number >= 10000 || x < 0 || y < 0 || width <= 0 || height <= 0
                    || !map.matches("[A-Za-z0-9_-]{1,48}")
                    || (!owner.isEmpty() && !owner.matches("[A-Za-z0-9_-]{1,48}"))) {
                throw new IllegalArgumentException("invalid land record");
            }
        }
    }

    public RetroRealm withLands(List<Land> configured) {
        return new RetroRealm(seed, name, maps, zones, links, chests, doors, npcs, shops, bosses,
                spawn, portal, news, configured);
    }

    public record Place(String map, int x, int y) {
        public Place step(int dx, int dy) {
            return new Place(map, x + dx, y + dy);
        }
    }

    /** Stepping onto {@code from} puts the party on {@code to}: a town gate, a cave mouth, a stair. */
    public record Link(Place from, Place to) {
    }

    /** What a chest holds: gold, an item, or a monster pretending to be a chest. */
    public record Loot(Kind kind, int gold, RetroItem item, RetroMonster mimic) {

        public enum Kind { GOLD, ITEM, MIMIC }

        public static Loot gold(int amount) {
            return new Loot(Kind.GOLD, amount, null, null);
        }

        public static Loot item(RetroItem item) {
            return new Loot(Kind.ITEM, 0, Objects.requireNonNull(item), null);
        }

        public static Loot mimic(RetroMonster monster) {
            return new Loot(Kind.MIMIC, 0, null, Objects.requireNonNull(monster));
        }
    }

    public record Chest(Place at, Loot loot) {
    }

    /** A locked door: a key of {@code tier} (1 bronze, 2 silver, 3 star) opens it and is used up. */
    public record Door(Place at, int tier) {
    }

    /** What a townsperson does when spoken to. */
    public enum Role {
        /** Says their lines. */
        TALK,
        /** Says their lines, then the news of the day. */
        NEWS,
        /** Offers a night's rest for {@code price} gold: full health and magic, poison cured. */
        INN,
        /** Runs the shop {@code shop}: buys and sells. */
        SHOP,
        /** The queen: her blessing heals the party and remembers the visit. */
        QUEEN
    }

    /**
     * Someone who lives in a town or the castle.
     *
     * @param look   five colours, 0xRRGGBB: hair, top, legs, hat (0 none), cape (0 none)
     * @param price  an innkeeper's price
     * @param shop   a shopkeeper's shop id
     */
    public record Npc(Place at, boolean wanders, List<Integer> look, Role role, int price, String shop,
                      List<String> lines) {
        public Npc {
            look = List.copyOf(look);
            lines = List.copyOf(lines);
            if (look.size() != 5) {
                throw new IllegalArgumentException("a look is five colours");
            }
        }
    }

    public record Shop(String id, List<RetroItem> stock) {
        public Shop {
            stock = List.copyOf(stock);
        }
    }

    /** A guardian standing on {@code at}: bump into it and the fight begins; beaten, it is gone for good. */
    public record Boss(Place at, RetroMonster monster) {
    }

    /** Which monsters roam where a map's tiles carry zone {@code id}, and how often they attack. */
    public record Zone(char id, int rate, List<Entry> entries) {
        public Zone {
            entries = List.copyOf(entries);
            if (entries.isEmpty()) {
                throw new IllegalArgumentException("zone " + id + " has no monsters");
            }
            if (rate < 2) {
                throw new IllegalArgumentException("zone " + id + " attacks too often");
            }
        }

        public int totalWeight() {
            return entries.stream().mapToInt(Entry::weight).sum();
        }
    }

    /** One line of a zone's table: the monster, its weight, and how many come together. */
    public record Entry(RetroMonster monster, int weight, int min, int max) {
        public Entry {
            if (weight < 1 || min < 1 || max < min || max > 3) {
                throw new IllegalArgumentException("bad zone entry for " + monster);
            }
        }
    }

    public Optional<RetroMap> map(String id) {
        return maps.stream().filter(m -> m.id().equals(id)).findFirst();
    }

    public RetroMap mapOrThrow(String id) {
        return map(id).orElseThrow(() -> new IllegalArgumentException("no map " + id));
    }

    public Optional<Zone> zone(char id) {
        return zones.stream().filter(z -> z.id() == id).findFirst();
    }

    public Optional<Shop> shop(String id) {
        return shops.stream().filter(s -> s.id().equals(id)).findFirst();
    }

    /** Where each link's tile leads. */
    public Map<Place, Place> linkMap() {
        java.util.Map<Place, Place> m = new java.util.HashMap<>();
        for (Link l : links) {
            m.put(l.from(), l.to());
        }
        return m;
    }
}
