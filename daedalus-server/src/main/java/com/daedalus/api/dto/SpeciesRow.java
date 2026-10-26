// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** One species of the canon (ADR-021). {@code strategy} is "R" or "K". */
public record SpeciesRow(String key, String name, String rarity, String temperament, String guild,
                         String size, String strategy, boolean disperses) {
}
