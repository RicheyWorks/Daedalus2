// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.cellar;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.BrewBench;
import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.MelodyBrew;
import com.daedalus.world.brew.PitchTable;
import com.daedalus.world.brew.cellar.Preserve.Method;
import com.daedalus.world.brew.exchange.RecordExchange;
import com.daedalus.world.brew.exchange.Trader;
import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.brew.story.SpringChain;
import com.daedalus.world.brew.week.Larder;
import com.daedalus.world.colony.PlotState;
import java.nio.charset.StandardCharsets;
import java.util.List;
import org.junit.jupiter.api.Test;

class RootCellarTest {
    final PlotState plot = new PlotState();

    @Test
    void shelfLivesAndCosts() {
        assertEquals(2, Preserve.shelfDays("fish", Method.FRESH));
        assertEquals(40, Preserve.shelfDays("fish", Method.SALT));
        assertEquals(20, Preserve.shelfDays("fish", Method.SMOKE));
        assertEquals(25, Preserve.shelfDays("Egg", Method.PICKLE));
        assertEquals(0, Preserve.shelfDays("Egg", Method.SALT));
        assertEquals(Preserve.HERB_DRIED, Preserve.shelfDays("Fasage", Method.DRY));
        assertEquals(Preserve.HERB_FRESH, Preserve.shelfDays("fasage", Method.FRESH));
        assertEquals(0, Preserve.shelfDays("Fasage", Method.SALT));
        assertEquals(0, Preserve.shelfDays("Clover", Method.DRY));
        assertEquals(0, Preserve.shelfDays(null, Method.DRY));
        assertEquals(0, Preserve.shelfDays("fish", null));
        assertTrue(Preserve.isHerb("Gloryroot"));
        assertEquals(java.util.Map.of(Preserve.SALT, 1, BrewBench.WATER, 1), Preserve.cost(Method.PICKLE));
        assertEquals(java.util.Map.of(Preserve.SALT, 1), Preserve.cost(Method.SALT));
        assertTrue(Preserve.cost(Method.SMOKE).isEmpty());
        assertEquals(2, Preserve.perDay(Method.SMOKE));
        assertEquals(3, Preserve.perDay(Method.DRY));
        assertEquals(0, Preserve.perDay(Method.SALT));
    }

    @Test
    void saltPanAndPreserveGuards() {
        RootCellar c = new RootCellar(5, 10);
        assertEquals(RootCellar.Outcome.NO_FOOD, c.preserve("a", "fish", Method.SALT, plot));
        plot.add("fish", 4);
        assertEquals(RootCellar.Outcome.NO_SALT, c.preserve("b", "fish", Method.SALT, plot));
        assertEquals(RootCellar.Outcome.BOILED, c.boilSea("s1", plot));
        assertEquals(RootCellar.Outcome.BOILED, c.boilSea("s2", plot));
        assertEquals(RootCellar.Outcome.SALT_PAN_DONE, c.boilSea("s3", plot));
        assertEquals(RootCellar.Outcome.DUPLICATE, c.boilSea("s1", plot));
        assertEquals(2, plot.count(Preserve.SALT));
        assertEquals(RootCellar.Outcome.NOT_PRESERVABLE, c.preserve("c", "fish", Method.PICKLE, plot));
        plot.add("Egg", 1);
        assertEquals(RootCellar.Outcome.NO_WATER, c.preserve("d", "Egg", Method.PICKLE, plot));
        assertEquals(RootCellar.Outcome.STORED, c.preserve("e", "fish", Method.SALT, plot));
        assertEquals(1, plot.count(Preserve.SALT));
        assertEquals(3, plot.count("fish"));
        assertEquals(RootCellar.Outcome.DUPLICATE, c.preserve("e", "fish", Method.SALT, plot));
        assertEquals(RootCellar.Outcome.STORED, c.preserve("f", "fish", Method.SMOKE, plot));
        assertEquals(RootCellar.Outcome.STORED, c.preserve("g", "fish", Method.SMOKE, plot));
        assertEquals(RootCellar.Outcome.RACK_FULL, c.preserve("h", "fish", Method.SMOKE, plot));
        assertEquals(RootCellar.Outcome.IGNORED, c.preserve("", "fish", Method.SMOKE, plot));
        assertEquals(RootCellar.Outcome.IGNORED, c.preserve("i", "fish", Method.SMOKE, null));
        c.nextDay(plot);
        assertEquals(RootCellar.Outcome.STORED, c.preserve("j", "fish", Method.SMOKE, plot));
        assertEquals(RootCellar.Outcome.BOILED, c.boilSea("s4", plot));
        assertEquals(4, c.jars().size());
        assertThrows(IllegalArgumentException.class, () -> new RootCellar(1, 0));
    }

    @Test
    void cellarHoldsTwelveJars() {
        RootCellar c = new RootCellar(1, 10);
        plot.add("Groat", 13);
        for (int i = 0; i < RootCellar.CAPACITY; i++) {
            assertEquals(RootCellar.Outcome.STORED, c.preserve("g" + i, "Groat", Method.FRESH, plot));
        }
        assertEquals(RootCellar.Outcome.CELLAR_FULL, c.preserve("g12", "Groat", Method.FRESH, plot));
        assertEquals(1, plot.count("Groat"));
        assertEquals(RootCellar.Outcome.NO_JAR, c.take("t0", 99, plot));
        assertEquals(RootCellar.Outcome.TAKEN, c.take("t1", c.jars().get(0).id(), plot));
        assertEquals(RootCellar.Outcome.STORED, c.preserve("g13", "Groat", Method.FRESH, plot));
    }

    @Test
    void badSealsAreSeededHalveLifeAndSpoiledJarsBecomeCompost() {
        int bad = 0;
        for (long s = 0; s < 400; s++) {
            RootCellar a = new RootCellar(s, 10);
            RootCellar b = new RootCellar(s, 10);
            PlotState pa = new PlotState();
            PlotState pb = new PlotState();
            pa.add("fish", 1);
            pb.add("fish", 1);
            a.preserve("x", "fish", Method.FRESH, pa);
            b.preserve("x", "fish", Method.FRESH, pb);
            RootCellar.Jar ja = a.jars().get(0);
            assertEquals(ja, b.jars().get(0));
            assertEquals(ja.badSeal() ? 1 : 2, ja.goodUntil());
            bad += ja.badSeal() ? 1 : 0;
        }
        assertTrue(bad > 15 && bad < 70, "about 10% bad seals, got " + bad);

        RootCellar c = new RootCellar(3, 10);
        plot.add("fish", 1);
        plot.add("Spudlet", 1);
        c.preserve("f", "fish", Method.FRESH, plot);
        c.preserve("p", "Spudlet", Method.FRESH, plot);
        RootCellar.Jar fish = c.firstJarOf("fish");
        assertNotNull(fish);
        assertNull(c.firstJarOf("Egg"));
        int spoiledBy = fish.goodUntil() + 1;
        while (c.day() < spoiledBy - 1) {
            assertTrue(c.nextDay(plot).isEmpty());
        }
        List<RootCellar.Jar> gone = c.nextDay(plot);
        assertEquals(List.of(fish), gone);
        assertEquals(1, plot.count(RootCellar.COMPOST));
        assertEquals(1, c.jars().size());
    }

    @Test
    void saltedFoodMustBeSoakedInCleanWater() {
        RootCellar c = new RootCellar(2, 10);
        plot.add("Bacon", 1);
        plot.add(Preserve.SALT, 1);
        c.preserve("s", "Bacon", Method.SALT, plot);
        int id = c.firstJarOf("Bacon").id();
        assertEquals(RootCellar.Outcome.NO_WATER, c.take("t1", id, plot));
        assertEquals(0, plot.count("Bacon"));
        plot.add(BrewBench.WATER, 1);
        assertEquals(RootCellar.Outcome.TAKEN, c.take("t2", id, plot));
        assertEquals(1, plot.count("Bacon"));
        assertEquals(0, plot.count(BrewBench.WATER));
        assertTrue(c.jars().isEmpty());
    }

    @Test
    void questThreeMethodsEightJarsFiveDarkDaysThenBrine() {
        RootCellar c = new RootCellar(7, 3);
        assertEquals(BrineLines.GREETING, c.talk("talk0"));
        plot.add("fish", 3);
        plot.add("Moonbean", 1);
        plot.add("Groat", 8);
        plot.add(Preserve.SALT, 1);
        assertEquals(RootCellar.Outcome.STORED, c.preserve("m1", "fish", Method.SALT, plot));
        assertEquals(RootCellar.Outcome.STORED, c.preserve("m1b", "fish", Method.SMOKE, plot));
        assertEquals(String.format(BrineLines.METHODS, 2, "s"), c.talk("talk1"));
        assertEquals(RootCellar.Outcome.STORED, c.preserve("m2", "fish", Method.SMOKE, plot));
        assertEquals(2, c.quest().stepCount(), "same method twice counts once");
        assertEquals(RootCellar.Outcome.STORED, c.preserve("m3", "Moonbean", Method.DRY, plot));
        assertEquals(1, c.quest().stepIndex());
        assertEquals(1, c.quest().stepCount(), "the third method's jar is the first of the eight");
        for (int i = 0; i < 7; i++) {
            c.preserve("g" + i, "Groat", Method.FRESH, plot);
        }
        assertEquals(2, c.quest().stepIndex());
        assertEquals(String.format(BrineLines.WAIT, 2, "s"), c.talk("talk2"));
        c.nextDay(plot);
        c.nextDay(plot);
        assertTrue(c.isDark());
        assertEquals(0, c.daysUntilDark());
        assertEquals(String.format(BrineLines.DARK, 1), c.talk("talk3"));
        c.nextDay(plot);
        assertEquals(0, c.quest().stepCount(), "a dark day without opening a jar does not count");
        for (int d = 0; d < RootCellar.DARK_DAYS - 1; d++) {
            assertEquals(RootCellar.Outcome.TAKEN, c.take("eat" + d, c.firstJarOf("Groat").id(), plot));
            c.nextDay(plot);
        }
        assertTrue(c.darkOver());
        assertFalse(c.isDark());
        assertEquals(4, c.quest().stepCount());
        assertEquals(BrineLines.MISSED, c.talk("talk4"));

        RootCellar ok = new RootCellar(7, 2);
        PlotState p = new PlotState();
        p.add("fish", 3);
        p.add("Moonbean", 1);
        p.add("Groat", 12);
        p.add(Preserve.SALT, 1);
        ok.preserve("a", "fish", Method.SALT, p);
        ok.preserve("b", "fish", Method.SMOKE, p);
        ok.preserve("c", "Moonbean", Method.DRY, p);
        for (int i = 0; i < 7; i++) {
            ok.preserve("g" + i, "Groat", Method.FRESH, p);
        }
        ok.nextDay(p);
        for (int d = 0; d < RootCellar.DARK_DAYS; d++) {
            ok.take("eat" + d, ok.firstJarOf("Groat").id(), p);
            ok.nextDay(p);
        }
        assertEquals(3, ok.quest().stepIndex());
        assertEquals(BrineLines.THANKS, ok.talk("brine"));
        assertTrue(ok.quest().complete());
        assertTrue(ok.quest().claimReward());
        assertEquals(BrineLines.DONE, ok.talk("after"));
        assertEquals(RootCellar.QUEST_ID, "q_root_cellar");
    }

    @Test
    void eggsFromTheExchangeArePickledAndCookedInTheLongDark() throws Exception {
        List<FoundTune> tunes;
        try (var in = getClass().getResourceAsStream("/com/daedalus/world/brew/found_tunes.csv")) {
            tunes = FoundTune.parseCsv(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        }
        SeedSongSpring songs = new SeedSongSpring(new BrewBench(PitchTable.ISLAND_CANON, tunes), tunes,
                SpringChain.island(), 9);
        RecordExchange x = new RecordExchange(songs, tunes, Trader.island(), 9);
        FoundTune t = tunes.get(0);
        plot.add(t.learnedFrom(), 1);
        t.herbs().forEach(h -> plot.add(h, 1));
        assertEquals(SeedSongSpring.Outcome.RESTORED, songs.restore("mend", t.learnedFrom(),
                t.herbs().stream().map(h -> new MelodyBrew.Ingredient(h, 3)).toList(), plot).outcome());
        x.press("press", t.learnedFrom(), plot);
        assertEquals(RecordExchange.Outcome.TRADED, x.trade("trade", "mora", t.learnedFrom(), plot).outcome());
        assertTrue(plot.count("Egg") >= 2);

        RootCellar c = new RootCellar(9, 2);
        plot.add(BrewBench.WATER, 2);
        c.boilSea("s1", plot);
        c.boilSea("s2", plot);
        assertEquals(RootCellar.Outcome.STORED, c.preserve("e1", "Egg", Method.PICKLE, plot));
        assertEquals(RootCellar.Outcome.STORED, c.preserve("e2", "Egg", Method.PICKLE, plot));
        plot.add("Fasage", 1);
        assertEquals(RootCellar.Outcome.STORED, c.preserve("h", "Fasage", Method.DRY, plot));
        plot.take("Egg", plot.count("Egg"));
        c.nextDay(plot);
        assertTrue(c.isDark());
        assertFalse(Larder.cook("Omelet", plot), "nothing fresh in the Long Dark");
        for (String item : List.of("Egg", "Egg", "Fasage")) {
            assertEquals(RootCellar.Outcome.TAKEN, c.take("open-" + plot.count(item) + item,
                    c.firstJarOf(item).id(), plot));
        }
        assertTrue(Larder.cook("Omelet", plot));
        assertEquals(1, plot.count(Larder.cooked("Omelet")));
        c.nextDay(plot);
        assertEquals(0, c.quest().stepIndex());
        assertEquals(2, c.quest().stepCount(), "pickle and dry are two of the three ways");
    }
}
