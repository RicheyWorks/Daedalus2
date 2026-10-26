// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/**
 * A Gallery City (ADR-035): its parcels and named streets, the Origin plaza and the drone pad. A parcel
 * covers x {@code minX..maxX} and z {@code minZ..maxZ}, from the ground to {@code height}. It has an
 * address on its nearest street. {@code gallery} says whether it opened with a gallery. {@code owner} is
 * empty while the parcel is unclaimed, and nobody builds on an unclaimed parcel.
 */
public record GalleryResponse(String worldId, int plazaMinX, int plazaMinZ, int plazaMaxX, int plazaMaxZ,
                              int padX, int padY, int padZ, List<Parcel> parcels, List<Street> streets) {

    public record Parcel(int n, int minX, int minZ, int maxX, int maxZ, int height, String address, boolean gallery,
                         String owner, List<String> builders) {

        public Parcel {
            owner = owner == null ? "" : owner;
            builders = builders == null ? List.of() : List.copyOf(builders);
        }
    }

    /** A street's name and its centreline from (x1, z1) to (x2, z2). */
    public record Street(String name, int x1, int z1, int x2, int z2) {
    }

    public GalleryResponse {
        parcels = parcels == null ? List.of() : List.copyOf(parcels);
        streets = streets == null ? List.of() : List.copyOf(streets);
    }
}
