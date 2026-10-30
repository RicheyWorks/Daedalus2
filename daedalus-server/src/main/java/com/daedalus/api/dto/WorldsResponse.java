// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/** Every mounted world (ADR-030), World Zero first, and every style with whether it is ready. */
public record WorldsResponse(List<WorldRow> worlds, List<StyleRow> styles) {

    /** A world style (ADR-029) and whether its generator and renderer have shipped. */
    public record StyleRow(String style, String title, boolean ready) {
    }

    /** Copy on construct: the caller's lists cannot change what this record says. */
    public WorldsResponse {
        worlds = worlds == null ? List.of() : List.copyOf(worlds);
        styles = styles == null ? List.of() : List.copyOf(styles);
    }
}
