// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.Arrays;
import java.util.SplittableRandom;

/**
 * Chimney Sightlines (contest gap G256): a row of forge chimneys. For each chimney name the nearest taller chimney to
 * its east, and how many chimneys in an unbroken run to its west (itself included) it stands at least as tall as.
 *
 * <p>The tool is plain: {@link #nextGreater} and {@link #span} are O(n) monotonic-stack passes over an {@code int[]}.
 * Any project can use them for next-greater-element and stock-span queries.
 */
public final class ChimneySightlines {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_chimney_sightlines";

    /** How a lookout's answers went. */
    public enum Grade { KEEN, HAZY }

    private ChimneySightlines() {
    }

    /** {@code n} seeded chimney heights in 1..maxHeight. Same seed, same row. */
    public static int[] row(long seed, int n, int maxHeight) {
        if (n < 0 || maxHeight < 1) {
            throw new IllegalArgumentException("need n >= 0 and maxHeight >= 1");
        }
        SplittableRandom r = new SplittableRandom(seed);
        int[] h = new int[n];
        for (int i = 0; i < n; i++) {
            h[i] = 1 + r.nextInt(maxHeight);
        }
        return h;
    }

    /** out[i] = index of the nearest strictly taller chimney east of i, or -1. */
    public static int[] nextGreater(int[] h) {
        int n = h.length;
        int[] out = new int[n];
        Arrays.fill(out, -1);
        int[] st = new int[n];
        int top = 0;
        for (int i = 0; i < n; i++) {
            while (top > 0 && h[st[top - 1]] < h[i]) {
                out[st[--top]] = i;
            }
            st[top++] = i;
        }
        return out;
    }

    /** out[i] = length of the run ending at i whose chimneys are all no taller than h[i]. */
    public static int[] span(int[] h) {
        int n = h.length;
        int[] out = new int[n];
        int[] st = new int[n];
        int top = 0;
        for (int i = 0; i < n; i++) {
            while (top > 0 && h[st[top - 1]] <= h[i]) {
                top--;
            }
            out[i] = top == 0 ? i + 1 : i - st[top - 1];
            st[top++] = i;
        }
        return out;
    }

    /** KEEN only if both the eastward sightlines and the westward spans are exactly right. */
    public static Grade grade(int[] h, int[] east, int[] west) {
        return Arrays.equals(nextGreater(h), east) && Arrays.equals(span(h), west) ? Grade.KEEN : Grade.HAZY;
    }

    /** The Forgemaster's line for a lookout. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case KEEN -> "Forgemaster: you read every chimney like a lookout. Smoke signals are yours to send.";
            case HAZY -> "Forgemaster: the smoke fooled your eye. Climb the tower and look again.";
        };
    }
}
