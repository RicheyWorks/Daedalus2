// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * STOMP frame on {@code /topic/world/{id}/events}. Separate from maze {@code /state}.
 */
public record WorldEventFrame(
        String worldId,
        String kind,
        int x,
        int y,
        int z,
        String type,
        String previous,
        long revision,
        String place,
        String lot,
        String occupant) {

    public WorldEventFrame {
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
        occupant = occupant == null ? "" : occupant;
    }

    public WorldEventFrame(String worldId, String kind, int x, int y, int z,
            String type, String previous, long revision) {
        this(worldId, kind, x, y, z, type, previous, revision, "", "", "");
    }

    public WorldEventFrame(String worldId, String kind, int x, int y, int z,
            String type, String previous, long revision, String place, String lot) {
        this(worldId, kind, x, y, z, type, previous, revision, place, lot, "");
    }
}
