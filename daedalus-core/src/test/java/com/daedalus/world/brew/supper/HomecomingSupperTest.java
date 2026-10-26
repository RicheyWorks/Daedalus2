// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.supper;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.BrewBench;
import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.MelodyBrew;
import com.daedalus.world.brew.PitchTable;
import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.brew.story.SpringChain;
import com.daedalus.world.brew.week.Larder;
import com.daedalus.world.colony.PlotState;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class HomecomingSupperTest {
    List<FoundTune> tunes;
    SeedSongSpring songs;
    HomecomingSupper s;
    PlotState plot;

    void mend(String record) {
        FoundTune t = tunes.stream().filter(x -> x.learnedFrom().equals(record)).findFirst().orElseThrow();
        if (songs.isRestored(record)) {
            return;
        }
        plot.add(record, 1);
        t.herbs().forEach(h -> plot.add(h, 1));
        assertEquals(SeedSongSpring.Outcome.RESTORED, songs.restore("mend-" + record, record,
                t.herbs().stream().map(h -> new MelodyBrew.Ingredient(h, 3)).toList(), plot).outcome());
    }

    /** Cooks a larder recipe (G62) from bought-in ingredients. */
    String cook(String recipe) {
        for (String i : Larder.RECIPES.get(recipe)) {
            plot.add(i.equals(Larder.CLEAN_WATER) ? BrewBench.WATER : i, 1);
        }
        assertTrue(Larder.cook(recipe, plot));
        return Larder.cooked(recipe);
    }

    @BeforeEach
    void setUp() throws Exception {
        try (var in = getClass().getResourceAsStream("/com/daedalus/world/brew/found_tunes.csv")) {
            tunes = FoundTune.parseCsv(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        }
        songs = new SeedSongSpring(new BrewBench(PitchTable.ISLAND_CANON, tunes), tunes, SpringChain.island(), 9);
        s = new HomecomingSupper(songs, tunes, Guest.island(), 11);
        plot = new PlotState();
    }

    @Test
    void nineGuestsFromEveryChapterWithSeededTastes() {
        assertEquals(9, s.guests().size());
        assertEquals(List.of("keeper_oriel", "archivist_tamsin", "mason_hale", "old_wick", "pell", "ida", "mora",
                "dov", "aunt_brine"), s.guests().stream().map(Guest::id).toList());
        HomecomingSupper again = new HomecomingSupper(songs, tunes, Guest.island(), 11);
        assertEquals(s.feuds(), again.feuds());
        assertEquals(s.friends(), again.friends());
        Set<String> records = new HashSet<>(tunes.stream().map(FoundTune::learnedFrom).toList());
        for (Guest g : s.guests()) {
            assertEquals(s.favouriteDish(g.id()), again.favouriteDish(g.id()));
            assertTrue(Larder.RECIPES.containsKey(s.favouriteDish(g.id())));
            assertTrue(records.contains(s.favouriteTune(g.id())));
        }
        assertEquals(HomecomingSupper.FEUDS, s.feuds().size());
        assertEquals(HomecomingSupper.FRIENDS, s.friends().size());
        s.friends().forEach(f -> assertFalse(s.feuds().contains(f)));
        assertThrows(IllegalArgumentException.class,
                () -> new HomecomingSupper(songs, tunes, Guest.island().subList(0, 4), 1));
    }

    @Test
    void aFeudFreeSeatingAlwaysExistsAndFeudsAreRefused() {
        for (long seed = 0; seed < 200; seed++) {
            HomecomingSupper x = new HomecomingSupper(songs, tunes, Guest.island(), seed);
            List<String> h = x.hint();
            assertEquals(9, new HashSet<>(h).size());
            for (int i = 1; i < h.size(); i++) {
                assertFalse(x.feuds().contains(Set.of(h.get(i - 1), h.get(i))));
            }
        }
        Set<String> feud = s.feuds().iterator().next();
        List<String> bad = new ArrayList<>(feud);
        s.guests().stream().map(Guest::id).filter(id -> !feud.contains(id)).forEach(bad::add);
        assertEquals(HomecomingSupper.Outcome.FEUD, s.seat("bad", bad));
        assertEquals(HomecomingSupper.Outcome.BAD_SEATING, s.seat("short", bad.subList(0, 8)));
        assertEquals(HomecomingSupper.Outcome.BAD_SEATING, s.seat("null", null));
        assertNull(s.seating());
        assertEquals(HomecomingSupper.Outcome.SEATED, s.seat("ok", s.hint()));
        assertEquals(HomecomingSupper.Outcome.ALREADY_SEATED, s.seat("again", s.hint()));
        assertEquals(HomecomingSupper.Outcome.DUPLICATE, s.seat("ok", s.hint()));
        assertEquals(HomecomingSupper.Outcome.IGNORED, s.seat("", s.hint()));
        assertTrue(HomecomingSupper.feudFreeSeating(List.of("a", "b", "c"),
                Set.of(Set.of("a", "b"), Set.of("b", "c"), Set.of("a", "c"))).isEmpty());
    }

    @Test
    void servingAndPlayingGuards() {
        String meal = cook("Omelet");
        assertEquals(HomecomingSupper.Outcome.NOT_SEATED, s.serve("s0", "pell", meal, plot));
        s.seat("seat", s.hint());
        assertEquals(HomecomingSupper.Outcome.UNKNOWN_GUEST, s.serve("s1", "nobody", meal, plot));
        assertEquals(HomecomingSupper.Outcome.NO_MEAL, s.serve("s2", "pell", "Item_YTM_Food_Rock", plot));
        assertEquals(HomecomingSupper.Outcome.NO_MEAL, s.serve("s3", "pell", Larder.cooked("Pie"), plot));
        assertEquals(HomecomingSupper.Outcome.IGNORED, s.serve("s4", "pell", meal, null));
        assertEquals(HomecomingSupper.Outcome.SERVED, s.serve("s5", "pell", meal, plot));
        assertEquals(0, plot.count(meal));
        assertEquals(HomecomingSupper.Outcome.ALREADY_SERVED, s.serve("s6", "pell", cook("Omelet"), plot));

        String r0 = tunes.get(0).learnedFrom();
        assertEquals(HomecomingSupper.Outcome.UNKNOWN_TUNE, s.play("p0", "Item_YTM_Record_Nope"));
        assertEquals(HomecomingSupper.Outcome.NOT_RESTORED, s.play("p1", r0));
        for (int i = 0; i < 4; i++) {
            mend(tunes.get(i).learnedFrom());
        }
        assertEquals(HomecomingSupper.Outcome.PLAYED, s.play("p2", r0));
        assertEquals(HomecomingSupper.Outcome.ALREADY_PLAYED, s.play("p3", r0));
        assertEquals(HomecomingSupper.Outcome.PLAYED, s.play("p4", tunes.get(1).learnedFrom()));
        assertEquals(HomecomingSupper.Outcome.PLAYED, s.play("p5", tunes.get(2).learnedFrom()));
        assertEquals(HomecomingSupper.Outcome.ALL_COURSES_PLAYED, s.play("p6", tunes.get(3).learnedFrom()));
        assertEquals(3, s.played().size());
    }

    @Test
    void contentmentAddsFriendsMealAndTune() {
        s.seat("seat", s.hint());
        for (Guest g : s.guests()) {
            int friendsBeside = (int) s.neighbours(g.id()).stream()
                    .filter(n -> s.friends().contains(Set.of(g.id(), n))).count();
            assertEquals(friendsBeside * HomecomingSupper.FRIEND_BONUS + HomecomingSupper.NO_MEAL,
                    s.contentment(g.id()));
        }
        String first = s.seating().get(0);
        String last = s.seating().get(8);
        assertEquals(1, s.neighbours(first).size(), "the host sits beside the first guest");
        assertEquals(1, s.neighbours(last).size());
        assertEquals(2, s.neighbours(s.seating().get(4)).size());

        String g = "dov";
        int before = s.contentment(g);
        s.serve("fav", g, cook(s.favouriteDish(g)), plot);
        assertEquals(before - HomecomingSupper.NO_MEAL + HomecomingSupper.FAVOURITE_MEAL, s.contentment(g));
        String other = Larder.RECIPES.keySet().stream().filter(r -> !r.equals(s.favouriteDish("mora")))
                .findFirst().orElseThrow();
        int moraBefore = s.contentment("mora");
        s.serve("other", "mora", cook(other), plot);
        assertEquals(moraBefore - HomecomingSupper.NO_MEAL + HomecomingSupper.OTHER_MEAL, s.contentment("mora"));
        int dovBefore = s.contentment(g);
        mend(s.favouriteTune(g));
        s.play("tune", s.favouriteTune(g));
        assertEquals(dovBefore + HomecomingSupper.FAVOURITE_TUNE, s.contentment(g));
        assertEquals(0, s.contentment("nobody"));
    }

    @Test
    void questSeatServePlayThenOrielNeedsAWarmSupper() {
        assertEquals(SupperLines.GREETING, s.talk("t0"));
        s.seat("seat", s.hint());
        assertEquals(String.format(SupperLines.SERVE, 9, "s"), s.talk("t1"));
        List<Guest> gs = s.guests();
        String plain = gs.stream().map(Guest::id).filter(id -> s.contentment(id) == HomecomingSupper.NO_MEAL)
                .findFirst().orElseThrow();
        for (Guest g : gs) {
            String dish = g.id().equals(plain)
                    ? Larder.RECIPES.keySet().stream().filter(r -> !r.equals(s.favouriteDish(plain))).findFirst()
                            .orElseThrow()
                    : s.favouriteDish(g.id());
            assertEquals(HomecomingSupper.Outcome.SERVED, s.serve("serve-" + g.id(), g.id(), cook(dish), plot));
        }
        assertEquals(String.format(SupperLines.PLAY, 3, "s"), s.talk("t2"));
        List<String> courses = new ArrayList<>();
        tunes.stream().map(FoundTune::learnedFrom).filter(r -> !r.equals(s.favouriteTune(plain)))
                .limit(HomecomingSupper.COURSES).forEach(courses::add);
        for (String r : courses) {
            mend(r);
            s.play("play-" + r, r);
        }
        assertEquals(3, s.quest().stepIndex());
        assertTrue(s.discontent().contains(plain));
        assertFalse(s.warm());
        assertTrue(s.talk("t3").startsWith(String.format(SupperLines.COLD, s.discontent().size(),
                s.discontent().size() == 1 ? "" : "s").substring(0, 8)));
        assertFalse(s.quest().complete());

        HomecomingSupper w = new HomecomingSupper(songs, tunes, Guest.island(), 11);
        w.seat("seat", w.hint());
        for (Guest g : w.guests()) {
            w.serve("serve-" + g.id(), g.id(), cook(w.favouriteDish(g.id())), plot);
        }
        for (String r : courses) {
            w.play("play-" + r, r);
        }
        assertTrue(w.warm());
        assertTrue(w.discontent().isEmpty());
        assertEquals(SupperLines.THANKS, w.talk("oriel"));
        assertTrue(w.quest().complete());
        assertTrue(w.quest().claimReward());
        assertEquals(SupperLines.DONE, w.talk("after"));
        assertEquals("q_homecoming_supper", HomecomingSupper.QUEST_ID);
    }
}
