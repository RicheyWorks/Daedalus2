// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/**
 * Where the server's RAM goes on cubes (ADR-064): per mounted world, chunks by storage form (one kind / 4 bits /
 * 8 bits per cube), the bytes they hold, and what dense 4 KiB chunks would have held. Plus the JVM heap.
 */
public record WorldsRamResponse(List<Row> worlds, long chunkBytes, long denseBytes, long heapUsed, long heapMax) {

    public record Row(String id, int chunks, long bytes, long denseBytes, int uniform, int nibble, int dense) {
    }

    public WorldsRamResponse {
        worlds = worlds == null ? List.of() : List.copyOf(worlds);
    }
}
