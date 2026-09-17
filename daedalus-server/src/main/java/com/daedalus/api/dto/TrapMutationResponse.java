// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of arm or disarm. {@code result} is never silent success. */
public record TrapMutationResponse(String id, String state, String result, long revision) {
}
