// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.apprentice;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.apprentice.Apprenticeships.Outcome;
import com.daedalus.world.brew.apprentice.Apprenticeships.Pair;
import com.daedalus.world.brew.letters.Destination;
import com.daedalus.world.brew.school.Pupil;
import com.daedalus.world.brew.school.SongSchool;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class ApprenticeshipsTest {
    static List<Pupil> children(long seed) {
        return SongSchool.fromFarIslands(Destination.island(), seed);
    }

    /** Every full pairing of children to masters. */
    static List<Map<String, String>> allPairings(Apprenticeships a) {
        List<Map<String, String>> out = new ArrayList<>();
        permute(new ArrayList<>(a.childPrefs().keySet()), new ArrayList<>(a.masterPrefs().keySet()), 0, out);
        return out;
    }

    static void permute(List<String> kids, List<String> ms, int i, List<Map<String, String>> out) {
        if (i == ms.size()) {
            Map<String, String> m = new LinkedHashMap<>();
            for (int k = 0; k < kids.size(); k++) {
                m.put(kids.get(k), ms.get(k));
            }
            out.add(m);
            return;
        }
        for (int j = i; j < ms.size(); j++) {
            java.util.Collections.swap(ms, i, j);
            permute(kids, ms, i + 1, out);
            java.util.Collections.swap(ms, i, j);
        }
    }

    @Test
    void seededRankingsOnBothSides() {
        Apprenticeships a = Apprenticeships.forChildren(children(2), 9);
        assertEquals(4, a.childPrefs().size());
        a.childPrefs().values().forEach(p -> assertEquals(new HashSet<>(Apprenticeships.MASTERS), new HashSet<>(p)));
        a.masterPrefs().values().forEach(p -> assertEquals(a.childPrefs().keySet(), new HashSet<>(p)));
        assertEquals(a.childPrefs(), Apprenticeships.forChildren(children(2), 9).childPrefs());
        assertEquals(a.masterPrefs(), Apprenticeships.forChildren(children(2), 9).masterPrefs());
        assertThrows(IllegalArgumentException.class, () -> Apprenticeships.forChildren(children(2).subList(0, 3), 1));
        assertThrows(IllegalArgumentException.class, () -> new Apprenticeships(Map.of("a", List.of("x")),
                Map.of("x", List.of("b"))));
    }

    @Test
    void twoStablePairingsChildrenAndMastersEachGetTheirBest() {
        Apprenticeships a = new Apprenticeships(
                Map.of("a", List.of("x", "y"), "b", List.of("y", "x")),
                Map.of("x", List.of("b", "a"), "y", List.of("a", "b")));
        assertEquals(Map.of("a", "x", "b", "y"), a.proposing(true));
        assertEquals(Map.of("a", "y", "b", "x"), a.proposing(false));
        assertTrue(a.blockingPairs(a.proposing(true)).isEmpty());
        assertTrue(a.blockingPairs(a.proposing(false)).isEmpty());
        Apprenticeships rivals = new Apprenticeships(
                Map.of("a", List.of("x", "y"), "b", List.of("x", "y")),
                Map.of("x", List.of("a", "b"), "y", List.of("a", "b")));
        assertEquals(List.of(new Pair("a", "x")), rivals.blockingPairs(Map.of("a", "y", "b", "x")));
        assertEquals(0, rivals.rank("x", "a"));
        assertEquals(1, rivals.rank("b", "y"));
    }

    @Test
    void galeShapleyIsStableAndOptimalForTheProposers() {
        for (long seed = 0; seed < 30; seed++) {
            Apprenticeships a = Apprenticeships.forChildren(children(seed), seed);
            List<Map<String, String>> stable = allPairings(a).stream().filter(p -> a.blockingPairs(p).isEmpty())
                    .toList();
            assertFalse(stable.isEmpty());
            Map<String, String> kids = a.proposing(true);
            Map<String, String> masters = a.proposing(false);
            assertTrue(stable.contains(kids), "seed " + seed);
            assertTrue(stable.contains(masters), "seed " + seed);
            for (Map<String, String> s : stable) {
                for (String c : a.childPrefs().keySet()) {
                    assertTrue(a.rank(c, kids.get(c)) <= a.rank(c, s.get(c)), "child-optimal");
                    assertTrue(a.rank(c, masters.get(c)) >= a.rank(c, s.get(c)), "child-pessimal");
                }
                Map<String, String> childOf = new LinkedHashMap<>();
                masters.forEach((c, m) -> childOf.put(m, c));
                Map<String, String> sChildOf = new LinkedHashMap<>();
                s.forEach((c, m) -> sChildOf.put(m, c));
                for (String m : a.masterPrefs().keySet()) {
                    assertTrue(a.rank(m, childOf.get(m)) <= a.rank(m, sChildOf.get(m)), "master-optimal");
                }
            }
        }
    }

    @Test
    void guards() {
        Apprenticeships a = Apprenticeships.forChildren(children(0), 0);
        List<String> kids = new ArrayList<>(a.childPrefs().keySet());
        assertEquals(WickApprenticeLines.GREETING, a.talk("t0"));
        assertEquals(Outcome.IGNORED, a.pair("", kids.get(0), "dov"));
        assertEquals(Outcome.UNKNOWN_CHILD, a.pair("e0", "nobody", "dov"));
        assertEquals(Outcome.UNKNOWN_MASTER, a.pair("e1", kids.get(0), "nobody"));
        assertEquals(Outcome.NOT_PAIRED, a.unpair("e2", kids.get(0)));
        assertEquals(Outcome.NOT_EVERYONE, a.announce("e3"));
        assertEquals(Outcome.PAIRED, a.pair("e4", kids.get(0), "dov"));
        assertEquals(Outcome.DUPLICATE, a.pair("e4", kids.get(1), "mason_hale"));
        assertEquals(Outcome.CHILD_TAKEN, a.pair("e5", kids.get(0), "mason_hale"));
        assertEquals(Outcome.MASTER_TAKEN, a.pair("e6", kids.get(1), "dov"));
        assertEquals(String.format(WickApprenticeLines.PINNING, 3, "ren"), a.talk("t1"));
        assertNull(a.announced());
    }

    @Test
    void questUnstableThenStableThenWick() {
        Apprenticeships a = Apprenticeships.forChildren(children(4), 4);
        Map<String, String> bad = allPairings(a).stream().filter(p -> !a.blockingPairs(p).isEmpty()).findFirst()
                .orElseThrow();
        int n = 0;
        for (Map.Entry<String, String> e : bad.entrySet()) {
            assertEquals(Outcome.PAIRED, a.pair("b" + n++, e.getKey(), e.getValue()));
        }
        assertEquals(WickApprenticeLines.READY, a.talk("t1"));
        assertEquals(Outcome.UNSTABLE, a.announce("night1"));
        Pair p = a.blockingPairs(a.board()).get(0);
        assertEquals(String.format(WickApprenticeLines.UNSTABLE, p.child(), p.master()), a.talk("t2"));
        assertEquals(1, a.quest().stepIndex());
        for (String c : bad.keySet()) {
            assertEquals(Outcome.UNPAIRED, a.unpair("u" + n++, c));
        }
        for (Map.Entry<String, String> e : a.proposing(true).entrySet()) {
            assertEquals(Outcome.PAIRED, a.pair("g" + n++, e.getKey(), e.getValue()));
        }
        assertEquals(1, a.quest().stepIndex(), "re-pinning a child does not re-count");
        assertEquals(Outcome.STABLE, a.announce("night2"));
        assertEquals(WickApprenticeLines.THANKS, a.talk("wick"));
        assertTrue(a.quest().complete());
        assertEquals(WickApprenticeLines.DONE, a.talk("after"));
        assertEquals("q_apprentices", Apprenticeships.QUEST_ID);
    }
}
