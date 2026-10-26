// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.round;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.letters.Destination;
import com.daedalus.world.brew.round.HarbourRound.Entry;
import com.daedalus.world.brew.round.HarbourRound.Outcome;
import com.daedalus.world.brew.school.Pupil;
import com.daedalus.world.brew.school.SongSchool;
import com.daedalus.world.brew.song.ThirteenthSong;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class HarbourRoundTest {
    static final String ALPINE = "Item_YTM_Record_Alpine";
    static final String DUDUK = "Item_YTM_Record_ArmenianDuduk";
    static final String BAROQUE = "Item_YTM_Record_BaroqueCounterpoint";
    List<FoundTune> tunes;
    Map<String, List<Integer>> notes;

    @BeforeEach
    void setUp() throws Exception {
        try (var in = getClass().getResourceAsStream("/com/daedalus/world/brew/found_tunes.csv")) {
            tunes = FoundTune.parseCsv(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        }
        notes = HarbourRound.notesOf(tunes);
    }

    @Test
    void harmonyCountsConsonantPairsBeatByBeat() {
        assertEquals(List.of(0, 4, 7, 4, 0), notes.get(ALPINE));
        assertEquals(1.0, HarbourRound.harmony(notes.get(ALPINE), List.of(new Entry(1, 0))), 1e-9,
                "0-0, 4-0, 7-4, 4-7, 0-4: all consonant");
        assertEquals(0.2, HarbourRound.harmony(notes.get(DUDUK), List.of(new Entry(1, 0))), 1e-9,
                "2-2 then four seconds");
        assertEquals(1.0, HarbourRound.harmony(notes.get(DUDUK), List.of()), 1e-9);
        assertEquals(Outcome.SWEET, HarbourRound.grade(0.75));
        assertEquals(Outcome.FAIR, HarbourRound.grade(0.5));
        assertEquals(Outcome.SOUR, HarbourRound.grade(0.49));
        assertTrue(HarbourRound.legal(5, List.of(new Entry(1, 7), new Entry(4, 3))));
        assertFalse(HarbourRound.legal(5, List.of(new Entry(0, 0))));
        assertFalse(HarbourRound.legal(5, List.of(new Entry(5, 0))));
        assertFalse(HarbourRound.legal(5, List.of(new Entry(2, 0), new Entry(2, 4))));
        assertFalse(HarbourRound.legal(5, List.of(new Entry(2, 2))), "a second is not a harmony interval");
    }

    @Test
    void solverIsExactAndSomeSongsWontRound() {
        HarbourRound r = new HarbourRound(notes, notes.keySet());
        for (String song : notes.keySet()) {
            List<Integer> n = notes.get(song);
            double max = -1;
            for (int d1 = 1; d1 < n.size(); d1++) {
                for (int d2 = 1; d2 < n.size(); d2++) {
                    for (int i1 : HarbourRound.INTERVALS) {
                        for (int i2 : HarbourRound.INTERVALS) {
                            List<Entry> e = List.of(new Entry(d1, i1), new Entry(d2, i2));
                            if (HarbourRound.legal(n.size(), e)) {
                                max = Math.max(max, HarbourRound.harmony(n, e));
                            }
                        }
                    }
                }
            }
            HarbourRound.Best b = r.best(song, 3);
            assertEquals(max, b.harmony(), 1e-9, song);
            assertEquals(b.harmony(), HarbourRound.harmony(n, b.entries()), 1e-9);
            assertTrue(HarbourRound.legal(n.size(), b.entries()));
        }
        assertEquals(1.0, r.best(ALPINE, 3).harmony(), 1e-9);
        assertEquals(1.0, r.best(BAROQUE, 3).harmony(), 1e-9);
        assertEquals(Outcome.FAIR, HarbourRound.grade(r.best(DUDUK, 3).harmony()), "the duduk lament won't round");
        long sweet = notes.keySet().stream().filter(s -> r.best(s, 3).harmony() >= HarbourRound.SWEET).count();
        assertEquals(11, sweet);
        assertThrows(IllegalArgumentException.class, () -> r.best(ALPINE, 1));
        assertThrows(IllegalArgumentException.class, () -> r.best("nope", 3));
        assertThrows(IllegalArgumentException.class, () -> new HarbourRound(Map.of("x", List.of(1)), Set.of()));
    }

    @Test
    void guards() {
        HarbourRound r = new HarbourRound(notes, Set.of(ALPINE));
        List<Entry> two = List.of(new Entry(1, 0));
        assertEquals(DovRoundLines.GREETING, r.talk("t0"));
        assertEquals(Outcome.IGNORED, r.rehearse("", ALPINE, two));
        assertEquals(Outcome.UNKNOWN_SONG, r.rehearse("a", "nope", two));
        assertEquals(Outcome.NOT_KNOWN, r.rehearse("b", DUDUK, two));
        assertEquals(Outcome.TOO_FEW_VOICES, r.rehearse("c", ALPINE, List.of()));
        assertEquals(Outcome.TOO_MANY_VOICES, r.rehearse("d", ALPINE,
                List.of(new Entry(1, 0), new Entry(2, 0), new Entry(3, 0), new Entry(4, 0))));
        assertEquals(Outcome.BAD_ENTRY, r.rehearse("e", ALPINE, List.of(new Entry(1, 0), new Entry(1, 4))));
        assertEquals(Outcome.TOO_FEW_VOICES, r.sing("f", ALPINE, two));
        assertNull(r.last());
        assertEquals(0, r.quest().stepCount());
        assertEquals(Outcome.SWEET, r.rehearse("g", ALPINE, two));
        assertEquals(Outcome.DUPLICATE, r.rehearse("g", ALPINE, two));
        assertEquals(String.format(DovRoundLines.REHEARSE, 2, "es"), r.talk("t1"));
    }

    @Test
    void questRehearseThenASweetHarbourRoundThenDov() {
        HarbourRound r = new HarbourRound(notes, Set.of(ALPINE, DUDUK));
        assertEquals(Outcome.SOUR, r.rehearse("r1", DUDUK, List.of(new Entry(1, 0))));
        assertEquals(DovRoundLines.SOUR, r.talk("t1"));
        assertEquals(Outcome.FAIR, r.rehearse("r2", DUDUK, r.best(DUDUK, 3).entries()));
        assertEquals(DovRoundLines.FAIR, r.talk("t2"));
        assertEquals(Outcome.SWEET, r.rehearse("r3", ALPINE, r.best(ALPINE, 4).entries()));
        assertEquals(1, r.quest().stepIndex());
        assertEquals(DovRoundLines.READY, r.talk("t3"));
        assertEquals(Outcome.FAIR, r.sing("s1", DUDUK, r.best(DUDUK, 3).entries()));
        assertEquals(1, r.quest().stepIndex(), "a fair round does not count at the harbour");
        assertEquals(Outcome.SWEET, r.sing("s2", ALPINE, r.best(ALPINE, 3).entries()));
        assertEquals(DovRoundLines.THANKS, r.talk("dov"));
        assertTrue(r.quest().complete());
        assertEquals(DovRoundLines.DONE, r.talk("after"));
        assertEquals("q_harbour_round", HarbourRound.QUEST_ID);
    }

    @Test
    void songSchoolGraduatesKnowASweetRound() {
        for (long seed = 0; seed < 6; seed++) {
            SongSchool s = new SongSchool(SongSchool.thirteenSongs(tunes),
                    SongSchool.fromFarIslands(Destination.island(), seed), seed);
            for (int day = 0; day < 200 && s.graduates().size() < SongSchool.GRADUATES_NEEDED; day++) {
                teach(s);
            }
            HarbourRound r = HarbourRound.fromSchool(s, tunes);
            assertFalse(r.known().contains(ThirteenthSong.RECORD), "record thirteen has no fixed notes");
            for (String g : s.graduates()) {
                s.songsFor(g).stream().filter(x -> !x.equals(ThirteenthSong.RECORD))
                        .forEach(x -> assertTrue(r.known().contains(x)));
            }
            assertTrue(r.known().stream().anyMatch(x -> r.best(x, HarbourRound.HARBOUR_VOICES).harmony()
                    >= HarbourRound.SWEET), "seed " + seed);
        }
    }

    static void teach(SongSchool s) {
        int n = 0;
        for (SongSchool.Card c : s.dueToday()) {
            if (s.lessonsLeft() == 0) {
                break;
            }
            s.review("d" + s.day() + "r" + n++, c.pupil(), c.song());
        }
        for (Pupil p : s.pupils()) {
            for (String song : s.songsFor(p.id())) {
                if (s.lessonsLeft() > 0 && s.card(p.id(), song) == null) {
                    s.introduce("d" + s.day() + "i" + n++, p.id(), song);
                }
            }
        }
        s.nextDay();
    }
}
