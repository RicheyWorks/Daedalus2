// SPDX-License-Identifier: MIT

package com.daedalus.world.island;

/**
 * Seeded 2-D value noise with fractal octaves. Pure integer hashing (SplitMix64 finaliser) on a
 * lattice, smoothstep between lattice points — no {@code java.util.Random}, no floating-point
 * transcendental in the lattice, so the same seed gives the same field on every JVM. That is what
 * lets an island be a function of its seed (ADR-018): the server, a test golden and a later
 * metadata renderer all regenerate identical terrain from one number.
 */
public final class IslandNoise {

    private final long seed;

    public IslandNoise(long seed) {
        this.seed = seed;
    }

    /** Lattice value in [-1, 1] for integer cell (ix, iz) on channel {@code channel}. */
    double lattice(int ix, int iz, int channel) {
        long h = seed;
        h ^= (long) ix * 0x9E3779B97F4A7C15L;
        h ^= (long) iz * 0xC2B2AE3D27D4EB4FL;
        h ^= (long) channel * 0x165667B19E3779F9L;
        h = mix(h);
        // 53 high bits → [0,1), then to [-1,1].
        return ((h >>> 11) * 0x1.0p-53) * 2.0 - 1.0;
    }

    /** Smooth value noise in about [-1, 1] at real coordinates. */
    public double value(double x, double z, int channel) {
        int x0 = (int) Math.floor(x);
        int z0 = (int) Math.floor(z);
        double fx = smooth(x - x0);
        double fz = smooth(z - z0);
        double a = lattice(x0, z0, channel);
        double b = lattice(x0 + 1, z0, channel);
        double c = lattice(x0, z0 + 1, channel);
        double d = lattice(x0 + 1, z0 + 1, channel);
        double top = a + (b - a) * fx;
        double bottom = c + (d - c) * fx;
        return top + (bottom - top) * fz;
    }

    /** Fractal sum of {@code octaves} value-noise layers, normalised back to about [-1, 1]. */
    public double fractal(double x, double z, int channel, int octaves) {
        double sum = 0;
        double amp = 1;
        double freq = 1;
        double norm = 0;
        for (int o = 0; o < octaves; o++) {
            sum += value(x * freq, z * freq, channel + o * 7919) * amp;
            norm += amp;
            amp *= 0.5;
            freq *= 2.0;
        }
        return sum / norm;
    }

    private static double smooth(double t) {
        return t * t * (3 - 2 * t);
    }

    static long mix(long z) {
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        return z ^ (z >>> 31);
    }
}
