// SPDX-License-Identifier: MIT
package com.daedalus.world.exploration;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Pure candidate transitions. Only the existing authenticated host may provide evidence and publish a snapshot. */
public final class ExplorationProgress {
    public static final int MAX_EVENTS = 512;
    public enum Action { CROSS_PORTAL, REACH_MARKER, COLLECT }
    public enum Status { CANDIDATE, REPLAY, CONFLICT, STALE, INVALID, LOCKED, NO_CHANGE, CAPACITY }

    public record Event(String id, long expectedRevision, Action action, String target) {
        public Event {
            ExplorationDefinition.text(id, 128); ExplorationDefinition.token(target);
            ExplorationDefinition.require(expectedRevision >= 0 && action != null, "invalid event");
        }
    }

    /** Complete bounded replay history is retained; nothing is evicted to make old events eligible again. */
    public record Snapshot(int schema, String definition, int definitionVersion, String realm, String subject,
                           long revision, String world, Set<String> visited, Set<String> reached,
                           Set<String> collected, Set<String> completed, List<Event> accepted) {
        public Snapshot {
            ExplorationDefinition.require(schema == 1 && definitionVersion > 0, "snapshot version");
            ExplorationDefinition.token(definition); ExplorationDefinition.token(world);
            identity(realm); identity(subject);
            ExplorationDefinition.require(visited != null && reached != null && collected != null
                    && completed != null && accepted != null, "snapshot collections required");
            ExplorationDefinition.require(visited.size() <= ExplorationDefinition.MAX_WORLDS
                    && reached.size() <= ExplorationDefinition.MAX_WORLDS * 64
                    && collected.size() <= ExplorationDefinition.MAX_COLLECTIBLES
                    && completed.size() <= ExplorationDefinition.MAX_OBJECTIVES
                    && accepted.size() <= MAX_EVENTS && revision == accepted.size(), "snapshot capacity or revision");
            visited = Set.copyOf(visited); reached = Set.copyOf(reached); collected = Set.copyOf(collected);
            completed = Set.copyOf(completed); accepted = List.copyOf(accepted);
            Set<String> ids = new HashSet<>();
            for (int i = 0; i < accepted.size(); i++) {
                Event e = accepted.get(i);
                ExplorationDefinition.require(ids.add(e.id()) && e.expectedRevision() == i, "invalid replay history");
            }
        }
    }

    public record Decision(Status status, Snapshot snapshot, String detail) {
        public boolean candidate() { return status == Status.CANDIDATE; }
    }

    private ExplorationProgress() { }

    public static Snapshot initial(ExplorationDefinition definition, String canonicalRealm, String canonicalSubject) {
        Set<String> visited = Set.of(definition.hub());
        Set<String> complete = completions(definition, visited, Set.of(), Set.of());
        return new Snapshot(1, definition.id(), definition.version(), canonicalRealm, canonicalSubject, 0,
                definition.hub(), visited, Set.of(), Set.of(), complete, List.of());
    }

    public static Decision prepare(ExplorationDefinition definition, Snapshot before, Event event) {
        if (definition == null || before == null || event == null || !valid(definition, before)) {
            return new Decision(Status.INVALID, before, "definition or snapshot does not match");
        }
        return transition(definition, before, event);
    }

    private static Decision transition(ExplorationDefinition definition, Snapshot before, Event event) {
        for (Event prior : before.accepted()) {
            if (prior.id().equals(event.id())) return new Decision(prior.equals(event) ? Status.REPLAY : Status.CONFLICT,
                    before, "event identity already retained");
        }
        if (event.expectedRevision() != before.revision()) return new Decision(Status.STALE, before, "revision mismatch");
        if (before.accepted().size() >= MAX_EVENTS) return new Decision(Status.CAPACITY, before, "replay capacity reached");
        String world = before.world();
        Set<String> visited = new HashSet<>(before.visited());
        Set<String> reached = new HashSet<>(before.reached());
        Set<String> collected = new HashSet<>(before.collected());
        switch (event.action()) {
            case CROSS_PORTAL -> {
                ExplorationDefinition.Portal portal = definition.portal(event.target());
                if (portal == null || !portal.from().equals(world)) {
                    return new Decision(Status.INVALID, before, "portal is not in current world");
                }
                if (collected.size() < portal.collectedRequired()
                        || !before.completed().containsAll(portal.objectivesRequired())) {
                    return new Decision(Status.LOCKED, before, "portal requirements incomplete");
                }
                world = portal.to(); visited.add(world); reached.add(portal.landingMarker());
            }
            case REACH_MARKER -> {
                if (!definition.markerIn(world, event.target())) return new Decision(Status.INVALID, before, "marker not here");
                if (!reached.add(event.target())) return new Decision(Status.NO_CHANGE, before, "marker already reached");
            }
            case COLLECT -> {
                ExplorationDefinition.Collectible collectible = definition.collectible(event.target());
                if (collectible == null || !collectible.world().equals(world)) {
                    return new Decision(Status.INVALID, before, "collectible not here");
                }
                if (!collected.add(event.target())) return new Decision(Status.NO_CHANGE, before, "collectible already recorded");
            }
        }
        if (before.accepted().size() + 1 + definition.freeReturnHops(world) > MAX_EVENTS) {
            return new Decision(Status.CAPACITY, before, "remaining replay slots are reserved for a free return home");
        }
        List<Event> accepted = new ArrayList<>(before.accepted()); accepted.add(event);
        Snapshot candidate = new Snapshot(1, definition.id(), definition.version(), before.realm(), before.subject(),
                before.revision() + 1, world, visited, reached, collected,
                completions(definition, visited, reached, collected), accepted);
        return new Decision(Status.CANDIDATE, candidate, "host evidence and durable publication required");
    }

    /** Restore replays complete retained history and compares exact state; no implicit version migration. */
    public static boolean valid(ExplorationDefinition definition, Snapshot snapshot) {
        if (definition == null || snapshot == null) return false;
        if (!definition.id().equals(snapshot.definition()) || definition.version() != snapshot.definitionVersion()
                || definition.world(snapshot.world()) == null || !snapshot.visited().contains(snapshot.world())
                || !snapshot.visited().contains(definition.hub())) return false;
        for (String world : snapshot.visited()) if (definition.world(world) == null) return false;
        for (String marker : snapshot.reached()) {
            if (snapshot.visited().stream().noneMatch(w -> definition.markerIn(w, marker))) return false;
        }
        for (String id : snapshot.collected()) {
            ExplorationDefinition.Collectible c = definition.collectible(id);
            if (c == null || !snapshot.visited().contains(c.world())) return false;
        }
        for (Event event : snapshot.accepted()) {
            boolean known = switch (event.action()) {
                case CROSS_PORTAL -> definition.portal(event.target()) != null;
                case REACH_MARKER -> definition.worlds().stream().anyMatch(w -> definition.markerIn(w.id(), event.target()));
                case COLLECT -> definition.collectible(event.target()) != null;
            };
            if (!known) return false;
        }
        if (!snapshot.completed().equals(completions(definition, snapshot.visited(), snapshot.reached(), snapshot.collected()))) {
            return false;
        }
        Snapshot replayed = initial(definition, snapshot.realm(), snapshot.subject());
        for (Event event : snapshot.accepted()) {
            Decision step = transition(definition, replayed, event);
            if (!step.candidate()) return false;
            replayed = step.snapshot();
        }
        return snapshot.equals(replayed);
    }

    private static Set<String> completions(ExplorationDefinition definition, Set<String> visited,
                                         Set<String> reached, Set<String> collected) {
        Set<String> completed = new HashSet<>();
        for (int pass = 0; pass < definition.objectives().size(); pass++) {
            boolean changed = false;
            for (ExplorationDefinition.Objective objective : definition.objectives()) {
                if (!visited.contains(objective.world()) || !completed.containsAll(objective.prerequisites())) continue;
                boolean satisfied = switch (objective.kind()) {
                    case VISIT -> true;
                    case REACH -> reached.containsAll(objective.targets());
                    case COLLECT -> collected.containsAll(objective.targets());
                };
                if (satisfied && completed.add(objective.id())) changed = true;
            }
            if (!changed) break;
        }
        return Set.copyOf(completed);
    }

    static void identity(String value) {
        ExplorationDefinition.require(value != null && value.matches("[A-Za-z0-9][A-Za-z0-9._:@-]{0,127}"),
                "invalid canonical identity");
    }
}
