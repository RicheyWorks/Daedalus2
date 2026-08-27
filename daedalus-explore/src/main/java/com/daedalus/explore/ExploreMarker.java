// SPDX-License-Identifier: MIT

package com.daedalus.explore;

import com.daedalus.model.Point;

/** A named place the story layer can attach content to. */
public record ExploreMarker(String name, Point cell, int depth, String kind) {
}
