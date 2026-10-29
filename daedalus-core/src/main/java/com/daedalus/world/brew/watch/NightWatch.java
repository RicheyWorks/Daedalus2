// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.watch;

import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 19 of the Youtube Master Island story, "The Night Watch" (quest {@code q_night_watch}). Every hour from dusk
 * (0) to dawn ({@link #night()}) needs a watcher. Each sailor offers one {@link Stretch}. The night is warm when it is
 * covered with the fewest sailors woken; {@link #rota()} is the exact greedy interval cover (furthest reach first).
 */
public final class NightWatch {
    public static final String QUEST_ID = "q_night_watch";
    public static final int SAILORS_TO_WAKE = 3;
    static final String[] NAMES = {"wren", "tamsin", "odd", "pell", "maro", "ilse", "brann", "cass", "juno", "fen"};

    public enum Outcome { WOKEN, SENT_TO_BED, ALREADY_WOKEN, NOT_WOKEN, UNKNOWN, WARM, WEARY, GAPS, NO_COVER, DUPLICATE,
        IGNORED }

    private final int night;
    private final Map<String, Stretch> offers = new LinkedHashMap<>();
    private final Map<String, Stretch> woken = new LinkedHashMap<>();
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("wake", "sailor", SAILORS_TO_WAKE),
            new QuestProgress.Step("night", "warm", 1),
            new QuestProgress.Step("talk", SeedSongSpring.KEEPER, 1)));
    private final List<Stretch> rota;
    private Outcome last;

    public NightWatch(int night, List<Stretch> list) {
        if (night <= 0) {
            throw new IllegalArgumentException("night must be positive");
        }
        this.night = night;
        for (Stretch s : list) {
            if (offers.put(s.sailor(), s) != null) {
                throw new IllegalArgumentException("duplicate sailor " + s.sailor());
            }
        }
        List<Stretch> r = cover(night, list);
        rota = r == null ? null : List.copyOf(r);
    }

    /** A seeded crew: a chain of stretches that covers the night, plus overlapping extras, shuffled. */
    public static NightWatch seeded(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x416E7L);
        int night = 8 + rng.nextInt(5);
        List<int[]> spans = new ArrayList<>();
        int at = 0;
        while (at < night) {
            int start = Math.max(0, at - rng.nextInt(2));
            int end = Math.min(night, at + 1 + rng.nextInt(3));
            spans.add(new int[] {start, end});
            at = end;
        }
        int extras = 3 + rng.nextInt(3);
        for (int i = 0; i < extras && spans.size() < NAMES.length; i++) {
            int start = rng.nextInt(night);
            spans.add(new int[] {start, Math.min(night, start + 2 + rng.nextInt(4))});
        }
        for (int i = spans.size() - 1; i > 0; i--) {
            int j = rng.nextInt(i + 1);
            int[] t = spans.get(i);
            spans.set(i, spans.get(j));
            spans.set(j, t);
        }
        List<Stretch> out = new ArrayList<>();
        for (int i = 0; i < spans.size(); i++) {
            out.add(new Stretch(NAMES[i], spans.get(i)[0], spans.get(i)[1]));
        }
        return new NightWatch(night, out);
    }

    /** Greedy interval cover of [0, night): from the first unwatched hour, take the offer reaching furthest. */
    static List<Stretch> cover(int night, List<Stretch> offers) {
        List<Stretch> out = new ArrayList<>();
        int at = 0;
        while (at < night) {
            Stretch pick = null;
            for (Stretch s : offers) {
                if (s.start() <= at && s.end() > at && (pick == null || s.end() > pick.end())) {
                    pick = s;
                }
            }
            if (pick == null) {
                return null;
            }
            out.add(pick);
            at = pick.end();
        }
        return out;
    }

    public int night() {
        return night;
    }

    public List<Stretch> offers() {
        return List.copyOf(offers.values());
    }

    /** One fewest-sailor rota, or empty when the offers cannot cover the night. */
    public List<Stretch> rota() {
        return rota == null ? List.of() : rota;
    }

    /** Whether the offered stretches can cover the whole night at all. */
    public boolean coverable() {
        return rota != null;
    }

    /** The fewest sailors that cover the night, or -1 when it cannot be covered. */
    public int fewest() {
        return rota == null ? -1 : rota.size();
    }

    public List<Stretch> woken() {
        return List.copyOf(woken.values());
    }

    /** The first hour nobody woken covers, or -1. */
    public int firstGap() {
        for (int h = 0; h < night; h++) {
            int hour = h;
            if (woken.values().stream().noneMatch(s -> s.covers(hour))) {
                return h;
            }
        }
        return -1;
    }

    /** The first hour no offered stretch covers, or -1. */
    public int firstUnoffered() {
        for (int h = 0; h < night; h++) {
            int hour = h;
            if (offers.values().stream().noneMatch(s -> s.covers(hour))) {
                return h;
            }
        }
        return -1;
    }

    public QuestProgress quest() {
        return quest;
    }

    public Outcome last() {
        return last;
    }

    private Outcome guard(String eventId, String sailor) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        return sailor == null || offers.containsKey(sailor) ? null : Outcome.UNKNOWN;
    }

    /** Wakes a sailor onto the rota. */
    public Outcome wake(String eventId, String sailor) {
        Outcome g = guard(eventId, sailor);
        if (g != null) {
            return g;
        }
        if (sailor == null) {
            return Outcome.UNKNOWN;
        }
        if (woken.containsKey(sailor)) {
            return Outcome.ALREADY_WOKEN;
        }
        events.add(eventId);
        woken.put(sailor, offers.get(sailor));
        last = null;
        quest.apply(eventId, "wake", "sailor");
        return Outcome.WOKEN;
    }

    /** Sends a woken sailor back to bed. */
    public Outcome sendToBed(String eventId, String sailor) {
        Outcome g = guard(eventId, sailor);
        if (g != null) {
            return g;
        }
        if (sailor == null || woken.remove(sailor) == null) {
            return Outcome.NOT_WOKEN;
        }
        events.add(eventId);
        last = null;
        return Outcome.SENT_TO_BED;
    }

    /** Calls the night: warm if every hour is watched by the fewest sailors, weary if more were woken, NO_COVER (no
     * credit) if the offers can never cover it. */
    public Outcome callNight(String eventId) {
        Outcome g = guard(eventId, null);
        if (g != null) {
            return g;
        }
        if (rota == null) {
            events.add(eventId);
            last = Outcome.NO_COVER;
            return last;
        }
        if (firstGap() >= 0) {
            return Outcome.GAPS;
        }
        events.add(eventId);
        last = woken.size() == fewest() ? Outcome.WARM : Outcome.WEARY;
        if (last == Outcome.WARM) {
            quest.apply(eventId, "night", "warm");
        }
        return last;
    }

    /** Talks to Keeper Oriel: the quest's talk step once a night was warm. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", SeedSongSpring.KEEPER);
            return KeeperWatchLines.THANKS;
        }
        return KeeperWatchLines.line(this);
    }
}
