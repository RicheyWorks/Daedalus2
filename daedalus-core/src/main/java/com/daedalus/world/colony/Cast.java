// SPDX-License-Identifier: MIT

package com.daedalus.world.colony;

import java.util.List;
import java.util.Optional;

/**
 * A realm's friendly cast and its quests, from {@code data/art/<realm>/population-plan.json}.
 *
 * @param roles  friendly NPC types, sorted (as {@code colony_ledger.population(realm)["types"]})
 * @param quests the plan's quests in file order
 */
public record Cast(List<String> roles, List<QuestDef> quests) {
    public static final Cast NONE = new Cast(List.of(), List.of());

    public Cast {
        roles = List.copyOf(roles);
        quests = List.copyOf(quests);
    }

    /** One quest of the plan: who gives it and its ordered story steps. */
    public record QuestDef(String id, String giverType, List<String> steps, String reward) {
        public QuestDef {
            steps = List.copyOf(steps);
        }
    }

    /** The first quest this role gives, as colony_ledger.requests picks it. */
    public Optional<QuestDef> questOf(String role) {
        return quests.stream().filter(q -> role.equals(q.giverType())).findFirst();
    }
}
