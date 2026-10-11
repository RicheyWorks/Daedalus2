// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * One sky gate (ADR-031): its index, the ring's centre {@code x,y,z}, the cloud berth a mount ties up
 * at, the slot arks use for it ({@code 1000 + gate}), and where its portal leads.
 */
public record GateRow(int gate, int slot, int x, int y, int z, int berthX, int berthY, int berthZ, String toWorld,
                      String toTitle, int toGate) {
}
