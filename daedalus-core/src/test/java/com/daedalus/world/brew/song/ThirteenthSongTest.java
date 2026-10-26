// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.song;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.BrewBench;
import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.PitchTable;
import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.brew.story.SpringChain;
import com.daedalus.world.brew.supper.Guest;
import com.daedalus.world.brew.supper.HomecomingSupper;
import com.daedalus.world.colony.PlotState;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class ThirteenthSongTest {
    List<FoundTune> tunes;
    SeedSongSpring songs;
    HomecomingSupper supper;
    ThirteenthSong s;
    PlotState plot;

    @BeforeEach
    void setUp() throws Exception {
        try (var in = getClass().getResourceAsStream("/com/daedalus/world/brew/found_tunes.csv")) {
            tunes = FoundTune.parseCsv(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        }
        songs = new SeedSongSpring(new BrewBench(PitchTable.ISLAND_CANON, tunes), tunes, SpringChain.island(), 9);
        supper = new HomecomingSupper(songs, tunes, Guest.island(), 11);
        s = new ThirteenthSong(supper, tunes, 4);
        plot = new PlotState();
    }

    void gatherAll(ThirteenthSong x) {
        for (Verse v : x.offers()) {
            if (!x.gathered().contains(v)) {
                assertEquals(ThirteenthSong.Outcome.GATHERED, x.ask("ask-" + v.guestId(), v.guestId()));
            }
        }
    }

    @Test
    void herbsFollowTheIslandCanon() {
        for (int i = 0; i < 12; i++) {
            assertEquals(i, PitchTable.ISLAND_CANON.pitchOf(ThirteenthSong.HERBS.get(i)).orElseThrow());
        }
        assertEquals(List.of("Doleaf", "Mimint", "Solthorn", "Doleaf"), ThirteenthSong.herbsFor(List.of(4, 3, 5)));
        assertEquals(List.of(4, 3, -5), ThirteenthSong.steps(List.of(0, 4, 7, 2)));
    }

    @Test
    void eachGuestOffersAStepFromTheirFavouriteRecord() {
        Map<String, FoundTune> byRecord = tunes.stream().collect(Collectors.toMap(FoundTune::learnedFrom, t -> t));
        assertEquals(9, s.offers().size());
        ThirteenthSong again = new ThirteenthSong(supper, tunes, 4);
        assertEquals(s.offers(), again.offers());
        for (Verse v : s.offers()) {
            assertEquals(supper.favouriteTune(v.guestId()), v.fromRecord());
            assertTrue(ThirteenthSong.steps(byRecord.get(v.fromRecord()).notes()).contains(v.step()));
            assertTrue(v.step() != 0);
        }
    }

    @Test
    void withEveryVerseASongAlwaysExists() {
        for (long seed = 0; seed < 150; seed++) {
            HomecomingSupper sup = new HomecomingSupper(songs, tunes, Guest.island(), seed);
            ThirteenthSong x = new ThirteenthSong(sup, tunes, seed * 3 + 1);
            gatherAll(x);
            List<String> h = x.hint();
            assertNotNull(h, "seed " + seed);
            assertEquals(ThirteenthSong.Outcome.COMPOSED, x.check(h));
            assertEquals(ThirteenthSong.Outcome.COMPOSED, x.compose("c", h));
            assertEquals(h.get(0), h.get(h.size() - 1));
        }
    }

    @Test
    void theRulesOfTheSong() {
        assertEquals(TamsinLines.GREETING, s.talk("t0", plot));
        assertEquals(ThirteenthSong.Outcome.UNKNOWN_GUEST, s.ask("a0", "nobody"));
        Verse first = s.offers().get(0);
        assertEquals(ThirteenthSong.Outcome.GATHERED, s.ask("a1", first.guestId()));
        assertEquals(ThirteenthSong.Outcome.ALREADY_GATHERED, s.ask("a2", first.guestId()));
        assertEquals(ThirteenthSong.Outcome.DUPLICATE, s.ask("a1", first.guestId()));
        assertEquals(ThirteenthSong.Outcome.IGNORED, s.ask("", first.guestId()));
        assertEquals(String.format(TamsinLines.GATHER, 4, "s"), s.talk("t1", plot));
        assertEquals(ThirteenthSong.Outcome.NOT_GATHERED, s.compose("c0", List.of("Doleaf", "Mimint", "Solthorn",
                "Doleaf")));

        assertEquals(ThirteenthSong.Outcome.WRONG_LENGTH, s.check(List.of("Doleaf", "Mimint", "Doleaf")));
        assertEquals(ThirteenthSong.Outcome.WRONG_LENGTH, s.check(null));
        assertEquals(ThirteenthSong.Outcome.UNKNOWN_HERB, s.check(List.of("Doleaf", "Clover", "Mimint", "Doleaf")));
        assertEquals(ThirteenthSong.Outcome.NO_HOME, s.check(List.of("Doleaf", "Mimint", "Solthorn", "Lavine")));
        FoundTune ark = tunes.stream().filter(t -> t.notes().get(0).equals(t.notes().get(t.notes().size() - 1)))
                .findFirst().orElseThrow();
        assertEquals(ThirteenthSong.Outcome.NOT_NEW, s.check(ark.herbs()));
        List<String> transposed = ark.notes().stream().map(n -> ThirteenthSong.HERBS.get((n + 5) % 12)).toList();
        assertEquals(ThirteenthSong.Outcome.NOT_NEW, s.check(transposed), "an ark tune in a new key is not new");
        assertEquals(ThirteenthSong.Outcome.NOT_OFFERED, s.check(List.of("Doleaf", "Doleaf", "Mimint", "Doleaf")));

        gatherAll(s);
        List<String> h = s.hint();
        List<Integer> steps = ThirteenthSong.steps(h.stream()
                .map(x -> PitchTable.ISLAND_CANON.pitchOf(x).orElseThrow()).toList());
        long uses = s.gathered().stream().filter(v -> v.step() == steps.get(0)).count();
        long need = steps.stream().filter(x -> x.equals(steps.get(0))).count();
        assertTrue(uses >= need, "each step uses a different verse");
    }

    @Test
    void questGatherComposeBrewThenTamsinPressesRecordThirteen() {
        assertNull(s.brew("early", plot));
        gatherAll(s);
        assertTrue(s.quest().stepIndex() >= 1);
        assertEquals(TamsinLines.COMPOSE, s.talk("t1", plot));
        List<String> h = s.hint();
        assertEquals(ThirteenthSong.Outcome.COMPOSED, s.compose("compose", h));
        assertEquals(ThirteenthSong.Outcome.ALREADY_COMPOSED, s.compose("again", h));
        FoundTune song = s.song();
        assertEquals(ThirteenthSong.RECORD, song.learnedFrom());
        assertEquals(h, song.herbs());
        assertTrue(song.baseMelody().endsWith("Cadence"));
        assertEquals(TamsinLines.BREW, s.talk("t2", plot));

        assertEquals(BrewBench.Outcome.MISSING_HERBS, s.brew("b0", plot).outcome());
        assertFalse(s.brewed());
        h.forEach(x -> plot.add(x, 1));
        plot.add(BrewBench.RAW_WATER, 3);
        BrewBench.Brew b = s.brew("b1", plot);
        assertEquals(BrewBench.Outcome.BREWED, b.outcome());
        assertEquals(ThirteenthSong.TONIC, b.item());
        assertEquals(song, b.tune());
        assertEquals(1, plot.count(ThirteenthSong.TONIC));
        assertEquals(3, b.purified(), "the island's song comes home, so it purifies water like the ark tunes");
        assertNull(s.brew("b2", plot));

        assertEquals(TamsinLines.THANKS, s.talk("tamsin", plot));
        assertEquals(1, plot.count(ThirteenthSong.RECORD));
        assertTrue(s.quest().complete());
        assertTrue(s.quest().claimReward());
        assertEquals(TamsinLines.DONE, s.talk("after", plot));
        assertEquals(1, plot.count(ThirteenthSong.RECORD));
        assertEquals("q_thirteenth_song", ThirteenthSong.QUEST_ID);
    }

    @Test
    void recordThirteenPlaysAtAnyBenchThatHasItLikeAnArkRecord() {
        gatherAll(s);
        s.compose("c", s.hint());
        List<FoundTune> all = new java.util.ArrayList<>(tunes);
        all.add(s.song());
        BrewBench bench = new BrewBench(PitchTable.ISLAND_CANON, all);
        assertEquals(s.song(), bench.playRecord(ThirteenthSong.RECORD));
        s.song().herbs().forEach(x -> plot.add(x, 1));
        var b = bench.brew("home", s.song().herbs().stream()
                .map(x -> new com.daedalus.world.brew.MelodyBrew.Ingredient(x, 2)).toList(), plot);
        assertEquals(ThirteenthSong.TONIC, b.item());
        assertEquals(13, all.stream().map(FoundTune::learnedFrom).distinct().count());
    }
}
