// SPDX-License-Identifier: MIT

package com.daedalus.world.retro;

import com.daedalus.world.retro.RetroRealm.Boss;
import com.daedalus.world.retro.RetroRealm.Chest;
import com.daedalus.world.retro.RetroRealm.Door;
import com.daedalus.world.retro.RetroRealm.Link;
import com.daedalus.world.retro.RetroRealm.Loot;
import com.daedalus.world.retro.RetroRealm.Npc;
import com.daedalus.world.retro.RetroRealm.Place;
import com.daedalus.world.retro.RetroRealm.Shop;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Proves a realm can be finished (ADR-052): walks it the way a party would, from the spawn, through every gate,
 * stair and cave mouth, opening chests it can reach and locks it has keys for, buying bronze keys once it has found
 * a shop that sells them, beating guardians in its way, and walking again, until nothing new opens.
 *
 * <p>A realm passes when every chest, every lock, every guardian and every townsperson was reached. A key is used
 * up by the lock it opens, as in the core; bronze keys can always be bought more of, silver and star keys cannot.
 * Also checks that the realm's lines agree with its maps: a chest line on a chest tile, a lock line on a lock tile,
 * every link landing on something walkable, a shop for every shopkeeper and a zone for every zone character.
 */
public final class RetroProgress {

    /** What the walk found. {@code problems} is empty for a realm that can be finished. */
    public record Report(int chests, int chestsReached, int doors, int doorsOpened, int bosses, int bossesBeaten,
                         int npcs, int npcsReached, int tilesReached, List<String> problems) {
        public Report {
            problems = List.copyOf(problems);
        }

        public boolean finishable() {
            return problems.isEmpty();
        }
    }

    private final RetroRealm realm;
    private final Map<Place, Place> links;
    private final Map<Place, Chest> chestAt = new HashMap<>();
    private final Map<Place, Door> doorAt = new HashMap<>();
    private final Map<Place, Boss> bossAt = new HashMap<>();
    private final Set<Place> reached = new HashSet<>();
    private final Set<Place> looted = new HashSet<>();
    private final Set<Place> opened = new HashSet<>();
    private final Set<Place> beaten = new HashSet<>();
    private final List<String> problems = new ArrayList<>();
    private int silver;
    private int star;
    private int bronze;
    private boolean bronzeForSale;

    private RetroProgress(RetroRealm realm) {
        this.realm = realm;
        this.links = realm.linkMap();
        for (Chest c : realm.chests()) {
            chestAt.put(c.at(), c);
        }
        for (Door d : realm.doors()) {
            doorAt.put(d.at(), d);
        }
        for (Boss b : realm.bosses()) {
            bossAt.put(b.at(), b);
        }
    }

    public static Report check(RetroRealm realm) {
        return new RetroProgress(realm).run();
    }

    private Report run() {
        consistency();
        boolean changed = true;
        while (changed) {
            flood();
            changed = loot() | unlock();
        }
        int npcsReached = 0;
        for (Npc n : realm.npcs()) {
            if (canTalk(n)) {
                npcsReached++;
            } else {
                problems.add("nobody can reach " + n.lines().get(0) + " at " + n.at());
            }
        }
        for (Chest c : realm.chests()) {
            if (!looted.contains(c.at())) {
                problems.add("chest at " + c.at() + " can't be reached");
            }
        }
        for (Door d : realm.doors()) {
            if (!opened.contains(d.at())) {
                problems.add("lock (tier " + d.tier() + ") at " + d.at() + " can't be opened");
            }
        }
        for (Boss b : realm.bosses()) {
            if (!beaten.contains(b.at())) {
                problems.add(b.monster().title() + " at " + b.at() + " can't be reached");
            }
        }
        return new Report(realm.chests().size(), looted.size(), realm.doors().size(), opened.size(),
                realm.bosses().size(), beaten.size(), realm.npcs().size(), npcsReached, reached.size(), problems);
    }

    /** The realm's lines must agree with its maps. */
    private void consistency() {
        for (Chest c : realm.chests()) {
            if (tile(c.at()) != RetroTile.CHEST) {
                problems.add("chest line at " + c.at() + " is on " + tile(c.at()));
            }
        }
        for (Door d : realm.doors()) {
            if (tile(d.at()) != RetroTile.LOCKED) {
                problems.add("lock line at " + d.at() + " is on " + tile(d.at()));
            }
            if (d.tier() < 1 || d.tier() > 3) {
                problems.add("lock at " + d.at() + " has tier " + d.tier());
            }
        }
        for (Link l : realm.links()) {
            if (!tile(l.from()).walkable() || !tile(l.to()).walkable()) {
                problems.add("link " + l.from() + " -> " + l.to() + " touches something solid");
            }
        }
        for (Boss b : realm.bosses()) {
            if (!tile(b.at()).walkable()) {
                problems.add("guardian at " + b.at() + " stands in rock");
            }
        }
        for (Npc n : realm.npcs()) {
            if (n.role() == RetroRealm.Role.SHOP && realm.shop(n.shop()).isEmpty()) {
                problems.add("no shop " + n.shop());
            }
            if (!tile(n.at()).walkable()) {
                problems.add(n.lines().get(0) + " stands in a wall at " + n.at());
            }
        }
        for (RetroMap m : realm.maps()) {
            for (int y = 0; y < m.height(); y++) {
                for (int x = 0; x < m.width(); x++) {
                    char z = m.zoneAt(x, y);
                    if (z != '.' && realm.zone(z).isEmpty()) {
                        problems.add("no zone '" + z + "' for " + m.id());
                        return;
                    }
                }
            }
        }
    }

    private RetroTile tile(Place p) {
        return realm.map(p.map()).map(m -> m.at(p.x(), p.y())).orElse(RetroTile.WALL);
    }

    private boolean passable(Place p) {
        RetroMap m = realm.map(p.map()).orElse(null);
        if (m == null || !m.inside(p.x(), p.y())) {
            return false;
        }
        RetroTile t = m.at(p.x(), p.y());
        return t.walkable() || (t == RetroTile.LOCKED && opened.contains(p));
    }

    /** Walk everywhere the party can go right now. */
    private void flood() {
        ArrayDeque<Place> q = new ArrayDeque<>();
        if (reached.isEmpty()) {
            reached.add(realm.spawn());
            q.add(realm.spawn());
        } else {
            q.addAll(reached);
        }
        int[][] steps = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
        while (!q.isEmpty()) {
            Place p = q.poll();
            if (bossAt.containsKey(p)) {
                beaten.add(p);   // walking into a guardian means fighting it; the walk assumes the party wins
            }
            Place to = links.get(p);
            if (to != null && reached.add(to)) {
                q.add(to);
            }
            RetroMap m = realm.mapOrThrow(p.map());
            for (int[] s : steps) {
                Place n = p.step(s[0], s[1]);
                if (!m.inside(n.x(), n.y())) {
                    if (m.exit() != null && reached.add(m.exit())) {
                        q.add(m.exit());
                    }
                    continue;
                }
                if (passable(n) && reached.add(n)) {
                    q.add(n);
                }
            }
        }
        for (Npc n : realm.npcs()) {
            if (n.role() == RetroRealm.Role.SHOP && canTalk(n)) {
                Shop s = realm.shop(n.shop()).orElse(null);
                if (s != null && s.stock().contains(RetroItem.BRONZE_KEY)) {
                    bronzeForSale = true;
                }
            }
        }
    }

    /** Open every chest beside the walk. */
    private boolean loot() {
        boolean any = false;
        for (Chest c : realm.chests()) {
            if (looted.contains(c.at()) || !besideReached(c.at())) {
                continue;
            }
            looted.add(c.at());
            any = true;
            Loot l = c.loot();
            if (l.kind() == Loot.Kind.ITEM) {
                switch (l.item()) {
                    case BRONZE_KEY -> bronze++;
                    case SILVER_KEY -> silver++;
                    case STAR_KEY -> star++;
                    default -> {
                    }
                }
            }
        }
        return any;
    }

    /** Open one lock beside the walk with a key in hand (or a bronze key bought); true if any opened. */
    private boolean unlock() {
        for (Door d : realm.doors()) {
            if (opened.contains(d.at()) || !besideReached(d.at())) {
                continue;
            }
            boolean ok = switch (d.tier()) {
                case 1 -> bronzeForSale || bronze-- > 0;
                case 2 -> silver-- > 0;
                case 3 -> star-- > 0;
                default -> false;
            };
            bronze = Math.max(0, bronze);
            silver = Math.max(0, silver);
            star = Math.max(0, star);
            if (ok) {
                opened.add(d.at());
                return true;
            }
        }
        return false;
    }

    private boolean besideReached(Place p) {
        return reached.contains(p.step(1, 0)) || reached.contains(p.step(-1, 0))
                || reached.contains(p.step(0, 1)) || reached.contains(p.step(0, -1));
    }

    /** Standing beside someone, or across a counter from them. */
    private boolean canTalk(Npc n) {
        Place p = n.at();
        if (besideReached(p) || reached.contains(p)) {
            return true;
        }
        int[][] steps = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
        for (int[] s : steps) {
            Place across = p.step(s[0], s[1]);
            if (tile(across) == RetroTile.COUNTER && reached.contains(across.step(s[0], s[1]))) {
                return true;
            }
        }
        return false;
    }
}
