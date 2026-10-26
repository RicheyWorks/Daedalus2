// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * STOMP frame on {@code /topic/world/{id}/arks} (ADR-020): an ark {@code DEPARTED} or
 * {@code ARRIVED}. {@code now} is the server clock when the frame was sent.
 */
public record ArkFrame(String worldId, String kind, String arkId, int fromSlot, int toSlot,
                       long departAt, long arriveAt, long now) {
}
