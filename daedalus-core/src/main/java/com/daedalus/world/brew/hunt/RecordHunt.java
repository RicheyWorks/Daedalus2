// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.hunt;

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
 * Chapter 3 of the Youtube Master Island story, the Ark Record Hunt (quest {@code q_ark_record_hunt}). When the
 * planet shattered, the arks' crates of seed-song records were flung across the broken shelf. Each record lies on a
 * seeded fragment (never the homestead). The player walks the rope bridges (1 stamina each), searches a fragment
 * (1 stamina) and carries every record found there into the homestead store, where the G33 Seed-Song Spring can
 * restore it. Stamina refills once per new day. The Archivist hums how far the nearest record is
 * ({@link #hint}). Quest: find 3 records, carry them home, tell the Archivist.
 */
public final class RecordHunt {
    public static final String QUEST_ID = "q_ark_record_hunt";
    public static final String ARCHIVIST = "archivist_tamsin";
    public static final int RECORDS_FOR_QUEST = 3;

    public enum Outcome { WALKED, FOUND, NOTHING_HERE, NO_BRIDGE, TIRED, RESTED, DUPLICATE, IGNORED }

    /** Result of an action; {@code found} lists records picked up by a search. */
    public record Step(Outcome outcome, int at, int stamina, List<String> found) {
        public Step {
            found = List.copyOf(found);
        }
    }

    /** The Archivist's reading: nearest unfound record, its distance in bridges and the first bridge to cross. */
    public record Hint(String record, int distance, int toward) {
    }

    private final FragmentMap map;
    private final int staminaPerDay;
    private final Map<String, Integer> where = new LinkedHashMap<>();
    private final Set<String> found = new HashSet<>();
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("find_record", "ark_record", RECORDS_FOR_QUEST),
            new QuestProgress.Step("return", "homestead", 1),
            new QuestProgress.Step("talk", ARCHIVIST, 1)));
    private int at = FragmentMap.HOME;
    private int stamina;
    private int day;

    /** Scatters {@code records} over {@code map}: distinct fragments while they last, never the homestead. */
    public RecordHunt(FragmentMap map, List<String> records, long seed, int staminaPerDay) {
        if (staminaPerDay < 1 || records == null || records.isEmpty()) {
            throw new IllegalArgumentException("need records and positive stamina");
        }
        this.map = map;
        this.staminaPerDay = staminaPerDay;
        this.stamina = staminaPerDay;
        SplittableRandom rng = new SplittableRandom(seed);
        List<Integer> pool = new ArrayList<>();
        for (String r : records) {
            if (pool.isEmpty()) {
                for (int f = 1; f < map.size(); f++) {
                    pool.add(f);
                }
            }
            if (where.containsKey(r)) {
                throw new IllegalArgumentException("duplicate record " + r);
            }
            where.put(r, pool.remove(rng.nextInt(pool.size())));
        }
    }

    public FragmentMap map() {
        return map;
    }

    public int at() {
        return at;
    }

    public int stamina() {
        return stamina;
    }

    public int day() {
        return day;
    }

    public QuestProgress quest() {
        return quest;
    }

    /** Where a record lies (host/debug view; the player only gets hints). */
    public int whereIs(String record) {
        return where.getOrDefault(record, -1);
    }

    public Set<String> found() {
        return Set.copyOf(found);
    }

    public int remaining() {
        return where.size() - found.size();
    }

    private boolean bad(String eventId) {
        return eventId == null || eventId.isBlank() || eventId.length() > 128;
    }

    /** Crosses one rope bridge. */
    public Step walk(String eventId, int to) {
        if (bad(eventId)) {
            return new Step(Outcome.IGNORED, at, stamina, List.of());
        }
        if (events.contains(eventId)) {
            return new Step(Outcome.DUPLICATE, at, stamina, List.of());
        }
        if (!map.bridged(at, to)) {
            return new Step(Outcome.NO_BRIDGE, at, stamina, List.of());
        }
        if (stamina < 1) {
            return new Step(Outcome.TIRED, at, stamina, List.of());
        }
        events.add(eventId);
        stamina--;
        at = to;
        if (at == FragmentMap.HOME && found.size() >= RECORDS_FOR_QUEST) {
            quest.apply(eventId, "return", "homestead");
        }
        return new Step(Outcome.WALKED, at, stamina, List.of());
    }

    /** Searches the current fragment; every record lying here goes into the plot store. */
    public Step search(String eventId, PlotState plot) {
        if (bad(eventId) || plot == null) {
            return new Step(Outcome.IGNORED, at, stamina, List.of());
        }
        if (events.contains(eventId)) {
            return new Step(Outcome.DUPLICATE, at, stamina, List.of());
        }
        if (stamina < 1) {
            return new Step(Outcome.TIRED, at, stamina, List.of());
        }
        events.add(eventId);
        stamina--;
        List<String> here = new ArrayList<>();
        where.forEach((r, f) -> {
            if (f == at && !found.contains(r)) {
                here.add(r);
            }
        });
        for (int i = 0; i < here.size(); i++) {
            String r = here.get(i);
            found.add(r);
            plot.add(r, 1);
            quest.apply(eventId + "#" + i, "find_record", "ark_record");
        }
        return new Step(here.isEmpty() ? Outcome.NOTHING_HERE : Outcome.FOUND, at, stamina, here);
    }

    /** Sleeps into {@code newDay} (must be later than the current day): stamina refills. */
    public Step rest(int newDay) {
        if (newDay <= day) {
            return new Step(Outcome.DUPLICATE, at, stamina, List.of());
        }
        day = newDay;
        stamina = staminaPerDay;
        return new Step(Outcome.RESTED, at, stamina, List.of());
    }

    /** The nearest unfound record from where the player stands (ties: first in record order), or null. */
    public Hint hint() {
        Hint best = null;
        for (var e : where.entrySet()) {
            if (found.contains(e.getKey())) {
                continue;
            }
            int d = map.distance(at, e.getValue());
            if (best == null || d < best.distance()) {
                best = new Hint(e.getKey(), d, map.nextStep(at, e.getValue()));
            }
        }
        return best;
    }

    /** Talks to the Archivist at the homestead: her line, and the quest's talk step when it is due. */
    public String talk(String eventId) {
        if (at == FragmentMap.HOME) {
            QuestProgress.Step due = quest.currentStep();
            if (due != null && due.type().equals("talk")) {
                quest.apply(eventId, "talk", ARCHIVIST);
                return ArchivistLines.THANKS;
            }
        }
        return ArchivistLines.line(this);
    }
}
