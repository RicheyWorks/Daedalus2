// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.SplittableRandom;

/**
 * Curse Sieve (contest gap G300): an inscription runs along a blade and a list of curse words must be found before it
 * is quenched. Count every occurrence of every curse, overlaps included, and report the first cursed position.
 *
 * <p>The tool is plain: an Aho-Corasick automaton (trie, BFS failure links, dictionary-suffix output links) scanned in
 * one pass over the text. Any project can use it for multi-pattern search such as chat filters or log scanning.
 */
public final class CurseSieve {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_curse_sieve";

    /** Runes used for seeded inscriptions. */
    public static final String RUNES = "fuxa";

    /** How a reading went. */
    public enum Grade { PURGED, CURSED }

    private final List<String> words;
    private final List<Map<Character, Integer>> next = new ArrayList<>();
    private final List<Integer> fail = new ArrayList<>();
    private final List<Integer> outLink = new ArrayList<>();
    private final List<int[]> ends = new ArrayList<>();

    /** Build the sieve for the given non-empty curse words (duplicates are counted separately). */
    public CurseSieve(List<String> curses) {
        this.words = List.copyOf(curses);
        newNode();
        for (int w = 0; w < words.size(); w++) {
            String s = words.get(w);
            if (s.isEmpty()) {
                throw new IllegalArgumentException("curse words must be non-empty");
            }
            int v = 0;
            for (int i = 0; i < s.length(); i++) {
                Integer to = next.get(v).get(s.charAt(i));
                if (to == null) {
                    to = newNode();
                    next.get(v).put(s.charAt(i), to);
                }
                v = to;
            }
            int[] old = ends.get(v);
            int[] grown = Arrays.copyOf(old, old.length + 1);
            grown[old.length] = w;
            ends.set(v, grown);
        }
        int[] queue = new int[next.size()];
        int head = 0;
        int tail = 0;
        for (int c : next.get(0).values()) {
            queue[tail++] = c;
        }
        while (head < tail) {
            int v = queue[head++];
            for (Map.Entry<Character, Integer> e : next.get(v).entrySet()) {
                int u = e.getValue();
                int f = fail.get(v);
                while (f > 0 && !next.get(f).containsKey(e.getKey())) {
                    f = fail.get(f);
                }
                Integer g = next.get(f).get(e.getKey());
                int fu = g != null && g != u ? g : 0;
                fail.set(u, fu);
                outLink.set(u, ends.get(fu).length > 0 ? fu : outLink.get(fu));
                queue[tail++] = u;
            }
        }
    }

    private int newNode() {
        next.add(new HashMap<>());
        fail.add(0);
        outLink.add(0);
        ends.add(new int[0]);
        return next.size() - 1;
    }

    /** A seeded inscription of {@code n} runes from the first {@code k} of {@link #RUNES}. */
    public static String inscription(long seed, int n, int k) {
        if (n < 0 || k < 1 || k > RUNES.length()) {
            throw new IllegalArgumentException("need n >= 0 and 1 <= k <= " + RUNES.length());
        }
        SplittableRandom r = new SplittableRandom(seed);
        StringBuilder sb = new StringBuilder(n);
        for (int i = 0; i < n; i++) {
            sb.append(RUNES.charAt(r.nextInt(k)));
        }
        return sb.toString();
    }

    private int step(int v, char c) {
        int s = v;
        while (s > 0 && !next.get(s).containsKey(c)) {
            s = fail.get(s);
        }
        Integer to = next.get(s).get(c);
        return to == null ? 0 : to;
    }

    /** counts[w] = occurrences of curse w in text, overlaps included. */
    public long[] counts(String text) {
        long[] c = new long[words.size()];
        int v = 0;
        for (int i = 0; i < text.length(); i++) {
            v = step(v, text.charAt(i));
            for (int u = v; u > 0; u = outLink.get(u)) {
                for (int w : ends.get(u)) {
                    c[w]++;
                }
            }
        }
        return c;
    }

    /** Start index of the earliest-ending curse occurrence (ties: the longest), or -1 if the text is clean. */
    public int firstHit(String text) {
        int v = 0;
        for (int i = 0; i < text.length(); i++) {
            v = step(v, text.charAt(i));
            int u = ends.get(v).length > 0 ? v : outLink.get(v);
            if (u > 0) {
                return i + 1 - words.get(ends.get(u)[0]).length();
            }
        }
        return -1;
    }

    /** PURGED only if every claimed count is right. */
    public Grade grade(String text, long[] claimed) {
        return Arrays.equals(counts(text), claimed) ? Grade.PURGED : Grade.CURSED;
    }

    /** The Forgemaster's line for a reading. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case PURGED -> "Forgemaster: every curse named and counted. The blade can take the quench.";
            case CURSED -> "Forgemaster: a curse slipped past you. Read the steel again, rune by rune.";
        };
    }
}
