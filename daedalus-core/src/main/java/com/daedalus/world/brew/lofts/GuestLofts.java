// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.lofts;

import com.daedalus.world.brew.cellar.RootCellar;
import com.daedalus.world.brew.letters.Destination;
import com.daedalus.world.brew.letters.LettersByArk;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SplittableRandom;
import java.util.TreeSet;

/**
 * Chapter 14 of the Youtube Master Island story, "The Guest Lofts" (quest {@code q_guest_lofts}). The ark brings the
 * far-island families to see their children: {@link #FAMILIES_PER_ISLAND} from each G97 {@link Destination}, arriving
 * after the voyage ({@link LettersByArk#DAYS_PER_LEG} per leg) plus a seeded wait, staying {@link #STAY_MIN} to
 * {@link #STAY_MAX} days. Aunt Brine airs lofts: one family per loft at a time. Every loft aired costs linen, so the
 * aim is the fewest lofts. That is {@link #fewest()}, the most families ever on the homestead at once (interval
 * partitioning); {@link #greedyPlan()} reaches it by housing families in arrival order in any loft already free.
 */
public final class GuestLofts {
    public static final String QUEST_ID = "q_guest_lofts";
    public static final int FAMILIES_PER_ISLAND = 2;
    public static final int STAY_MIN = 2;
    public static final int STAY_MAX = 6;
    public static final int WAIT_MAX = 3;
    public static final int LOFTS = 8;

    public enum Outcome { HOUSED, MOVED_OUT, CLASH, ALREADY_HOUSED, NOT_HOUSED, UNKNOWN_FAMILY, NO_SUCH_LOFT, SNUG,
        SPRAWL, NOT_EVERYONE, DUPLICATE, IGNORED }

    private final Map<String, Family> families = new LinkedHashMap<>();
    private final Map<String, Integer> loftOf = new LinkedHashMap<>();
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest;
    private final Set<String> everHoused = new HashSet<>();
    private final int fewest;
    private Outcome settled;

    /** Lofts for these families (at most {@link #LOFTS} of them). */
    public GuestLofts(List<Family> list) {
        if (list.isEmpty() || list.size() > LOFTS) {
            throw new IllegalArgumentException("1 to " + LOFTS + " families");
        }
        for (Family f : list) {
            if (families.put(f.id(), f) != null) {
                throw new IllegalArgumentException("duplicate family " + f.id());
            }
        }
        quest = new QuestProgress(List.of(
                new QuestProgress.Step("house", "family", list.size()),
                new QuestProgress.Step("settle", "lofts", 1),
                new QuestProgress.Step("talk", RootCellar.BRINE, 1)));
        fewest = maxOverlap(list);
    }

    /** The families the ark brings: two per far island, seeded waits and stays. */
    public static List<Family> fromFarIslands(List<Destination> destinations, long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x10F7L);
        List<Family> out = new ArrayList<>();
        for (Destination d : destinations) {
            int voyage = d.route().legs().size() * LettersByArk.DAYS_PER_LEG;
            for (int i = 1; i <= FAMILIES_PER_ISLAND; i++) {
                int arrive = 1 + voyage + rng.nextInt(WAIT_MAX + 1);
                int stay = STAY_MIN + rng.nextInt(STAY_MAX - STAY_MIN + 1);
                out.add(new Family(d.id() + "_" + i, d.id(), arrive, arrive + stay));
            }
        }
        return out;
    }

    /** The most families on the homestead on any one night. */
    public static int maxOverlap(List<Family> list) {
        TreeSet<Integer> days = new TreeSet<>();
        list.forEach(f -> days.add(f.arrive()));
        int best = 0;
        for (int day : days) {
            int n = 0;
            for (Family f : list) {
                if (f.arrive() <= day && day < f.leave()) {
                    n++;
                }
            }
            best = Math.max(best, n);
        }
        return best;
    }

    /** Arrival order (ties: earlier leaver, then id), each into the lowest-numbered loft free that day. */
    public Map<String, Integer> greedyPlan() {
        List<Family> order = new ArrayList<>(families.values());
        order.sort(Comparator.comparingInt(Family::arrive).thenComparingInt(Family::leave).thenComparing(Family::id));
        Map<String, Integer> plan = new LinkedHashMap<>();
        List<Integer> freeFrom = new ArrayList<>();
        for (Family f : order) {
            int loft = -1;
            for (int i = 0; i < freeFrom.size(); i++) {
                if (freeFrom.get(i) <= f.arrive()) {
                    loft = i;
                    break;
                }
            }
            if (loft < 0) {
                freeFrom.add(0);
                loft = freeFrom.size() - 1;
            }
            freeFrom.set(loft, f.leave());
            plan.put(f.id(), loft + 1);
        }
        return plan;
    }

    public int fewest() {
        return fewest;
    }

    public List<Family> families() {
        return List.copyOf(families.values());
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Loft number (1..{@link #LOFTS}) a family is in, or null. */
    public Integer loftOf(String familyId) {
        return loftOf.get(familyId);
    }

    /** Lofts aired: distinct lofts in use. */
    public int aired() {
        return new HashSet<>(loftOf.values()).size();
    }

    public int housed() {
        return loftOf.size();
    }

    /** The last settle result (SNUG or SPRAWL), or null. */
    public Outcome settled() {
        return settled;
    }

    private Outcome guard(String eventId, String familyId) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (!families.containsKey(familyId)) {
            return Outcome.UNKNOWN_FAMILY;
        }
        return null;
    }

    /** Houses a family in a loft, if no one staying there shares a night with them. */
    public Outcome assign(String eventId, String familyId, int loft) {
        Outcome g = guard(eventId, familyId);
        if (g != null) {
            return g;
        }
        if (loft < 1 || loft > LOFTS) {
            return Outcome.NO_SUCH_LOFT;
        }
        if (loftOf.containsKey(familyId)) {
            return Outcome.ALREADY_HOUSED;
        }
        Family f = families.get(familyId);
        for (Map.Entry<String, Integer> e : loftOf.entrySet()) {
            if (e.getValue() == loft && families.get(e.getKey()).overlaps(f)) {
                return Outcome.CLASH;
            }
        }
        events.add(eventId);
        loftOf.put(familyId, loft);
        settled = null;
        if (everHoused.add(familyId)) {
            quest.apply("house-" + familyId, "house", "family");
        }
        return Outcome.HOUSED;
    }

    /** Moves a family out of their loft (to house them elsewhere). */
    public Outcome moveOut(String eventId, String familyId) {
        Outcome g = guard(eventId, familyId);
        if (g != null) {
            return g;
        }
        if (!loftOf.containsKey(familyId)) {
            return Outcome.NOT_HOUSED;
        }
        events.add(eventId);
        loftOf.remove(familyId);
        settled = null;
        return Outcome.MOVED_OUT;
    }

    /** Aunt Brine counts the linen: snug when everyone is housed in the fewest lofts. */
    public Outcome settle(String eventId) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (loftOf.size() < families.size()) {
            return Outcome.NOT_EVERYONE;
        }
        events.add(eventId);
        settled = aired() == fewest ? Outcome.SNUG : Outcome.SPRAWL;
        if (settled == Outcome.SNUG) {
            quest.apply(eventId, "settle", "lofts");
        }
        return settled;
    }

    /** Talks to Aunt Brine: the quest's talk step once the lofts are snug. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", RootCellar.BRINE);
            return BrineLoftLines.THANKS;
        }
        return BrineLoftLines.line(this);
    }
}
