// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** OPENED (with the gate in each world), SAME_WORLD, NO_SUCH_WORLD, ALREADY_LINKED or FULL. */
public record OpenGateResponse(String result, int gate, String toWorld, int toGate) {
}
