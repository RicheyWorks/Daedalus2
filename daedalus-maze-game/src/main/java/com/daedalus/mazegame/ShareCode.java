// SPDX-License-Identifier: MIT

package com.daedalus.mazegame;

import java.util.Locale;

/**
 * Share codes like {@code LR-H-1KQ3Z}: game prefix, difficulty letter, base-36 seed. Seeds are
 * kept non-negative so codes stay short and round-trip exactly.
 */
public final class ShareCode {

    private static final String PREFIX = "LR-";

    private final long seed;
    private final Difficulty difficulty;

    public ShareCode(long seed, Difficulty difficulty) {
        if (seed < 0) {
            throw new IllegalArgumentException("Seed must be non-negative: " + seed);
        }
        this.seed = seed;
        this.difficulty = difficulty;
    }

    public long seed() { return seed; }
    public Difficulty difficulty() { return difficulty; }

    public String encode() {
        return PREFIX + difficulty.code() + "-" + Long.toString(seed, 36).toUpperCase(Locale.ROOT);
    }

    public static ShareCode parse(String code) {
        String c = code.trim().toUpperCase(Locale.ROOT);
        if (!c.startsWith(PREFIX) || c.length() < PREFIX.length() + 3 || c.charAt(PREFIX.length() + 1) != '-') {
            throw new IllegalArgumentException("Not a Labyrinth Run code: " + code);
        }
        Difficulty d = Difficulty.parse(c.substring(PREFIX.length(), PREFIX.length() + 1));
        long seed = Long.parseLong(c.substring(PREFIX.length() + 2), 36);
        return new ShareCode(seed, d);
    }

    @Override
    public String toString() {
        return encode();
    }
}
