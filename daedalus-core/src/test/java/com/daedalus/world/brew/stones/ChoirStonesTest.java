// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.stones;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.BrewBench;
import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.MelodyBrew;
import com.daedalus.world.brew.PitchTable;
import com.daedalus.world.brew.hunt.FragmentMap;
import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.brew.story.SpringChain;
import com.daedalus.world.colony.PlotState;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class ChoirStonesTest {
    List<FoundTune> tunes;
    SeedSongSpring songs;
    PlotState plot;

    /** A straight shelf: Homestead - 1 - 2 - ... - (n-1). */
    static FragmentMap line(int n) {
        int[][] b = new int[n - 1][];
        for (int i = 0; i < n - 1; i++) {
            b[i] = new int[] {i, i + 1};
        }
        return FragmentMap.of(n, b);
    }

    String mend(int i) {
        FoundTune t = tunes.get(i);
        plot.add(t.learnedFrom(), 1);
        t.herbs().forEach(h -> plot.add(h, 1));
        var r = songs.restore("mend-" + i, t.learnedFrom(),
                t.herbs().stream().map(h -> new MelodyBrew.Ingredient(h, 3)).toList(), plot);
        assertEquals(SeedSongSpring.Outcome.RESTORED, r.outcome());
        return t.learnedFrom();
    }

    @BeforeEach
    void setUp() throws Exception {
        try (var in = getClass().getResourceAsStream("/com/daedalus/world/brew/found_tunes.csv")) {
            tunes = FoundTune.parseCsv(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        }
        songs = new SeedSongSpring(new BrewBench(PitchTable.ISLAND_CANON, tunes), tunes, SpringChain.island(), 4);
        plot = new PlotState();
    }

    @Test
    void bridgesFraySnapAndRestringWithRope() {
        BridgeLedger l = new BridgeLedger(line(3));
        assertEquals(2, l.bridges().size());
        assertEquals(BridgeLedger.MAX_STRENGTH, l.strength(1, 0));
        assertEquals(-1, l.strength(0, 2));
        assertFalse(l.restring(0, 1, plot), "already full");
        BridgeLedger.Bridge b = BridgeLedger.Bridge.of(2, 1);
        assertEquals(new BridgeLedger.Bridge(1, 2), b);
        assertFalse(l.fray(b));
        assertFalse(l.fray(b));
        assertTrue(l.fray(b), "third fray snaps it");
        assertFalse(l.fray(b), "a snapped bridge stays snapped");
        assertFalse(l.intact(1, 2));
        assertEquals(Set.of(2), l.cutOff());
        assertFalse(l.restring(1, 2, plot), "no rope");
        assertFalse(l.restring(0, 2, plot), "no bridge");
        assertFalse(l.restring(1, 2, null));
        plot.add(BridgeLedger.ROPE, 3);
        assertTrue(l.restring(1, 2, plot));
        assertEquals(1, plot.count(BridgeLedger.ROPE));
        assertEquals(Set.of(), l.cutOff());
        assertEquals(BridgeLedger.MAX_STRENGTH, l.snapshot().get(b));
        assertTrue(b.compareTo(new BridgeLedger.Bridge(0, 1)) > 0);
        assertTrue(b.compareTo(new BridgeLedger.Bridge(1, 3)) < 0);
    }

    @Test
    void onlyAMendedRecordAndABlankStoneMakeAChoirStone() {
        ChoirStones c = new ChoirStones(line(6), songs, 1);
        String rec = tunes.get(0).learnedFrom();
        assertEquals(ChoirStones.Outcome.NOT_RESTORED, c.carve("c0", 2, rec, 2, plot));
        mend(0);
        assertEquals(ChoirStones.Outcome.NO_STONE, c.carve("c1", 2, rec, 2, plot));
        plot.add(ChoirStones.STONE, 3);
        assertEquals(ChoirStones.Outcome.UNKNOWN_FRAGMENT, c.carve("c2", 6, rec, 2, plot));
        assertEquals(ChoirStones.Outcome.UNKNOWN_FRAGMENT, c.carve("c2", -1, rec, 2, plot));
        assertEquals(ChoirStones.Outcome.IGNORED, c.carve("", 2, rec, 2, plot));
        assertEquals(ChoirStones.Outcome.IGNORED, c.carve("c3", 2, rec, 2, null));
        assertEquals(ChoirStones.Outcome.CARVED, c.carve("c4", 2, rec, 2, plot));
        assertEquals(ChoirStones.Outcome.DUPLICATE, c.carve("c4", 3, rec, 2, plot));
        assertEquals(ChoirStones.Outcome.RECORD_USED, c.carve("c5", 3, rec, 2, plot));
        String rec2 = mend(1);
        assertEquals(ChoirStones.Outcome.FRAGMENT_TAKEN, c.carve("c6", 2, rec2, 2, plot));
        assertEquals(2, plot.count(ChoirStones.STONE), "only the carved stone was spent");
        assertEquals(List.of(new ChoirStones.Stone(2, rec, 2)), c.stones());
    }

    @Test
    void humRangeComesFromTheBrewTier() {
        assertEquals(1, ChoirStones.range(1));
        assertEquals(2, ChoirStones.range(2));
        assertEquals(2, ChoirStones.range(3));
        assertEquals(3, ChoirStones.range(4));
        assertEquals(1, ChoirStones.range(0));
        assertEquals(3, ChoirStones.range(9));
        assertEquals(1, ChoirStones.fraysPerNight(3));
        assertEquals(4, ChoirStones.fraysPerNight(12));
    }

    @Test
    void aHummingBridgeNeverFrays() {
        String rec = mend(0);
        for (long seed = 0; seed < 20; seed++) {
            FragmentMap m = FragmentMap.seeded(seed, 16);
            ChoirStones c = new ChoirStones(m, songs, seed);
            plot.add(ChoirStones.STONE, 1);
            assertEquals(ChoirStones.Outcome.CARVED, c.carve("s" + seed, 0, rec, 4, plot));
            for (int n = 1; n <= 40; n++) {
                ChoirStones.Night night = c.night(n);
                for (BridgeLedger.Bridge b : night.frayed()) {
                    assertFalse(c.humming(b), "seed " + seed + " night " + n + " frayed a humming bridge " + b);
                }
            }
            for (BridgeLedger.Bridge b : c.ledger().bridges()) {
                if (c.humming(b)) {
                    assertEquals(BridgeLedger.MAX_STRENGTH, c.ledger().strength(b.a(), b.b()));
                }
            }
        }
    }

    @Test
    void tremorsAreSeededAndUnguardedShelvesFallApart() {
        ChoirStones a = new ChoirStones(line(8), songs, 77);
        ChoirStones b = new ChoirStones(line(8), songs, 77);
        boolean anyCut = false;
        for (int n = 1; n <= 30; n++) {
            ChoirStones.Night x = a.night(n);
            ChoirStones.Night y = b.night(n);
            assertEquals(x, y, "same seed, same night");
            assertEquals(x.cutOff().isEmpty(), x.held());
            anyCut |= !x.held();
        }
        assertTrue(anyCut, "with no stones the straight shelf breaks");
        assertNull(a.night(30), "a night runs once");
        assertNull(a.night(5));
        int firstCut = a.ledger().cutOff().stream().findFirst().orElseThrow();
        for (int f = firstCut; f < 8; f++) {
            assertTrue(a.ledger().cutOff().contains(f), "everything past a snap is cut off");
        }
    }

    @Test
    void questCarveTwoHoldThreeNightsTellTheMason() {
        FragmentMap m = line(7);
        ChoirStones c = new ChoirStones(m, songs, 5);
        assertEquals(MasonLines.GREETING, c.talk("t0"));
        plot.add(ChoirStones.STONE, 2);
        assertEquals(ChoirStones.Outcome.CARVED, c.carve("k1", 1, mend(0), 4, plot));
        assertEquals(MasonLines.ONE_STONE, MasonLines.line(c));
        assertEquals(ChoirStones.Outcome.CARVED, c.carve("k2", 5, mend(1), 4, plot));
        assertEquals(String.format(MasonLines.HOLDING, 0, "s"), MasonLines.line(c));
        // range 3 from fragments 1 and 5 covers every bridge of the 7-fragment line: nothing can fray.
        for (BridgeLedger.Bridge b : c.ledger().bridges()) {
            assertTrue(c.humming(b), b.toString());
        }
        for (int n = 1; n <= 3; n++) {
            ChoirStones.Night night = c.night(n);
            assertTrue(night.held());
            assertTrue(night.frayed().isEmpty());
        }
        assertEquals(String.format(MasonLines.HOLDING, 3, "s"), MasonLines.line(c));
        assertEquals(MasonLines.THANKS, c.talk("t1"));
        assertTrue(c.quest().complete());
        assertTrue(c.quest().claimReward());
        assertFalse(c.quest().claimReward());
        assertEquals(3, c.heldNights());
    }

    @Test
    void theMasonNamesWhatTheShakeCutOff() {
        ChoirStones c = new ChoirStones(line(8), songs, 77);
        plot.add(ChoirStones.STONE, 1);
        assertEquals(ChoirStones.Outcome.CARVED, c.carve("k", 0, mend(2), 1, plot));
        ChoirStones.Night bad = null;
        for (int n = 1; n <= 60 && bad == null; n++) {
            ChoirStones.Night x = c.night(n);
            if (!x.held()) {
                bad = x;
            } else {
                assertEquals(String.format(MasonLines.HOLDING, c.heldNights(), c.heldNights() == 1 ? "" : "s"),
                        MasonLines.line(c));
            }
        }
        assertNotNull(bad);
        int k = bad.cutOff().size();
        assertEquals(String.format(MasonLines.CUT_OFF, k, k == 1 ? "" : "s"), c.talk("t"));
        assertFalse(c.ledger().cutOff().isEmpty());
        assertEquals(0, c.quest().stepIndex(), "one stone is not enough for the carve step");
        assertEquals(1, c.quest().stepCount());
    }
}
