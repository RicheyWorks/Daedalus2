// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.watch;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.watch.NightWatch.Outcome;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class NightWatchTest {
    static boolean covered(int night, List<Stretch> chosen) {
        for (int h = 0; h < night; h++) {
            int hour = h;
            if (chosen.stream().noneMatch(s -> s.covers(hour))) {
                return false;
            }
        }
        return true;
    }

    static int brute(int night, List<Stretch> offers) {
        int best = Integer.MAX_VALUE;
        for (int mask = 1; mask < (1 << offers.size()); mask++) {
            List<Stretch> chosen = new ArrayList<>();
            for (int i = 0; i < offers.size(); i++) {
                if ((mask >> i & 1) == 1) {
                    chosen.add(offers.get(i));
                }
            }
            if (chosen.size() < best && covered(night, chosen)) {
                best = chosen.size();
            }
        }
        return best;
    }

    @Test
    void seededCrewCoversTheNightAndIsDeterministic() {
        NightWatch w = NightWatch.seeded(5);
        assertTrue(w.night() >= 8 && w.night() <= 12);
        assertTrue(covered(w.night(), w.offers()));
        assertEquals(w.offers(), NightWatch.seeded(5).offers());
        assertThrows(IllegalArgumentException.class, () -> new Stretch("a", 3, 3));
    }

    @Test
    void touchingEndpointsCountAsCovered() {
        // dusk ends at hour 5 and dawn starts at hour 5: they touch, and hour 5 is watched by dawn, so no gap.
        NightWatch w = new NightWatch(10, List.of(new Stretch("dusk", 0, 5), new Stretch("dawn", 5, 10)));
        assertTrue(w.coverable());
        assertEquals(2, w.fewest());
        w.wake("w1", "dusk");
        w.wake("w2", "dawn");
        assertEquals(-1, w.firstGap());
        assertEquals(Outcome.WARM, w.callNight("n1"));
    }

    @Test
    void anUncoverableNightIsNoCoverWithNoCredit() {
        NightWatch w = new NightWatch(6, List.of(new Stretch("a", 0, 2), new Stretch("b", 3, 6)));
        assertTrue(!w.coverable());
        assertEquals(-1, w.fewest());
        assertEquals(Integer.MAX_VALUE, brute(6, w.offers()));
        w.wake("w1", "a");
        w.wake("w2", "b");
        assertEquals(Outcome.NO_COVER, w.callNight("n1"));
        assertEquals(String.format(KeeperWatchLines.NO_COVER, 2), KeeperWatchLines.line(w));
        assertEquals("wake", w.quest().currentStep().type(), "no warm-night credit");
    }

    @Test
    void theLongestStretchIsNotAlwaysInTheBestRota() {
        List<Stretch> offers = List.of(new Stretch("long", 2, 8), new Stretch("dusk", 0, 5),
                new Stretch("dawn", 5, 10));
        NightWatch w = new NightWatch(10, offers);
        assertEquals(2, w.fewest());
        assertEquals(List.of("dusk", "dawn"), w.rota().stream().map(Stretch::sailor).toList());
    }

    @Test
    void fewestMatchesBruteForce() {
        for (long seed = 0; seed < 20; seed++) {
            NightWatch w = NightWatch.seeded(seed);
            assertTrue(w.offers().size() <= 10, "brute force stays small");
            assertEquals(brute(w.night(), w.offers()), w.fewest(), "greedy == true minimum, seed " + seed);
            assertTrue(covered(w.night(), w.rota()), "dusk to dawn with no gap, seed " + seed);
        }
    }

    @Test
    void guards() {
        NightWatch w = new NightWatch(4, List.of(new Stretch("a", 0, 4), new Stretch("b", 0, 2)));
        assertEquals(Outcome.IGNORED, w.wake("", "a"));
        assertEquals(Outcome.UNKNOWN, w.wake("e0", "zed"));
        assertEquals(Outcome.GAPS, w.callNight("n0"));
        assertEquals(Outcome.WOKEN, w.wake("e1", "b"));
        assertEquals(Outcome.DUPLICATE, w.wake("e1", "a"));
        assertEquals(Outcome.ALREADY_WOKEN, w.wake("e2", "b"));
        assertEquals(Outcome.NOT_WOKEN, w.sendToBed("e3", "a"));
        assertEquals(Outcome.SENT_TO_BED, w.sendToBed("e4", "b"));
        assertThrows(IllegalArgumentException.class,
                () -> new NightWatch(2, List.of(new Stretch("a", 0, 2), new Stretch("a", 0, 1))));
    }

    @Test
    void questWearyNightThenWarmThenKeeper() {
        NightWatch w = new NightWatch(10, List.of(new Stretch("long", 2, 8), new Stretch("dusk", 0, 5),
                new Stretch("dawn", 5, 10)));
        assertEquals(KeeperWatchLines.GREETING, w.talk("t0"));
        assertEquals(Outcome.WOKEN, w.wake("w1", "long"));
        assertEquals("1 on the rota. Hour 0 has nobody yet.", KeeperWatchLines.line(w));
        w.wake("w2", "dusk");
        w.wake("w3", "dawn");
        assertEquals(KeeperWatchLines.READY, w.talk("t1"));
        assertEquals(Outcome.WEARY, w.callNight("n1"));
        assertEquals(String.format(KeeperWatchLines.WEARY, 3, 2), w.talk("t2"));
        assertEquals(Outcome.SENT_TO_BED, w.sendToBed("b1", "long"));
        assertEquals(Outcome.WARM, w.callNight("n2"));
        assertEquals(KeeperWatchLines.THANKS, w.talk("t3"));
        assertNull(w.quest().currentStep());
        assertEquals(KeeperWatchLines.DONE, w.talk("t4"));
    }
}
