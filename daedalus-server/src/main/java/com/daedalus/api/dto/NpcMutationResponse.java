// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** Result of talk or hush. {@code result} is never silent success. */
public record NpcMutationResponse(String id, String state, String result, long revision) {
}
