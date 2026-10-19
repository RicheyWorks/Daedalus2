// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.cellar;

import com.daedalus.world.brew.BrewBench;
import com.daedalus.world.colony.PlotState;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.EnumSet;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 7 of the Youtube Master Island story, "The Root Cellar" (quest {@code q_root_cellar}). The cloud season
 * brings the Long Dark: {@link #DARK_DAYS} days with no boats and no laying hens. Before it, food goes into a
 * twelve-jar cellar, kept by a {@link Preserve.Method}. Salt is boiled from the sea, two a day. Each jar has a
 * seeded chance of a bad seal that halves its life; a jar past its day spoils into compost for the plot. Salted food
 * has to be soaked in clean water before it goes back into the store. Quest: keep food three different ways (not
 * fresh), fill eight more jars, eat from the cellar on all five Long Dark days, then tell Aunt Brine.
 */
public final class RootCellar {
    public static final String QUEST_ID = "q_root_cellar";
    public static final String BRINE = "aunt_brine";
    public static final String COMPOST = "compost";
    public static final int CAPACITY = 12;
    public static final int SALT_PER_DAY = 2;
    public static final int DARK_DAYS = 5;
    public static final double BAD_SEAL_CHANCE = 0.1;

    public enum Outcome { STORED, BOILED, TAKEN, NOT_PRESERVABLE, NO_FOOD, NO_SALT, NO_WATER, CELLAR_FULL,
        RACK_FULL, SALT_PAN_DONE, NO_JAR, DUPLICATE, IGNORED }

    /** One jar: what is in it, how it was kept, when it went in and the last day it is good. */
    public record Jar(int id, String item, Preserve.Method method, int stored, int goodUntil, boolean badSeal) {
    }

    private final long seed;
    private final int darkStart;
    private final Map<Integer, Jar> jars = new LinkedHashMap<>();
    private final Map<Preserve.Method, Integer> usedToday = new EnumMap<>(Preserve.Method.class);
    private final Set<Preserve.Method> methods = EnumSet.noneOf(Preserve.Method.class);
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("new_method", "cellar", 3),
            new QuestProgress.Step("jar", "cellar", 8),
            new QuestProgress.Step("dark_day", "cellar", DARK_DAYS),
            new QuestProgress.Step("talk", BRINE, 1)));
    private int day = 1;
    private int nextId = 1;
    private int saltToday;
    private boolean ateFromCellarToday;

    /** A cellar whose Long Dark starts on {@code darkStart} (day 1 = today). */
    public RootCellar(long seed, int darkStart) {
        if (darkStart < 1) {
            throw new IllegalArgumentException("darkStart must be >= 1");
        }
        this.seed = seed;
        this.darkStart = darkStart;
    }

    public int day() {
        return day;
    }

    public QuestProgress quest() {
        return quest;
    }

    public List<Jar> jars() {
        return List.copyOf(jars.values());
    }

    /** True on the Long Dark days. */
    public boolean isDark() {
        return day >= darkStart && day < darkStart + DARK_DAYS;
    }

    /** True once the Long Dark has passed. */
    public boolean darkOver() {
        return day >= darkStart + DARK_DAYS;
    }

    /** Days until the Long Dark begins (0 once it has begun). */
    public int daysUntilDark() {
        return Math.max(0, darkStart - day);
    }

    private Outcome guard(String eventId, PlotState plot) {
        if (eventId == null || eventId.isBlank() || eventId.length() > QuestProgress.MAX_EVENT_ID || plot == null) {
            return Outcome.IGNORED;
        }
        return events.contains(eventId) ? Outcome.DUPLICATE : null;
    }

    /** Boils a pan of sea water at the salt pan: one salt into the store, {@link #SALT_PER_DAY} a day. */
    public Outcome boilSea(String eventId, PlotState plot) {
        Outcome g = guard(eventId, plot);
        if (g != null) {
            return g;
        }
        if (saltToday >= SALT_PER_DAY) {
            return Outcome.SALT_PAN_DONE;
        }
        events.add(eventId);
        saltToday++;
        plot.add(Preserve.SALT, 1);
        return Outcome.BOILED;
    }

    /** Puts one unit of food from the store into a jar, kept this way. */
    public Outcome preserve(String eventId, String item, Preserve.Method method, PlotState plot) {
        Outcome g = guard(eventId, plot);
        if (g != null) {
            return g;
        }
        int life = Preserve.shelfDays(item, method);
        if (life <= 0) {
            return Outcome.NOT_PRESERVABLE;
        }
        if (jars.size() >= CAPACITY) {
            return Outcome.CELLAR_FULL;
        }
        int cap = Preserve.perDay(method);
        if (cap > 0 && usedToday.getOrDefault(method, 0) >= cap) {
            return Outcome.RACK_FULL;
        }
        if (plot.count(item) < 1) {
            return Outcome.NO_FOOD;
        }
        Map<String, Integer> cost = Preserve.cost(method);
        if (plot.count(Preserve.SALT) < cost.getOrDefault(Preserve.SALT, 0)) {
            return Outcome.NO_SALT;
        }
        if (plot.count(BrewBench.WATER) < cost.getOrDefault(BrewBench.WATER, 0)) {
            return Outcome.NO_WATER;
        }
        events.add(eventId);
        plot.take(item, 1);
        cost.forEach((k, v) -> plot.take(k, v));
        usedToday.merge(method, 1, Integer::sum);
        int id = nextId++;
        boolean bad = new SplittableRandom(seed * 31_337L + id).nextDouble() < BAD_SEAL_CHANCE;
        int days = bad ? Math.max(1, life / 2) : life;
        jars.put(id, new Jar(id, item, method, day, day + days - 1, bad));
        if (method != Preserve.Method.FRESH && methods.add(method)) {
            quest.apply(eventId + "#m", "new_method", "cellar");
        }
        quest.apply(eventId, "jar", "cellar");
        return Outcome.STORED;
    }

    /** Opens a jar back into the store (salted food takes one clean water to soak). */
    public Outcome take(String eventId, int jarId, PlotState plot) {
        Outcome g = guard(eventId, plot);
        if (g != null) {
            return g;
        }
        Jar j = jars.get(jarId);
        if (j == null) {
            return Outcome.NO_JAR;
        }
        if (j.method() == Preserve.Method.SALT && !plot.take(BrewBench.WATER, 1)) {
            return Outcome.NO_WATER;
        }
        events.add(eventId);
        jars.remove(jarId);
        plot.add(j.item(), 1);
        if (isDark()) {
            ateFromCellarToday = true;
        }
        return Outcome.TAKEN;
    }

    /** The first good jar holding this item (soonest to spoil first), or null. */
    public Jar firstJarOf(String item) {
        return jars.values().stream().filter(j -> j.item().equals(item))
                .min((a, b) -> Integer.compare(a.goodUntil(), b.goodUntil())).orElse(null);
    }

    /**
     * Ends the day: a Long Dark day on which a jar was opened counts for the quest; the next day starts and every
     * jar past its last good day spoils into compost in the plot store. Returns the spoiled jars.
     */
    public List<Jar> nextDay(PlotState plot) {
        if (isDark() && ateFromCellarToday) {
            quest.apply("cellar-dark-day-" + day, "dark_day", "cellar");
        }
        day++;
        saltToday = 0;
        usedToday.clear();
        ateFromCellarToday = false;
        List<Jar> spoiled = new ArrayList<>();
        for (Jar j : List.copyOf(jars.values())) {
            if (j.goodUntil() < day) {
                jars.remove(j.id());
                spoiled.add(j);
                if (plot != null) {
                    plot.add(COMPOST, 1);
                }
            }
        }
        return spoiled;
    }

    /** Talks to Aunt Brine: her line, and the quest's talk step when it is due. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", BRINE);
            return BrineLines.THANKS;
        }
        return BrineLines.line(this);
    }
}
