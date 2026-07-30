// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.UUID;

/**
 * STOMP frame published to {@code /topic/maze/{id}/state} after each traffic pulse
 * (ADR-006 idea #3). Third frame shape on the topic — consumers branch: {@code tick} ⇒
 * mutation, {@code congestedCells} ⇒ traffic, {@code generatorId} ⇒ fresh generation.
 * Deltas only; clients re-fetch the maze for the new cost picture (the response's
 * {@code hotspots} list mirrors the congested cells, so existing shading just works).
 *
 * @param congestedCells cells currently costing more than uniform
 * @param peakCost       most expensive cell after this pulse
 * @param settled        true when tracking retired (fully decayed and quiet)
 */
public record TrafficFrame(UUID mazeId, int congestedCells, double peakCost,
                           boolean settled) {}
