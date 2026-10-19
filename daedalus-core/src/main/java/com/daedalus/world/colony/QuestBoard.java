// SPDX-License-Identifier: MIT

package com.daedalus.world.colony;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Binds day-book requests to PORT09 quest progress (the "NPC binding pending" of WZ14).
 *
 * <p>A request whose NPC gives a quest opens that quest for the plot. The quest's steps are: first
 * {@code deliver -> <npc>} (filling the news-board request is how the player meets the quest giver), then each story
 * step of the population plan as {@code story -> <questId>#<n>}, advanced by the host when the story beat happens.
 * Filling a request takes one of each wanted item from the store and pays one of the item the island cannot make.
 * Every fill has an event id and counts once (the same id twice is {@code DUPLICATE}, and nothing moves).
 */
public final class QuestBoard {
    public static final String DELIVER = "deliver";
    public static final String STORY = "story";

    /** Outcome of filling one request. */
    public enum Fill { FILLED, DUPLICATE, MISSING_ITEMS, IGNORED }

    public record FillResult(Fill fill, String questId, QuestProgress.Result quest) {
    }

    private final Cast cast;
    private final Map<String, QuestProgress> open = new LinkedHashMap<>();
    private final Set<String> fills = new HashSet<>();

    public QuestBoard(Cast cast) {
        this.cast = cast;
    }

    /** PORT09 steps for a quest of the plan: deliver to its giver, then its story steps in order (max 32). */
    public static List<QuestProgress.Step> stepsOf(Cast.QuestDef q) {
        List<QuestProgress.Step> s = new ArrayList<>();
        s.add(new QuestProgress.Step(DELIVER, q.giverType(), 1));
        for (int i = 0; i < q.steps().size(); i++) {
            s.add(new QuestProgress.Step(STORY, q.id() + "#" + (i + 1), 1));
        }
        return s;
    }

    /** Opens (once) the quest a request carries; returns its progress or null if the request has no quest. */
    public QuestProgress openFor(DayBook.Request r) {
        if (r.questId() == null) {
            return null;
        }
        return open.computeIfAbsent(r.questId(), id -> cast.quests().stream().filter(q -> q.id().equals(id)).findFirst()
                .map(q -> new QuestProgress(stepsOf(q))).orElse(null));
    }

    /**
     * Fill a request from the plot store. {@code eventId} must be unique per fill (e.g.
     * {@code "daybook:<deed>:<day>:<npc>"}); a repeat is {@code DUPLICATE} and changes nothing.
     */
    public FillResult fill(String eventId, DayBook.Request r, PlotState plot) {
        if (eventId == null || eventId.isEmpty() || eventId.length() > QuestProgress.MAX_EVENT_ID) {
            return new FillResult(Fill.IGNORED, r.questId(), null);
        }
        if (fills.contains(eventId)) {
            return new FillResult(Fill.DUPLICATE, r.questId(), null);
        }
        for (String w : r.wants()) {
            if (plot.count(w) < 1) {
                return new FillResult(Fill.MISSING_ITEMS, r.questId(), null);
            }
        }
        fills.add(eventId);
        r.wants().forEach(w -> plot.take(w, 1));
        plot.add(r.pays(), 1);
        QuestProgress q = openFor(r);
        QuestProgress.Result qr = q == null ? null : q.apply(eventId, DELIVER, r.npc());
        return new FillResult(Fill.FILLED, r.questId(), qr);
    }

    /** Story beat of an open quest (step n, 1-based), from the host. */
    public QuestProgress.Result story(String eventId, String questId, int n) {
        QuestProgress q = open.get(questId);
        return q == null ? QuestProgress.Result.IGNORED : q.apply(eventId, STORY, questId + "#" + n);
    }

    public Map<String, QuestProgress> open() {
        return Collections.unmodifiableMap(open);
    }
}
