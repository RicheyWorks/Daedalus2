// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * One ark (ADR-019). {@code x,y,z} is its berth: the pier-tip cube of the island it is moored at,
 * where a passenger steps off. {@code state} is {@code MOORED} until voyages exist.
 */
public record ArkRow(String id, String name, int homeSlot, int slot, int x, int y, int z, String state) {
}
