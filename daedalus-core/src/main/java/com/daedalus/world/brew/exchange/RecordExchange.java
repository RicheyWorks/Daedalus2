// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.exchange;

import com.daedalus.world.brew.FoundTune;
import com.daedalus.world.brew.story.SeedSongSpring;
import com.daedalus.world.colony.PlotState;
import com.daedalus.world.colony.QuestProgress;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Chapter 6 of the Youtube Master Island story, "The Record Exchange" (quest {@code q_record_exchange}). Neighbours
 * on the other fragments have rope, blank stones, eggs and fish, and no music since the shattering. A record mended
 * in chapter 2 ({@link SeedSongSpring}) can be pressed into one copy a day; a copy is bartered to a {@link Trader}
 * for their good. Price: one unit per note, +1 if the tune comes home (cadence); doubled if the tune is one the
 * trader wants today (seeded); halved (floor) for every copy of that tune the trader already holds, and a trader
 * refuses a copy worth nothing. Quest: four trades, two of them wanted tunes, then tell Pell.
 * In-game barter only; nothing here touches money or the colony ledger.
 */
public final class RecordExchange {
    public static final String QUEST_ID = "q_record_exchange";
    public static final String COPY_PREFIX = "Item_YTM_RecordCopy_";

    public enum Outcome { PRESSED, TRADED, NOT_RESTORED, PRESSED_TODAY, NO_COPY, UNKNOWN_TRADER, UNKNOWN_TUNE,
        REFUSED, DUPLICATE, IGNORED }

    /** Result of a trade: what was paid and whether the tune was wanted today. */
    public record Trade(Outcome outcome, String good, int amount, boolean wanted) {
    }

    private final SeedSongSpring songs;
    private final Map<String, FoundTune> tunesByRecord = new LinkedHashMap<>();
    private final Map<String, Trader> traders = new LinkedHashMap<>();
    private final long seed;
    private final Map<String, Integer> held = new HashMap<>();
    private final Set<String> pressedToday = new HashSet<>();
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("trade", "neighbour", 4),
            new QuestProgress.Step("trade_wanted", "neighbour", 2),
            new QuestProgress.Step("talk", "pell", 1)));
    private int day = 1;

    public RecordExchange(SeedSongSpring songs, List<FoundTune> tunes, List<Trader> traders, long seed) {
        this.songs = songs;
        this.seed = seed;
        tunes.forEach(t -> tunesByRecord.put(t.learnedFrom(), t));
        traders.forEach(t -> this.traders.put(t.id(), t));
    }

    public int day() {
        return day;
    }

    public QuestProgress quest() {
        return quest;
    }

    public List<Trader> traders() {
        return List.copyOf(traders.values());
    }

    /** The copy item for a record, e.g. {@code Item_YTM_RecordCopy_Item_YTM_Record_Alpine}. */
    public static String copyOf(String recordItem) {
        return COPY_PREFIX + recordItem;
    }

    /** Next day: every mended record can be pressed again and traders want new tunes. */
    public void nextDay() {
        day++;
        pressedToday.clear();
    }

    /** The records a trader wants today: seeded per (seed, day, trader), distinct, from all twelve. */
    public List<String> wantsToday(String traderId) {
        Trader t = traders.get(traderId);
        if (t == null) {
            return List.of();
        }
        List<String> pool = new ArrayList<>(tunesByRecord.keySet());
        SplittableRandom rng = new SplittableRandom(seed * 7_919L + day * 104_729L + traderId.hashCode());
        List<String> out = new ArrayList<>();
        for (int i = 0; i < t.wants() && !pool.isEmpty(); i++) {
            out.add(pool.remove(rng.nextInt(pool.size())));
        }
        return out;
    }

    /** What a copy of this record is worth to this trader right now (0 = refused). */
    public int price(String traderId, String recordItem) {
        FoundTune tune = tunesByRecord.get(recordItem);
        if (tune == null || !traders.containsKey(traderId)) {
            return 0;
        }
        List<Integer> n = tune.notes();
        int p = n.size() + (n.get(0).equals(n.get(n.size() - 1)) ? 1 : 0);
        if (wantsToday(traderId).contains(recordItem)) {
            p *= 2;
        }
        return p >> held.getOrDefault(traderId + "|" + recordItem, 0);
    }

    /** Presses today's copy of a mended record into the plot store. */
    public Outcome press(String eventId, String recordItem, PlotState plot) {
        if (eventId == null || eventId.isBlank() || eventId.length() > 128 || plot == null) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        if (!tunesByRecord.containsKey(recordItem)) {
            return Outcome.UNKNOWN_TUNE;
        }
        if (!songs.isRestored(recordItem)) {
            return Outcome.NOT_RESTORED;
        }
        if (pressedToday.contains(recordItem)) {
            return Outcome.PRESSED_TODAY;
        }
        events.add(eventId);
        pressedToday.add(recordItem);
        plot.add(copyOf(recordItem), 1);
        return Outcome.PRESSED;
    }

    /** Barters one copy from the store to a trader for their good. */
    public Trade trade(String eventId, String traderId, String recordItem, PlotState plot) {
        if (eventId == null || eventId.isBlank() || eventId.length() > 128 || plot == null) {
            return new Trade(Outcome.IGNORED, null, 0, false);
        }
        if (events.contains(eventId)) {
            return new Trade(Outcome.DUPLICATE, null, 0, false);
        }
        Trader t = traders.get(traderId);
        if (t == null) {
            return new Trade(Outcome.UNKNOWN_TRADER, null, 0, false);
        }
        if (!tunesByRecord.containsKey(recordItem)) {
            return new Trade(Outcome.UNKNOWN_TUNE, null, 0, false);
        }
        if (plot.count(copyOf(recordItem)) < 1) {
            return new Trade(Outcome.NO_COPY, null, 0, false);
        }
        int p = price(traderId, recordItem);
        boolean wanted = wantsToday(traderId).contains(recordItem);
        if (p <= 0) {
            return new Trade(Outcome.REFUSED, t.good(), 0, wanted);
        }
        events.add(eventId);
        plot.take(copyOf(recordItem), 1);
        plot.add(t.good(), p);
        held.merge(traderId + "|" + recordItem, 1, Integer::sum);
        quest.apply(eventId, "trade", "neighbour");
        if (wanted) {
            quest.apply(eventId + "#w", "trade_wanted", "neighbour");
        }
        return new Trade(Outcome.TRADED, t.good(), p, wanted);
    }

    /** Talks to Pell: his line, and the quest's talk step when it is due. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", "pell");
            return TraderLines.THANKS;
        }
        return TraderLines.line(this);
    }
}
