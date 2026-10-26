// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.week;

import com.daedalus.world.brew.BrewBench;
import com.daedalus.world.colony.PlotState;
import com.daedalus.world.colony.QuestProgress;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 5 of the Youtube Master Island story, "The First Week Home" (quest {@code q_first_week}): seven days on
 * the homestead with thirst, hunger and health, at day resolution. Numbers follow
 * {@code engines/unreal/ytm-island/food_water.json}: start 80 of 100, clean water +35, raw +20 with a seeded 25%
 * chance of sickness, salt -10. Each day drains {@link #THIRST_PER_DAY} thirst ({@link #SICK_EXTRA} more while
 * sick, halved by the found desert_thirst tonic) and {@link #HUNGER_PER_DAY} hunger. A day that ends with thirst or
 * hunger at 0 costs {@link #HEALTH_HIT} health; at 0 health the week is lost.
 */
public final class FirstWeek {
    public static final int MAX = 100;
    public static final int START = 80;
    public static final int CLEAN = 35;
    public static final int RAW = 20;
    public static final int SALT = -10;
    public static final double SICK_CHANCE = 0.25;
    public static final int THIRST_PER_DAY = 60;
    public static final int HUNGER_PER_DAY = 45;
    public static final int SICK_EXTRA = 20;
    public static final int HEALTH_HIT = 40;
    public static final int DAYS = 7;
    public static final String SEA = "sea";
    public static final String DESERT_THIRST_TONIC = "Item_YTM_Tonic_Found_desert_thirst";
    public static final String QUEST_ID = "q_first_week";
    public static final String WICK = "old_wick";

    public enum Water { CLEAN, RAW, SALT }

    public enum Outcome { DRANK, ATE, TONIC, NOTHING_TO_USE, OVER, DUPLICATE, IGNORED }

    /** End of one day: vitals after the drain, whether sickness or the tonic applied, and whether the day was survived. */
    public record Day(int day, int thirst, int hunger, int health, boolean sick, boolean tonic, boolean survived) {
    }

    private final SplittableRandom rng;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("survive", "day", DAYS),
            new QuestProgress.Step("talk", WICK, 1)));
    private int thirst = START;
    private int hunger = START;
    private int health = MAX;
    private int day = 1;
    private boolean sickToday;
    private boolean tonicToday;
    private Day last;

    public FirstWeek(long seed) {
        rng = new SplittableRandom(seed);
    }

    public int thirst() {
        return thirst;
    }

    public int hunger() {
        return hunger;
    }

    public int health() {
        return health;
    }

    /** The day being played (1-based); {@link #DAYS} + 1 once the week is over. */
    public int day() {
        return day;
    }

    public boolean sick() {
        return sickToday;
    }

    public boolean lost() {
        return health <= 0;
    }

    public boolean over() {
        return lost() || day > DAYS;
    }

    public Day lastDay() {
        return last;
    }

    public QuestProgress quest() {
        return quest;
    }

    private Outcome guard(String eventId, PlotState plot) {
        if (eventId == null || eventId.isBlank() || eventId.length() > 128 || plot == null) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (over()) {
            return Outcome.OVER;
        }
        return null;
    }

    /** Drinks one unit: clean ({@code water}) or raw ({@code raw_water}) from the store, or salt from the sea. */
    public Outcome drink(String eventId, Water kind, PlotState plot) {
        Outcome g = guard(eventId, plot);
        if (g != null) {
            return g;
        }
        if (kind == null) {
            return Outcome.IGNORED;
        }
        String item = switch (kind) {
            case CLEAN -> BrewBench.WATER;
            case RAW -> BrewBench.RAW_WATER;
            case SALT -> null;
        };
        if (item != null && !plot.take(item, 1)) {
            return Outcome.NOTHING_TO_USE;
        }
        events.add(eventId);
        int gain = switch (kind) {
            case CLEAN -> CLEAN;
            case RAW -> RAW;
            case SALT -> SALT;
        };
        thirst = Math.max(0, Math.min(MAX, thirst + gain));
        if (kind == Water.RAW && rng.nextDouble() < SICK_CHANCE) {
            sickToday = true;
        }
        return Outcome.DRANK;
    }

    /** Eats one cooked meal from the store ({@link Larder#cooked}). */
    public Outcome eat(String eventId, String cookedItem, PlotState plot) {
        Outcome g = guard(eventId, plot);
        if (g != null) {
            return g;
        }
        String recipe = Larder.recipeOf(cookedItem);
        if (recipe == null || !plot.take(cookedItem, 1)) {
            return Outcome.NOTHING_TO_USE;
        }
        events.add(eventId);
        hunger = Math.min(MAX, hunger + Larder.restore(recipe));
        return Outcome.ATE;
    }

    /** Drinks the found desert_thirst tonic (G25/G33 found tune): today's thirst drain is halved. */
    public Outcome tonic(String eventId, PlotState plot) {
        Outcome g = guard(eventId, plot);
        if (g != null) {
            return g;
        }
        if (tonicToday || !plot.take(DESERT_THIRST_TONIC, 1)) {
            return Outcome.NOTHING_TO_USE;
        }
        events.add(eventId);
        tonicToday = true;
        return Outcome.TONIC;
    }

    /** Ends the day: drains, health check, quest step. Returns null when the week is already over. */
    public Day endDay() {
        if (over()) {
            return null;
        }
        int drain = THIRST_PER_DAY + (sickToday ? SICK_EXTRA : 0);
        if (tonicToday) {
            drain /= 2;
        }
        thirst = Math.max(0, thirst - drain);
        hunger = Math.max(0, hunger - HUNGER_PER_DAY);
        if (thirst == 0) {
            health -= HEALTH_HIT;
        }
        if (hunger == 0) {
            health -= HEALTH_HIT;
        }
        health = Math.max(0, health);
        boolean survived = health > 0;
        last = new Day(day, thirst, hunger, health, sickToday, tonicToday, survived);
        if (survived) {
            quest.apply("first-week-day-" + day, "survive", "day");
        }
        day++;
        sickToday = false;
        tonicToday = false;
        return last;
    }

    /** Talks to Old Wick: his line, and the quest's talk step when it is due. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", WICK);
            return WickLines.THANKS;
        }
        return WickLines.line(this);
    }
}
