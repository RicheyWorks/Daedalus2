// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.school;

import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.letters.Destination;
import com.daedalus.world.brew.song.ThirteenthSong;
import com.daedalus.world.brew.week.FirstWeek;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 11 of the Youtube Master Island story, "The Song School" (quest {@code q_song_school}). Each pupil is set
 * {@link #SONGS_EACH} of the thirteen songs (the twelve ark records and the island's own, G94). A pupil's song is a
 * card on a Leitner shelf: introduced into box 1, then reviewed when due ({@link #INTERVALS} days after the last
 * review, by box). A review succeeds with chance aptitude - {@link #OVERDUE_PENALTY} per overdue day (seeded per
 * pupil, song and day); success moves the card up a box (to {@link #TOP_BOX} at most), a miss sends it back to box
 * 1. A card that reaches the top box is learned for good and leaves the review shelf. Old Wick has
 * {@link #LESSONS_PER_DAY} lessons a day for introductions and reviews. A pupil graduates with every set song in the
 * top box.
 */
public final class SongSchool {
    public static final String QUEST_ID = "q_song_school";
    public static final int SONGS_EACH = 4;
    public static final int LESSONS_PER_DAY = 6;
    public static final int TOP_BOX = 5;
    public static final List<Integer> INTERVALS = List.of(1, 2, 4, 8, 16);
    public static final double OVERDUE_PENALTY = 0.10;
    public static final int GRADUATES_NEEDED = 3;

    public enum Outcome { INTRODUCED, REMEMBERED, FORGOTTEN, TOO_SOON, NOT_INTRODUCED, ALREADY_INTRODUCED,
        NOT_SET, UNKNOWN_PUPIL, NO_LESSONS_LEFT, DUPLICATE, IGNORED }

    /** One pupil's song on the shelf. */
    public record Card(String pupil, String song, int box, int lastReview) {
        public int due() {
            return lastReview + INTERVALS.get(box - 1);
        }
    }

    private final Map<String, Pupil> pupils = new LinkedHashMap<>();
    private final Map<String, List<String>> set = new LinkedHashMap<>();
    private final Map<String, Card> cards = new LinkedHashMap<>();
    private final Set<String> graduates = new HashSet<>();
    private final Set<String> events = new HashSet<>();
    private final long seed;
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("introduce", "card", SONGS_EACH),
            new QuestProgress.Step("graduate", "pupil", GRADUATES_NEEDED),
            new QuestProgress.Step("talk", FirstWeek.WICK, 1)));
    private int day = 1;
    private int lessons;

    /** A school for these pupils; each is set {@link #SONGS_EACH} distinct songs (seeded) from {@code songs}. */
    public SongSchool(List<String> songs, List<Pupil> pupilList, long seed) {
        if (songs.size() < SONGS_EACH) {
            throw new IllegalArgumentException("need at least " + SONGS_EACH + " songs");
        }
        this.seed = seed;
        SplittableRandom rng = new SplittableRandom(seed);
        for (Pupil p : pupilList) {
            pupils.put(p.id(), p);
            List<String> pool = new ArrayList<>(songs);
            List<String> mine = new ArrayList<>();
            for (int i = 0; i < SONGS_EACH; i++) {
                mine.add(pool.remove(rng.nextInt(pool.size())));
            }
            set.put(p.id(), List.copyOf(mine));
        }
    }

    /** The thirteen songs: every ark record plus record thirteen. */
    public static List<String> thirteenSongs(List<FoundTune> tunes) {
        List<String> s = new ArrayList<>(tunes.stream().map(FoundTune::learnedFrom).toList());
        s.add(ThirteenthSong.RECORD);
        return List.copyOf(s);
    }

    /** One child from each far island (G97), seeded aptitude 0.60-0.95. */
    public static List<Pupil> fromFarIslands(List<Destination> destinations, long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0x5c400L);
        List<Pupil> out = new ArrayList<>();
        for (Destination d : destinations) {
            double apt = Math.round((0.60 + 0.35 * rng.nextDouble()) * 100) / 100.0;
            out.add(new Pupil("pupil_" + d.id(), "child from " + d.npc(), d.id(), apt));
        }
        return out;
    }

    public int day() {
        return day;
    }

    public QuestProgress quest() {
        return quest;
    }

    public List<Pupil> pupils() {
        return List.copyOf(pupils.values());
    }

    public List<String> songsFor(String pupilId) {
        return set.getOrDefault(pupilId, List.of());
    }

    public int lessonsLeft() {
        return LESSONS_PER_DAY - lessons;
    }

    public Card card(String pupilId, String song) {
        return cards.get(pupilId + "|" + song);
    }

    public Set<String> graduates() {
        return Set.copyOf(graduates);
    }

    /** Chance a review of this card succeeds today. */
    public double recallChance(Card c) {
        Pupil p = pupils.get(c.pupil());
        int overdue = Math.max(0, day - c.due());
        return Math.max(0.0, Math.min(1.0, p.aptitude() - OVERDUE_PENALTY * overdue));
    }

    /** Cards due today, most overdue first (Wick's lesson plan). */
    public List<Card> dueToday() {
        return cards.values().stream().filter(c -> c.box() < TOP_BOX && c.due() <= day)
                .sorted(Comparator.comparingInt(Card::due).thenComparing(Card::pupil).thenComparing(Card::song))
                .toList();
    }

    private Outcome guard(String eventId, String pupilId, String song) {
        if (eventId == null || eventId.isBlank() || eventId.length() > QuestProgress.MAX_EVENT_ID) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (!pupils.containsKey(pupilId)) {
            return Outcome.UNKNOWN_PUPIL;
        }
        if (!songsFor(pupilId).contains(song)) {
            return Outcome.NOT_SET;
        }
        return null;
    }

    /** Teaches a pupil a set song for the first time: it goes into box 1. One lesson. */
    public Outcome introduce(String eventId, String pupilId, String song) {
        Outcome g = guard(eventId, pupilId, song);
        if (g != null) {
            return g;
        }
        if (card(pupilId, song) != null) {
            return Outcome.ALREADY_INTRODUCED;
        }
        if (lessonsLeft() <= 0) {
            return Outcome.NO_LESSONS_LEFT;
        }
        events.add(eventId);
        lessons++;
        cards.put(pupilId + "|" + song, new Card(pupilId, song, 1, day));
        quest.apply(eventId, "introduce", "card");
        return Outcome.INTRODUCED;
    }

    /** Reviews a due card. One lesson; success moves it up a box, a miss sends it back to box 1. */
    public Outcome review(String eventId, String pupilId, String song) {
        Outcome g = guard(eventId, pupilId, song);
        if (g != null) {
            return g;
        }
        Card c = card(pupilId, song);
        if (c == null) {
            return Outcome.NOT_INTRODUCED;
        }
        if (c.box() == TOP_BOX || day < c.due()) {
            return Outcome.TOO_SOON;
        }
        if (lessonsLeft() <= 0) {
            return Outcome.NO_LESSONS_LEFT;
        }
        events.add(eventId);
        lessons++;
        double draw = new SplittableRandom(seed * 1_000_003L + (pupilId + "|" + song).hashCode() * 31L + day)
                .nextDouble();
        boolean ok = draw < recallChance(c);
        cards.put(pupilId + "|" + song, new Card(pupilId, song, ok ? Math.min(TOP_BOX, c.box() + 1) : 1, day));
        if (ok && !graduates.contains(pupilId) && songsFor(pupilId).stream()
                .allMatch(s -> card(pupilId, s) != null && card(pupilId, s).box() == TOP_BOX)) {
            graduates.add(pupilId);
            quest.apply("graduate-" + pupilId, "graduate", "pupil");
        }
        return ok ? Outcome.REMEMBERED : Outcome.FORGOTTEN;
    }

    /** Next school day: lessons reset. */
    public void nextDay() {
        day++;
        lessons = 0;
    }

    /** Talks to Old Wick: his line, and the quest's talk step when it is due. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", FirstWeek.WICK);
            return WickSchoolLines.THANKS;
        }
        return WickSchoolLines.line(this);
    }
}
