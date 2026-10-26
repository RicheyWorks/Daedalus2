// SPDX-License-Identifier: MIT

package com.daedalus.world.ecology;

/**
 * MacArthur–Wilson island biogeography (1967), ported from CSRBT's
 * {@code experimental.ecology.TheoreticalModels} (ADR-022). The closed forms are the theory a sky
 * island is measured against; {@link Community} is what the island actually does.
 */
public final class Biogeography {

    private Biogeography() {
    }

    /** Equilibrium richness S* = c / (c + e) · pool; 0 when both rates are 0. */
    public static double equilibrium(double c, double e, double pool) {
        if (c < 0 || e < 0) {
            throw new IllegalArgumentException("rates must be >= 0");
        }
        return c + e <= 0 ? 0.0 : c / (c + e) * pool;
    }

    /** Richness at time t from S0: S* + (S0 − S*)·e^(−(c+e)t). */
    public static double richnessAt(double c, double e, double pool, double s0, double t) {
        double sStar = equilibrium(c, e, pool);
        return sStar + (s0 - sStar) * Math.exp(-(c + e) * t);
    }

    /** Logistic population at time t: K / (1 + ((K − N0)/N0)·e^(−rt)); 0 from an empty start. */
    public static double logisticAt(double r, double k, double n0, double t) {
        if (!(k > 0)) {
            throw new IllegalArgumentException("carrying capacity K must be > 0");
        }
        return n0 <= 0 ? 0.0 : k / (1.0 + ((k - n0) / n0) * Math.exp(-r * t));
    }

    /**
     * The island's environment, as CSRBT's {@code TheoreticalModels.Environment}: colonization
     * c·wind·temperature·e^(−distance), extinction e / area, growth r·temperature, capacity K·area.
     */
    public record Environment(double area, double temperature, double wind, double distance) {

        public Environment {
            if (area <= 0) {
                throw new IllegalArgumentException("area must be > 0");
            }
            if (temperature < 0 || wind < 0 || distance < 0) {
                throw new IllegalArgumentException("temperature, wind, distance must be >= 0");
            }
        }

        public double colonization(double c) {
            return c * wind * temperature * Math.exp(-distance);
        }

        public double extinction(double e) {
            return e / area;
        }

        public double growth(double r) {
            return r * temperature;
        }

        public double capacity(double k) {
            return k * area;
        }
    }
}
