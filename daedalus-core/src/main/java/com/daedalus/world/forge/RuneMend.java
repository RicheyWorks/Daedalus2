// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

/**
 * Rune Mend (contest gap G205): the forge stamps a maker's mark of runes on every ingot ({@link IngotCuts}), and a worn
 * stamp garbles it. Mend the garbled string back to the true mark with the fewest strikes: insert, delete or change
 * one rune.
 *
 * <p>The tool is plain: {@link #distance} is the exact Levenshtein DP, {@link #script} gives one shortest edit script
 * and {@link #nearest} names the registered mark closest to a garbled stamp (ties go to the earliest). Any project can
 * use it for fuzzy names or typo-tolerant commands.
 */
public final class RuneMend {

    /** Quest id for the forge board. */
    public static final String QUEST_ID = "q_rune_mend";
    /** The runes a stamp can carry. */
    public static final String RUNES = "ABDEFGHIKLMNORSTUW";

    /** How a mend went. */
    public enum Grade { CLEAN, ROUGH, WRONG_MARK }

    /** One strike: KEEP, CHANGE, INSERT or DELETE at a position of the string being mended. */
    public record Strike(String op, int at, char rune) {
    }

    private RuneMend() {
    }

    /** A seeded garble of {@code mark}: {@code wear} random strikes. Same seed, same garble. */
    public static String garble(long seed, String mark, int wear) {
        if (wear < 0) {
            throw new IllegalArgumentException("wear must be >= 0");
        }
        SplittableRandom r = new SplittableRandom(seed);
        StringBuilder s = new StringBuilder(mark);
        for (int i = 0; i < wear; i++) {
            char c = RUNES.charAt(r.nextInt(RUNES.length()));
            int kind = s.length() == 0 ? 1 : r.nextInt(3);
            if (kind == 0) {
                s.setCharAt(r.nextInt(s.length()), c);
            } else if (kind == 1) {
                s.insert(r.nextInt(s.length() + 1), c);
            } else {
                s.deleteCharAt(r.nextInt(s.length()));
            }
        }
        return s.toString();
    }

    private static int[][] table(String a, String b) {
        int[][] d = new int[a.length() + 1][b.length() + 1];
        for (int i = 0; i <= a.length(); i++) {
            d[i][0] = i;
        }
        for (int j = 0; j <= b.length(); j++) {
            d[0][j] = j;
        }
        for (int i = 1; i <= a.length(); i++) {
            for (int j = 1; j <= b.length(); j++) {
                int sub = d[i - 1][j - 1] + (a.charAt(i - 1) == b.charAt(j - 1) ? 0 : 1);
                d[i][j] = Math.min(sub, Math.min(d[i - 1][j], d[i][j - 1]) + 1);
            }
        }
        return d;
    }

    /** Fewest strikes turning {@code a} into {@code b}. */
    public static int distance(String a, String b) {
        return table(a, b)[a.length()][b.length()];
    }

    /** One shortest edit script from {@code a} to {@code b}; positions refer to {@code a} as it is being mended. */
    public static List<Strike> script(String a, String b) {
        int[][] d = table(a, b);
        List<Strike> rev = new ArrayList<>();
        int i = a.length();
        int j = b.length();
        while (i > 0 || j > 0) {
            if (i > 0 && j > 0 && d[i][j] == d[i - 1][j - 1] + (a.charAt(i - 1) == b.charAt(j - 1) ? 0 : 1)) {
                rev.add(new Strike(a.charAt(i - 1) == b.charAt(j - 1) ? "KEEP" : "CHANGE", i - 1, b.charAt(j - 1)));
                i--;
                j--;
            } else if (i > 0 && d[i][j] == d[i - 1][j] + 1) {
                rev.add(new Strike("DELETE", i - 1, a.charAt(i - 1)));
                i--;
            } else {
                rev.add(new Strike("INSERT", i, b.charAt(j - 1)));
                j--;
            }
        }
        List<Strike> out = new ArrayList<>();
        for (int k = rev.size() - 1; k >= 0; k--) {
            out.add(rev.get(k));
        }
        return out;
    }

    /** Applies a script produced by {@link #script} to {@code a}. */
    public static String apply(String a, List<Strike> script) {
        StringBuilder s = new StringBuilder();
        for (Strike k : script) {
            String op = k.op();
            if (!List.of("KEEP", "CHANGE", "INSERT", "DELETE").contains(op)) {
                throw new IllegalArgumentException("unknown strike " + op);
            }
            if ("KEEP".equals(op)) {
                s.append(a.charAt(k.at()));
            } else if (!"DELETE".equals(op)) {
                s.append(k.rune());
            }
        }
        return s.toString();
    }

    /** Strikes in a script that cost something (all but KEEP). */
    public static int cost(List<Strike> script) {
        int c = 0;
        for (Strike k : script) {
            if (!"KEEP".equals(k.op())) {
                c++;
            }
        }
        return c;
    }

    /** Index of the registered mark closest to {@code stamp} (earliest on ties). */
    public static int nearest(List<String> marks, String stamp) {
        if (marks.isEmpty()) {
            throw new IllegalArgumentException("no marks registered");
        }
        int best = 0;
        int bd = distance(marks.get(0), stamp);
        for (int i = 1; i < marks.size(); i++) {
            int dd = distance(marks.get(i), stamp);
            if (dd < bd) {
                bd = dd;
                best = i;
            }
        }
        return best;
    }

    /** CLEAN if the mend reaches the mark in the fewest strikes, ROUGH if more, WRONG_MARK if it misses. */
    public static Grade grade(String garbled, String mark, String mended, int strikes) {
        if (!mark.equals(mended)) {
            return Grade.WRONG_MARK;
        }
        return strikes <= distance(garbled, mark) ? Grade.CLEAN : Grade.ROUGH;
    }

    /** The Forgemaster's line for a mend. */
    public static String forgemasterLine(Grade g) {
        return switch (g) {
            case CLEAN -> "Forgemaster: the mark reads true, and not a strike wasted.";
            case ROUGH -> "Forgemaster: it reads true, but you hammered it more than it needed.";
            case WRONG_MARK -> "Forgemaster: that is somebody else's mark now. Start again.";
        };
    }
}
