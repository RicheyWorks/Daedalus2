// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.Arrays;

/**
 * G513 The Twin Logs: the captain and the mate each keep a ship's log. The purser indexes the captain's log in a
 * suffix automaton (at most 2n states), so any phrase's number of occurrences is read off in time linear in the
 * phrase, and the longest passage the two logs share is found in one pass over the mate's log. Logs use printable
 * ASCII (space to tilde), up to {@link #MAX_LOG} characters.
 *
 * <p>Daedalus hook: the purser's desk on the ark answers "how often does the log say X" and "where do the two logs
 * agree"; quest {@link #QUEST_ID} asks the player for the longest shared passage.
 */
public final class TwinLogs {

    public static final String QUEST_ID = "q_twin_logs";
    /** Longest log the purser indexes. */
    public static final int MAX_LOG = 20_000;

    private static final int FIRST = ' ';
    private static final int SIGMA = '~' - ' ' + 1;

    private final String log;
    private final int[][] next;
    private final int[] link;
    private final int[] len;
    private final long[] occ;
    private int states;

    /** Indexes the captain's log. */
    public TwinLogs(String captainsLog) {
        String s = captainsLog == null ? "" : captainsLog;
        if (s.length() > MAX_LOG) {
            throw new IllegalArgumentException("log longer than " + MAX_LOG);
        }
        for (int i = 0; i < s.length(); i++) {
            code(s.charAt(i));
        }
        this.log = s;
        int cap = 2 * s.length() + 2;
        next = new int[cap][];
        link = new int[cap];
        len = new int[cap];
        occ = new long[cap];
        next[0] = blank();
        link[0] = -1;
        states = 1;
        int last = 0;
        for (int i = 0; i < s.length(); i++) {
            last = extend(last, code(s.charAt(i)));
        }
        countOccurrences();
    }

    private static int code(char c) {
        int k = c - FIRST;
        if (k < 0 || k >= SIGMA) {
            throw new IllegalArgumentException("logs use printable ASCII only");
        }
        return k;
    }

    private static int[] blank() {
        int[] t = new int[SIGMA];
        Arrays.fill(t, -1);
        return t;
    }

    private int extend(int last, int c) {
        int cur = states++;
        next[cur] = blank();
        len[cur] = len[last] + 1;
        occ[cur] = 1;
        int p = last;
        while (p != -1 && next[p][c] == -1) {
            next[p][c] = cur;
            p = link[p];
        }
        if (p == -1) {
            link[cur] = 0;
        } else {
            int q = next[p][c];
            if (len[p] + 1 == len[q]) {
                link[cur] = q;
            } else {
                int clone = states++;
                next[clone] = next[q].clone();
                len[clone] = len[p] + 1;
                link[clone] = link[q];
                while (p != -1 && next[p][c] == q) {
                    next[p][c] = clone;
                    p = link[p];
                }
                link[q] = clone;
                link[cur] = clone;
            }
        }
        return cur;
    }

    private void countOccurrences() {
        int n = log.length();
        int[] bucket = new int[n + 2];
        for (int v = 0; v < states; v++) {
            bucket[len[v]]++;
        }
        for (int i = 1; i <= n; i++) {
            bucket[i] += bucket[i - 1];
        }
        int[] order = new int[states];
        for (int v = states - 1; v >= 0; v--) {
            order[--bucket[len[v]]] = v;
        }
        for (int i = states - 1; i > 0; i--) {
            int v = order[i];
            occ[link[v]] += occ[v];
        }
    }

    /** States in the automaton (at most 2n, or 1 for an empty log). */
    public int states() {
        return states;
    }

    /** Times the phrase occurs in the captain's log, overlaps counted; the empty phrase occurs n+1 times. */
    public long occurrences(String phrase) {
        if (phrase == null || phrase.isEmpty()) {
            return log.length() + 1L;
        }
        int v = 0;
        for (int i = 0; i < phrase.length(); i++) {
            int k = phrase.charAt(i) - FIRST;
            if (k < 0 || k >= SIGMA || next[v][k] == -1) {
                return 0;
            }
            v = next[v][k];
        }
        return occ[v];
    }

    /** Longest passage of the mate's log that also appears in the captain's log (earliest in the mate's log). */
    public String sharedPassage(String matesLog) {
        String t = matesLog == null ? "" : matesLog;
        int v = 0;
        int l = 0;
        int best = 0;
        int bestEnd = 0;
        for (int i = 0; i < t.length(); i++) {
            int k = t.charAt(i) - FIRST;
            if (k < 0 || k >= SIGMA) {
                v = 0;
                l = 0;
                continue;
            }
            while (v != 0 && next[v][k] == -1) {
                v = link[v];
                l = len[v];
            }
            if (next[v][k] != -1) {
                v = next[v][k];
                l++;
            }
            if (l > best) {
                best = l;
                bestEnd = i + 1;
            }
        }
        return t.substring(bestEnd - best, bestEnd);
    }

    /** Purser's desk line. */
    public String desk(String matesLog) {
        String p = sharedPassage(matesLog);
        if (p.isEmpty()) {
            return "The Twin Logs: the captain and the mate agree on nothing.";
        }
        return "The Twin Logs: the logs agree on \"" + p + "\" (" + p.length() + " characters).";
    }

    /** Quest q_twin_logs: the player names the longest shared passage (any passage of the right length counts). */
    public static boolean quest(String captainsLog, String matesLog, String answer) {
        if (answer == null) {
            return false;
        }
        TwinLogs tl = new TwinLogs(captainsLog);
        String m = matesLog == null ? "" : matesLog;
        return answer.length() == tl.sharedPassage(m).length() && m.contains(answer) && tl.occurrences(answer) > 0;
    }
}