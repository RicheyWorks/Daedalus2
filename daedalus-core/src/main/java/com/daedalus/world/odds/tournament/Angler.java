// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.tournament;

import com.daedalus.world.fishing.AnglerSkill;
import java.util.Objects;

/** One entrant in the Squall Cup: a display name and the G07 reaction model that decides their strikes. */
public record Angler(String name, AnglerSkill skill) {

    public Angler {
        Objects.requireNonNull(name, "name");
        Objects.requireNonNull(skill, "skill");
        if (name.isBlank()) {
            throw new IllegalArgumentException("angler name is blank");
        }
    }
}
