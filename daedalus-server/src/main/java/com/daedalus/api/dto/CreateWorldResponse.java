// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

/** What a create asked for came to: CREATED, EXISTS, BAD_ID, BAD_TITLE, BAD_STYLE, STYLE_NOT_READY or FULL. */
public record CreateWorldResponse(String result, WorldRow world) {
}
