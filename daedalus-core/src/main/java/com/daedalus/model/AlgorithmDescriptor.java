// SPDX-License-Identifier: MIT

package com.daedalus.model;

/**
 * Descriptive metadata about a generator or solver — surfaced to the UI's algorithm selector
 * and to the {@code /api/algorithms} endpoint.
 */
public record AlgorithmDescriptor(
        String id,
        String displayName,
        String category,        // "generator" or "solver"
        String complexity,      // e.g. "O(n) time, O(n) space"
        String biasNote,        // e.g. "long winding corridors", "no bias", "horizontal bias"
        String description
) { }
