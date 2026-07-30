// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * {@code GET /api/v1/maze/daily} — today's shared challenge (ADR-006 idea #4).
 *
 * @param date ISO-8601 UTC date the maze belongs to; at midnight UTC everyone rolls over
 *             to a fresh maze together
 * @param maze the maze itself, same shape as every other maze response — play it, solve
 *             it, bring it to life, or walk it blind like any other maze id
 */
public record DailyMazeResponse(String date, GenerateResponse maze) {}
