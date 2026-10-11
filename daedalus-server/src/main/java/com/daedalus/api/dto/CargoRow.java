// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** One kind in an ark's hold or on an island (ADR-023): canon key and name, guild, how many. */
public record CargoRow(String key, String name, String guild, double count) {
}
