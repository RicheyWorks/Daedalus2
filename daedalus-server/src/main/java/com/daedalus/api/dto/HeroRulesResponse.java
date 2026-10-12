// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/**
 * The rules every client plays by (ADR-037): each foe's life, power, experience, the height it can be
 * reached at, the height it guards, the height it strikes at (null when it strikes where it is not
 * guarding), whether its shield moves, and its speed. Also Zelda II's experience costs for the first seven
 * levels (index 0 is level 1 → 2); past them each costs half again the last, without end. And what Heal
 * costs and restores.
 */
public record HeroRulesResponse(List<Foe> foes, List<Integer> attackCosts, List<Integer> magicCosts,
                                List<Integer> lifeCosts, int healCost, int healAmount, long minBetweenMs) {

    public record Foe(String kind, String title, int life, int power, int exp, String reach, String guard, String strike,
                      boolean shifting, double speed) {
    }

    public HeroRulesResponse {
        foes = List.copyOf(foes);
        attackCosts = List.copyOf(attackCosts);
        magicCosts = List.copyOf(magicCosts);
        lifeCosts = List.copyOf(lifeCosts);
    }
}
