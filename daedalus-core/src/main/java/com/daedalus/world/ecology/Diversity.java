// SPDX-License-Identifier: MIT

package com.daedalus.world.ecology;

import java.util.Map;

/**
 * Community diversity, the CSRBT {@code CommunityMetrics} formulas over abundances (ADR-022).
 *
 * @param richness S, kinds present
 * @param shannon  H' = −Σ p·ln p
 * @param evenness Pielou J = H' / ln S (1 when every kind is equally common; 0 for S ≤ 1)
 * @param simpson  1 − Σ p² (chance two random individuals differ)
 */
public record Diversity(int richness, double total, double shannon, double evenness, double simpson) {

    public static Diversity of(Map<String, Double> abundance) {
        double total = 0;
        int s = 0;
        for (double n : abundance.values()) {
            if (n > 0) {
                total += n;
                s++;
            }
        }
        if (total <= 0) {
            return new Diversity(0, 0, 0, 0, 0);
        }
        double h = 0;
        double d = 0;
        for (double n : abundance.values()) {
            if (n > 0) {
                double p = n / total;
                h -= p * Math.log(p);
                d += p * p;
            }
        }
        double j = s > 1 ? h / Math.log(s) : 0;
        return new Diversity(s, total, h, j, 1 - d);
    }
}
