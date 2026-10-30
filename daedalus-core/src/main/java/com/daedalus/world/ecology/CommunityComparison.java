// SPDX-License-Identifier: MIT
// Adapted from CSRBT BetaDiversity, Copyright (c) 2026 Richmond.
// The complete upstream notice is in docs/third-party/CSRBT-MIT.txt.

package com.daedalus.world.ecology;

import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * CSRBT's six between-community measures, preserving Daedalus's fractional abundances.
 * Zero means absent. Counts must be finite and nonnegative; no rounding to individuals occurs.
 * Each measure retains the upstream empty-community convention. This compares snapshots, not
 * migration causes, habitat suitability or a synchronized census across worlds.
 */
public record CommunityComparison(int firstRichness, int secondRichness, int sharedRichness,
                                  double jaccard, double sorensen, double brayCurtis,
                                  double renkonen, double pianka, double whittakerTurnover,
                                  List<String> shared, List<String> onlyFirst,
                                  List<String> onlySecond) {

    public CommunityComparison {
        shared = List.copyOf(shared);
        onlyFirst = List.copyOf(onlyFirst);
        onlySecond = List.copyOf(onlySecond);
    }

    public static CommunityComparison between(Map<String, Double> first, Map<String, Double> second) {
        Map<String, Double> a = weights(first);
        Map<String, Double> b = weights(second);
        Set<String> both = new TreeSet<>(a.keySet());
        both.retainAll(b.keySet());
        Set<String> justA = new TreeSet<>(a.keySet());
        justA.removeAll(b.keySet());
        Set<String> justB = new TreeSet<>(b.keySet());
        justB.removeAll(a.keySet());
        return new CommunityComparison(a.size(), b.size(), both.size(),
                jaccard(a.keySet(), b.keySet()), sorensen(a.keySet(), b.keySet()),
                brayCurtis(a, b), renkonen(a, b), pianka(a, b),
                whittakerTurnover(List.of(a, b)), List.copyOf(both),
                List.copyOf(justA), List.copyOf(justB));
    }

    /** Presence/absence similarity. Two empty communities have similarity one. */
    public static double jaccard(Set<String> a, Set<String> b) {
        Set<String> union = new TreeSet<>(a);
        union.addAll(b);
        if (union.isEmpty()) return 1;
        Set<String> intersection = new TreeSet<>(a);
        intersection.retainAll(b);
        return (double) intersection.size() / union.size();
    }

    /** Presence/absence similarity, with twice the shared richness in the numerator. */
    public static double sorensen(Set<String> a, Set<String> b) {
        double total = (double) a.size() + b.size();
        if (total == 0) return 1;
        Set<String> intersection = new TreeSet<>(a);
        intersection.retainAll(b);
        return 2.0 * intersection.size() / total;
    }

    /** Abundance dissimilarity: zero is identical, one has no shared abundance. */
    public static double brayCurtis(Map<String, Double> first, Map<String, Double> second) {
        Map<String, Double> a = weights(first);
        Map<String, Double> b = weights(second);
        double scale = Math.max(maximum(a), maximum(b));
        if (scale == 0) return 0;
        double total = scaledTotal(a, scale) + scaledTotal(b, scale);
        double overlap = 0;
        for (var entry : a.entrySet()) {
            overlap += Math.min(entry.getValue() / scale, b.getOrDefault(entry.getKey(), 0.0) / scale);
        }
        return unit(1 - 2 * overlap / total);
    }

    /** Proportional abundance overlap. Two empty communities have overlap one. */
    public static double renkonen(Map<String, Double> first, Map<String, Double> second) {
        Map<String, Double> a = proportions(weights(first));
        Map<String, Double> b = proportions(weights(second));
        if (a.isEmpty() && b.isEmpty()) return 1;
        double overlap = 0;
        for (var entry : a.entrySet()) {
            overlap += Math.min(entry.getValue(), b.getOrDefault(entry.getKey(), 0.0));
        }
        return unit(overlap);
    }

    /** Cosine overlap of relative abundances. Either empty community gives zero. */
    public static double pianka(Map<String, Double> first, Map<String, Double> second) {
        Map<String, Double> a = proportions(weights(first));
        Map<String, Double> b = proportions(weights(second));
        double cross = 0;
        double aa = 0;
        double bb = 0;
        for (var entry : a.entrySet()) {
            double p = entry.getValue();
            aa += p * p;
            cross += p * b.getOrDefault(entry.getKey(), 0.0);
        }
        for (double p : b.values()) bb += p * p;
        double denominator = Math.sqrt(aa * bb);
        return denominator == 0 ? 0 : unit(cross / denominator);
    }

    /** Regional richness / mean local richness - 1; an empty collection gives zero. */
    public static double whittakerTurnover(List<Map<String, Double>> communities) {
        if (communities.isEmpty()) return 0;
        Set<String> region = new TreeSet<>();
        double richness = 0;
        for (Map<String, Double> community : communities) {
            Map<String, Double> positive = weights(community);
            region.addAll(positive.keySet());
            richness += positive.size();
        }
        return richness == 0 ? 0 : region.size() / (richness / communities.size()) - 1;
    }

    /** Sorted positive-presence keys, useful to other ecology consumers. */
    public static List<String> presence(Map<String, Double> community) {
        return List.copyOf(weights(community).keySet());
    }

    private static Map<String, Double> weights(Map<String, Double> community) {
        if (community == null) throw new IllegalArgumentException("Community is required");
        Map<String, Double> positive = new TreeMap<>();
        for (var entry : community.entrySet()) {
            String key = entry.getKey();
            Double count = entry.getValue();
            if (key == null || key.isBlank() || count == null || !Double.isFinite(count) || count < 0) {
                throw new IllegalArgumentException("Community requires species keys and finite nonnegative abundances");
            }
            if (count > 0) positive.put(key, count);
        }
        return positive;
    }

    private static double maximum(Map<String, Double> community) {
        double maximum = 0;
        for (double count : community.values()) maximum = Math.max(maximum, count);
        return maximum;
    }

    private static double scaledTotal(Map<String, Double> community, double scale) {
        double total = 0;
        for (double count : community.values()) total += count / scale;
        return total;
    }

    /** Common scaling avoids overflowing the sum of otherwise finite abundances. */
    private static Map<String, Double> proportions(Map<String, Double> community) {
        if (community.isEmpty()) return community;
        double scale = maximum(community);
        double total = scaledTotal(community, scale);
        Map<String, Double> result = new TreeMap<>();
        community.forEach((key, count) -> result.put(key, (count / scale) / total));
        return result;
    }

    private static double unit(double value) {
        return Math.max(0, Math.min(1, value));
    }
}
