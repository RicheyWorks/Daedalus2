// SPDX-License-Identifier: MIT

package com.daedalus.wallet;

import java.security.SecureRandom;
import java.time.Duration;
import java.time.Instant;
import java.util.HexFormat;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Single-use sign-in nonces (ADR-028). The server hands one out, the wallet signs a message that
 * carries it, and the sign-in consumes it: a captured signature cannot be replayed. Bounded — at
 * most {@code capacity} outstanding, oldest dropped first — and expiring after {@code ttl}, so an
 * unauthenticated route that mints them cannot grow memory without limit. Thread-safe.
 */
public final class WalletNonces {

    private static final SecureRandom RANDOM = new SecureRandom();

    private final Duration ttl;
    private final int capacity;
    private final LinkedHashMap<String, Instant> issued = new LinkedHashMap<>();

    public WalletNonces(Duration ttl, int capacity) {
        if (ttl == null || ttl.isNegative() || ttl.isZero()) {
            throw new IllegalArgumentException("ttl must be positive");
        }
        if (capacity < 1) {
            throw new IllegalArgumentException("capacity must be at least 1");
        }
        this.ttl = ttl;
        this.capacity = capacity;
    }

    /** A fresh 32-hex-digit nonce, valid until {@code now + ttl}. */
    public synchronized String issue(Instant now) {
        prune(now);
        byte[] b = new byte[16];
        RANDOM.nextBytes(b);
        String nonce = HexFormat.of().formatHex(b);
        issued.put(nonce, now.plus(ttl));
        while (issued.size() > capacity) {
            Iterator<String> oldest = issued.keySet().iterator();
            oldest.next();
            oldest.remove();
        }
        return nonce;
    }

    /** True exactly once for a nonce issued here and not yet expired; it is gone afterwards. */
    public synchronized boolean consume(String nonce, Instant now) {
        if (nonce == null) {
            return false;
        }
        Instant until = issued.remove(nonce);
        return until != null && !now.isAfter(until);
    }

    /** Hold a nonce issued elsewhere (another replica, a test fixture) as if it were issued at {@code at}. */
    public synchronized void adopt(String nonce, Instant at) {
        if (nonce == null || !nonce.matches("[A-Za-z0-9]{8,64}")) {
            throw new IllegalArgumentException("nonce must be 8-64 letters or digits");
        }
        issued.put(nonce, at.plus(ttl));
    }

    public synchronized int outstanding() {
        return issued.size();
    }

    private void prune(Instant now) {
        for (Iterator<Map.Entry<String, Instant>> it = issued.entrySet().iterator(); it.hasNext();) {
            if (now.isAfter(it.next().getValue())) {
                it.remove();
            }
        }
    }
}
