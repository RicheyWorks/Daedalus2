package com.daedalus.world.audio;

/** SplitMix64: tiny, portable and identical in C++/JS ports. */
public final class Rng {
    private long state;

    /** Seeds the generator. */
    public Rng(long seed) {
        this.state = seed;
    }

    /** Next raw 64-bit value. */
    public long nextLong() {
        long z = state += 0x9e3779b97f4a7c15L;
        z = (z ^ (z >>> 30)) * 0xbf58476d1ce4e5b9L;
        z = (z ^ (z >>> 27)) * 0x94d049bb133111ebL;
        return z ^ (z >>> 31);
    }

    /** Uniform double in [0,1). */
    public double nextDouble() {
        return (nextLong() >>> 11) * 0x1.0p-53;
    }
}
