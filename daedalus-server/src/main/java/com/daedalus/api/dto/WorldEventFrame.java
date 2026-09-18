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
        String lot) {

    public WorldEventFrame {
        place = place == null ? "" : place;
        lot = lot == null ? "" : lot;
    }

    public WorldEventFrame(String worldId, String kind, int x, int y, int z,
            String type, String previous, long revision) {
        this(worldId, kind, x, y, z, type, previous, revision, "", "");
    }
}
