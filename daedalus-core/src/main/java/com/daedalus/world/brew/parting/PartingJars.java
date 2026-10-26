// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.parting;

import com.daedalus.world.brew.cellar.Preserve;
import com.daedalus.world.brew.cellar.RootCellar;
import com.daedalus.world.brew.letters.Destination;
import com.daedalus.world.brew.lofts.Family;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 16 of the Youtube Master Island story, "The Parting Jars" (quest {@code q_parting_jars}). Each visiting
 * family (G149) wants a jar of their island's favourite food (G97) to take home, kept the longest-lasting way it can
 * be (G73). The cellar apprentice works one order at a time, from day {@link #start()}; an order takes
 * {@link #PREP_DAYS} for its method per jar and is on time if it is finished by the family's leave day. The player
 * chooses the order of work (and may leave orders out). {@link #best()} is the Moore-Hodgson plan: take orders by
 * earliest due day and, whenever the last one would be late, drop the longest order taken so far. No plan sends
 * more families home with a jar.
 */
public final class PartingJars {
    public static final String QUEST_ID = "q_parting_jars";
    public static final int JARS_MAX = 2;
    public static final Map<Preserve.Method, Integer> PREP_DAYS = prep();

    public enum Outcome { FULL_SHELF, SHORT, EMPTY, UNKNOWN_FAMILY, REPEATED, DUPLICATE, IGNORED }

    private final Map<String, PartingJar> orders = new LinkedHashMap<>();
    private final int start;
    private final List<PartingJar> best;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("plan", "jars", 1),
            new QuestProgress.Step("fill", "shelf", 1),
            new QuestProgress.Step("talk", RootCellar.BRINE, 1)));
    private Outcome last;
    private int lastOnTime;

    private static Map<Preserve.Method, Integer> prep() {
        Map<Preserve.Method, Integer> m = new EnumMap<>(Preserve.Method.class);
        m.put(Preserve.Method.SALT, 1);
        m.put(Preserve.Method.PICKLE, 2);
        m.put(Preserve.Method.SMOKE, 2);
        m.put(Preserve.Method.DRY, 3);
        return java.util.Collections.unmodifiableMap(m);
    }

    /** Orders worked from day {@code start}. */
    public PartingJars(List<PartingJar> list, int start) {
        if (list.isEmpty()) {
            throw new IllegalArgumentException("no orders");
        }
        for (PartingJar j : list) {
            if (orders.put(j.family(), j) != null) {
                throw new IllegalArgumentException("one order per family: " + j.family());
            }
        }
        this.start = start;
        this.best = List.copyOf(mooreHodgson(list, start));
    }

    /** The longest-keeping preserve for a food (FRESH never counts as a parting jar). */
    public static Preserve.Method methodFor(String food) {
        Preserve.Method m = null;
        int days = 0;
        for (Preserve.Method x : PREP_DAYS.keySet()) {
            int d = Preserve.shelfDays(food, x);
            if (d > days) {
                days = d;
                m = x;
            }
        }
        if (m == null) {
            throw new IllegalArgumentException(food + " cannot be preserved");
        }
        return m;
    }

    /** One order per visiting family: their island's favourite, 1-{@link #JARS_MAX} jars (seeded), due on leaving. */
    public static PartingJars forFamilies(List<Family> families, List<Destination> destinations, long seed) {
        Map<String, Destination> byId = new LinkedHashMap<>();
        destinations.forEach(d -> byId.put(d.id(), d));
        SplittableRandom rng = new SplittableRandom(seed ^ 0x5A17L);
        List<PartingJar> out = new ArrayList<>();
        int first = Integer.MAX_VALUE;
        for (Family f : families) {
            String food = byId.get(f.home()).favourite();
            Preserve.Method m = methodFor(food);
            int jars = 1 + rng.nextInt(JARS_MAX);
            out.add(new PartingJar(f.id(), food, m, jars, jars * PREP_DAYS.get(m), f.leave()));
            first = Math.min(first, f.arrive());
        }
        return new PartingJars(out, first);
    }

    /** Families whose jar is finished by their leave day, working in this order from day {@code start}. */
    public static int onTime(List<PartingJar> order, int start) {
        int day = start;
        int n = 0;
        for (PartingJar j : order) {
            day += j.prepDays();
            if (day <= j.due()) {
                n++;
            }
        }
        return n;
    }

    static List<PartingJar> mooreHodgson(List<PartingJar> list, int start) {
        List<PartingJar> byDue = new ArrayList<>(list);
        byDue.sort(Comparator.comparingInt(PartingJar::due).thenComparing(PartingJar::family));
        List<PartingJar> taken = new ArrayList<>();
        int day = start;
        for (PartingJar j : byDue) {
            taken.add(j);
            day += j.prepDays();
            if (day > j.due()) {
                PartingJar longest = taken.stream().max(Comparator.comparingInt(PartingJar::prepDays)
                        .thenComparing(PartingJar::family)).orElseThrow();
                taken.remove(longest);
                day -= longest.prepDays();
            }
        }
        return taken;
    }

    public int start() {
        return start;
    }

    public List<PartingJar> orders() {
        return List.copyOf(orders.values());
    }

    /** A best plan: on-time orders in earliest-due order. */
    public List<PartingJar> best() {
        return best;
    }

    public QuestProgress quest() {
        return quest;
    }

    public Outcome last() {
        return last;
    }

    public int lastOnTime() {
        return lastOnTime;
    }

    /** Sets the apprentice's work order (families by id). FULL_SHELF if it sends as many home with a jar as any plan. */
    public Outcome plan(String eventId, List<String> familyOrder) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (familyOrder.isEmpty()) {
            return Outcome.EMPTY;
        }
        if (new HashSet<>(familyOrder).size() != familyOrder.size()) {
            return Outcome.REPEATED;
        }
        List<PartingJar> order = new ArrayList<>();
        for (String f : familyOrder) {
            PartingJar j = orders.get(f);
            if (j == null) {
                return Outcome.UNKNOWN_FAMILY;
            }
            order.add(j);
        }
        events.add(eventId);
        lastOnTime = onTime(order, start);
        last = lastOnTime == best.size() ? Outcome.FULL_SHELF : Outcome.SHORT;
        quest.apply(eventId, "plan", "jars");
        if (last == Outcome.FULL_SHELF) {
            quest.apply(eventId + "-fill", "fill", "shelf");
        }
        return last;
    }

    /** Talks to Aunt Brine: the quest's talk step once a full-shelf plan was set. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", RootCellar.BRINE);
            return ApprenticeJarLines.THANKS;
        }
        return ApprenticeJarLines.line(this);
    }
}
