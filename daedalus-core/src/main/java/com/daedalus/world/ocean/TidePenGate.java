// SPDX-License-Identifier: MIT
package com.daedalus.world.ocean;

import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/**
 * Tide-Pen rule (data/ocean/tidepen.json): a creature may be penned only after the actor has settled its care.
 *
 * <p>This class is a pure decision. It holds no state, stores nothing and grants nothing. A trusted host gives it the
 * care events it has already recorded for one actor and one creature, and it answers whether {@code settled_care}
 * holds and whether an action is allowed. Leaving a creature wild is always allowed. This is a fantasy rule, not
 * biology.
 *
 * <p>{@code settled_care} holds when all of these are true:
 * <ul>
 *   <li>the actor fed the creature its own food at least {@code feedingsMin} times, on at least
 *       {@code distinctDaysMin} different days;</li>
 *   <li>there are no more than {@code harmEventsMax} harm events;</li>
 *   <li>at least {@code habitatPlantedMin} of its habitat plants were planted in the pen.</li>
 * </ul>
 * Events are deduplicated by request id, so a replayed event counts once (the same pattern as LivingWorld
 * receipts).
 */
public final class TidePenGate {

    public enum Kind { FEED, HARM, PLANT }

    public enum Action { ENCLOSE, CAPTURE, LEAVE_WILD, FEED }

    /** One care event the host recorded for an actor and a creature. {@code item} is the food or the plant. */
    public record CareEvent(String requestId, Kind kind, int day, String item) {
        public CareEvent {
            Objects.requireNonNull(requestId, "requestId");
            Objects.requireNonNull(kind, "kind");
        }
    }

    /** A species' needs, as listed in tidepen.json residents. */
    public record Species(String id, Set<String> food, Set<String> habitat) { }

    /** The thresholds from tidepen.json settled_care.requires. */
    public record Rule(int feedingsMin, int distinctDaysMin, int harmEventsMax, int habitatPlantedMin) {
        public static final Rule DEFAULT = new Rule(3, 2, 0, 1);
    }

    /** The answer, with a reason a player could read. */
    public record Decision(boolean allowed, String reason) { }

    private TidePenGate() { }

    /** Whether settled_care holds for these events. */
    public static Decision settled(Species s, List<CareEvent> events, Rule r) {
        Set<String> seen = new HashSet<>();
        int feeds = 0, harms = 0;
        Set<Integer> days = new HashSet<>();
        Set<String> planted = new HashSet<>();
        for (CareEvent e : events) {
            if (!seen.add(e.requestId())) {
                continue;                                   // replayed request: counts once
            }
            switch (e.kind()) {
                case FEED -> {
                    if (e.item() != null && s.food().contains(e.item())) {
                        feeds++;
                        days.add(e.day());
                    }
                }
                case HARM -> harms++;
                case PLANT -> {
                    if (e.item() != null && s.habitat().contains(e.item())) {
                        planted.add(e.item());
                    }
                }
                default -> { }
            }
        }
        if (harms > r.harmEventsMax()) {
            return new Decision(false, "it was harmed; it will not settle with you");
        }
        if (planted.size() < r.habitatPlantedMin()) {
            return new Decision(false, "plant its habitat in the pen first");
        }
        if (feeds < r.feedingsMin()) {
            return new Decision(false, "feed it its own food " + (r.feedingsMin() - feeds) + " more time(s)");
        }
        if (days.size() < r.distinctDaysMin()) {
            return new Decision(false, "come back another day; care takes time");
        }
        return new Decision(true, "settled: it trusts you");
    }

    /** Whether the action is allowed. ENCLOSE and CAPTURE need settled_care; LEAVE_WILD and FEED never do. */
    public static Decision allow(Action a, Species s, List<CareEvent> events, Rule r) {
        return switch (a) {
            case LEAVE_WILD -> new Decision(true, "left wild");
            case FEED -> new Decision(true, "fed");
            case ENCLOSE, CAPTURE -> {
                Decision d = settled(s, events, r);
                yield d.allowed() ? d : new Decision(false, "not settled: " + d.reason());
            }
        };
    }
}
