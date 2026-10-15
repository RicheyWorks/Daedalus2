// SPDX-License-Identifier: MIT
package com.daedalus.world.ocean;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/**
 * Tide-Pen rule (data/ocean/tidepen.json): a creature may be penned only after the actor has settled its care.
 *
 * <p>This class is a pure decision. It holds no state, stores nothing and grants nothing. Leaving a creature wild is
 * always allowed. This is a fantasy rule, not biology. The numeric thresholds are owner-proposed data, not an
 * approved authority or time model.
 *
 * <h2>Verified-caller contract (PootScoot review 32524)</h2>
 * The gate decides only over what a trusted caller hands it. The caller, not this class, must:
 * <ul>
 *   <li>bind the {@link Subject}: actor, the individual creature, its species, realm and season. Events are refused
 *       if they name another actor or another individual. Care of one individual, a herder's sheep say, is never
 *       care of a different aquatic individual;</li>
 *   <li>pass only host-accepted events, each with an accepted receipt and revision, checked for freshness and
 *       revocation;</li>
 *   <li>provide persistent replay protection. Deduplication here is per invocation only: within one call, a repeated
 *       request id with an identical payload counts once;</li>
 *   <li>choose the route. A trusted, scoped, imported settled_care fact, or equivalently verified destination-local
 *       onboarding (CREATURE-HANDLING-AND-FARM-BINDING.md, proposed), is the caller's alternative to these events.
 *       This gate does not model it.</li>
 * </ul>
 * Anything the gate cannot trust is refused, never guessed: a blank subject, a blank request id, one request id
 * carrying two different payloads (a later HARM could hide behind it), or an event for another actor or individual.
 *
 * <p>{@code settled_care} holds when, over the accepted events, the actor fed the creature its own food at least
 * {@code feedingsMin} times on at least {@code distinctDaysMin} different days, harmed it no more than
 * {@code harmEventsMax} times, and planted at least {@code habitatPlantedMin} of its habitat plants.
 */
public final class TidePenGate {

    public enum Kind { FEED, HARM, PLANT }

    public enum Action { ENCLOSE, CAPTURE, LEAVE_WILD, FEED }

    /** Who and what the decision is about. The caller binds this; every field must be non-blank. */
    public record Subject(String actor, String individual, String species, String realm, String season) {
        boolean complete() {
            return !blank(actor) && !blank(individual) && !blank(species) && !blank(realm) && !blank(season);
        }
    }

    /** One host-accepted care event. {@code item} is the food or the plant. */
    public record CareEvent(String requestId, String actor, String individual, Kind kind, int day, String item) {
        public CareEvent {
            Objects.requireNonNull(kind, "kind");
        }
    }

    /** A species' needs, as listed in tidepen.json residents. */
    public record Species(String id, Set<String> food, Set<String> habitat) { }

    /** Thresholds (tidepen.json settled_care.requires, owner-proposed). Ranges are checked here. */
    public record Rule(int feedingsMin, int distinctDaysMin, int harmEventsMax, int habitatPlantedMin) {
        public static final Rule DEFAULT = new Rule(3, 2, 0, 1);

        public Rule {
            if (feedingsMin < 1 || distinctDaysMin < 1 || distinctDaysMin > feedingsMin || harmEventsMax < 0 || habitatPlantedMin < 0) {
                throw new IllegalArgumentException(
                        "rule out of range: feedingsMin>=1, 1<=distinctDaysMin<=feedingsMin, harmEventsMax>=0, habitatPlantedMin>=0");
            }
        }
    }

    /** The answer, with a reason a player could read. */
    public record Decision(boolean allowed, String reason) { }

    private TidePenGate() { }

    private static boolean blank(String s) {
        return s == null || s.isBlank();
    }

    private static Decision refuse(String why) {
        return new Decision(false, why);
    }

    /** Whether settled_care holds for this subject and these events. */
    public static Decision settled(Subject who, Species s, List<CareEvent> events, Rule r) {
        if (who == null || !who.complete()) {
            return refuse("who is caring for which creature? (subject incomplete)");
        }
        if (s == null || !who.species().equals(s.id())) {
            return refuse("that is not this creature's kind");
        }
        Map<String, CareEvent> byId = new HashMap<>();
        int feeds = 0, harms = 0;
        Set<Integer> days = new HashSet<>();
        Set<String> planted = new HashSet<>();
        for (CareEvent e : events) {
            if (blank(e.requestId())) {
                return refuse("a care event has no request id");
            }
            if (!who.actor().equals(e.actor()) || !who.individual().equals(e.individual())) {
                return refuse("care of another creature or by someone else does not count here");
            }
            CareEvent prior = byId.putIfAbsent(e.requestId(), e);
            if (prior != null) {
                if (!prior.equals(e)) {
                    return refuse("one request id carries two different events");
                }
                continue;                                   // an identical replay within this call counts once
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
            return refuse("it was harmed; it will not settle with you");
        }
        if (planted.size() < r.habitatPlantedMin()) {
            return refuse("plant its habitat in the pen first");
        }
        if (feeds < r.feedingsMin()) {
            return refuse("feed it its own food " + (r.feedingsMin() - feeds) + " more time(s)");
        }
        if (days.size() < r.distinctDaysMin()) {
            return refuse("come back another day; care takes time");
        }
        return new Decision(true, "settled: it trusts you");
    }

    /** Whether the action is allowed. ENCLOSE and CAPTURE need settled_care; LEAVE_WILD and FEED never do. */
    public static Decision allow(Action a, Subject who, Species s, List<CareEvent> events, Rule r) {
        return switch (a) {
            case LEAVE_WILD -> new Decision(true, "left wild");
            case FEED -> new Decision(true, "fed");
            case ENCLOSE, CAPTURE -> {
                Decision d = settled(who, s, events, r);
                yield d.allowed() ? d : refuse("not settled: " + d.reason());
            }
        };
    }
}
