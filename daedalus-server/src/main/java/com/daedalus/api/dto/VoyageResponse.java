// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * Outcome of an order to sail: {@code SAILING}, {@code ALREADY_THERE}, {@code UNDERWAY} or
 * {@code NO_SUCH_ISLAND} — never a silent success — with the ark as it stands after the order.
 */
public record VoyageResponse(String result, long now, ArkRow ark) {
}
