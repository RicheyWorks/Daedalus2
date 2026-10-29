// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.netrack;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.netrack.NetRack.Outcome;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

class NetRackTest {
    /** Brute force: try sending back every net on the rack at every full-rack trip. */
    static int brute(NetRack r) {
        return trips(r, 0, new ArrayList<>());
    }

    static int trips(NetRack r, int i, List<Integer> rack) {
        if (i == r.asks().size()) {
            return 0;
        }
        int net = r.asks().get(i);
        if (rack.contains(net)) {
            return trips(r, i + 1, rack);
        }
        if (rack.size() < r.slots()) {
            List<Integer> next = new ArrayList<>(rack);
            next.add(net);
            return 1 + trips(r, i + 1, next);
        }
        int best = Integer.MAX_VALUE;
        for (int k = 0; k < rack.size(); k++) {
            List<Integer> next = new ArrayList<>(rack);
            next.set(k, net);
            best = Math.min(best, 1 + trips(r, i + 1, next));
        }
        return best;
    }

    /** Two slots, asks 0 1 2 0 1 2: the fewest is 4 trips; sending back the net unused longest costs 6. */
    static NetRack rack() {
        return new NetRack(2, List.of(0, 1, 2, 0, 1, 2));
    }

    @Test
    void seededRackIsDeterministic() {
        assertEquals(NetRack.seeded(1).asks(), NetRack.seeded(1).asks());
        assertEquals(NetRack.seeded(1).fewest(), NetRack.seeded(1).fewest());
        assertThrows(IllegalArgumentException.class, () -> new NetRack(0, List.of()));
        assertThrows(IllegalArgumentException.class, () -> new NetRack(1, List.of(-1)));
    }

    @Test
    void fewestMatchesBruteForce() {
        for (long seed = 0; seed < 30; seed++) {
            NetRack r = NetRack.seeded(seed);
            assertEquals(brute(r), r.fewest(), "Belady == brute force, seed " + seed);
            assertTrue(r.lruTrips() >= r.fewest(), "LRU never beats Belady, seed " + seed);
        }
    }

    @Test
    void unusedLongestIsATrap() {
        NetRack r = rack();
        assertEquals(4, r.fewest());
        assertEquals(6, r.lruTrips());
        assertEquals(Outcome.WRONG, r.count("c0", 6), "LRU sends back the very net needed next");
        assertEquals(String.format(KeeperNetRack.WRONG, 6), r.talk("t0"));
    }

    @Test
    void wrongAndRoomyEarnNoCredit() {
        NetRack r = rack();
        r.read("r");
        assertEquals(Outcome.WRONG, r.count("c1", 3));
        assertEquals(Outcome.MALFORMED, r.count("c2", -1));
        assertEquals("count", r.quest().currentStep().type(), "no credit for a wrong count");
        NetRack roomy = new NetRack(3, List.of(0, 1, 2, 0, 1, 2));
        assertTrue(roomy.roomy());
        assertEquals(Outcome.ROOMY, roomy.count("x", 3));
        assertEquals(KeeperNetRack.ROOMY, roomy.talk("tx"));
    }

    @Test
    void guards() {
        NetRack r = rack();
        assertEquals(Outcome.IGNORED, r.count("", 4));
        assertEquals(Outcome.IGNORED, r.count(null, 4));
        assertEquals(Outcome.RIGHT, r.count("e1", 4));
        assertEquals(Outcome.DUPLICATE, r.count("e1", 4));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        NetRack r = rack();
        assertEquals(String.format(KeeperNetRack.GREETING, 2, List.of(0, 1, 2, 0, 1, 2)), r.talk("t0"));
        r.read("r0");
        assertEquals(Outcome.WRONG, r.count("c1", 6));
        assertEquals(Outcome.RIGHT, r.count("c2", 4));
        assertEquals(KeeperNetRack.THANKS, r.talk("t2"));
        assertNull(r.quest().currentStep());
        assertEquals(KeeperNetRack.DONE, r.talk("t3"));
    }
}
