// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * One trait in token metadata (ADR-027), in the shape marketplaces read: {@code trait_type},
 * {@code value} (a string or a number) and, for numbers, an optional {@code display_type}.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record TokenAttribute(@JsonProperty("trait_type") String traitType, Object value,
                             @JsonProperty("display_type") String displayType) {

    public static TokenAttribute of(String trait, String value) {
        return new TokenAttribute(trait, value, null);
    }

    public static TokenAttribute number(String trait, long value) {
        return new TokenAttribute(trait, value, "number");
    }
}
