// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.HashMap;
import java.util.Map;
import java.util.OptionalLong;

/**
 * G314 The Beacon Cycle: a beacon's brightness steps from 1 by multiplying by g modulo a prime p.
 * Finds how many steps before it returns to 1 (the multiplicative order, from the prime lots of
 * p - 1 via {@link CrateManifest}), the smallest primitive root (a g that visits every brightness),
 * and how many steps reach a target brightness, by baby-step giant-step in O(sqrt p).
 */
public final class BeaconCycle {

    public static final String QUEST_ID = "q_beacon_cycle";

    private BeaconCycle() { }

    private static void check(long g, long p) {
        if (p < 2 || p >= LanternHandshake.MAX_MOD || !LanternHandshake.isPrime(p)) {
            throw new IllegalArgumentException("p must be a prime below MAX_MOD: " + p);
        }
        if (g % p == 0 || g < 1) {
            throw new IllegalArgumentException("g must be a positive unit mod p");
        }
    }

    public static long order(long g, long p) {
        check(g, p);
        long t = p - 1;
        if (t == 1) {
            return 1;
        }
        for (long q : CrateManifest.lots(p - 1).keySet()) {
            while (t % q == 0 && LanternHandshake.powMod(g, t / q, p) == 1) {
                t /= q;
            }
        }
        return t;
    }

    public static long primitiveRoot(long p) {
        check(1, p);
        for (long g = 1; g < p; g++) {
            if (order(g, p) == p - 1) {
                return g;
            }
        }
        throw new IllegalStateException("no primitive root for " + p);
    }

    /** Smallest x >= 0 with g^x = h (mod p), or empty when h is never reached. */
    public static OptionalLong steps(long g, long h, long p) {
        check(g, p);
        long target = Math.floorMod(h, p);
        long ord = order(g, p);
        long m = (long) Math.ceil(Math.sqrt((double) ord));
        Map<Long, Long> baby = new HashMap<>();
        long cur = 1;
        for (long j = 0; j < m; j++) {
            baby.putIfAbsent(cur, j);
            cur = cur * (g % p) % p;
        }
        long giant = LanternHandshake.powMod(g, (p - 1) - (m % (p - 1)), p);
        long y = target;
        for (long i = 0; i <= m; i++) {
            Long j = baby.get(y);
            if (j != null) {
                long x = i * m + j;
                if (x < ord) {
                    return OptionalLong.of(x);
                }
            }
            y = y * giant % p;
        }
        return OptionalLong.empty();
    }

    /** Quest q_beacon_cycle: name the steps from 1 to the target brightness. */
    public static boolean quest(long g, long h, long p, long answer) {
        OptionalLong x = steps(g, h, p);
        return x.isPresent() && x.getAsLong() == answer;
    }
}