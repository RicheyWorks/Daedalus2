// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.week;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.BrewBench;
import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.MelodyBrew;
import com.daedalus.world.brew.PitchTable;
import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.brew.story.SpringChain;
import com.daedalus.world.colony.PlotState;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;

class FirstWeekTest {
    PlotState plot = new PlotState();

    static String foodWaterJson() throws Exception {
        Path p = Path.of("..", "engines", "unreal", "ytm-island", "food_water.json");
        return Files.readString(p, StandardCharsets.UTF_8);
    }

    static int intAfter(String json, String regex) {
        Matcher m = Pattern.compile(regex).matcher(json);
        assertTrue(m.find(), regex);
        return Integer.parseInt(m.group(1));
    }

    /** Stocks and runs one ordinary day: two clean waters and one omelet (a note-herb meal). */
    void goodDay(FirstWeek w, int d) {
        plot.add(BrewBench.WATER, 2);
        plot.add("Egg", 2);
        plot.add("Fasage", 1);
        assertEquals(FirstWeek.Outcome.DRANK, w.drink("d" + d + "a", FirstWeek.Water.CLEAN, plot));
        assertEquals(FirstWeek.Outcome.DRANK, w.drink("d" + d + "b", FirstWeek.Water.CLEAN, plot));
        assertTrue(Larder.cook("Omelet", plot));
        assertEquals(FirstWeek.Outcome.ATE, w.eat("d" + d + "e", Larder.cooked("Omelet"), plot));
    }

    @Test
    void numbersMatchFoodWaterJson() throws Exception {
        String j = foodWaterJson();
        assertEquals(FirstWeek.MAX, intAfter(j, "\"thirst_max\":\\s*(\\d+)"));
        assertEquals(FirstWeek.START, intAfter(j, "\"start\":\\s*(\\d+)"));
        assertEquals(FirstWeek.CLEAN, intAfter(j, "\"clean\":\\s*\\{\\s*\"thirst\":\\s*(-?\\d+)"));
        assertEquals(FirstWeek.RAW, intAfter(j, "\"raw\":\\s*\\{\\s*\"thirst\":\\s*(-?\\d+)"));
        assertEquals(FirstWeek.SALT, intAfter(j, "\"salt\":\\s*\\{\\s*\"thirst\":\\s*(-?\\d+)"));
        assertTrue(Pattern.compile("\"sick_chance\":\\s*0\\.25").matcher(j).find());
        assertTrue(j.contains("cooked restores hunger 25-45"));
        for (var e : Larder.RECIPES.entrySet()) {
            StringBuilder re = new StringBuilder("\"" + e.getKey() + "\":\\s*\\[");
            for (int i = 0; i < e.getValue().size(); i++) {
                re.append(i == 0 ? "\\s*" : ",\\s*").append('"').append(e.getValue().get(i)).append('"');
            }
            re.append("\\s*\\]");
            assertTrue(Pattern.compile(re.toString()).matcher(j).find(), "recipe drift: " + e.getKey());
        }
    }

    @Test
    void theStoveTakesEverythingOrNothing() {
        assertEquals(25, Larder.restore("Porridge"));
        assertEquals(35, Larder.restore("Stew"));
        assertEquals(35, Larder.restore("Roast"), "Gloryroot is a note-herb");
        assertEquals(45, Larder.restore("Omelet"));
        assertEquals(45, Larder.restore("Salad"));
        assertEquals(0, Larder.restore("Cake"));
        assertNull(Larder.recipeOf("Item_YTM_Food_Cake_Cooked"));
        assertEquals("Bread", Larder.recipeOf(Larder.cooked("Bread")));
        plot.add("Groat", 2);
        assertFalse(Larder.cook("Bread", plot), "no clean water");
        assertEquals(2, plot.count("Groat"));
        plot.add(BrewBench.RAW_WATER, 1);
        assertFalse(Larder.cook("Bread", plot), "raw water is not clean_water");
        plot.add(BrewBench.WATER, 1);
        assertTrue(Larder.cook("Bread", plot));
        assertEquals(0, plot.count("Groat"));
        assertEquals(1, plot.count(Larder.cooked("Bread")));
        assertFalse(Larder.cook("Cake", plot));
        assertFalse(Larder.cook("Bread", null));
    }

    @Test
    void aWellKeptWeekIsSurvivedAndOldWickWelcomesYou() {
        FirstWeek w = new FirstWeek(1);
        assertEquals(WickLines.GREETING, w.talk("hello"));
        for (int d = 1; d <= FirstWeek.DAYS; d++) {
            goodDay(w, d);
            FirstWeek.Day day = w.endDay();
            assertTrue(day.survived(), "day " + d);
            assertEquals(FirstWeek.MAX, day.health());
            if (d < FirstWeek.DAYS) {
                assertEquals(String.format(WickLines.STEADY, d + 1), WickLines.line(w));
            }
        }
        assertTrue(w.over());
        assertFalse(w.lost());
        assertNull(w.endDay());
        assertEquals(FirstWeek.Outcome.OVER, w.drink("late", FirstWeek.Water.SALT, plot));
        assertEquals(WickLines.THANKS, w.talk("bye"));
        assertTrue(w.quest().complete());
        assertTrue(w.quest().claimReward());
        assertFalse(w.quest().claimReward());
    }

    @Test
    void goingWithoutWaterCostsHealthUntilTheWeekIsLost() {
        FirstWeek w = new FirstWeek(2);
        FirstWeek.Day d1 = w.endDay();
        assertEquals(20, d1.thirst());
        assertEquals(35, d1.hunger());
        assertEquals(FirstWeek.MAX, d1.health());
        assertEquals(WickLines.THIRSTY, WickLines.line(w));
        FirstWeek.Day d2 = w.endDay();
        assertEquals(0, d2.thirst());
        assertEquals(0, d2.hunger());
        assertEquals(FirstWeek.MAX - 2 * FirstWeek.HEALTH_HIT, d2.health());
        assertTrue(d2.survived());
        FirstWeek.Day d3 = w.endDay();
        assertFalse(d3.survived());
        assertTrue(w.lost());
        assertEquals(WickLines.LOST, w.talk("t"));
        assertEquals(2, w.quest().stepCount(), "only survived days count");
        assertNull(w.endDay());
    }

    @Test
    void rawWaterSicknessIsSeededAtAboutOneInFour() {
        int sick = 0;
        int trials = 800;
        for (int s = 0; s < trials; s++) {
            FirstWeek w = new FirstWeek(s);
            plot.add(BrewBench.RAW_WATER, 1);
            assertEquals(FirstWeek.Outcome.DRANK, w.drink("r", FirstWeek.Water.RAW, plot));
            assertEquals(FirstWeek.START + FirstWeek.RAW, w.thirst());
            if (w.sick()) {
                sick++;
                assertEquals(WickLines.SICK, WickLines.line(w));
                FirstWeek.Day d = w.endDay();
                assertTrue(d.sick());
                assertEquals(FirstWeek.START + FirstWeek.RAW - FirstWeek.THIRST_PER_DAY - FirstWeek.SICK_EXTRA, d.thirst());
                assertFalse(w.sick(), "sickness lasts the day");
            }
        }
        assertTrue(sick > trials * 0.18 && sick < trials * 0.32, "sick " + sick);
        FirstWeek a = new FirstWeek(99);
        FirstWeek b = new FirstWeek(99);
        plot.add(BrewBench.RAW_WATER, 2);
        a.drink("x", FirstWeek.Water.RAW, plot);
        b.drink("x", FirstWeek.Water.RAW, plot);
        assertEquals(a.sick(), b.sick());
    }

    @Test
    void theSeaMakesItWorseAndTheDesertTuneHalvesTheDrain() {
        FirstWeek w = new FirstWeek(3);
        assertEquals(FirstWeek.Outcome.DRANK, w.drink("salt", FirstWeek.Water.SALT, plot));
        assertEquals(FirstWeek.START + FirstWeek.SALT, w.thirst());
        assertEquals(FirstWeek.Outcome.NOTHING_TO_USE, w.tonic("t0", plot));
        plot.add(FirstWeek.DESERT_THIRST_TONIC, 2);
        assertEquals(FirstWeek.Outcome.TONIC, w.tonic("t1", plot));
        assertEquals(FirstWeek.Outcome.NOTHING_TO_USE, w.tonic("t2", plot), "once a day");
        FirstWeek.Day d = w.endDay();
        assertTrue(d.tonic());
        assertEquals(FirstWeek.START + FirstWeek.SALT - FirstWeek.THIRST_PER_DAY / 2, d.thirst());
        assertEquals(FirstWeek.Outcome.TONIC, w.tonic("t3", plot), "a new day");
        for (int i = 0; i < 20; i++) {
            plot.add(BrewBench.WATER, 1);
            w.drink("w" + i, FirstWeek.Water.CLEAN, plot);
        }
        assertEquals(FirstWeek.MAX, w.thirst(), "capped");
        for (int i = 0; i < 20; i++) {
            w.drink("s" + i, FirstWeek.Water.SALT, plot);
        }
        assertEquals(0, w.thirst(), "floored");
    }

    @Test
    void guards() {
        FirstWeek w = new FirstWeek(4);
        assertEquals(FirstWeek.Outcome.IGNORED, w.drink("", FirstWeek.Water.CLEAN, plot));
        assertEquals(FirstWeek.Outcome.IGNORED, w.drink("a", FirstWeek.Water.CLEAN, null));
        assertEquals(FirstWeek.Outcome.IGNORED, w.drink("a", null, plot));
        assertEquals(FirstWeek.Outcome.IGNORED, w.eat("x".repeat(129), "y", plot));
        assertEquals(FirstWeek.Outcome.NOTHING_TO_USE, w.drink("a", FirstWeek.Water.CLEAN, plot));
        assertEquals(FirstWeek.Outcome.NOTHING_TO_USE, w.drink("a2", FirstWeek.Water.RAW, plot));
        assertEquals(FirstWeek.Outcome.NOTHING_TO_USE, w.eat("b", Larder.cooked("Stew"), plot));
        assertEquals(FirstWeek.Outcome.NOTHING_TO_USE, w.eat("b2", "Item_YTM_Food_Cake_Cooked", plot));
        plot.add(BrewBench.WATER, 2);
        assertEquals(FirstWeek.Outcome.DRANK, w.drink("c", FirstWeek.Water.CLEAN, plot));
        assertEquals(FirstWeek.Outcome.DUPLICATE, w.drink("c", FirstWeek.Water.CLEAN, plot));
        assertEquals(FirstWeek.Outcome.DUPLICATE, w.eat("c", Larder.cooked("Stew"), plot));
        assertEquals(FirstWeek.Outcome.DUPLICATE, w.tonic("c", plot));
        assertEquals(1, plot.count(BrewBench.WATER));
        assertEquals(1, w.day());
        FirstWeek hungry = new FirstWeek(5);
        plot.add(BrewBench.WATER, 4);
        hungry.drink("h1", FirstWeek.Water.CLEAN, plot);
        hungry.drink("h2", FirstWeek.Water.CLEAN, plot);
        hungry.endDay();
        assertEquals(WickLines.STEADY.formatted(2), WickLines.line(hungry));
        hungry.drink("h3", FirstWeek.Water.CLEAN, plot);
        hungry.drink("h4", FirstWeek.Water.CLEAN, plot);
        hungry.endDay();
        assertEquals(WickLines.HUNGRY, WickLines.line(hungry));
    }

    @Test
    void theSpringsOfChapterTwoKeepYouAlive() throws Exception {
        List<FoundTune> tunes;
        try (var in = getClass().getResourceAsStream("/com/daedalus/world/brew/found_tunes.csv")) {
            tunes = FoundTune.parseCsv(new String(in.readAllBytes(), StandardCharsets.UTF_8));
        }
        SeedSongSpring springs = new SeedSongSpring(new BrewBench(PitchTable.ISLAND_CANON, tunes), tunes,
                SpringChain.island(), 6);
        FoundTune t = tunes.get(0);
        plot.add(t.learnedFrom(), 1);
        t.herbs().forEach(h -> plot.add(h, 1));
        springs.restore("mend", t.learnedFrom(), t.herbs().stream().map(h -> new MelodyBrew.Ingredient(h, 3)).toList(),
                plot);
        FirstWeek w = new FirstWeek(6);
        for (int d = 1; d <= FirstWeek.DAYS; d++) {
            assertEquals(SpringChain.Outcome.CLEAN, springs.draw("draw-" + d, "spring_1", plot).outcome());
            while (plot.count(BrewBench.WATER) >= 1 && w.thirst() < FirstWeek.MAX) {
                w.drink("sip-" + d + "-" + plot.count(BrewBench.WATER), FirstWeek.Water.CLEAN, plot);
            }
            plot.add("Egg", 2);
            plot.add("Fasage", 1);
            assertTrue(Larder.cook("Omelet", plot));
            w.eat("eat-" + d, Larder.cooked("Omelet"), plot);
            assertTrue(w.endDay().survived(), "day " + d);
        }
        assertEquals(1, w.quest().stepIndex());
    }
}
