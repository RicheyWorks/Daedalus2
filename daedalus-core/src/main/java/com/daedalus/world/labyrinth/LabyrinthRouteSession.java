// SPDX-License-Identifier: MIT
package com.daedalus.world.labyrinth;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;

/**
 * Authoritative, per-player Broken Survey chalk lesson, composed with ChalkTrail.
 * Host callers verify observed turns, proximity, inventory debit and world erasures.
 * Never expose these methods directly as client-authorized commands. The host must
 * commit a changed snapshot with its inventory/world save before acknowledging it.
 * No reward, HTTP route, global session store or second persistence system is added.
 */
public final class LabyrinthRouteSession {
    public static final int REQUIRED_TURNS = 3;

    public enum Stage { MARK_THREE_TURNS, RETURN_TO_LECTERN, COMPLETE }
    public enum Result {
        ADDED, ERASED, LESSON_COMPLETED, DUPLICATE, EVENT_CONFLICT,
        ALREADY_MARKED, NOT_MARKED, OUT_OF_CHALK, TRAIL_FULL, REPLAY_CAPACITY,
        WRONG_PLAYER, WRONG_REALM, WRONG_INSTANCE, STALE_REVISION, INVALID,
        NOT_READY, ALREADY_COMPLETED, NOT_AT_LECTERN, NOT_A_TURN
    }

    /** Identity comes from the authenticated host, not an untrusted request body. */
    public record Command(String playerId, String realmId, String instanceId,
            String eventId, long expectedRevision) { }

    /** Immutable view for UI/replication; not accepted as a save or a source of truth. */
    public record View(String playerId, String realmId, String instanceId, long revision,
            int capacity, int charges, ChalkTrail.Point lectern,
            List<ChalkTrail.Point> marks, List<ChalkTrail.Point> learnedTurns, Stage stage) {
        public View {
            marks = List.copyOf(marks);
            learnedTurns = List.copyOf(learnedTurns);
        }
    }

    public record Decision(Result result, boolean changed, View view) { }

    private final String playerId;
    private final String instanceId;
    private final int initialCharges;
    private final int capacity;
    private final ChalkTrail.Point lectern;
    private final ChalkTrail trail;
    private final List<LabyrinthRouteSnapshot.Event> events = new ArrayList<>();
    private final Map<String, LabyrinthRouteSnapshot.Event> seen = new LinkedHashMap<>();
    private final LinkedHashSet<ChalkTrail.Point> learnedTurns = new LinkedHashSet<>();
    private boolean returned;

    public LabyrinthRouteSession(String playerId, String instanceId, int charges,
            int capacity, ChalkTrail.Point lectern) {
        // Reuse the save contract's bounds for new sessions and restored sessions.
        new LabyrinthRouteSnapshot(LabyrinthRouteSnapshot.SCHEMA, playerId,
                LabyrinthRouteSnapshot.REALM, instanceId, charges, capacity, lectern, List.of());
        this.playerId = playerId;
        this.instanceId = instanceId;
        this.initialCharges = charges;
        this.capacity = capacity;
        this.lectern = lectern;
        this.trail = new ChalkTrail(charges, capacity);
    }

    /**
     * Replays a host-owned save, validating every transition. The expected identities
     * are supplied separately so another player's or another maze's save cannot mount.
     * A snapshot is data, not a signature: the host still controls its provenance.
     */
    public static LabyrinthRouteSession restore(String expectedPlayerId,
            String expectedInstanceId, LabyrinthRouteSnapshot saved) {
        if (saved == null || !saved.playerId().equals(expectedPlayerId)
                || !saved.instanceId().equals(expectedInstanceId)) {
            throw new IllegalArgumentException("route save identity mismatch");
        }
        var session = new LabyrinthRouteSession(saved.playerId(), saved.instanceId(),
                saved.initialCharges(), saved.capacity(), saved.lectern());
        for (LabyrinthRouteSnapshot.Event event : saved.events()) {
            Command command = new Command(saved.playerId(), saved.realmId(), saved.instanceId(),
                    event.id(), event.expectedRevision());
            Decision result = session.apply(command, event.kind(), event.point());
            if (!result.changed()) {
                throw new IllegalArgumentException("route save contains unapplied event");
            }
        }
        return session;
    }

    /** Called only after the host observes a deliberate turn at this grid point. */
    public synchronized Decision markTurn(Command command, ChalkTrail.Point point) {
        return apply(command, LabyrinthRouteSnapshot.Kind.MARK_TURN, point);
    }

    /** Called by a trusted Chalk Eater or approved world event, never by client choice. */
    public synchronized Decision erase(Command command, ChalkTrail.Point point) {
        return apply(command, LabyrinthRouteSnapshot.Kind.ERASE, point);
    }

    /** Host verifies that observedPoint is the player's actual lectern interaction. */
    public synchronized Decision returnToLectern(Command command, ChalkTrail.Point observedPoint) {
        return apply(command, LabyrinthRouteSnapshot.Kind.RETURN_TO_LECTERN, observedPoint);
    }

    private Decision apply(Command command, LabyrinthRouteSnapshot.Kind kind, ChalkTrail.Point point) {
        if (command == null || point == null || !LabyrinthRouteSnapshot.validId(command.eventId())
                || command.expectedRevision() < 0) return decision(Result.INVALID, false);
        if (!playerId.equals(command.playerId())) return decision(Result.WRONG_PLAYER, false);
        if (!LabyrinthRouteSnapshot.REALM.equals(command.realmId())) return decision(Result.WRONG_REALM, false);
        if (!instanceId.equals(command.instanceId())) return decision(Result.WRONG_INSTANCE, false);

        LabyrinthRouteSnapshot.Event prior = seen.get(command.eventId());
        if (prior != null) {
            return decision(prior.kind() == kind && prior.point().equals(point)
                    && prior.expectedRevision() == command.expectedRevision()
                    ? Result.DUPLICATE : Result.EVENT_CONFLICT, false);
        }
        if (command.expectedRevision() != events.size()) return decision(Result.STALE_REVISION, false);

        Result outcome;
        switch (kind) {
            case MARK_TURN -> {
                if (point.equals(lectern)) return decision(Result.NOT_A_TURN, false);
                if (trail.marks().contains(point)) return decision(Result.ALREADY_MARKED, false);
                if (trail.marks().size() == capacity) return decision(Result.TRAIL_FULL, false);
                if (trail.charges() == 0) return decision(Result.OUT_OF_CHALK, false);
                if (!hasRouteEventSpace(!learnedTurns.contains(point))) return decision(Result.REPLAY_CAPACITY, false);
                if (trail.mark(point) != ChalkTrail.Result.ADDED) {
                    throw new IllegalStateException("route and chalk state disagree");
                }
                // Erasure changes visible cues, never already-earned lesson progress.
                if (learnedTurns.size() < REQUIRED_TURNS) learnedTurns.add(point);
                outcome = Result.ADDED;
            }
            case ERASE -> {
                if (!trail.marks().contains(point)) return decision(Result.NOT_MARKED, false);
                if (!hasRouteEventSpace(false)) return decision(Result.REPLAY_CAPACITY, false);
                trail.erase(point);
                outcome = Result.ERASED;
            }
            case RETURN_TO_LECTERN -> {
                if (returned) return decision(Result.ALREADY_COMPLETED, false);
                if (learnedTurns.size() != REQUIRED_TURNS) return decision(Result.NOT_READY, false);
                if (!lectern.equals(point)) return decision(Result.NOT_AT_LECTERN, false);
                if (events.size() == LabyrinthRouteSnapshot.MAX_EVENTS) return decision(Result.REPLAY_CAPACITY, false);
                returned = true;
                outcome = Result.LESSON_COMPLETED;
            }
            default -> throw new IllegalArgumentException("route action required");
        }
        var event = new LabyrinthRouteSnapshot.Event(command.eventId(), kind, point, command.expectedRevision());
        events.add(event);
        seen.put(event.id(), event);
        return decision(outcome, true);
    }

    private Decision decision(Result result, boolean changed) {
        return new Decision(result, changed, view());
    }

    /** Optional exploration/erosion cannot consume slots needed to finish the lesson. */
    private boolean hasRouteEventSpace(boolean earnsTurn) {
        int remainingLessonEvents = returned ? 0 : REQUIRED_TURNS - learnedTurns.size() + 1;
        if (!returned && learnedTurns.size() < REQUIRED_TURNS && earnsTurn) remainingLessonEvents--;
        return events.size() + 1 + remainingLessonEvents <= LabyrinthRouteSnapshot.MAX_EVENTS;
    }

    public synchronized View view() {
        Stage stage = returned ? Stage.COMPLETE : learnedTurns.size() == REQUIRED_TURNS
                ? Stage.RETURN_TO_LECTERN : Stage.MARK_THREE_TURNS;
        return new View(playerId, LabyrinthRouteSnapshot.REALM, instanceId, events.size(),
                capacity, trail.charges(), lectern, trail.marks(), List.copyOf(learnedTurns), stage);
    }

    public synchronized LabyrinthRouteSnapshot snapshot() {
        return new LabyrinthRouteSnapshot(LabyrinthRouteSnapshot.SCHEMA, playerId,
                LabyrinthRouteSnapshot.REALM, instanceId, initialCharges, capacity, lectern, events);
    }
}
