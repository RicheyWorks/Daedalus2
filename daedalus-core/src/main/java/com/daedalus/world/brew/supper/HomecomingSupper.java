// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.supper;

import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.brew.week.Larder;
import com.daedalus.world.colony.PlotState;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 8 of the Youtube Master Island story, "The Homecoming Supper" (quest {@code q_homecoming_supper}). The
 * host sits at the head of a round table; the nine guests sit clockwise from the host's left, so each guest's
 * neighbours are the guests either side (the first and last sit beside the host). Seeded feuds must never sit side
 * by side (a feud-free seating always exists: the constructor reseeds until one does); seeded friends side by side
 * are +2 each. Each guest has a seeded favourite larder recipe (G62) and a favourite tune (one of the mended G33
 * records). A cooked meal is +3 if it is the favourite, +1 otherwise, -2 if the guest gets nothing; hearing one's
 * tune during the three courses is +2. A guest is content at {@link #CONTENT}; the supper is warm when the table is
 * seated, every guest is served, three courses are played and everyone is content.
 */
public final class HomecomingSupper {
    public static final String QUEST_ID = "q_homecoming_supper";
    public static final int FEUDS = 4;
    public static final int FRIENDS = 3;
    public static final int COURSES = 3;
    public static final int CONTENT = 3;
    public static final int FRIEND_BONUS = 2;
    public static final int FAVOURITE_MEAL = 3;
    public static final int OTHER_MEAL = 1;
    public static final int NO_MEAL = -2;
    public static final int FAVOURITE_TUNE = 2;

    public enum Outcome { SEATED, FEUD, BAD_SEATING, ALREADY_SEATED, SERVED, NOT_SEATED, UNKNOWN_GUEST, NO_MEAL,
        ALREADY_SERVED, PLAYED, NOT_RESTORED, UNKNOWN_TUNE, ALREADY_PLAYED, ALL_COURSES_PLAYED, DUPLICATE, IGNORED }

    private final SeedSongSpring songs;
    private final Map<String, Guest> guests = new LinkedHashMap<>();
    private final Set<String> records = new LinkedHashSet<>();
    private final Map<String, String> favouriteDish = new HashMap<>();
    private final Map<String, String> favouriteTune = new HashMap<>();
    private final Set<Set<String>> feuds = new LinkedHashSet<>();
    private final Set<Set<String>> friends = new LinkedHashSet<>();
    private final Map<String, String> served = new HashMap<>();
    private final List<String> played = new ArrayList<>();
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("seat", "table", 1),
            new QuestProgress.Step("serve", "guest", Guest.island().size()),
            new QuestProgress.Step("play", "course", COURSES),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private List<String> seating;

    public HomecomingSupper(SeedSongSpring songs, List<FoundTune> tunes, List<Guest> guestList, long seed) {
        if (guestList.size() < 5) {
            throw new IllegalArgumentException("a supper needs at least five guests");
        }
        this.songs = songs;
        guestList.forEach(g -> guests.put(g.id(), g));
        tunes.forEach(t -> records.add(t.learnedFrom()));
        List<String> ids = List.copyOf(guests.keySet());
        List<String> recipes = List.copyOf(Larder.RECIPES.keySet());
        List<String> recs = List.copyOf(records);
        SplittableRandom rng = new SplittableRandom(seed);
        for (String id : ids) {
            favouriteDish.put(id, recipes.get(rng.nextInt(recipes.size())));
            favouriteTune.put(id, recs.get(rng.nextInt(recs.size())));
        }
        do {
            feuds.clear();
            friends.clear();
            while (feuds.size() < FEUDS) {
                feuds.add(pair(ids, rng));
            }
            while (friends.size() < FRIENDS) {
                Set<String> p = pair(ids, rng);
                if (!feuds.contains(p)) {
                    friends.add(p);
                }
            }
        } while (feudFreeSeating(ids, feuds).isEmpty());
    }

    private static Set<String> pair(List<String> ids, SplittableRandom rng) {
        int a = rng.nextInt(ids.size());
        int b = (a + 1 + rng.nextInt(ids.size() - 1)) % ids.size();
        return Set.of(ids.get(a), ids.get(b));
    }

    /** A seating (clockwise from the host's left) with no feud side by side, by backtracking; empty if none. */
    public static Optional<List<String>> feudFreeSeating(List<String> ids, Set<Set<String>> feuds) {
        List<String> out = new ArrayList<>();
        return place(ids, feuds, out, new HashSet<>()) ? Optional.of(List.copyOf(out)) : Optional.empty();
    }

    private static boolean place(List<String> ids, Set<Set<String>> feuds, List<String> out, Set<String> used) {
        if (out.size() == ids.size()) {
            return true;
        }
        for (String id : ids) {
            if (used.contains(id) || (!out.isEmpty() && feuds.contains(Set.of(out.get(out.size() - 1), id)))) {
                continue;
            }
            out.add(id);
            used.add(id);
            if (place(ids, feuds, out, used)) {
                return true;
            }
            out.remove(out.size() - 1);
            used.remove(id);
        }
        return false;
    }

    public QuestProgress quest() {
        return quest;
    }

    public List<Guest> guests() {
        return List.copyOf(guests.values());
    }

    public Set<Set<String>> feuds() {
        return Set.copyOf(feuds);
    }

    public Set<Set<String>> friends() {
        return Set.copyOf(friends);
    }

    public String favouriteDish(String guestId) {
        return favouriteDish.get(guestId);
    }

    public String favouriteTune(String guestId) {
        return favouriteTune.get(guestId);
    }

    /** The seating, or null before the table is seated. */
    public List<String> seating() {
        return seating;
    }

    public List<String> played() {
        return List.copyOf(played);
    }

    /** A feud-free seating to offer as a hint. */
    public List<String> hint() {
        return feudFreeSeating(List.copyOf(guests.keySet()), feuds).orElseThrow();
    }

    private Outcome guard(String eventId) {
        if (eventId == null || eventId.isBlank() || eventId.length() > QuestProgress.MAX_EVENT_ID) {
            return Outcome.IGNORED;
        }
        return events.contains(eventId) ? Outcome.DUPLICATE : null;
    }

    /** Seats every guest once, clockwise from the host's left. Two feuding guests side by side are refused. */
    public Outcome seat(String eventId, List<String> order) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (seating != null) {
            return Outcome.ALREADY_SEATED;
        }
        if (order == null || order.size() != guests.size() || !new HashSet<>(order).equals(guests.keySet())) {
            return Outcome.BAD_SEATING;
        }
        for (int i = 1; i < order.size(); i++) {
            if (feuds.contains(Set.of(order.get(i - 1), order.get(i)))) {
                return Outcome.FEUD;
            }
        }
        events.add(eventId);
        seating = List.copyOf(order);
        quest.apply(eventId, "seat", "table");
        return Outcome.SEATED;
    }

    /** Serves one cooked larder meal from the store to a seated guest. */
    public Outcome serve(String eventId, String guestId, String cookedItem, PlotState plot) {
        Outcome g = plot == null ? Outcome.IGNORED : guard(eventId);
        if (g != null) {
            return g;
        }
        if (!guests.containsKey(guestId)) {
            return Outcome.UNKNOWN_GUEST;
        }
        if (seating == null) {
            return Outcome.NOT_SEATED;
        }
        if (served.containsKey(guestId)) {
            return Outcome.ALREADY_SERVED;
        }
        String recipe = Larder.recipeOf(cookedItem);
        if (recipe == null || !plot.take(cookedItem, 1)) {
            return Outcome.NO_MEAL;
        }
        events.add(eventId);
        served.put(guestId, recipe);
        quest.apply(eventId, "serve", "guest");
        return Outcome.SERVED;
    }

    /** Plays a mended record for the next course (three courses, each record once). */
    public Outcome play(String eventId, String recordItem) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (!records.contains(recordItem)) {
            return Outcome.UNKNOWN_TUNE;
        }
        if (played.size() >= COURSES) {
            return Outcome.ALL_COURSES_PLAYED;
        }
        if (played.contains(recordItem)) {
            return Outcome.ALREADY_PLAYED;
        }
        if (!songs.isRestored(recordItem)) {
            return Outcome.NOT_RESTORED;
        }
        events.add(eventId);
        played.add(recordItem);
        quest.apply(eventId, "play", "course");
        return Outcome.PLAYED;
    }

    /** The guests either side of this one (the host is not counted). */
    public List<String> neighbours(String guestId) {
        if (seating == null) {
            return List.of();
        }
        int i = seating.indexOf(guestId);
        List<String> n = new ArrayList<>();
        if (i > 0) {
            n.add(seating.get(i - 1));
        }
        if (i >= 0 && i < seating.size() - 1) {
            n.add(seating.get(i + 1));
        }
        return n;
    }

    /** How content a guest is right now. */
    public int contentment(String guestId) {
        if (!guests.containsKey(guestId)) {
            return 0;
        }
        int c = 0;
        for (String n : neighbours(guestId)) {
            if (friends.contains(Set.of(guestId, n))) {
                c += FRIEND_BONUS;
            }
        }
        String meal = served.get(guestId);
        c += meal == null ? NO_MEAL : meal.equals(favouriteDish.get(guestId)) ? FAVOURITE_MEAL : OTHER_MEAL;
        if (played.contains(favouriteTune.get(guestId))) {
            c += FAVOURITE_TUNE;
        }
        return c;
    }

    /** True once seated, everyone served, three courses played and every guest content. */
    public boolean warm() {
        return seating != null && served.size() == guests.size() && played.size() == COURSES
                && guests.keySet().stream().allMatch(id -> contentment(id) >= CONTENT);
    }

    /** Guests not yet content. */
    public List<String> discontent() {
        return guests.keySet().stream().filter(id -> contentment(id) < CONTENT).toList();
    }

    /** Talks to Keeper Oriel at the head of the table; the last quest step needs a warm supper. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            if (!warm()) {
                return String.format(SupperLines.COLD, discontent().size(), discontent().size() == 1 ? "" : "s");
            }
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return SupperLines.THANKS;
        }
        return SupperLines.line(this);
    }
}
