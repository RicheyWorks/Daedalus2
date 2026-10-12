// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox;

import java.util.function.LongSupplier;

/**
 * A small consecutive-failure circuit breaker for one upstream (rd-studio, an RPC endpoint). CLOSED lets calls through;
 * {@code threshold} failures in a row trip it OPEN, which fails calls instantly for {@code openMs}; then HALF_OPEN lets a
 * single probe through: success closes it, failure re-opens it. Thread-safe; cheap enough to ask on every request.
 */
public final class CircuitBreaker {

    public enum State { CLOSED, OPEN, HALF_OPEN }

    private final int threshold;
    private final long openMs;
    private final LongSupplier clock;
    private int failures;
    private long openedAt;
    private State state = State.CLOSED;
    private boolean probing;

    public CircuitBreaker(int threshold, long openMs, LongSupplier clock) {
        this.threshold = Math.max(1, threshold);
        this.openMs = Math.max(1, openMs);
        this.clock = clock;
    }

    /** True if a call may go out now. In HALF_OPEN only one caller gets the probe. */
    public synchronized boolean allow() {
        if (state == State.OPEN && clock.getAsLong() - openedAt >= openMs) {
            state = State.HALF_OPEN;
            probing = false;
        }
        if (state == State.CLOSED) return true;
        if (state == State.HALF_OPEN && !probing) {
            probing = true;
            return true;
        }
        return false;
    }

    public synchronized void success() {
        failures = 0;
        probing = false;
        state = State.CLOSED;
    }

    public synchronized void failure() {
        probing = false;
        if (state == State.HALF_OPEN || ++failures >= threshold) {
            state = State.OPEN;
            openedAt = clock.getAsLong();
        }
    }

    /** Opens now for {@code ms} (the upstream asked us to back off, e.g. 503 + Retry-After), then half-opens as usual. */
    public synchronized void trip(long ms) {
        probing = false;
        state = State.OPEN;
        openedAt = clock.getAsLong() - openMs + Math.max(1, ms);
    }

    public synchronized State state() {
        if (state == State.OPEN && clock.getAsLong() - openedAt >= openMs) return State.HALF_OPEN;
        return state;
    }
}
