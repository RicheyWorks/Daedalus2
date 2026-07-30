// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.UUID;

/**
 * STOMP frame published to {@code /topic/maze/{id}/state} after each living-maze mutation
 * tick (ADR-006). The topic also carries {@link GeneratedFrame}; consumers branch on shape —
 * a frame with a {@code tick} field is a mutation, one with a {@code generatorId} is a fresh
 * generation. The web UI re-fetches the maze and re-solves on every mutation frame so the
 * drawn route adapts live.
 *
 * @param mazeId            id of the maze that just mutated
 * @param tick              1-based tick index within the current run
 * @param wallsOpened       walls erosion carved this tick
 * @param deadEndsRemaining dead ends left after this tick
 * @param settled           true on the run's final frame (ticks exhausted or nothing left
 *                          to erode) — clients can stop expecting further frames
 */
public record MutationFrame(UUID mazeId, int tick, int wallsOpened,
                            int deadEndsRemaining, boolean settled) {}
