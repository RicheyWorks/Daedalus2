// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * World-level inspect. Not a maze snapshot — no tiles, no Caffeine id.
 */
public record WorldInspectResponse(String id, long revision, int chunkCount) {
}
