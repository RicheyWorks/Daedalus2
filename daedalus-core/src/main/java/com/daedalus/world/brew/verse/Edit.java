// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.verse;

/** One letter edit at a position in the sung verse: SWAP and ADD carry a letter, DROP does not. */
public record Edit(Kind kind, int pos, char letter) {
    public enum Kind { SWAP, ADD, DROP }

    /** Applies this edit to a verse. */
    public String apply(String verse) {
        return switch (kind) {
            case SWAP -> verse.substring(0, pos) + letter + verse.substring(pos + 1);
            case ADD -> verse.substring(0, pos) + letter + verse.substring(pos);
            case DROP -> verse.substring(0, pos) + verse.substring(pos + 1);
        };
    }
}
