// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/**
 * Discover surface. Not the drive script — extras a plugin advertised
 * appear here and stay UNACCOUNTED until driven.
 */
public record WorldCapabilitiesResponse(String worldId, List<String> capabilities) {
}
