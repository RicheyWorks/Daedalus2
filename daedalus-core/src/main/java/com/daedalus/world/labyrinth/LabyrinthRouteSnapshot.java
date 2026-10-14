// SPDX-License-Identifier: MIT
package com.daedalus.world.labyrinth;

import java.util.HashSet;
import java.util.List;

/**
 * Versioned, immutable save extension for one Broken Survey route lesson.
 * The existing host save transaction owns storage; this type opens no files.
 * Applied events are retained, never evicted, so restoring cannot reopen old event IDs.
 */
public record LabyrinthRouteSnapshot(int schema, String playerId, String realmId,
        String instanceId, int initialCharges, int capacity, ChalkTrail.Point lectern,
        List<Event> events) {
    public static final int SCHEMA = 1;
    public static final int MAX_EVENTS = 512;
    public static final String REALM = "LABYRINTH";

    public enum Kind { MARK_TURN, ERASE, RETURN_TO_LECTERN }

    /** An applied host event; the list position plus one is its revision. */
    public record Event(String id, Kind kind, ChalkTrail.Point point, long expectedRevision) {
        public Event {
            if (!validId(id) || kind == null || point == null
                    || expectedRevision < 0 || expectedRevision >= MAX_EVENTS) {
                throw new IllegalArgumentException("invalid route event");
            }
        }
    }

    public LabyrinthRouteSnapshot {
        if (schema != SCHEMA || !validId(playerId) || !REALM.equals(realmId)
                || !validId(instanceId) || initialCharges < 0 || initialCharges > 10_000
                || capacity < 1 || capacity > 512 || lectern == null
                || events == null || events.size() > MAX_EVENTS) {
            throw new IllegalArgumentException("invalid route snapshot");
        }
        events = List.copyOf(events);
        var ids = new HashSet<String>();
        for (int i = 0; i < events.size(); i++) {
            Event event = events.get(i);
            if (!ids.add(event.id()) || event.expectedRevision() != i) {
                throw new IllegalArgumentException("duplicate or out-of-order saved route event");
            }
        }
    }

    static boolean validId(String id) {
        if (id == null || id.isBlank() || id.length() > 128) return false;
        for (int i = 0; i < id.length(); i++) {
            if (Character.isISOControl(id.charAt(i))) return false;
        }
        return true;
    }
}
