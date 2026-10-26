// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/**
 * Who holds an island after a claim, abandon or builder change (ADR-026). {@code result} names
 * what happened: CLAIMED, ALREADY_CLAIMED, BLOCKED, BAD_OWNER, ABANDONED, NOT_OWNER, NOT_CLAIMED,
 * GRANTED, REVOKED, BAD_BUILDER or NO_SUCH_ISLAND. {@code owner} is empty when the island is open.
 */
public record IslandClaimResponse(String result, int slot, String owner, List<String> builders,
                                  long revision) {

    /** Copy on construct: the caller's list cannot change what this record says. */
    public IslandClaimResponse {
        builders = builders == null ? List.of() : List.copyOf(builders);
    }
}
