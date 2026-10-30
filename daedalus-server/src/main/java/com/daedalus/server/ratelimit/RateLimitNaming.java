// SPDX-License-Identifier: MIT

package com.daedalus.server.ratelimit;

/**
 * Single source of truth for how per-key rate-limiter instances are named.
 *
 * <p>A per-key Resilience4j instance is named {@code <base><SEP><key>}, e.g.
 * {@code mazeGenerate::ip:203.0.113.7} or {@code authLogin::sub:admin}. Two subsystems care
 * about this convention and must agree on it:
 * <ul>
 *   <li>{@link PerKeyRateLimitInterceptor} <em>builds</em> the composite name when acquiring a
 *       permit;</li>
 *   <li>{@code ApiExceptionHandler} <em>parses</em> the composite name back down to the base so
 *       the {@code 429} body reports {@code mazeGenerate} (stable, non-identifying) rather than
 *       the full per-key name (which would leak the caller's IP or subject).</li>
 * </ul>
 *
 * <p>The separator is {@code "::"} — chosen because it never appears in a Resilience4j instance
 * base name (they are simple identifiers) and is trivial to strip. Caller keys may in theory
 * contain it (a pathological subject name), but {@link #baseOf(String)} splits on the
 * <em>first</em> occurrence, so the base is always recovered intact.
 */
public final class RateLimitNaming {

    /** Separator between the base instance name and the caller key. */
    public static final String SEP = "::";

    private RateLimitNaming() {
    }

    /**
     * Compose the per-key instance name from a base instance name and a caller key.
     *
     * @param base the Resilience4j base instance name (e.g. {@code mazeGenerate})
     * @param key  the resolved caller key (e.g. {@code ip:203.0.113.7})
     * @return the composite per-key instance name
     */
    public static String perKey(String base, String key) {
        return base + SEP + key;
    }

    /**
     * Recover the base instance name from a (possibly composite) instance name. Names with no
     * separator — the plain base instances configured in YAML — are returned unchanged, which
     * keeps the handler correct for both the old global limiters and the new per-key ones.
     *
     * @param name a plain or composite instance name; {@code null} yields {@code "unknown"}
     * @return the base instance name
     */
    public static String baseOf(String name) {
        if (name == null) {
            return "unknown";
        }
        int i = name.indexOf(SEP);
        return i < 0 ? name : name.substring(0, i);
    }
}
