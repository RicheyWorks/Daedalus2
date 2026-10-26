// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.round;

import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.school.SongSchool;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

/**
 * Chapter 13 of the Youtube Master Island story, "The Harbour Round" (quest {@code q_harbour_round}). The children
 * sing a round for the ark coming in from the far islands. The lead voice sings a song's notes over and over; each
 * further voice ({@link Entry}) comes in some beats later and at a harmony interval above it. At every beat, each pair
 * of sounding notes is consonant (interval class in {@link #CONSONANT}) or a clash. Harmony is consonant pairs over
 * all pairs across one pass of the song: sweet at {@link #SWEET} or better, fair at {@link #FAIR}, sour below.
 * {@link #best} searches every round exactly. Rehearse on the green, then sing a sweet round of at least
 * {@link #HARBOUR_VOICES} voices at the harbour.
 */
public final class HarbourRound {
    public static final String QUEST_ID = "q_harbour_round";
    public static final String DOV = "dov";
    public static final Set<Integer> CONSONANT = Set.of(0, 3, 4, 5, 7, 8, 9);
    /** Harmony intervals a voice may enter at: unison, minor and major 3rd, 4th, 5th, minor and major 6th. */
    public static final List<Integer> INTERVALS = List.of(0, 3, 4, 5, 7, 8, 9);
    public static final double SWEET = 0.75;
    public static final double FAIR = 0.5;
    public static final int MAX_VOICES = 4;
    public static final int HARBOUR_VOICES = 3;
    public static final int REHEARSALS = 3;

    public enum Outcome { SWEET, FAIR, SOUR, UNKNOWN_SONG, NOT_KNOWN, TOO_MANY_VOICES, TOO_FEW_VOICES, BAD_ENTRY,
        DUPLICATE, IGNORED }

    /** A voice after the lead: comes in {@code delay} beats later, {@code interval} semitones above. */
    public record Entry(int delay, int interval) {
    }

    /** The best round for a song and voice count. */
    public record Best(List<Entry> entries, double harmony) {
        public Best {
            entries = List.copyOf(entries);
        }
    }

    private final Map<String, List<Integer>> notes = new LinkedHashMap<>();
    private final Set<String> known;
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("rehearse", "round", REHEARSALS),
            new QuestProgress.Step("sing", "harbour", 1),
            new QuestProgress.Step("talk", DOV, 1)));
    private Outcome last;
    private double lastHarmony;

    /** A round book: each song's notes (pitch classes), and the songs the children know. */
    public HarbourRound(Map<String, List<Integer>> songNotes, Set<String> known) {
        songNotes.forEach((k, v) -> {
            if (v.size() < 2) {
                throw new IllegalArgumentException(k + " is too short to round");
            }
            notes.put(k, List.copyOf(v));
        });
        this.known = Set.copyOf(known);
    }

    /** Every found tune's notes, keyed by its record. */
    public static Map<String, List<Integer>> notesOf(List<FoundTune> tunes) {
        Map<String, List<Integer>> out = new LinkedHashMap<>();
        tunes.forEach(t -> out.put(t.learnedFrom(), t.notes()));
        return out;
    }

    /** The round book for a Song School: the songs its graduates know. */
    public static HarbourRound fromSchool(SongSchool school, List<FoundTune> tunes) {
        Set<String> known = new TreeSet<>();
        school.graduates().forEach(g -> known.addAll(school.songsFor(g)));
        Map<String, List<Integer>> n = notesOf(tunes);
        known.retainAll(n.keySet());
        return new HarbourRound(n, known);
    }

    /** Harmony of a round: consonant pairs over all pairs, beat by beat over one pass of the song. */
    public static double harmony(List<Integer> song, List<Entry> entries) {
        int n = song.size();
        int good = 0;
        int all = 0;
        for (int t = 0; t < n; t++) {
            List<Integer> sounding = new ArrayList<>();
            sounding.add(Math.floorMod(song.get(t), 12));
            for (Entry e : entries) {
                sounding.add(Math.floorMod(song.get(Math.floorMod(t - e.delay(), n)) + e.interval(), 12));
            }
            for (int i = 0; i < sounding.size(); i++) {
                for (int j = i + 1; j < sounding.size(); j++) {
                    all++;
                    if (CONSONANT.contains(Math.floorMod(sounding.get(i) - sounding.get(j), 12))) {
                        good++;
                    }
                }
            }
        }
        return all == 0 ? 1.0 : (double) good / all;
    }

    public static Outcome grade(double harmony) {
        return harmony >= SWEET ? Outcome.SWEET : harmony >= FAIR ? Outcome.FAIR : Outcome.SOUR;
    }

    /** Entries are legal when each delay is 1..length-1, all different, and each interval is in {@link #INTERVALS}. */
    public static boolean legal(int length, List<Entry> entries) {
        Set<Integer> delays = new HashSet<>();
        for (Entry e : entries) {
            if (e.delay() < 1 || e.delay() >= length || !delays.add(e.delay()) || !INTERVALS.contains(e.interval())) {
                return false;
            }
        }
        return true;
    }

    /** The sweetest round of {@code voices} voices for a song (exact; ties go to the earliest entries found). */
    public Best best(String song, int voices) {
        List<Integer> n = notes.get(song);
        if (n == null || voices < 2 || voices > Math.min(MAX_VOICES, n.size())) {
            throw new IllegalArgumentException("no round of " + voices + " for " + song);
        }
        Best[] top = {new Best(List.of(), -1)};
        search(n, voices - 1, 1, new ArrayList<>(), top);
        return top[0];
    }

    private static void search(List<Integer> n, int left, int minDelay, List<Entry> cur, Best[] top) {
        if (left == 0) {
            double h = harmony(n, cur);
            if (h > top[0].harmony() + 1e-12) {
                top[0] = new Best(cur, h);
            }
            return;
        }
        for (int d = minDelay; d < n.size(); d++) {
            for (int iv : INTERVALS) {
                cur.add(new Entry(d, iv));
                search(n, left - 1, d + 1, cur, top);
                cur.remove(cur.size() - 1);
            }
        }
    }

    public QuestProgress quest() {
        return quest;
    }

    public Set<String> known() {
        return known;
    }

    public List<Integer> notes(String song) {
        return notes.get(song);
    }

    /** The last rehearsal or harbour round's grade, or null. */
    public Outcome last() {
        return last;
    }

    public double lastHarmony() {
        return lastHarmony;
    }

    private Outcome guard(String eventId, String song, List<Entry> entries, int minVoices) {
        if (eventId == null || eventId.isBlank()) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (!notes.containsKey(song)) {
            return Outcome.UNKNOWN_SONG;
        }
        if (!known.contains(song)) {
            return Outcome.NOT_KNOWN;
        }
        if (entries.size() + 1 > MAX_VOICES) {
            return Outcome.TOO_MANY_VOICES;
        }
        if (entries.size() + 1 < minVoices) {
            return Outcome.TOO_FEW_VOICES;
        }
        if (!legal(notes.get(song).size(), entries)) {
            return Outcome.BAD_ENTRY;
        }
        return null;
    }

    private Outcome perform(String eventId, String song, List<Entry> entries) {
        events.add(eventId);
        lastHarmony = harmony(notes.get(song), entries);
        last = grade(lastHarmony);
        return last;
    }

    /** Rehearses a round on the green (at least two voices). Every rehearsal counts toward the quest. */
    public Outcome rehearse(String eventId, String song, List<Entry> entries) {
        Outcome g = guard(eventId, song, entries, 2);
        if (g != null) {
            return g;
        }
        Outcome o = perform(eventId, song, entries);
        quest.apply(eventId, "rehearse", "round");
        return o;
    }

    /** Sings at the harbour for the ark (at least {@link #HARBOUR_VOICES} voices). Only a sweet round counts. */
    public Outcome sing(String eventId, String song, List<Entry> entries) {
        Outcome g = guard(eventId, song, entries, HARBOUR_VOICES);
        if (g != null) {
            return g;
        }
        Outcome o = perform(eventId, song, entries);
        if (o == Outcome.SWEET) {
            quest.apply(eventId, "sing", "harbour");
        }
        return o;
    }

    /** Talks to Fisher Dov on the jetty: the quest's talk step once the harbour round was sweet. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", DOV);
            return DovRoundLines.THANKS;
        }
        return DovRoundLines.line(this);
    }
}
