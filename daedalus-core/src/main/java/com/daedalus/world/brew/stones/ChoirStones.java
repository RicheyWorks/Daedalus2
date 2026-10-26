// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.stones;

import com.daedalus.world.brew.hunt.FragmentMap;
import com.daedalus.world.brew.story.SeedSongSpring;
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
 * Chapter 4 of the Youtube Master Island story, "Choir Stones" (quest {@code q_choir_stones}). The shelf still
 * trembles: every night a seeded tremor frays a few rope bridges, and a bridge at 0 snaps. A record mended in
 * chapter 2 ({@link SeedSongSpring}) can be carved into a choir stone on a fragment (one stone per record, one per
 * fragment, costs one {@link #STONE}). A stone hums over every bridge with an end closer than its range
 * ({@link #range}, from the brew tier), and a humming bridge does not fray. Stones are few, so where they go is the
 * puzzle: keep every fragment linked to the homestead. Quest: carve 2 stones, hold 3 nights with nothing cut off,
 * tell Mason Hale.
 */
public final class ChoirStones {
    public static final String QUEST_ID = "q_choir_stones";
    public static final String MASON = "mason_hale";
    public static final String STONE = "choir_stone_blank";

    public enum Outcome { CARVED, NOT_RESTORED, RECORD_USED, FRAGMENT_TAKEN, NO_STONE, UNKNOWN_FRAGMENT, DUPLICATE,
        IGNORED }

    /** A carved stone: where it stands, which record's tune it hums, and its range in bridges. */
    public record Stone(int fragment, String record, int range) {
    }

    /** One tremor night: bridges frayed, bridges that snapped, fragments cut off afterwards, and whether it held. */
    public record Night(int night, List<BridgeLedger.Bridge> frayed, List<BridgeLedger.Bridge> snapped,
            Set<Integer> cutOff, boolean held) {
        public Night {
            frayed = List.copyOf(frayed);
            snapped = List.copyOf(snapped);
            cutOff = Set.copyOf(cutOff);
        }
    }

    private final BridgeLedger ledger;
    private final SeedSongSpring songs;
    private final long seed;
    private final Map<Integer, Stone> stones = new LinkedHashMap<>();
    private final Set<String> carvedRecords = new HashSet<>();
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("carve", "choir_stone", 2),
            new QuestProgress.Step("hold", "night", 3),
            new QuestProgress.Step("talk", MASON, 1)));
    private int lastNight;
    private int heldNights;
    private Night last;

    public ChoirStones(FragmentMap map, SeedSongSpring songs, long seed) {
        this.ledger = new BridgeLedger(map);
        this.songs = songs;
        this.seed = seed;
    }

    /** Hum range in bridges for a brew tier 1-4: T1 1, T2-T3 2, T4 3. */
    public static int range(int tier) {
        return Math.max(1, Math.min(4, tier)) / 2 + 1;
    }

    /** Bridges a tremor frays per night on a map of {@code n} fragments. */
    public static int fraysPerNight(int n) {
        return 1 + n / 4;
    }

    public BridgeLedger ledger() {
        return ledger;
    }

    public QuestProgress quest() {
        return quest;
    }

    public List<Stone> stones() {
        return List.copyOf(stones.values());
    }

    public int heldNights() {
        return heldNights;
    }

    /** The last night run, or null. */
    public Night lastNight() {
        return last;
    }

    /** Carves a mended record's tune (brewed at {@code tier}) into a stone on {@code fragment}. */
    public Outcome carve(String eventId, int fragment, String recordItem, int tier, PlotState plot) {
        if (eventId == null || eventId.isBlank() || eventId.length() > 128 || plot == null) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (fragment < 0 || fragment >= ledger.map().size()) {
            return Outcome.UNKNOWN_FRAGMENT;
        }
        if (!songs.isRestored(recordItem)) {
            return Outcome.NOT_RESTORED;
        }
        if (carvedRecords.contains(recordItem)) {
            return Outcome.RECORD_USED;
        }
        if (stones.containsKey(fragment)) {
            return Outcome.FRAGMENT_TAKEN;
        }
        if (plot.count(STONE) < 1) {
            return Outcome.NO_STONE;
        }
        events.add(eventId);
        plot.take(STONE, 1);
        carvedRecords.add(recordItem);
        stones.put(fragment, new Stone(fragment, recordItem, range(tier)));
        quest.apply(eventId, "carve", "choir_stone");
        return Outcome.CARVED;
    }

    /** True when some stone hums over this bridge (an end closer than the stone's range). */
    public boolean humming(BridgeLedger.Bridge b) {
        FragmentMap m = ledger.map();
        for (Stone s : stones.values()) {
            int d = Math.min(m.distance(s.fragment(), b.a()), m.distance(s.fragment(), b.b()));
            if (d < s.range()) {
                return true;
            }
        }
        return false;
    }

    /** Runs tremor night {@code n} (must be later than the last one); returns null for a repeat or earlier night. */
    public Night night(int n) {
        if (n <= lastNight) {
            return null;
        }
        lastNight = n;
        SplittableRandom rng = new SplittableRandom(seed * 1_000_003L + n);
        List<BridgeLedger.Bridge> frayed = new ArrayList<>();
        List<BridgeLedger.Bridge> snapped = new ArrayList<>();
        int k = fraysPerNight(ledger.map().size());
        for (int i = 0; i < k; i++) {
            List<BridgeLedger.Bridge> live = ledger.intactBridges();
            if (live.isEmpty()) {
                break;
            }
            BridgeLedger.Bridge b = live.get(rng.nextInt(live.size()));
            if (humming(b)) {
                continue;
            }
            frayed.add(b);
            if (ledger.fray(b)) {
                snapped.add(b);
            }
        }
        Set<Integer> cut = ledger.cutOff();
        boolean held = cut.isEmpty();
        if (held) {
            heldNights++;
            quest.apply("night-" + n, "hold", "night");
        }
        last = new Night(n, frayed, snapped, cut, held);
        return last;
    }

    /** Talks to Mason Hale: her line, and the quest's talk step when it is due. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", MASON);
            return MasonLines.THANKS;
        }
        return MasonLines.line(this);
    }
}
