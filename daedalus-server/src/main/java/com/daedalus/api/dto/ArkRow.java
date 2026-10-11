// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/**
 * One ark (ADR-019/020). {@code x,y,z} is the berth of the island it is moored at — or, while
 * {@code SAILING}, of the island it is bound for. While sailing, {@code fromSlot}/{@code toSlot} and
 * the server-epoch {@code departAt}/{@code arriveAt} let a client place it; moored, they are
 * {@code -1}/{@code -1}/{@code 0}/{@code 0}.
 */
public record ArkRow(String id, String name, int homeSlot, int slot, int x, int y, int z, String state,
                     int fromSlot, int toSlot, long departAt, long arriveAt) {
}
