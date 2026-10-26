// SPDX-License-Identifier: MIT

package com.daedalus.world.adventure;

/**
 * High or low (ADR-037), the whole of the high/low sword game. Standing, you thrust high and your shield
 * covers high; crouching, you thrust low and your shield covers low. A foe guards a height, and attacks at
 * one; a thrust lands where the foe is not guarding, and a shield stops an attack at its own height.
 */
public enum Height {
    HIGH, LOW;

    public Height other() {
        return this == HIGH ? LOW : HIGH;
    }
}
