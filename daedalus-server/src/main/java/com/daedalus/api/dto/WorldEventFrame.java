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
        long revision) {
}
