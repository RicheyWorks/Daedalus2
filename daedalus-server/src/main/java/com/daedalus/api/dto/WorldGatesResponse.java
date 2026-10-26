// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/** A world's sky gates (ADR-031) and the mount its people fly to them with. */
public record WorldGatesResponse(String worldId, String mount, boolean mountReady, List<GateRow> gates) {

    /** Copy on construct: the caller's list cannot change what this record says. */
    public WorldGatesResponse {
        gates = gates == null ? List.of() : List.copyOf(gates);
    }
}
