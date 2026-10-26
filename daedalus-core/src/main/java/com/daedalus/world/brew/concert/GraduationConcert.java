// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.concert;

import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.school.SongSchool;
import com.daedalus.world.brew.song.ThirteenthSong;
import com.daedalus.world.brew.week.FirstWeek;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * Chapter 12 of the Youtube Master Island story, "The Graduation Concert" (quest {@code q_graduation_concert}). The
 * G116 Song School graduates sing on the homestead green. The player builds the set list: {@link #SOLOS} solos, each
 * a graduate singing one of their own set songs, then the whole choir closes on record thirteen (G94). Every song
 * sits in a key, the pitch class it starts and ends on. Each change of key between neighbouring songs costs the
 * audience's warmth by the circle-of-fifths distance between the keys (0 to 6). Every graduate must sing at least
 * once, nobody sings twice in a row, and no song is sung twice. {@link #best()} is the smoothest legal set (exact
 * search). A concert within {@link #SLACK} of it brings the green to its feet; a rougher one can be run again the
 * next evening.
 */
public final class GraduationConcert {
    public static final String QUEST_ID = "q_graduation_concert";
    public static final int SOLOS = 5;
    public static final int WARMTH = 12;
    public static final int SLACK = 2;
    public static final String CHOIR = "choir";

    public enum Outcome { SUNG, CHEERED, ROUGH, NOT_GRADUATE, NOT_THEIRS, SAME_SINGER, ALREADY_SUNG, SET_FULL,
        NOT_READY, LEAVES_SOMEONE_OUT, OVER, NOT_OVER, RERUN, UNKNOWN_SONG, DUPLICATE, IGNORED }

    /** One song on the set list. */
    public record Slot(String singer, String song, int key) {
    }

    private final Map<String, List<String>> repertoire = new TreeMap<>();
    private final Map<String, Integer> keys;
    private final String closer;
    private final List<Slot> set = new ArrayList<>();
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("perform", "solo", SOLOS),
            new QuestProgress.Step("cheer", "concert", 1),
            new QuestProgress.Step("talk", FirstWeek.WICK, 1)));
    private final int best;
    private final List<Slot> bestSet;
    private int evening = 1;
    private Outcome result;

    /**
     * A concert. {@code repertoire} maps each graduate to the songs they may sing; {@code keys} gives every song's
     * key (pitch class 0-11); {@code closer} is the choir's song.
     */
    public GraduationConcert(Map<String, List<String>> repertoire, Map<String, Integer> keys, String closer) {
        if (repertoire.size() < 2 || repertoire.size() > SOLOS) {
            throw new IllegalArgumentException("need 2 to " + SOLOS + " graduates, got " + repertoire.size());
        }
        repertoire.forEach((k, v) -> this.repertoire.put(k, List.copyOf(v)));
        this.keys = Map.copyOf(keys);
        this.closer = closer;
        for (List<String> songs : this.repertoire.values()) {
            for (String s : songs) {
                keyOf(s);
            }
        }
        keyOf(closer);
        List<Slot> found = new ArrayList<>();
        best = search(new ArrayList<>(), 0, Integer.MAX_VALUE, found);
        if (best == Integer.MAX_VALUE) {
            throw new IllegalArgumentException("no legal set list for this repertoire");
        }
        bestSet = List.copyOf(found);
    }

    /** The concert for a Song School's graduates (their set songs), keyed from the found tunes. */
    public static GraduationConcert fromSchool(SongSchool school, List<FoundTune> tunes, int islandKey) {
        Map<String, List<String>> rep = new LinkedHashMap<>();
        for (String g : school.graduates()) {
            rep.put(g, school.songsFor(g));
        }
        return new GraduationConcert(rep, keysOf(tunes, islandKey), ThirteenthSong.RECORD);
    }

    /** Each ark record's key is its tune's first note; record thirteen sits in {@code islandKey}. */
    public static Map<String, Integer> keysOf(List<FoundTune> tunes, int islandKey) {
        Map<String, Integer> out = new LinkedHashMap<>();
        for (FoundTune t : tunes) {
            out.put(t.learnedFrom(), Math.floorMod(t.notes().get(0), 12));
        }
        out.put(ThirteenthSong.RECORD, Math.floorMod(islandKey, 12));
        return out;
    }

    /** Steps between two keys on the circle of fifths, 0 to 6. */
    public static int fifths(int a, int b) {
        int k = Math.floorMod((b - a) * 7, 12);
        return Math.min(k, 12 - k);
    }

    /** Total key-change cost of a full running order (solos then the closer). */
    public static int cost(List<Slot> order) {
        int c = 0;
        for (int i = 1; i < order.size(); i++) {
            c += fifths(order.get(i - 1).key(), order.get(i).key());
        }
        return c;
    }

    private int keyOf(String song) {
        Integer k = keys.get(song);
        if (k == null) {
            throw new IllegalArgumentException("no key for " + song);
        }
        return k;
    }

    private boolean legalNext(List<Slot> order, String singer, String song) {
        if (!order.isEmpty() && order.get(order.size() - 1).singer().equals(singer)) {
            return false;
        }
        if (order.stream().anyMatch(s -> s.song().equals(song))) {
            return false;
        }
        Set<String> featured = new HashSet<>();
        order.forEach(s -> featured.add(s.singer()));
        featured.add(singer);
        int left = SOLOS - order.size() - 1;
        return repertoire.size() - featured.size() <= left;
    }

    private int search(List<Slot> order, int sofar, int bound, List<Slot> out) {
        if (sofar >= bound) {
            return bound;
        }
        if (order.size() == SOLOS) {
            int total = sofar + fifths(order.get(SOLOS - 1).key(), keyOf(closer));
            if (total < bound) {
                out.clear();
                out.addAll(order);
                out.add(new Slot(CHOIR, closer, keyOf(closer)));
                return total;
            }
            return bound;
        }
        for (Map.Entry<String, List<String>> e : repertoire.entrySet()) {
            for (String song : e.getValue()) {
                if (!legalNext(order, e.getKey(), song)) {
                    continue;
                }
                int k = keyOf(song);
                int step = order.isEmpty() ? 0 : fifths(order.get(order.size() - 1).key(), k);
                order.add(new Slot(e.getKey(), song, k));
                bound = search(order, sofar + step, bound, out);
                order.remove(order.size() - 1);
            }
        }
        return bound;
    }

    public QuestProgress quest() {
        return quest;
    }

    public Map<String, List<String>> repertoire() {
        return java.util.Collections.unmodifiableMap(repertoire);
    }

    /** The set list so far (solos, then the closer once sung). */
    public List<Slot> setList() {
        return List.copyOf(set);
    }

    public int best() {
        return best;
    }

    /** One smoothest legal running order, closer included. */
    public List<Slot> bestSet() {
        return bestSet;
    }

    public int evening() {
        return evening;
    }

    /** The last concert's result (CHEERED or ROUGH), or null while one is under way. */
    public Outcome result() {
        return result;
    }

    /** Audience warmth: {@link #WARMTH} less the key changes so far. */
    public int warmth() {
        return WARMTH - cost(set);
    }

    /** A graduate sings one of their songs next. */
    public Outcome perform(String eventId, String singer, String song) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (result != null) {
            return Outcome.OVER;
        }
        if (!repertoire.containsKey(singer)) {
            return Outcome.NOT_GRADUATE;
        }
        if (!keys.containsKey(song)) {
            return Outcome.UNKNOWN_SONG;
        }
        if (!repertoire.get(singer).contains(song)) {
            return Outcome.NOT_THEIRS;
        }
        if (set.size() == SOLOS) {
            return Outcome.SET_FULL;
        }
        if (!set.isEmpty() && set.get(set.size() - 1).singer().equals(singer)) {
            return Outcome.SAME_SINGER;
        }
        if (set.stream().anyMatch(s -> s.song().equals(song))) {
            return Outcome.ALREADY_SUNG;
        }
        if (!legalNext(set, singer, song)) {
            return Outcome.LEAVES_SOMEONE_OUT;
        }
        events.add(eventId);
        set.add(new Slot(singer, song, keyOf(song)));
        quest.apply(eventId, "perform", "solo");
        return Outcome.SUNG;
    }

    /** The choir closes on record thirteen; the green cheers if the set was within {@link #SLACK} of the best. */
    public Outcome close(String eventId) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (result != null) {
            return Outcome.OVER;
        }
        if (set.size() < SOLOS) {
            return Outcome.NOT_READY;
        }
        events.add(eventId);
        set.add(new Slot(CHOIR, closer, keyOf(closer)));
        result = cost(set) <= best + SLACK ? Outcome.CHEERED : Outcome.ROUGH;
        if (result == Outcome.CHEERED) {
            quest.apply(eventId, "cheer", "concert");
        }
        return result;
    }

    /** After a rough concert, the next evening starts a fresh set list. */
    public Outcome rerun() {
        if (result != Outcome.ROUGH) {
            return result == null ? Outcome.NOT_OVER : Outcome.OVER;
        }
        set.clear();
        result = null;
        evening++;
        return Outcome.RERUN;
    }

    /** Talks to Old Wick after the concert: the quest's talk step once the green has cheered. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", FirstWeek.WICK);
            return ConcertLines.THANKS;
        }
        return ConcertLines.line(this);
    }
}
