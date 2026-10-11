// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * ERC-721 metadata for one island (ADR-027): the JSON a contract's {@code tokenURI(tokenId)} points
 * at, in the ERC-721 metadata schema plus the {@code attributes} and {@code external_url}
 * marketplaces read. {@code image} is the island's isometric portrait, grown from its seed.
 */
public record IslandTokenMetadata(String name, String description, String image,
                                  @JsonProperty("external_url") String externalUrl,
                                  List<TokenAttribute> attributes) {

    /** Copy on construct: the caller's list cannot change what this record says. */
    public IslandTokenMetadata {
        attributes = attributes == null ? List.of() : List.copyOf(attributes);
    }
}
