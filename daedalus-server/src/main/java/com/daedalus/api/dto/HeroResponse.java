// SPDX-License-Identifier: MIT

package com.daedalus.api.dto;

import java.util.List;

/**
 * An adventurer (ADR-037). {@code exp} is unspent experience. {@code attack}, {@code magic} and
 * {@code life} are levels from 1, with no ceiling. The {@code next*} fields are the experience the next level of each costs
 * (there is no top level), and {@code canRaise} lists which can be raised now. {@code maxLife} (in half-hearts),
 * {@code maxMagic} and {@code damage} are what those levels mean. {@code result} says what the last request
 * did: BEAT, TOO_FAST, RAISED, NOT_ENOUGH, FELL, or SEEN for a read.
 */
public record HeroResponse(String result, String name, int exp, int attack, int magic, int life, int beaten,
                           int nextAttack, int nextMagic, int nextLife, List<String> canRaise, int maxLife,
                           int maxMagic, int damage) {

    public HeroResponse {
        canRaise = canRaise == null ? List.of() : List.copyOf(canRaise);
    }
}
