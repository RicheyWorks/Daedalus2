// SPDX-License-Identifier: MIT

package com.daedalus.world.retro;

import com.daedalus.world.retro.RetroRealm.Boss;
import com.daedalus.world.retro.RetroRealm.Chest;
import com.daedalus.world.retro.RetroRealm.Door;
import com.daedalus.world.retro.RetroRealm.Entry;
import com.daedalus.world.retro.RetroRealm.Link;
import com.daedalus.world.retro.RetroRealm.Loot;
import com.daedalus.world.retro.RetroRealm.Npc;
import com.daedalus.world.retro.RetroRealm.Place;
import com.daedalus.world.retro.RetroRealm.Role;
import com.daedalus.world.retro.RetroRealm.Shop;
import com.daedalus.world.retro.RetroRealm.Zone;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * The realm spec (ADR-052): a realm as plain text, one fact per line, so a C++ core with no JSON library can read it
 * with a line splitter, and a person can read it too.
 *
 * <pre>
 * DRR 1
 * seed 42
 * name SHARDLANDS
 * item HERB USE 10 25 HERB                                      id kind price power title
 * monster BLIGHT_SLIME 0 58d840 188c10 6 5 2 3 2 2 COMMON POISON HERB 8 BLIGHT SLIME
 *                                       id shape body accent hp atk def agi exp gold rarity traits(,|-) drop 1-in title
 * map FIELD 64 64 FIELD 0 - 0 0 FIELD   id w h music dark exitMap exitX exitY title
 * row ~~~~....                          h rows of tile characters
 * zrow ....0011                         h rows of zone characters
 * end
 * zone 0 22 BLIGHT_SLIME:50:1:3 DUST_WISP:30:1:2
 * link FIELD 10 12 TOWN1 12 18
 * chest TOWN1 3 11 GOLD 25              GOLD amount | ITEM id | MIMIC monster
 * door TOWN1 8 12 1
 * npc TOWN1 5 3 0 7c4c14 008888 0028a0 0 0 INN 6 - INNKEEPER: WELCOME./SECOND LINE
 *                                       map x y wanders hair top legs hat cape role price shop text('/' between lines)
 * shop T1ITEMS HERB ANTIDOTE TORCH WINGS
 * boss CAVE3 13 9 SHARD_TYRANT
 * spawn FIELD 30 31
 * portal FIELD 30 30
 * news THE ARKS SAIL AT DUSK.
 * </pre>
 */
public final class RetroCodec {

    public static final String MAGIC = "DRR 1";

    private RetroCodec() {
    }

    public static String write(RetroRealm r) {
        StringBuilder sb = new StringBuilder(64 * 1024);
        sb.append(MAGIC).append('\n');
        sb.append("seed ").append(r.seed()).append('\n');
        sb.append("name ").append(r.name()).append('\n');
        for (RetroItem i : RetroItem.values()) {
            sb.append("item ").append(i.name()).append(' ').append(i.kind()).append(' ').append(i.price()).append(' ')
                    .append(i.power()).append(' ').append(i.title()).append('\n');
        }
        for (RetroMonster m : RetroMonster.values()) {
            List<String> traits = new ArrayList<>();
            for (RetroMonster.Trait t : m.traits()) {
                traits.add(t.name());
            }
            sb.append("monster ").append(m.name()).append(' ').append(m.shape()).append(' ').append(hex(m.body()))
                    .append(' ').append(hex(m.accent())).append(' ').append(m.hp()).append(' ').append(m.atk())
                    .append(' ').append(m.def()).append(' ').append(m.agi()).append(' ').append(m.exp()).append(' ')
                    .append(m.gold()).append(' ').append(m.rarity()).append(' ')
                    .append(traits.isEmpty() ? "-" : String.join(",", traits)).append(' ')
                    .append(m.drop() == null ? "-" : m.drop().name()).append(' ').append(m.dropOneIn()).append(' ')
                    .append(m.title()).append('\n');
        }
        for (RetroMap m : r.maps()) {
            Place e = m.exit();
            sb.append("map ").append(m.id()).append(' ').append(m.width()).append(' ').append(m.height()).append(' ')
                    .append(m.music()).append(' ').append(m.dark() ? 1 : 0).append(' ')
                    .append(e == null ? "- 0 0" : e.map() + " " + e.x() + " " + e.y()).append(' ').append(m.title())
                    .append('\n');
            for (int y = 0; y < m.height(); y++) {
                sb.append("row ").append(m.row(y)).append('\n');
            }
            if (m.hasEncounters()) {
                for (int y = 0; y < m.height(); y++) {
                    sb.append("zrow ").append(m.zoneRow(y)).append('\n');
                }
            }
            sb.append("end\n");
        }
        for (Zone z : r.zones()) {
            sb.append("zone ").append(z.id()).append(' ').append(z.rate());
            for (Entry e : z.entries()) {
                sb.append(' ').append(e.monster().name()).append(':').append(e.weight()).append(':').append(e.min())
                        .append(':').append(e.max());
            }
            sb.append('\n');
        }
        for (Link l : r.links()) {
            sb.append("link ").append(place(l.from())).append(' ').append(place(l.to())).append('\n');
        }
        for (Chest c : r.chests()) {
            Loot l = c.loot();
            sb.append("chest ").append(place(c.at())).append(' ').append(l.kind()).append(' ').append(switch (l.kind()) {
                case GOLD -> String.valueOf(l.gold());
                case ITEM -> l.item().name();
                case MIMIC -> l.mimic().name();
            }).append('\n');
        }
        for (Door d : r.doors()) {
            sb.append("door ").append(place(d.at())).append(' ').append(d.tier()).append('\n');
        }
        for (Npc n : r.npcs()) {
            sb.append("npc ").append(place(n.at())).append(' ').append(n.wanders() ? 1 : 0);
            for (int c : n.look()) {
                sb.append(' ').append(hex(c));
            }
            sb.append(' ').append(n.role()).append(' ').append(n.price()).append(' ')
                    .append(n.shop().isEmpty() ? "-" : n.shop()).append(' ').append(String.join("/", n.lines()))
                    .append('\n');
        }
        for (Shop s : r.shops()) {
            sb.append("shop ").append(s.id());
            for (RetroItem i : s.stock()) {
                sb.append(' ').append(i.name());
            }
            sb.append('\n');
        }
        for (Boss b : r.bosses()) {
            sb.append("boss ").append(place(b.at())).append(' ').append(b.monster().name()).append('\n');
        }
        sb.append("spawn ").append(place(r.spawn())).append('\n');
        sb.append("portal ").append(place(r.portal())).append('\n');
        for (String n : r.news()) {
            sb.append("news ").append(n).append('\n');
        }
        return sb.toString();
    }

    /** Read a spec back. Item and monster lines are checked against this build's tables, not trusted. */
    public static RetroRealm read(String text) {
        String[] lines = text.split("\n", -1);
        if (lines.length == 0 || !MAGIC.equals(lines[0].strip())) {
            throw new IllegalArgumentException("not a realm spec (want '" + MAGIC + "' first)");
        }
        long seed = 0;
        String name = "";
        List<RetroMap> maps = new ArrayList<>();
        List<Zone> zones = new ArrayList<>();
        List<Link> links = new ArrayList<>();
        List<Chest> chests = new ArrayList<>();
        List<Door> doors = new ArrayList<>();
        List<Npc> npcs = new ArrayList<>();
        List<Shop> shops = new ArrayList<>();
        List<Boss> bosses = new ArrayList<>();
        List<String> news = new ArrayList<>();
        Place spawn = null;
        Place portal = null;
        for (int i = 1; i < lines.length; i++) {
            String line = lines[i];
            if (line.isBlank()) {
                continue;
            }
            String[] f = line.split(" ");
            switch (f[0]) {
                case "seed" -> seed = Long.parseLong(f[1]);
                case "name" -> name = rest(line, 1);
                case "item" -> checkItem(f, line);
                case "monster" -> checkMonster(f);
                case "map" -> i = readMap(lines, i, f, maps);
                case "zone" -> {
                    List<Entry> entries = new ArrayList<>();
                    for (int k = 3; k < f.length; k++) {
                        String[] e = f[k].split(":");
                        entries.add(new Entry(RetroMonster.valueOf(e[0]), Integer.parseInt(e[1]),
                                Integer.parseInt(e[2]), Integer.parseInt(e[3])));
                    }
                    zones.add(new Zone(f[1].charAt(0), Integer.parseInt(f[2]), entries));
                }
                case "link" -> links.add(new Link(place(f, 1), place(f, 4)));
                case "chest" -> chests.add(new Chest(place(f, 1), switch (Loot.Kind.valueOf(f[4])) {
                    case GOLD -> Loot.gold(Integer.parseInt(f[5]));
                    case ITEM -> Loot.item(RetroItem.valueOf(f[5]));
                    case MIMIC -> Loot.mimic(RetroMonster.valueOf(f[5]));
                }));
                case "door" -> doors.add(new Door(place(f, 1), Integer.parseInt(f[4])));
                case "npc" -> {
                    List<Integer> look = new ArrayList<>();
                    for (int k = 5; k < 10; k++) {
                        look.add(Integer.parseInt(f[k], 16));
                    }
                    npcs.add(new Npc(place(f, 1), "1".equals(f[4]), look, Role.valueOf(f[10]),
                            Integer.parseInt(f[11]), "-".equals(f[12]) ? "" : f[12],
                            Arrays.asList(rest(line, 13).split("/"))));
                }
                case "shop" -> {
                    List<RetroItem> stock = new ArrayList<>();
                    for (int k = 2; k < f.length; k++) {
                        stock.add(RetroItem.valueOf(f[k]));
                    }
                    shops.add(new Shop(f[1], stock));
                }
                case "boss" -> bosses.add(new Boss(place(f, 1), RetroMonster.valueOf(f[4])));
                case "spawn" -> spawn = place(f, 1);
                case "portal" -> portal = place(f, 1);
                case "news" -> news.add(rest(line, 1));
                default -> throw new IllegalArgumentException("line " + (i + 1) + ": unknown '" + f[0] + "'");
            }
        }
        if (spawn == null || portal == null) {
            throw new IllegalArgumentException("a realm needs a spawn and a portal");
        }
        return new RetroRealm(seed, name, maps, zones, links, chests, doors, npcs, shops, bosses, spawn, portal, news);
    }

    private static int readMap(String[] lines, int at, String[] f, List<RetroMap> maps) {
        int w = Integer.parseInt(f[2]);
        int h = Integer.parseInt(f[3]);
        Place exit = "-".equals(f[6]) ? null : new Place(f[6], Integer.parseInt(f[7]), Integer.parseInt(f[8]));
        RetroMap m = new RetroMap(f[1], rest(lines[at], 9), w, h, f[4], "1".equals(f[5]), exit, RetroTile.WATER);
        int y = 0;
        int zy = 0;
        int i = at + 1;
        for (; i < lines.length && !"end".equals(lines[i].strip()); i++) {
            String l = lines[i];
            if (l.startsWith("row ")) {
                String row = l.substring(4);
                if (row.length() != w || y >= h) {
                    throw new IllegalArgumentException("map " + m.id() + " row " + y + " is the wrong size");
                }
                for (int x = 0; x < w; x++) {
                    m.set(x, y, RetroTile.of(row.charAt(x)));
                }
                y++;
            } else if (l.startsWith("zrow ")) {
                String row = l.substring(5);
                for (int x = 0; x < Math.min(w, row.length()); x++) {
                    m.setZone(x, zy, row.charAt(x));
                }
                zy++;
            } else {
                throw new IllegalArgumentException("map " + m.id() + ": unexpected '" + l + "'");
            }
        }
        if (y != h) {
            throw new IllegalArgumentException("map " + m.id() + " has " + y + " rows, wants " + h);
        }
        maps.add(m);
        return i;
    }

    private static void checkItem(String[] f, String line) {
        RetroItem i = RetroItem.valueOf(f[1]);
        if (i.kind() != RetroItem.Kind.valueOf(f[2]) || i.price() != Integer.parseInt(f[3])
                || i.power() != Integer.parseInt(f[4]) || !i.title().equals(rest(line, 5))) {
            throw new IllegalArgumentException("item " + f[1] + " differs from this build's");
        }
    }

    private static void checkMonster(String[] f) {
        RetroMonster m = RetroMonster.valueOf(f[1]);
        if (m.hp() != Integer.parseInt(f[5]) || m.atk() != Integer.parseInt(f[6]) || m.exp() != Integer.parseInt(f[9])) {
            throw new IllegalArgumentException("monster " + f[1] + " differs from this build's");
        }
    }

    private static Place place(String[] f, int at) {
        return new Place(f[at], Integer.parseInt(f[at + 1]), Integer.parseInt(f[at + 2]));
    }

    private static String place(Place p) {
        return p.map() + " " + p.x() + " " + p.y();
    }

    private static String hex(int c) {
        return Integer.toHexString(c);
    }

    /** Everything after the first {@code fields} space-separated fields. */
    private static String rest(String line, int fields) {
        int at = 0;
        for (int k = 0; k < fields; k++) {
            at = line.indexOf(' ', at);
            if (at < 0) {
                return "";
            }
            at++;
        }
        return line.substring(at);
    }
}
