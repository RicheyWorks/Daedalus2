// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.song;

import com.daedalus.world.brew.BrewBench;
import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.MelodyBrew;
import com.daedalus.world.brew.PitchTable;
import com.daedalus.world.brew.hunt.RecordHunt;
import com.daedalus.world.brew.supper.Guest;
import com.daedalus.world.brew.supper.HomecomingSupper;
import com.daedalus.world.colony.PlotState;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 9 of the Youtube Master Island story, "The Thirteenth Song" (quest {@code q_thirteenth_song}). Each supper
 * guest offers one verse: a step from their favourite record (seeded). The island's own song is a 4-5 herb order
 * on the {@link PitchTable#ISLAND_CANON} whose steps each use a different gathered verse, that comes home (last note
 * = first), and whose step pattern is none of the ark tunes' (so not a transposed copy either). The constructor
 * re-draws the verses until such a song exists. Brew it once at a bench that knows it (G25), then Archivist Tamsin
 * catalogues it and presses record thirteen.
 */
public final class ThirteenthSong {
    public static final String QUEST_ID = "q_thirteenth_song";
    public static final String RECORD = "Item_YTM_Record_IslandHome";
    public static final String NAME = "Tune_island_home";
    public static final String TONIC = "Item_YTM_Tonic_Found_island_home";
    public static final int VERSES_NEEDED = 5;
    public static final int MIN_NOTES = 4;
    public static final int MAX_NOTES = 5;
    public static final int STAGE = 3;
    public static final int MAX_DRAWS = 256;

    /** The twelve island herbs in canon order (pitch class = index). */
    public static final List<String> HERBS = List.of("Doleaf", "Sharpcress", "Rebell", "Flatfern", "Mimint",
            "Fasage", "Hushmoss", "Solthorn", "Gloryroot", "Lavine", "Dronebloom", "Tisquill");

    public enum Outcome { GATHERED, COMPOSED, BREWED, WRONG_LENGTH, UNKNOWN_HERB, NO_HOME, NOT_NEW, NOT_OFFERED,
        NOT_GATHERED, UNKNOWN_GUEST, ALREADY_GATHERED, ALREADY_COMPOSED, NOT_COMPOSED, ALREADY_BREWED, MISSING_HERBS,
        DUPLICATE, IGNORED }

    private final Map<String, Verse> offers = new LinkedHashMap<>();
    private final Map<String, Verse> gathered = new LinkedHashMap<>();
    private final Set<List<Integer>> arkPatterns = new HashSet<>();
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("gather", "verse", VERSES_NEEDED),
            new QuestProgress.Step("compose", "song", 1),
            new QuestProgress.Step("brew", "song", 1),
            new QuestProgress.Step("talk", RecordHunt.ARCHIVIST, 1)));
    private FoundTune song;
    private boolean brewed;
    private boolean pressed;

    public ThirteenthSong(HomecomingSupper supper, List<FoundTune> tunes, long seed) {
        Map<String, List<Integer>> stepsByRecord = new LinkedHashMap<>();
        for (FoundTune t : tunes) {
            List<Integer> s = steps(t.notes());
            stepsByRecord.put(t.learnedFrom(), s);
            arkPatterns.add(s);
        }
        SplittableRandom rng = new SplittableRandom(seed);
        for (int draw = 0; draw < MAX_DRAWS; draw++) {
            offers.clear();
            for (Guest g : supper.guests()) {
                String rec = supper.favouriteTune(g.id());
                List<Integer> s = stepsByRecord.getOrDefault(rec, List.of()).stream().filter(x -> x != 0).toList();
                if (!s.isEmpty()) {
                    offers.put(g.id(), new Verse(g.id(), rec, s.get(rng.nextInt(s.size()))));
                }
            }
            if (solve(List.copyOf(offers.values())) != null) {
                return;
            }
        }
        throw new IllegalStateException("no thirteenth song in " + MAX_DRAWS + " draws");
    }

    /** Signed steps between consecutive pitch classes ({@link MelodyBrew#step}). */
    public static List<Integer> steps(List<Integer> notes) {
        List<Integer> out = new ArrayList<>();
        for (int i = 1; i < notes.size(); i++) {
            out.add(MelodyBrew.step(notes.get(i - 1), notes.get(i)));
        }
        return out;
    }

    private List<Integer> solve(List<Verse> pool) {
        for (int n = MIN_NOTES - 1; n <= MAX_NOTES - 1; n++) {
            List<Integer> r = search(pool, new ArrayList<>(), new boolean[pool.size()], n);
            if (r != null) {
                return r;
            }
        }
        return null;
    }

    private List<Integer> search(List<Verse> pool, List<Integer> acc, boolean[] used, int n) {
        if (acc.size() == n) {
            int sum = acc.stream().mapToInt(Integer::intValue).sum();
            return Math.floorMod(sum, 12) == 0 && !arkPatterns.contains(acc) ? List.copyOf(acc) : null;
        }
        for (int i = 0; i < pool.size(); i++) {
            if (used[i]) {
                continue;
            }
            used[i] = true;
            acc.add(pool.get(i).step());
            List<Integer> r = search(pool, acc, used, n);
            acc.remove(acc.size() - 1);
            used[i] = false;
            if (r != null) {
                return r;
            }
        }
        return null;
    }

    /** True when every step can be paired with a different verse in the pool. */
    private static boolean covered(List<Integer> steps, List<Verse> pool) {
        return cover(steps, 0, pool, new boolean[pool.size()]);
    }

    private static boolean cover(List<Integer> steps, int i, List<Verse> pool, boolean[] used) {
        if (i == steps.size()) {
            return true;
        }
        for (int j = 0; j < pool.size(); j++) {
            if (!used[j] && pool.get(j).step() == steps.get(i)) {
                used[j] = true;
                if (cover(steps, i + 1, pool, used)) {
                    return true;
                }
                used[j] = false;
            }
        }
        return false;
    }

    /** Herb names for a step pattern starting on Doleaf. */
    public static List<String> herbsFor(List<Integer> steps) {
        List<String> out = new ArrayList<>();
        int pc = 0;
        out.add(HERBS.get(pc));
        for (int s : steps) {
            pc = Math.floorMod(pc + s, 12);
            out.add(HERBS.get(pc));
        }
        return out;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Every guest's verse (what each would offer if asked). */
    public List<Verse> offers() {
        return List.copyOf(offers.values());
    }

    public List<Verse> gathered() {
        return List.copyOf(gathered.values());
    }

    /** The composed song as a found tune (learned from record thirteen), or null before it is composed. */
    public FoundTune song() {
        return song;
    }

    /** A herb order that works with the verses gathered so far, or null if none does yet. */
    public List<String> hint() {
        List<Integer> s = solve(List.copyOf(gathered.values()));
        return s == null ? null : herbsFor(s);
    }

    private Outcome guard(String eventId) {
        if (eventId == null || eventId.isBlank() || eventId.length() > QuestProgress.MAX_EVENT_ID) {
            return Outcome.IGNORED;
        }
        return events.contains(eventId) ? Outcome.DUPLICATE : null;
    }

    /** Asks a guest for their verse. */
    public Outcome ask(String eventId, String guestId) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        Verse v = offers.get(guestId);
        if (v == null) {
            return Outcome.UNKNOWN_GUEST;
        }
        if (gathered.containsKey(guestId)) {
            return Outcome.ALREADY_GATHERED;
        }
        events.add(eventId);
        gathered.put(guestId, v);
        quest.apply(eventId, "gather", "verse");
        return Outcome.GATHERED;
    }

    /** Checks a herb order against the rules without composing it. */
    public Outcome check(List<String> herbs) {
        if (herbs == null || herbs.size() < MIN_NOTES || herbs.size() > MAX_NOTES) {
            return Outcome.WRONG_LENGTH;
        }
        List<Integer> notes = new ArrayList<>();
        for (String h : herbs) {
            var pc = PitchTable.ISLAND_CANON.pitchOf(h);
            if (pc.isEmpty()) {
                return Outcome.UNKNOWN_HERB;
            }
            notes.add(pc.get());
        }
        if (!notes.get(0).equals(notes.get(notes.size() - 1))) {
            return Outcome.NO_HOME;
        }
        List<Integer> s = steps(notes);
        if (arkPatterns.contains(s)) {
            return Outcome.NOT_NEW;
        }
        if (s.contains(0) || !covered(s, List.copyOf(gathered.values()))) {
            return Outcome.NOT_OFFERED;
        }
        return Outcome.COMPOSED;
    }

    /** Composes the island's song from this herb order (once). */
    public Outcome compose(String eventId, List<String> herbs) {
        Outcome g = guard(eventId);
        if (g != null) {
            return g;
        }
        if (song != null) {
            return Outcome.ALREADY_COMPOSED;
        }
        if (gathered.size() < VERSES_NEEDED) {
            return Outcome.NOT_GATHERED;
        }
        Outcome c = check(herbs);
        if (c != Outcome.COMPOSED) {
            return c;
        }
        events.add(eventId);
        List<Integer> notes = herbs.stream().map(h -> PitchTable.ISLAND_CANON.pitchOf(h).orElseThrow()).toList();
        MelodyBrew.Tonic t = MelodyBrew.brew(herbs.stream().map(h -> new MelodyBrew.Ingredient(h, STAGE)).toList());
        song = new FoundTune(NAME, "island_home", herbs, notes, t.melody(), t.effect(),
                "everyone on the island hums along", TONIC, RECORD);
        quest.apply(eventId, "compose", "song");
        return Outcome.COMPOSED;
    }

    /** Brews the song once at a bench that knows it, taking its herbs from the store. */
    public BrewBench.Brew brew(String eventId, PlotState plot) {
        Outcome g = plot == null ? Outcome.IGNORED : guard(eventId);
        if (g != null || song == null || brewed) {
            return null;
        }
        BrewBench bench = new BrewBench(PitchTable.ISLAND_CANON, List.of(song));
        bench.playRecord(RECORD);
        BrewBench.Brew b = bench.brew(eventId, song.herbs().stream().map(h -> new MelodyBrew.Ingredient(h, STAGE))
                .toList(), plot);
        if (b.outcome() != BrewBench.Outcome.BREWED) {
            return b;
        }
        events.add(eventId);
        brewed = true;
        quest.apply(eventId, "brew", "song");
        return b;
    }

    public boolean brewed() {
        return brewed;
    }

    /** Talks to Archivist Tamsin: once the song is brewed she catalogues it and presses record thirteen. */
    public String talk(String eventId, PlotState plot) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk") && plot != null && !pressed) {
            quest.apply(eventId, "talk", RecordHunt.ARCHIVIST);
            pressed = true;
            plot.add(RECORD, 1);
            return TamsinLines.THANKS;
        }
        return TamsinLines.line(this);
    }
}
