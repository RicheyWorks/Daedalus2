// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.concert;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.concert.GraduationConcert.Outcome;
import com.daedalus.world.brew.concert.GraduationConcert.Slot;
import com.daedalus.world.brew.letters.Destination;
import com.daedalus.world.brew.school.Pupil;
import com.daedalus.world.brew.school.SongSchool;
import com.daedalus.world.brew.song.ThirteenthSong;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class GraduationConcertTest {
    List<FoundTune> tunes;

    @BeforeEach
    void setUp() throws Exception {
        try (var in = getClass().getResourceAsStream("/com/daedalus/world/brew/found_tunes.csv")) {
            tunes = FoundTune.parseCsv(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        }
    }

    /** Three graduates: keys C F# E / G D / F A; the choir closes in C. */
    static GraduationConcert small() {
        Map<String, List<String>> rep = new LinkedHashMap<>();
        rep.put("ana", List.of("s0", "s6", "s4"));
        rep.put("ben", List.of("s7", "s2"));
        rep.put("cal", List.of("s5", "s9"));
        Map<String, Integer> keys = Map.of("s0", 0, "s6", 6, "s4", 4, "s7", 7, "s2", 2, "s5", 5, "s9", 9, "home", 0);
        return new GraduationConcert(rep, keys, "home");
    }

    /** Every legal running order, by brute force (independent of the solver). */
    static List<List<Slot>> allSets(GraduationConcert c, int closerKey, String closer) {
        List<Slot> pool = new ArrayList<>();
        List<List<Slot>> out = new ArrayList<>();
        c.repertoire().forEach((g, songs) -> songs.forEach(s -> pool.add(new Slot(g, s, -1))));
        walk(c, pool, new ArrayList<>(), out, closerKey, closer);
        return out;
    }

    static void walk(GraduationConcert c, List<Slot> pool, List<Slot> order, List<List<Slot>> out, int ck, String closer) {
        if (order.size() == GraduationConcert.SOLOS) {
            Set<String> who = new HashSet<>();
            order.forEach(s -> who.add(s.singer()));
            if (who.size() == c.repertoire().size()) {
                List<Slot> full = new ArrayList<>(order);
                full.add(new Slot(GraduationConcert.CHOIR, closer, ck));
                out.add(full);
            }
            return;
        }
        for (Slot s : pool) {
            boolean used = order.stream().anyMatch(o -> o.song().equals(s.song()));
            boolean same = !order.isEmpty() && order.get(order.size() - 1).singer().equals(s.singer());
            if (!used && !same) {
                order.add(new Slot(s.singer(), s.song(), KEYS.apply(c, s.song())));
                walk(c, pool, order, out, ck, closer);
                order.remove(order.size() - 1);
            }
        }
    }

    interface KeyFn {
        int apply(GraduationConcert c, String song);
    }

    static final Map<String, Integer> SMALL_KEYS = Map.of("s0", 0, "s6", 6, "s4", 4, "s7", 7, "s2", 2, "s5", 5, "s9", 9);
    static Map<String, Integer> tuneKeys = new LinkedHashMap<>();
    static final KeyFn KEYS = (c, song) -> SMALL_KEYS.containsKey(song) ? SMALL_KEYS.get(song) : tuneKeys.get(song);

    @Test
    void keysSitOnTheCircleOfFifths() {
        assertEquals(0, GraduationConcert.fifths(4, 4));
        assertEquals(1, GraduationConcert.fifths(0, 7));
        assertEquals(1, GraduationConcert.fifths(7, 0));
        assertEquals(1, GraduationConcert.fifths(0, 5));
        assertEquals(2, GraduationConcert.fifths(0, 2));
        assertEquals(5, GraduationConcert.fifths(0, 1));
        assertEquals(6, GraduationConcert.fifths(0, 6));
        for (int a = 0; a < 12; a++) {
            for (int b = 0; b < 12; b++) {
                assertEquals(GraduationConcert.fifths(a, b), GraduationConcert.fifths(b, a));
                assertTrue(GraduationConcert.fifths(a, b) <= 6);
            }
        }
        Map<String, Integer> keys = GraduationConcert.keysOf(tunes, 14);
        assertEquals(13, keys.size());
        assertEquals(7, keys.get("Item_YTM_Record_AmericanOldTime"));
        assertEquals(0, keys.get("Item_YTM_Record_Alpine"));
        assertEquals(2, keys.get(ThirteenthSong.RECORD));
    }

    @Test
    void solverFindsTheSmoothestLegalSet() {
        GraduationConcert c = small();
        List<List<Slot>> all = allSets(c, 0, "home");
        int min = all.stream().mapToInt(GraduationConcert::cost).min().orElseThrow();
        assertEquals(min, c.best());
        assertEquals(c.best(), GraduationConcert.cost(c.bestSet()));
        assertEquals(GraduationConcert.SOLOS + 1, c.bestSet().size());
        assertTrue(all.stream().anyMatch(s -> s.equals(c.bestSet())), "the best set is legal");
        assertThrows(IllegalArgumentException.class, () -> new GraduationConcert(Map.of("solo", List.of("s0")),
                Map.of("s0", 0, "home", 0), "home"));
        assertThrows(IllegalArgumentException.class, () -> new GraduationConcert(
                Map.of("a", List.of("s0"), "b", List.of("s7")), Map.of("s0", 0, "s7", 7, "home", 0), "home"),
                "two songs cannot fill five solos");
        assertThrows(IllegalArgumentException.class, () -> new GraduationConcert(
                Map.of("a", List.of("x"), "b", List.of("s7")), Map.of("s7", 7, "home", 0), "home"));
    }

    @Test
    void setListRules() {
        GraduationConcert c = small();
        assertEquals(ConcertLines.GREETING, c.talk("t0"));
        assertEquals(Outcome.IGNORED, c.perform(" ", "ana", "s0"));
        assertEquals(Outcome.NOT_GRADUATE, c.perform("e0", "dov", "s0"));
        assertEquals(Outcome.UNKNOWN_SONG, c.perform("e1", "ana", "nope"));
        assertEquals(Outcome.NOT_THEIRS, c.perform("e2", "ana", "s7"));
        assertEquals(Outcome.NOT_READY, c.close("early"));
        assertEquals(Outcome.SUNG, c.perform("p1", "ana", "s0"));
        assertEquals(Outcome.DUPLICATE, c.perform("p1", "ben", "s7"));
        assertEquals(Outcome.SAME_SINGER, c.perform("p2", "ana", "s6"));
        assertEquals(Outcome.SUNG, c.perform("p2", "ben", "s7"));
        assertEquals(Outcome.SUNG, c.perform("p3", "ana", "s6"));
        assertEquals(Outcome.SUNG, c.perform("p4", "ben", "s2"));
        assertEquals(Outcome.LEAVES_SOMEONE_OUT, c.perform("p5", "ana", "s4"), "cal has not sung yet");
        assertEquals(12 - (1 + 5 + 4), c.warmth(), "C-G 1, G-F# 5, F#-D 4");
        assertEquals(String.format(ConcertLines.WARMTH, 2, 1, ""), c.talk("t1"));
        assertEquals(Outcome.SUNG, c.perform("p5", "cal", "s5"));
        assertEquals(Outcome.SET_FULL, c.perform("p6", "ana", "s0"));
        assertEquals(ConcertLines.READY, c.talk("t2"));
        assertNull(c.result());
        assertEquals(Outcome.NOT_OVER, c.rerun());
    }

    @Test
    void roughConcertRerunsThenTheBestSetIsCheered() {
        GraduationConcert c = small();
        List<Slot> worst = allSets(c, 0, "home").stream()
                .max((a, b) -> Integer.compare(GraduationConcert.cost(a), GraduationConcert.cost(b))).orElseThrow();
        assertTrue(GraduationConcert.cost(worst) > c.best() + GraduationConcert.SLACK);
        int n = 0;
        for (Slot s : worst.subList(0, GraduationConcert.SOLOS)) {
            assertEquals(Outcome.SUNG, c.perform("w" + n++, s.singer(), s.song()));
        }
        assertEquals(Outcome.ROUGH, c.close("w-close"));
        assertEquals(ConcertLines.ROUGH, c.talk("t"));
        assertEquals(Outcome.OVER, c.perform("late", "ana", "s0"));
        assertEquals(1, c.quest().stepIndex(), "solos counted, no cheer yet");
        assertEquals(Outcome.RERUN, c.rerun());
        assertEquals(2, c.evening());
        for (Slot s : c.bestSet().subList(0, GraduationConcert.SOLOS)) {
            assertEquals(Outcome.SUNG, c.perform("b" + n++, s.singer(), s.song()));
        }
        assertEquals(Outcome.CHEERED, c.close("b-close"));
        assertEquals(c.bestSet(), c.setList());
        assertEquals(Outcome.OVER, c.rerun());
        assertEquals(ConcertLines.THANKS, c.talk("wick"));
        assertTrue(c.quest().complete());
        assertEquals(ConcertLines.DONE, c.talk("after"));
    }

    @Test
    void songSchoolGraduatesGiveTheConcert() {
        tuneKeys = GraduationConcert.keysOf(tunes, 0);
        for (long seed = 0; seed < 6; seed++) {
            SongSchool s = new SongSchool(SongSchool.thirteenSongs(tunes),
                    SongSchool.fromFarIslands(Destination.island(), seed), seed);
            for (int day = 0; day < 200 && s.graduates().size() < SongSchool.GRADUATES_NEEDED; day++) {
                teach(s);
            }
            GraduationConcert c = GraduationConcert.fromSchool(s, tunes, 0);
            assertEquals(s.graduates(), c.repertoire().keySet());
            int min = allSets(c, 0, ThirteenthSong.RECORD).stream().mapToInt(GraduationConcert::cost).min()
                    .orElseThrow();
            assertEquals(min, c.best(), "seed " + seed);
            assertEquals(ThirteenthSong.RECORD, c.bestSet().get(GraduationConcert.SOLOS).song());
            assertEquals(c.best(), GraduationConcert.fromSchool(s, tunes, 0).best());
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
