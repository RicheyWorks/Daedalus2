// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.school;

import java.util.Objects;

/** A child at the song school: where they came from (a G97 far island) and how readily they remember (0..1). */
public record Pupil(String id, String name, String home, double aptitude) {
    public Pupil {
        Objects.requireNonNull(id, "id");
        if (!(aptitude >= 0 && aptitude <= 1)) {
            throw new IllegalArgumentException("aptitude must be in [0, 1]: " + aptitude);
        }
    }
}
