// SPDX-License-Identifier: MIT

package com.daedalus.world.retro;

import com.daedalus.engine.Braider;
import com.daedalus.engine.MazeGrid;
import com.daedalus.engine.generators.DungeonGenerator;
import com.daedalus.engine.generators.RecursiveBacktrackerGenerator;
import com.daedalus.model.Direction;
import com.daedalus.world.retro.RetroRealm.Boss;
import com.daedalus.world.retro.RetroRealm.Chest;
import com.daedalus.world.retro.RetroRealm.Door;
import com.daedalus.world.retro.RetroRealm.Link;
import com.daedalus.world.retro.RetroRealm.Loot;
import com.daedalus.world.retro.RetroRealm.Npc;
import com.daedalus.world.retro.RetroRealm.Place;
import com.daedalus.world.retro.RetroRealm.Role;
import com.daedalus.world.retro.RetroRealm.Shop;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.SplittableRandom;
import java.util.function.IntPredicate;

/**
 * Generates a realm behind a portal (ADR-052), whole, from one seed.
 *
 * <ul>
 *   <li><b>The field</b>: a 64x64 island from layered value noise (mountains, hills, forest, swamp, sand, sea), the
 *       portal home beside the spawn, and the places strung along walking distance from it, found breadth-first
 *       like the maze solvers do: the first town a short walk out, the castle further, the second town and the cave
 *       mouth at the far end of the land. Encounter zones follow the walk: rings of rising danger, with the hills,
 *       forests and swamps keeping their own monsters.</li>
 *   <li><b>Two towns and the castle</b>, from templates the seed varies: an inn, an item shop and a smithy behind
 *       counters, a storeroom behind a bronze lock, townsfolk with hints the generator writes from the real map
 *       ("the cave lies far to the east"), the queen, her treasury behind a silver lock and her vault behind the
 *       star lock.</li>
 *   <li><b>The cave</b>, three dark floors from the maze engines: rooms and corridors (the BSP dungeon), then a
 *       braided backtracker maze, then a perfect maze whose farthest dead end holds the star key with the shard
 *       tyrant standing in the only way in.</li>
 *   <li><b>Every chest rolled</b> from the loot tables of its depth; mimics included. The keys the story needs are
 *       placed, not rolled.</li>
 * </ul>
 *
 * <p>Deterministic: the same seed is the same realm, on every machine. {@link RetroProgress} proves each one can be
 * finished.
 */
public final class RetroRealmGenerator {

    public static final int FIELD_SIZE = 64;
    /** Fewer reachable field tiles than this and the island is re-rolled. */
    static final int MIN_LAND = 700;

    private static final String[] FIRST = {"MOSS", "EMBER", "BRIGHT", "STONE", "FERN", "WILLOW", "ASH", "DEW", "HOLLY",
        "AMBER"};
    private static final String[] LAST = {"FORD", "WICK", "DALE", "HOLM", "BURY", "MERE", "GATE", "VALE"};
    private static final int[] HAIRS = {0x7C4C14, 0xF8B800, 0x3C3C3C, 0xD82800, 0xBCBCBC, 0xF87818};
    private static final int[] TOPS = {0x008888, 0xD82800, 0x0058F8, 0x8C34C8, 0x2C8C18, 0xF878C8, 0xA0581C};
    private static final int[] LEGS = {0x0028A0, 0x3C3C3C, 0x603008, 0x7C7C7C};

    private final long seed;
    private final SplittableRandom rng;
    private final List<RetroMap> maps = new ArrayList<>();
    private final List<Link> links = new ArrayList<>();
    private final List<Chest> chests = new ArrayList<>();
    private final List<Door> doors = new ArrayList<>();
    private final List<Npc> npcs = new ArrayList<>();
    private final List<Boss> bosses = new ArrayList<>();
    private final List<String> news = new ArrayList<>();

    private RetroMap field;
    private int[] dist;
    private Place spawn;
    private Place portal;
    private Place town1;
    private Place town2;
    private Place castle;
    private Place cave;
    private String town1Name;
    private String town2Name;

    private RetroRealmGenerator(long seed) {
        this.seed = seed;
        this.rng = new SplittableRandom(seed);
    }

    /** The realm for {@code seed}. */
    public static RetroRealm generate(long seed) {
        return new RetroRealmGenerator(seed).build();
    }

    private RetroRealm build() {
        buildField();
        town1Name = townName();
        do {
            town2Name = townName();
        } while (town2Name.equals(town1Name));
        buildTown("TOWN1", town1Name, town1, 1);
        buildTown("TOWN2", town2Name, town2, 2);
        buildCastle();
        buildCave();
        news.add("A STAR FELL BEYOND " + town2Name + ".");
        news.add("THE ARKS SAIL AT DUSK.");
        news.add(rng.nextBoolean() ? "SHARDBACKS ARE STIRRING IN THE HILLS." : "LUCKY DRIPS WERE SEEN IN THE MEADOW.");
        List<Shop> shops = List.of(
                new Shop("T1ITEMS", List.of(RetroItem.HERB, RetroItem.ANTIDOTE, RetroItem.TORCH, RetroItem.WINGS)),
                new Shop("T1GEAR", List.of(RetroItem.CLUB, RetroItem.COPPER_SWORD, RetroItem.CLOTHES,
                        RetroItem.LEATHER_VEST)),
                new Shop("T2ITEMS", List.of(RetroItem.HERB, RetroItem.TONIC, RetroItem.ANTIDOTE, RetroItem.TORCH,
                        RetroItem.WINGS)),
                new Shop("T2GEAR", List.of(RetroItem.COPPER_SWORD, RetroItem.IRON_AXE, RetroItem.LEATHER_VEST,
                        RetroItem.CHAIN_MAIL)),
                new Shop("KEYS", List.of(RetroItem.BRONZE_KEY, RetroItem.TORCH, RetroItem.WINGS, RetroItem.HERB)));
        return new RetroRealm(seed, "SHARDLANDS", maps, RetroEncounters.zones(), links, chests, doors, npcs, shops,
                bosses, spawn, portal, news);
    }

    // ------------------------------------------------------------------------------------------------ the field

    private void buildField() {
        long salt = seed;
        for (int attempt = 0; ; attempt++) {
            field = new RetroMap("FIELD", "FIELD", FIELD_SIZE, FIELD_SIZE, "FIELD", false, null, RetroTile.WATER);
            paintIsland(salt);
            if (reachableLand() >= MIN_LAND || attempt >= 40) {
                break;
            }
            salt = mix(salt + 0x9E3779B97F4A7C15L);
        }
        maps.add(field);
        int far = 0;
        for (int d : dist) {
            far = Math.max(far, d);
        }
        portal = spawn.step(0, -1);
        field.set(portal.x(), portal.y(), RetroTile.PORTAL);
        List<Place> taken = new ArrayList<>(List.of(spawn, portal));
        town1 = pick(Math.min(8, far / 4), taken, false);
        taken.add(town1);
        castle = pick(Math.min(16, far / 2), taken, false);
        taken.add(castle);
        town2 = pick(Math.max(far * 3 / 4, 18), taken, false);
        taken.add(town2);
        cave = pick(far * 9 / 10, taken, true);
        field.set(town1.x(), town1.y(), RetroTile.TOWN);
        field.set(town2.x(), town2.y(), RetroTile.TOWN);
        field.set(castle.x(), castle.y(), RetroTile.CASTLE);
        field.set(cave.x(), cave.y(), RetroTile.CAVE);
        zoneField();
    }

    private void paintIsland(long salt) {
        for (int y = 0; y < FIELD_SIZE; y++) {
            for (int x = 0; x < FIELD_SIZE; x++) {
                double dx = (x - 32) / 32.0;
                double dy = (y - 32) / 32.0;
                double e = fractal(salt, x * 0.08, y * 0.08) - (dx * dx + dy * dy) * 0.45;
                double v = fractal(salt + 99, x * 0.12, y * 0.12);
                RetroTile t = RetroTile.WATER;
                if (e > 0.62) {
                    t = RetroTile.MOUNTAIN;
                } else if (e > 0.54) {
                    t = RetroTile.HILL;
                } else if (e > 0.30) {
                    t = v > 0.66 && e < 0.40 ? RetroTile.SWAMP : v > 0.58 ? RetroTile.TREE : RetroTile.GRASS;
                } else if (e > 0.26) {
                    t = RetroTile.SAND;
                }
                field.set(x, y, t);
            }
        }
        // Spawn: the grass nearest the middle with grass to its north for the portal.
        int best = Integer.MAX_VALUE;
        spawn = new Place("FIELD", 32, 32);
        for (int y = 1; y < FIELD_SIZE; y++) {
            for (int x = 0; x < FIELD_SIZE; x++) {
                if (field.at(x, y) == RetroTile.GRASS && field.at(x, y - 1).walkable()) {
                    int d = (x - 32) * (x - 32) + (y - 32) * (y - 32);
                    if (d < best) {
                        best = d;
                        spawn = new Place("FIELD", x, y);
                    }
                }
            }
        }
        if (best == Integer.MAX_VALUE) {   // no land at all: make a meadow so the walk below has somewhere to go
            field.set(32, 32, RetroTile.GRASS);
            field.set(32, 31, RetroTile.GRASS);
        }
        dist = walk(field, spawn.x(), spawn.y(), t -> true);
    }

    private int reachableLand() {
        int n = 0;
        for (int d : dist) {
            if (d >= 0) {
                n++;
            }
        }
        return n;
    }

    /** Grass at about {@code want} steps from spawn, at least six tiles from anything taken; near hills if asked. */
    private Place pick(int want, List<Place> taken, boolean nearHills) {
        Place best = null;
        long bestScore = Long.MAX_VALUE;
        for (int i = 0; i < dist.length; i++) {
            int x = i % FIELD_SIZE;
            int y = i / FIELD_SIZE;
            if (dist[i] < 0 || field.at(x, y) != RetroTile.GRASS) {
                continue;
            }
            boolean clear = true;
            for (Place p : taken) {
                if (Math.abs(p.x() - x) + Math.abs(p.y() - y) < 6) {
                    clear = false;
                    break;
                }
            }
            if (!clear) {
                continue;
            }
            long score = Math.abs(dist[i] - want) * 64L + (mix(seed + i) & 63);
            if (nearHills && !besideRock(x, y)) {
                score += 64L * 6;
            }
            if (score < bestScore) {
                bestScore = score;
                best = new Place("FIELD", x, y);
            }
        }
        if (best == null) {   // a tiny island: fall back to any reachable grass not yet used
            for (int i = 0; i < dist.length && best == null; i++) {
                Place p = new Place("FIELD", i % FIELD_SIZE, i / FIELD_SIZE);
                if (dist[i] >= 0 && field.at(p.x(), p.y()) == RetroTile.GRASS && !taken.contains(p)) {
                    best = p;
                }
            }
        }
        if (best == null) {
            throw new IllegalStateException("no room on the island for every place");
        }
        return best;
    }

    private boolean besideRock(int x, int y) {
        for (int dy = -1; dy <= 1; dy++) {
            for (int dx = -1; dx <= 1; dx++) {
                RetroTile t = field.at(x + dx, y + dy);
                if (t == RetroTile.HILL || t == RetroTile.MOUNTAIN) {
                    return true;
                }
            }
        }
        return false;
    }

    private void zoneField() {
        for (int i = 0; i < dist.length; i++) {
            int x = i % FIELD_SIZE;
            int y = i / FIELD_SIZE;
            int d = dist[i];
            RetroTile t = field.at(x, y);
            if (d < 0 || d <= 2 || t == RetroTile.TOWN || t == RetroTile.CASTLE || t == RetroTile.CAVE
                    || t == RetroTile.PORTAL) {
                continue;   // unreachable, a place, or the safe ground beside the portal
            }
            char ring = d < 10 ? RetroEncounters.NEAR : d < 20 ? RetroEncounters.MIDDLE : RetroEncounters.FAR;
            char z = ring;
            if (t == RetroTile.SWAMP) {
                z = RetroEncounters.SWAMP;
            } else if (t == RetroTile.HILL && ring != RetroEncounters.NEAR) {
                z = RetroEncounters.HILLS;
            } else if (t == RetroTile.TREE && ring != RetroEncounters.NEAR) {
                z = RetroEncounters.FOREST;
            }
            field.setZone(x, y, z);
        }
    }

    // ------------------------------------------------------------------------------------------------ the towns

    private void buildTown(String id, String title, Place gate, int tier) {
        RetroMap m = new RetroMap(id, title, 24, 20, "TOWN", false, gate, RetroTile.COBBLE);
        border(m, 0, 0, 23, 19, RetroTile.STONE);
        m.set(12, 19, RetroTile.DOOR);
        // Gardens: grass and trees the seed scatters over the open square.
        for (int y = 9; y <= 17; y++) {
            for (int x = 1; x <= 22; x++) {
                if ((x >= 9 && x <= 14) || (x >= 2 && x <= 8 && y >= 10 && y <= 15) || (x >= 15 && y <= 16)) {
                    continue;   // keep the main street, the storeroom and the smithy clear
                }
                int r = rng.nextInt(10);
                m.set(x, y, r < 2 ? RetroTile.TREE : r < 5 ? RetroTile.GRASS : RetroTile.COBBLE);
            }
        }
        building(m, 2, 2, 8, 7, 5, 7);     // inn
        building(m, 15, 2, 21, 7, 18, 7);  // item shop
        building(m, 15, 10, 21, 15, 18, 15);   // smithy
        // Counters across each shop, the keeper behind.
        for (int x = 3; x <= 7; x++) {
            m.set(x, 4, RetroTile.COUNTER);
        }
        for (int x = 16; x <= 20; x++) {
            m.set(x, 4, RetroTile.COUNTER);
            m.set(x, 12, RetroTile.COUNTER);
        }
        // The storeroom: two chests behind a bronze lock.
        building(m, 2, 10, 8, 15, -1, -1);
        m.set(8, 12, RetroTile.LOCKED);
        doors.add(new Door(new Place(id, 8, 12), 1));
        chest(m, 3, 11, RetroLoot.roll(1, rng));
        chest(m, 7, 14, RetroLoot.roll(1, rng));
        if (tier == 2) {
            chest(m, 3, 14, RetroLoot.rollHonest(2, rng));
        }
        maps.add(m);
        links.add(new Link(gate, new Place(id, 12, 18)));

        npcs.add(npc(id, 5, 3, false, Role.INN, tier == 1 ? 6 : 14, "",
                "INNKEEPER: WELCOME, TRAVELERS."));
        npcs.add(npc(id, 18, 3, false, Role.SHOP, 0, tier == 1 ? "T1ITEMS" : "T2ITEMS",
                "MERCHANT: HERBS AND TORCHES!"));
        npcs.add(npc(id, 18, 11, false, Role.SHOP, 0, tier == 1 ? "T1GEAR" : "T2GEAR",
                "SMITH: STEEL FOR THE ROAD."));
        npcs.add(npc(id, 11, 9, true, Role.NEWS, 0, "", "ELDER: NEWS OF THE DAY!"));
        if (tier == 1) {
            npcs.add(npc(id, 13, 17, false, Role.TALK, 0, "", "GUARD: THE CAVE MOUTH LIES",
                    "FAR TO THE " + compass(gate, cave) + "."));
            npcs.add(npc(id, 10, 14, true, Role.TALK, 0, "", "KID: A GOLD SLIME RAN FROM ME!",
                    "LUCKY DRIPS FLEE. HIT THEM FAST."));
            npcs.add(npc(id, 13, 5, true, Role.TALK, 0, "", "WOMAN: THE STOREROOM WANTS",
                    "A BRONZE KEY. THE CASTLE SELLS THEM.", "THE CASTLE IS TO THE " + compass(gate, castle) + "."));
        } else {
            npcs.add(npc(id, 13, 17, false, Role.TALK, 0, "", "GUARD: THE QUEEN'S VAULT",
                    "OPENS ONLY TO A STAR KEY."));
            npcs.add(npc(id, 10, 14, true, Role.TALK, 0, "", "MINER: THE STAR KEY LIES AT THE",
                    "BOTTOM OF THE CAVE, PAST A", "TYRANT MADE OF SHARDS."));
            npcs.add(npc(id, 13, 5, true, Role.TALK, 0, "", "SAGE: CHESTS IN THE DEEP CAN BITE.",
                    "BRING TORCHES. THE DARK IS LONG."));
        }
    }

    // ----------------------------------------------------------------------------------------------- the castle

    private void buildCastle() {
        String id = "CASTLE";
        RetroMap m = new RetroMap(id, "CASTLE", 20, 18, "CASTLE", false, castle, RetroTile.BRICK);
        border(m, 0, 0, 19, 17, RetroTile.STONE);
        m.set(10, 17, RetroTile.DOOR);
        for (int y = 2; y <= 16; y++) {
            m.set(10, y, RetroTile.CARPET);
        }
        m.set(10, 1, RetroTile.THRONE);
        for (int x : new int[] {3, 7, 13, 17}) {
            for (int y : new int[] {9, 13}) {
                m.set(x, y, RetroTile.STONE);
            }
        }
        // The treasury (silver) on the left, the vault (star) on the right.
        for (int k = 1; k <= 6; k++) {
            m.set(6, k, RetroTile.STONE);
            m.set(k, 6, RetroTile.STONE);
            m.set(13, k, RetroTile.STONE);
            m.set(12 + k, 6, RetroTile.STONE);
        }
        m.set(6, 3, RetroTile.LOCKED);
        doors.add(new Door(new Place(id, 6, 3), 2));
        m.set(13, 3, RetroTile.LOCKED);
        doors.add(new Door(new Place(id, 13, 3), 3));
        chest(m, 2, 2, RetroLoot.roll(2, rng));
        chest(m, 4, 2, RetroLoot.roll(2, rng));
        chest(m, 2, 4, RetroLoot.rollHonest(2, rng));
        chest(m, 16, 2, Loot.item(RetroItem.STAR_BLADE));
        chest(m, 16, 4, Loot.item(RetroItem.METEOR_MAIL));
        maps.add(m);
        links.add(new Link(castle, new Place(id, 10, 16)));
        npcs.add(npc(id, 10, 2, false, Role.QUEEN, 0, "", "QUEEN: WELCOME, TRAVELERS.",
                "OUR WORLD BROKE, BUT WE ENDURE.", "HELP EACH OTHER. THAT IS HOW WE LIVE."));
        npcs.add(npc(id, 7, 11, true, Role.TALK, 0, "", "KNIGHT: A SILVER KEY OPENS",
                "THE TREASURY. IT WAS LOST", "IN THE CAVE'S SECOND FLOOR."));
        npcs.add(npc(id, 15, 11, true, Role.NEWS, 0, "", "SCHOLAR: THE BUBBLE HOLDS",
                "EVERY PIECE OF OUR WORLD."));
        npcs.add(npc(id, 4, 15, false, Role.SHOP, 0, "KEYS", "KEYMAKER: KEYS, TORCHES, WINGS."));
    }

    // -------------------------------------------------------------------------------------------------- the cave

    private void buildCave() {
        MazeGrid g1 = new DungeonGenerator(4).generate(11, 15, seed ^ 0xCA7E1L);
        MazeGrid g2 = new RecursiveBacktrackerGenerator().generate(9, 13, seed ^ 0xCA7E2L);
        Braider.braid(g2, 0.35, seed ^ 0xB4A1DL);
        MazeGrid g3 = new RecursiveBacktrackerGenerator().generate(9, 13, seed ^ 0xCA7E3L);

        RetroMap f1 = caveFloor("CAVE1", "CAVE B1", g1, RetroEncounters.CAVE1);
        RetroMap f2 = caveFloor("CAVE2", "CAVE B2", g2, RetroEncounters.CAVE2);
        RetroMap f3 = caveFloor("CAVE3", "CAVE B3", g3, RetroEncounters.CAVE3);

        int[] up1 = cellTile(g1.start().row(), g1.start().col());
        int[] down1 = farthest(f1, up1);
        int[] up2 = cellTile(g2.start().row(), g2.start().col());
        int[] down2 = farthest(f2, up2);
        int[] up3 = cellTile(g3.start().row(), g3.start().col());
        int[] end3 = farthest(f3, up3);
        stairs(f1, up1, RetroTile.STAIRS_UP);
        stairs(f1, down1, RetroTile.STAIRS_DOWN);
        stairs(f2, up2, RetroTile.STAIRS_UP);
        stairs(f2, down2, RetroTile.STAIRS_DOWN);
        stairs(f3, up3, RetroTile.STAIRS_UP);

        links.add(new Link(cave, new Place("CAVE1", up1[0], up1[1])));
        links.add(new Link(new Place("CAVE1", up1[0], up1[1]), cave));
        links.add(new Link(new Place("CAVE1", down1[0], down1[1]), new Place("CAVE2", up2[0], up2[1])));
        links.add(new Link(new Place("CAVE2", up2[0], up2[1]), new Place("CAVE1", down1[0], down1[1])));
        links.add(new Link(new Place("CAVE2", down2[0], down2[1]), new Place("CAVE3", up3[0], up3[1])));
        links.add(new Link(new Place("CAVE3", up3[0], up3[1]), new Place("CAVE2", down2[0], down2[1])));

        // The bottom: the star key in the farthest dead end, the tyrant in the one passage leading to it.
        int[] gap = soleOpening(f3, end3);
        chest(f3, end3[0], end3[1], Loot.item(RetroItem.STAR_KEY));
        bosses.add(new Boss(new Place("CAVE3", gap[0], gap[1]), RetroMonster.SHARD_TYRANT));
        f3.setZone(gap[0], gap[1], '.');

        scatterChests(f1, up1, 3, 2, null);
        scatterChests(f2, up2, 4, 2, RetroItem.SILVER_KEY);
        scatterChests(f3, up3, 3, 3, null);
        maps.add(f1);
        maps.add(f2);
        maps.add(f3);
    }

    /** Maze cells become a tile map twice the size plus one: cells and the passages between them are floor. */
    private static RetroMap caveFloor(String id, String title, MazeGrid g, char zone) {
        RetroMap m = new RetroMap(id, title, g.cols() * 2 + 1, g.rows() * 2 + 1, "CAVE", true, null, RetroTile.WALL);
        for (int r = 0; r < g.rows(); r++) {
            for (int c = 0; c < g.cols(); c++) {
                boolean east = g.isOpen(r, c, Direction.EAST);
                boolean south = g.isOpen(r, c, Direction.SOUTH);
                boolean any = east || south || g.isOpen(r, c, Direction.WEST) || g.isOpen(r, c, Direction.NORTH);
                if (!any) {
                    continue;   // solid rock the dungeon never carved
                }
                m.set(c * 2 + 1, r * 2 + 1, RetroTile.FLOOR);
                if (east) {
                    m.set(c * 2 + 2, r * 2 + 1, RetroTile.FLOOR);
                }
                if (south) {
                    m.set(c * 2 + 1, r * 2 + 2, RetroTile.FLOOR);
                }
                // Four cells open to each other are a room, not four corridors: fill the pillar between them.
                if (east && south && r + 1 < g.rows() && c + 1 < g.cols() && g.isOpen(r + 1, c, Direction.EAST)
                        && g.isOpen(r, c + 1, Direction.SOUTH)) {
                    m.set(c * 2 + 2, r * 2 + 2, RetroTile.FLOOR);
                }
            }
        }
        for (int y = 0; y < m.height(); y++) {
            for (int x = 0; x < m.width(); x++) {
                if (m.at(x, y) == RetroTile.FLOOR) {
                    m.setZone(x, y, zone);
                }
            }
        }
        return m;
    }

    private static int[] cellTile(int row, int col) {
        return new int[] {col * 2 + 1, row * 2 + 1};
    }

    private static void stairs(RetroMap m, int[] at, RetroTile t) {
        m.set(at[0], at[1], t);
        for (int dy = -1; dy <= 1; dy++) {
            for (int dx = -1; dx <= 1; dx++) {
                m.setZone(at[0] + dx, at[1] + dy, '.');   // no ambush on the stairs
            }
        }
    }

    /** The cell-centre floor tile furthest (by walking) from {@code from}. */
    private static int[] farthest(RetroMap m, int[] from) {
        int[] d = walk(m, from[0], from[1], t -> true);
        int best = -1;
        int[] at = from;
        for (int i = 0; i < d.length; i++) {
            int x = i % m.width();
            int y = i / m.width();
            if (d[i] > best && (x & 1) == 1 && (y & 1) == 1) {
                best = d[i];
                at = new int[] {x, y};
            }
        }
        return at;
    }

    /** The one walkable neighbour of a dead end (in a perfect maze, every way in passes through it). */
    private static int[] soleOpening(RetroMap m, int[] at) {
        int[][] steps = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
        for (int[] s : steps) {
            if (m.at(at[0] + s[0], at[1] + s[1]).walkable()) {
                return new int[] {at[0] + s[0], at[1] + s[1]};
            }
        }
        throw new IllegalStateException("the cave's end has no way in");
    }

    /**
     * Put {@code count} chests on a floor, dead ends first, never closing a passage (each one is checked by walking
     * the floor with it in place). The first holds {@code first} if given; the rest are rolled from {@code tier}.
     */
    private void scatterChests(RetroMap m, int[] from, int count, int tier, RetroItem first) {
        int[] d = walk(m, from[0], from[1], t -> true);
        List<int[]> spots = new ArrayList<>();
        for (int i = 0; i < d.length; i++) {
            int x = i % m.width();
            int y = i / m.width();
            if (d[i] >= 6 && (x & 1) == 1 && (y & 1) == 1 && m.at(x, y) == RetroTile.FLOOR) {
                spots.add(new int[] {x, y, openSides(m, x, y)});
            }
        }
        // Dead ends first, then by a seeded shuffle.
        for (int i = spots.size() - 1; i > 0; i--) {
            int j = rng.nextInt(i + 1);
            int[] t = spots.get(i);
            spots.set(i, spots.get(j));
            spots.set(j, t);
        }
        spots.sort((a, b) -> Integer.compare(a[2], b[2]));
        int placed = 0;
        int reach = countWalkable(walk(m, from[0], from[1], t -> true));
        for (int[] s : spots) {
            if (placed == count) {
                break;
            }
            m.set(s[0], s[1], RetroTile.CHEST);
            if (countWalkable(walk(m, from[0], from[1], t -> true)) != reach - 1 || nearChest(m, s[0], s[1])) {
                m.set(s[0], s[1], RetroTile.FLOOR);   // it would cut the floor in two, or crowd another chest
                continue;
            }
            reach--;
            Loot loot = placed == 0 && first != null ? Loot.item(first) : RetroLoot.roll(tier, rng);
            chests.add(new Chest(new Place(m.id(), s[0], s[1]), loot));
            m.setZone(s[0], s[1], '.');
            placed++;
        }
        if (first != null && placed == 0) {
            throw new IllegalStateException("no room for the " + first.title() + " on " + m.id());
        }
    }

    private static boolean nearChest(RetroMap m, int x, int y) {
        for (int dy = -2; dy <= 2; dy++) {
            for (int dx = -2; dx <= 2; dx++) {
                if ((dx != 0 || dy != 0) && m.at(x + dx, y + dy) == RetroTile.CHEST) {
                    return true;
                }
            }
        }
        return false;
    }

    private static int openSides(RetroMap m, int x, int y) {
        int n = 0;
        if (m.at(x + 1, y).walkable()) {
            n++;
        }
        if (m.at(x - 1, y).walkable()) {
            n++;
        }
        if (m.at(x, y + 1).walkable()) {
            n++;
        }
        if (m.at(x, y - 1).walkable()) {
            n++;
        }
        return n;
    }

    private static int countWalkable(int[] d) {
        int n = 0;
        for (int v : d) {
            if (v >= 0) {
                n++;
            }
        }
        return n;
    }

    // -------------------------------------------------------------------------------------------------- helpers

    /** Breadth-first walking distance from (x, y) over walkable tiles of {@code m}; -1 where it can't reach. */
    static int[] walk(RetroMap m, int x, int y, IntPredicate allow) {
        int w = m.width();
        int[] d = new int[w * m.height()];
        Arrays.fill(d, -1);
        if (!m.inside(x, y)) {
            return d;
        }
        ArrayDeque<Integer> q = new ArrayDeque<>();
        d[y * w + x] = 0;
        q.add(y * w + x);
        int[][] steps = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
        while (!q.isEmpty()) {
            int c = q.poll();
            int cx = c % w;
            int cy = c / w;
            for (int[] s : steps) {
                int nx = cx + s[0];
                int ny = cy + s[1];
                if (!m.inside(nx, ny) || d[ny * w + nx] >= 0 || !m.at(nx, ny).walkable() || !allow.test(ny * w + nx)) {
                    continue;
                }
                d[ny * w + nx] = d[c] + 1;
                q.add(ny * w + nx);
            }
        }
        return d;
    }

    private static void border(RetroMap m, int x0, int y0, int x1, int y1, RetroTile t) {
        for (int x = x0; x <= x1; x++) {
            m.set(x, y0, t);
            m.set(x, y1, t);
        }
        for (int y = y0; y <= y1; y++) {
            m.set(x0, y, t);
            m.set(x1, y, t);
        }
    }

    /** A stone building with a brick floor and a door in its south wall at (doorX, doorY), or none if negative. */
    private static void building(RetroMap m, int x0, int y0, int x1, int y1, int doorX, int doorY) {
        for (int y = y0; y <= y1; y++) {
            for (int x = x0; x <= x1; x++) {
                m.set(x, y, RetroTile.BRICK);
            }
        }
        border(m, x0, y0, x1, y1, RetroTile.STONE);
        if (doorX >= 0) {
            m.set(doorX, doorY, RetroTile.DOOR);
        }
    }

    private void chest(RetroMap m, int x, int y, Loot loot) {
        m.set(x, y, RetroTile.CHEST);
        chests.add(new Chest(new Place(m.id(), x, y), loot));
    }

    private Npc npc(String map, int x, int y, boolean wanders, Role role, int price, String shop, String... lines) {
        List<Integer> look = List.of(HAIRS[rng.nextInt(HAIRS.length)], TOPS[rng.nextInt(TOPS.length)],
                LEGS[rng.nextInt(LEGS.length)], role == Role.QUEEN ? 0xF8B800 : 0,
                role == Role.QUEEN ? 0xD82800 : 0);
        return new Npc(new Place(map, x, y), wanders, look, role, price, shop, List.of(lines));
    }

    private String townName() {
        return FIRST[rng.nextInt(FIRST.length)] + LAST[rng.nextInt(LAST.length)];
    }

    /** Which way {@code to} lies from {@code from}, in eight words. */
    static String compass(Place from, Place to) {
        int dx = to.x() - from.x();
        int dy = to.y() - from.y();
        String ns = Math.abs(dy) * 2 > Math.abs(dx) ? (dy < 0 ? "NORTH" : "SOUTH") : "";
        String ew = Math.abs(dx) * 2 > Math.abs(dy) ? (dx < 0 ? "WEST" : "EAST") : "";
        String s = ns + ew;
        return s.isEmpty() ? "NEAR" : s;
    }

    static long mix(long z) {
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        return z ^ (z >>> 31);
    }

    /** Smooth value noise in [0, 1). */
    static double noise(long s, double x, double y) {
        int x0 = (int) Math.floor(x);
        int y0 = (int) Math.floor(y);
        double fx = smooth(x - x0);
        double fy = smooth(y - y0);
        double a = lattice(s, x0, y0);
        double b = lattice(s, x0 + 1, y0);
        double c = lattice(s, x0, y0 + 1);
        double d = lattice(s, x0 + 1, y0 + 1);
        double top = a + (b - a) * fx;
        double bottom = c + (d - c) * fx;
        return top + (bottom - top) * fy;
    }

    private static double lattice(long s, int x, int y) {
        return (mix(s ^ (x * 0x9E3779B97F4A7C15L) ^ (y * 0xC2B2AE3D27D4EB4FL)) >>> 11) * 0x1.0p-53;
    }

    private static double smooth(double t) {
        return t * t * (3 - 2 * t);
    }

    static double fractal(long s, double x, double y) {
        return noise(s, x, y) * 0.6 + noise(s + 7, x * 2, y * 2) * 0.3 + noise(s + 13, x * 4, y * 4) * 0.1;
    }
}
