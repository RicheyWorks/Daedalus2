// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.fires;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.fires.SignalFires.Link;
import com.daedalus.world.brew.fires.SignalFires.Outcome;
import com.daedalus.world.brew.letters.Destination;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;

class SignalFiresTest {
    static SignalFires map(long seed) {
        return SignalFires.seaMap(Destination.island(), seed);
    }

    @Test
    void seaMapPutsFarIslandsAtTheirArkDistance() {
        SignalFires s = map(3);
        assertEquals(1 + Destination.island().size() + SignalFires.RELAYS, s.isles().size());
        Isle home = s.isles().get(0);
        assertEquals(SignalFires.HOME, home.id());
        for (Destination d : Destination.island()) {
            Isle i = s.isles().stream().filter(x -> x.id().equals(d.id())).findFirst().orElseThrow();
            assertFalse(i.relay());
            assertEquals(d.route().legs().size() * SignalFires.MILES_PER_LEG, Math.hypot(i.x(), i.y()), 0.2);
        }
        assertEquals(SignalFires.RELAYS, s.isles().stream().filter(Isle::relay).count());
        assertEquals(s.isles(), map(3).isles());
        assertEquals(5, new Isle("a", 0, 0, false).woodTo(new Isle("b", 3, 4, false)));
        assertEquals(2, new Isle("a", 0, 0, false).woodTo(new Isle("b", 1, 1, false)));
        assertThrows(IllegalArgumentException.class, () -> new SignalFires(List.of(new Isle("a", 0, 0, false))));
    }

    @Test
    void aStackInTheMiddleSavesWood() {
        double h = 10 * Math.sqrt(3) / 2;
        Isle a = new Isle("a", 0, 0, false);
        Isle b = new Isle("b", 10, 0, false);
        Isle c = new Isle("c", 5, h, false);
        assertEquals(20, new SignalFires(List.of(a, b, c)).bestWood(), "two sides of the triangle");
        SignalFires s = new SignalFires(List.of(a, b, c, new Isle("stack", 5, h / 3, true)));
        assertEquals(18, s.bestWood(), "three spokes of 5.77, rounded up to 6");
        assertEquals(3, s.best().size());
        assertTrue(s.best().stream().allMatch(l -> l.a().equals("stack") || l.b().equals("stack")));
        SignalFires far = new SignalFires(List.of(a, b, c, new Isle("stack", 50, 50, true)));
        assertEquals(20, far.bestWood(), "a far stack is left out");
    }

    /** Least wood over every set of at most (places - 1) links that joins all islands. */
    static int bruteForce(SignalFires s) {
        List<Isle> isles = s.isles();
        List<Link> all = new ArrayList<>();
        for (int i = 0; i < isles.size(); i++) {
            for (int j = i + 1; j < isles.size(); j++) {
                all.add(s.link(isles.get(i).id(), isles.get(j).id()));
            }
        }
        int[] best = {Integer.MAX_VALUE};
        pick(s, all, 0, new ArrayList<>(), isles.size() - 1, best);
        return best[0];
    }

    static void pick(SignalFires s, List<Link> all, int from, List<Link> cur, int max, int[] best) {
        int w = cur.stream().mapToInt(Link::wood).sum();
        if (w >= best[0]) {
            return;
        }
        if (joins(s, cur)) {
            best[0] = w;
            return;
        }
        if (cur.size() == max) {
            return;
        }
        for (int i = from; i < all.size(); i++) {
            cur.add(all.get(i));
            pick(s, all, i + 1, cur, max, best);
            cur.remove(cur.size() - 1);
        }
    }

    static boolean joins(SignalFires s, List<Link> links) {
        Map<String, Set<String>> adj = new HashMap<>();
        for (Link l : links) {
            adj.computeIfAbsent(l.a(), k -> new HashSet<>()).add(l.b());
            adj.computeIfAbsent(l.b(), k -> new HashSet<>()).add(l.a());
        }
        Set<String> seen = new HashSet<>();
        List<String> todo = new ArrayList<>(List.of(SignalFires.HOME));
        while (!todo.isEmpty()) {
            String x = todo.remove(todo.size() - 1);
            if (seen.add(x)) {
                todo.addAll(adj.getOrDefault(x, Set.of()));
            }
        }
        return s.isles().stream().filter(i -> !i.relay()).allMatch(i -> seen.contains(i.id()));
    }

    @Test
    void leastWoodMatchesBruteForce() {
        for (long seed = 0; seed < 12; seed++) {
            SignalFires s = map(seed);
            assertEquals(bruteForce(s), s.bestWood(), "seed " + seed);
            assertTrue(joins(s, s.best()));
        }
    }

    @Test
    void guards() {
        SignalFires s = map(0);
        assertEquals(KeeperFireLines.GREETING, s.talk("t0"));
        assertEquals(Outcome.IGNORED, s.light(" ", "home", "kelp_harbour"));
        assertEquals(Outcome.UNKNOWN_ISLE, s.light("e0", "home", "atlantis"));
        assertEquals(Outcome.SAME_ISLE, s.light("e1", "home", "home"));
        assertEquals(Outcome.NOT_LIT, s.douse("e2", "home", "kelp_harbour"));
        assertEquals(Outcome.NOT_JOINED, s.signal("e3"));
        assertEquals(Outcome.LIT, s.light("e4", "home", "kelp_harbour"));
        assertEquals(Outcome.DUPLICATE, s.light("e4", "home", "cinder_reach"));
        assertEquals(Outcome.ALREADY_LIT, s.light("e5", "kelp_harbour", "home"));
        assertEquals(String.format(KeeperFireLines.BUILDING, 1, s.wood()), s.talk("t1"));
        assertNull(s.last());
    }

    @Test
    void questSmokyStarThenWarmTreeThenKeeper() {
        long seed = 0;
        while (spokes(map(seed)) <= map(seed).bestWood()) {
            seed++;
        }
        SignalFires s = map(seed);
        int n = 0;
        for (Destination d : Destination.island()) {
            assertEquals(Outcome.LIT, s.light("s" + n++, SignalFires.HOME, d.id()));
        }
        assertTrue(s.joined());
        assertEquals(KeeperFireLines.READY, s.talk("t1"));
        assertEquals(1, s.quest().stepIndex());
        assertEquals(Outcome.SMOKY, s.signal("sig1"));
        assertEquals(String.format(KeeperFireLines.SMOKY, s.wood(), s.bestWood()), s.talk("t2"));
        for (Link l : s.lit()) {
            assertEquals(Outcome.DOUSED, s.douse("d" + n++, l.a(), l.b()));
        }
        for (Link l : s.best()) {
            assertEquals(Outcome.LIT, s.light("b" + n++, l.a(), l.b()));
        }
        assertEquals(Outcome.WARM, s.signal("sig2"));
        assertEquals(KeeperFireLines.THANKS, s.talk("keeper"));
        assertTrue(s.quest().complete());
        assertEquals(KeeperFireLines.DONE, s.talk("after"));
        assertEquals("q_signal_fires", SignalFires.QUEST_ID);
    }

    static int spokes(SignalFires s) {
        return Destination.island().stream().mapToInt(d -> s.link(SignalFires.HOME, d.id()).wood()).sum();
    }
}
