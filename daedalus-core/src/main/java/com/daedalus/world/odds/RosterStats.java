// SPDX-License-Identifier: MIT

package com.daedalus.world.odds;

import com.daedalus.world.tactics.TacticalOrders;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

/**
 * Turns a DTR 1 roster (Unreal's trusted snapshot of the squad) into per-unit combat stats for
 * {@link Encounter#fromOrders}: each live unit gets the template for its {@code kind}, with the health it has right now.
 * Units that are down are left out, as the Director never orders them.
 */
public final class RosterStats {

    private RosterStats() {
    }

    public static Map<String, Combatant> fromRoster(TacticalOrders.Roster roster, Map<String, Combatant> templatesByKind) {
        Objects.requireNonNull(roster, "roster");
        Objects.requireNonNull(templatesByKind, "templatesByKind");
        Map<String, Combatant> out = new LinkedHashMap<>();
        for (TacticalOrders.RosterUnit u : roster.units()) {
            if (u.health() <= 0) {
                continue;
            }
            Combatant t = templatesByKind.get(u.kind());
            if (t == null) {
                throw new IllegalArgumentException("no combat template for unit kind " + u.kind());
            }
            out.put(u.unit(), t.renamedWithHealth(u.unit(), u.health()));
        }
        return out;
    }
}