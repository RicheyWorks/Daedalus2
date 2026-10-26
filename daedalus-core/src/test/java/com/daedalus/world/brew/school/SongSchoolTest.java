// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.school;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.letters.Destination;
import com.daedalus.world.brew.song.ThirteenthSong;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class SongSchoolTest {
    List<String> songs;

    @BeforeEach
    void setUp() throws Exception {
        try (var in = getClass().getResourceAsStream("/com/daedalus/world/brew/found_tunes.csv")) {
            List<FoundTune> tunes = FoundTune.parseCsv(new String(in.readAllBytes(), StandardCharsets.UTF_8));
            songs = SongSchool.thirteenSongs(tunes);
        }
    }

    SongSchool island(long seed) {
        return new SongSchool(songs, SongSchool.fromFarIslands(Destination.island(), seed), seed);
    }

    @Test
    void thirteenSongsAndAChildFromEachFarIsland() {
        assertEquals(13, new HashSet<>(songs).size());
        assertTrue(songs.contains(ThirteenthSong.RECORD));
        SongSchool s = island(3);
        assertEquals(List.of("kelp_harbour", "cinder_reach", "glass_shoals", "far_orchard"),
                s.pupils().stream().map(Pupil::home).toList());
        for (Pupil p : s.pupils()) {
            assertTrue(p.aptitude() >= 0.60 && p.aptitude() <= 0.95);
            assertEquals(SongSchool.SONGS_EACH, new HashSet<>(s.songsFor(p.id())).size());
            assertTrue(songs.containsAll(s.songsFor(p.id())));
            assertEquals(s.songsFor(p.id()), island(3).songsFor(p.id()));
        }
        assertEquals(s.pupils(), island(3).pupils());
        assertThrows(IllegalArgumentException.class, () -> new Pupil("x", "x", "h", 1.5));
        assertThrows(IllegalArgumentException.class, () -> new SongSchool(songs.subList(0, 3), List.of(), 1));
    }

    @Test
    void leitnerBoxesClimbOnTimeAndAMissGoesBackToBoxOne() {
        SongSchool s = new SongSchool(songs, List.of(new Pupil("ace", "Ace", "kelp_harbour", 1.0),
                new Pupil("dud", "Dud", "kelp_harbour", 0.0)), 5);
        String song = s.songsFor("ace").get(0);
        assertEquals(SongSchool.Outcome.INTRODUCED, s.introduce("i", "ace", song));
        assertEquals(1, s.card("ace", song).box());
        assertEquals(2, s.card("ace", song).due());
        assertEquals(SongSchool.Outcome.TOO_SOON, s.review("r0", "ace", song));
        int[] reviewDays = {2, 4, 8, 16};
        for (int i = 0; i < reviewDays.length; i++) {
            while (s.day() < reviewDays[i]) {
                s.nextDay();
            }
            assertEquals(SongSchool.Outcome.REMEMBERED, s.review("r" + reviewDays[i], "ace", song));
            assertEquals(i + 2, s.card("ace", song).box());
        }
        assertEquals(SongSchool.TOP_BOX, s.card("ace", song).box());
        s.nextDay();
        assertEquals(SongSchool.Outcome.TOO_SOON, s.review("learned", "ace", song), "a learned song leaves the shelf");
        assertTrue(s.dueToday().isEmpty());

        String dsong = s.songsFor("dud").get(0);
        s.introduce("di", "dud", dsong);
        s.nextDay();
        assertEquals(SongSchool.Outcome.FORGOTTEN, s.review("dr", "dud", dsong));
        assertEquals(1, s.card("dud", dsong).box());
    }

    @Test
    void lateReviewsAreLessLikelyToStick() {
        SongSchool s = new SongSchool(songs, List.of(new Pupil("p", "P", "h", 0.8)), 1);
        String song = s.songsFor("p").get(0);
        s.introduce("i", "p", song);
        s.nextDay();
        SongSchool.Card c = s.card("p", song);
        assertEquals(0.8, s.recallChance(c), 1e-9);
        s.nextDay();
        s.nextDay();
        assertEquals(0.6, s.recallChance(c), 1e-9);
        for (int i = 0; i < 10; i++) {
            s.nextDay();
        }
        assertEquals(0.0, s.recallChance(c), 1e-9);
        assertEquals(List.of(c), s.dueToday());
    }

    @Test
    void sixLessonsADayAndGuards() {
        SongSchool s = island(4);
        Pupil a = s.pupils().get(0);
        Pupil b = s.pupils().get(1);
        String notSet = songs.stream().filter(x -> !s.songsFor(a.id()).contains(x)).findFirst().orElseThrow();
        assertEquals(SongSchool.Outcome.NOT_SET, s.introduce("x", a.id(), notSet));
        assertEquals(SongSchool.Outcome.UNKNOWN_PUPIL, s.introduce("y", "nobody", notSet));
        assertEquals(SongSchool.Outcome.NOT_INTRODUCED, s.review("z", a.id(), s.songsFor(a.id()).get(0)));
        assertEquals(SongSchool.Outcome.IGNORED, s.introduce("", a.id(), s.songsFor(a.id()).get(0)));
        int n = 0;
        for (Pupil p : List.of(a, b)) {
            for (String song : s.songsFor(p.id())) {
                SongSchool.Outcome o = s.introduce("i" + n++, p.id(), song);
                assertEquals(n <= SongSchool.LESSONS_PER_DAY ? SongSchool.Outcome.INTRODUCED
                        : SongSchool.Outcome.NO_LESSONS_LEFT, o);
            }
        }
        assertEquals(0, s.lessonsLeft());
        assertEquals(SongSchool.Outcome.DUPLICATE, s.introduce("i0", a.id(), s.songsFor(a.id()).get(0)));
        assertEquals(SongSchool.Outcome.ALREADY_INTRODUCED, s.introduce("again", a.id(), s.songsFor(a.id()).get(0)));
        s.nextDay();
        assertEquals(SongSchool.LESSONS_PER_DAY, s.lessonsLeft());
        assertEquals(6, s.dueToday().size());
    }

    /** Wick's plan: review what's due, most overdue first, then start new songs with the lessons left. */
    static void teachADay(SongSchool s) {
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

    @Test
    void questIntroduceGraduateThreeThenWick() {
        for (long seed = 0; seed < 20; seed++) {
            SongSchool s = island(seed);
            if (seed == 0) {
                assertEquals(WickSchoolLines.GREETING, s.talk("t0"));
            }
            int guard = 0;
            while (s.graduates().size() < SongSchool.GRADUATES_NEEDED && guard++ < 200) {
                teachADay(s);
                if (seed == 0 && guard == 1) {
                    assertEquals(String.format(WickSchoolLines.SHELF, 3, "s"), s.talk("t1"));
                }
            }
            assertTrue(s.graduates().size() >= SongSchool.GRADUATES_NEEDED, "seed " + seed);
            assertTrue(s.day() >= 16, "the top box takes at least 15 days");
            assertEquals(2, s.quest().stepIndex());
            assertEquals(WickSchoolLines.THANKS, s.talk("wick"));
            assertTrue(s.quest().complete());
            assertTrue(s.quest().claimReward());
            assertEquals(WickSchoolLines.DONE, s.talk("after"));
        }
        assertEquals("q_song_school", SongSchool.QUEST_ID);
    }
}
