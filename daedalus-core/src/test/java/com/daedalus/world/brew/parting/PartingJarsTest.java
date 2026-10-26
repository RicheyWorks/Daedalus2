// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.parting;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.cellar.Preserve;
import com.daedalus.world.brew.letters.Destination;
import com.daedalus.world.brew.lofts.Family;
import com.daedalus.world.brew.lofts.GuestLofts;
import com.daedalus.world.brew.parting.PartingJars.Outcome;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import org.junit.jupiter.api.Test;

class PartingJarsTest {
    static PartingJars forSeed(long seed) {
        return PartingJars.forFamilies(GuestLofts.fromFarIslands(Destination.island(), seed), Destination.island(), seed);
    }

    static List<PartingJar> byDue(List<PartingJar> l) {
        List<PartingJar> s = new ArrayList<>(l);
        s.sort(Comparator.comparingInt(PartingJar::due).thenComparing(PartingJar::family));
        return s;
    }

    /** Most on-time orders over every subset (each worked in due order, which is best for a fixed subset). */
    static int bruteForce(List<PartingJar> all, int start) {
        int best = 0;
        for (int mask = 0; mask < (1 << all.size()); mask++) {
            List<PartingJar> sub = new ArrayList<>();
            for (int i = 0; i < all.size(); i++) {
                if ((mask & (1 << i)) != 0) {
                    sub.add(all.get(i));
                }
            }
            if (PartingJars.onTime(byDue(sub), start) == sub.size()) {
                best = Math.max(best, sub.size());
            }
        }
        return best;
    }

    @Test
    void eachFamilyGetsTheirIslandsFavouriteKeptTheLongestWay() {
        assertEquals(Preserve.Method.SALT, PartingJars.methodFor("fish"));
        assertEquals(Preserve.Method.SALT, PartingJars.methodFor("Bacon"));
        assertEquals(Preserve.Method.PICKLE, PartingJars.methodFor("Egg"));
        assertEquals(Preserve.Method.DRY, PartingJars.methodFor("Moonbean"));
        assertThrows(IllegalArgumentException.class, () -> PartingJars.methodFor("Milk"));
        List<Family> fam = GuestLofts.fromFarIslands(Destination.island(), 5);
        PartingJars p = PartingJars.forFamilies(fam, Destination.island(), 5);
        assertEquals(fam.size(), p.orders().size());
        assertEquals(fam.stream().mapToInt(Family::arrive).min().orElseThrow(), p.start());
        for (int i = 0; i < fam.size(); i++) {
            PartingJar j = p.orders().get(i);
            assertEquals(fam.get(i).leave(), j.due());
            assertEquals(j.jars() * PartingJars.PREP_DAYS.get(j.method()), j.prepDays());
            assertTrue(j.jars() >= 1 && j.jars() <= PartingJars.JARS_MAX);
        }
        assertEquals(p.orders(), PartingJars.forFamilies(fam, Destination.island(), 5).orders());
        assertThrows(IllegalArgumentException.class, () -> new PartingJar("x", "fish", Preserve.Method.SALT, 1, 0, 3));
    }

    @Test
    void mooreHodgsonDropsTheLongestWhenLate() {
        PartingJar a = new PartingJar("a", "Moonbean", Preserve.Method.DRY, 1, 3, 3);
        PartingJar b = new PartingJar("b", "fish", Preserve.Method.SALT, 1, 1, 2);
        PartingJar c = new PartingJar("c", "fish", Preserve.Method.SALT, 1, 1, 2);
        PartingJars p = new PartingJars(List.of(a, b, c), 0);
        assertEquals(1, PartingJars.onTime(List.of(a, b, c), 0), "a done on day 3, then b and c late on 4 and 5");
        assertEquals(List.of(b, c), p.best(), "dropping a (3 days) lets b and c both go");
        assertEquals(2, bruteForce(List.of(a, b, c), 0));
        assertThrows(IllegalArgumentException.class, () -> new PartingJars(List.of(a, a), 0));
    }

    @Test
    void bestMatchesBruteForceAndThePuzzleBites() {
        int bites = 0;
        for (long seed = 0; seed < 30; seed++) {
            PartingJars p = forSeed(seed);
            assertEquals(bruteForce(p.orders(), p.start()), p.best().size(), "seed " + seed);
            assertEquals(p.best().size(), PartingJars.onTime(p.best(), p.start()));
            if (PartingJars.onTime(byDue(p.orders()), p.start()) < p.best().size()) {
                bites++;
            }
        }
        assertTrue(bites > 0, "working everything in due order is not always best");
    }

    @Test
    void questShortThenFullShelfThenBrine() {
        long seed = 0;
        while (PartingJars.onTime(byDue(forSeed(seed).orders()), forSeed(seed).start()) >= forSeed(seed).best().size()) {
            seed++;
        }
        PartingJars p = forSeed(seed);
        List<String> all = byDue(p.orders()).stream().map(PartingJar::family).toList();
        assertEquals(ApprenticeJarLines.GREETING, p.talk("t0"));
        assertEquals(Outcome.IGNORED, p.plan("", all));
        assertEquals(Outcome.EMPTY, p.plan("e0", List.of()));
        assertEquals(Outcome.REPEATED, p.plan("e1", List.of(all.get(0), all.get(0))));
        assertEquals(Outcome.UNKNOWN_FAMILY, p.plan("e2", List.of("nobody")));
        assertEquals(Outcome.SHORT, p.plan("p1", all));
        assertEquals(Outcome.DUPLICATE, p.plan("p1", all));
        assertEquals(String.format(ApprenticeJarLines.SHORT, p.lastOnTime(), p.best().size()), p.talk("t1"));
        assertEquals(1, p.quest().stepIndex());
        assertEquals(Outcome.FULL_SHELF, p.plan("p2", p.best().stream().map(PartingJar::family).toList()));
        assertEquals(ApprenticeJarLines.THANKS, p.talk("brine"));
        assertTrue(p.quest().complete());
        assertEquals(ApprenticeJarLines.DONE, p.talk("after"));
        assertEquals("q_parting_jars", PartingJars.QUEST_ID);
    }
}
