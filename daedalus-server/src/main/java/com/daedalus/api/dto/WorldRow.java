// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * One mounted world (ADR-030): its id (the {@code {id}} in every {@code /world/{id}/…} route), style,
 * seed and title, plus how many islands it has and its revision.
 */
public record WorldRow(String id, String style, String styleTitle, long seed, String title, int islands,
                       long revision) {
}
