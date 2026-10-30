// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.OptionalInt;
import java.util.SplittableRandom;

/**
 * G524 The Berth Leases: the ark harbourmaster leases berths for closed tick spans [from, to]. Leases come and go,
 * and the harbourmaster asks which leases hold a given tick, how many do, and whether a requested span clashes with
 * any lease. A dynamic interval tree (a treap keyed by lease start, each node keeping the latest end in its subtree)
 * answers a clash check in O(log n) expected, a stab query in O(k + log n) expected for k hits, and adds or removes a
 * lease in O(log n) expected.
 *
 * <p>Daedalus hook: the harbourmaster's lease ledger on the ark shows berth spans; quest {@link #QUEST_ID} asks the
 * player how many leases hold a shown tick ({@link #quest}).
 */
public final class BerthLeases {

    public static final String QUEST_ID = "q_berth_leases";
    /** Most leases the ledger holds. */
    public static final int MAX_LEASES = 500_000;

    private static final class Node {
        final long from;
        final long to;
        final int id;
        final long prio;
        long maxTo;
        Node left;
        Node right;

        Node(long from, long to, int id, long prio) {
            this.from = from;
            this.to = to;
            this.id = id;
            this.prio = prio;
            this.maxTo = to;
        }
    }

    private final SplittableRandom rng;
    private Node root;
    private int count;

    /** Creates an empty ledger; the seed fixes the treap shape for reproducible runs. */
    public BerthLeases(long seed) {
        this.rng = new SplittableRandom(seed);
    }

    /** Number of leases on the ledger. */
    public int size() {
        return count;
    }

    private static long maxTo(Node t) {
        return t == null ? Long.MIN_VALUE : t.maxTo;
    }

    private static void pull(Node t) {
        t.maxTo = Math.max(t.to, Math.max(maxTo(t.left), maxTo(t.right)));
    }

    private static int cmp(long f, int id, Node t) {
        int c = Long.compare(f, t.from);
        return c != 0 ? c : Integer.compare(id, t.id);
    }

    /** Splits t into keys less than (f, id) and keys at least (f, id). */
    private static Node[] split(Node t, long f, int id) {
        if (t == null) {
            return new Node[2];
        }
        if (cmp(f, id, t) > 0) {
            Node[] r = split(t.right, f, id);
            t.right = r[0];
            pull(t);
            r[0] = t;
            return r;
        }
        Node[] r = split(t.left, f, id);
        t.left = r[1];
        pull(t);
        r[1] = t;
        return r;
    }

    private static Node merge(Node a, Node b) {
        if (a == null) {
            return b;
        }
        if (b == null) {
            return a;
        }
        if (a.prio > b.prio) {
            a.right = merge(a.right, b);
            pull(a);
            return a;
        }
        b.left = merge(a, b.left);
        pull(b);
        return b;
    }

    /**
     * Adds lease id on span [from, to]. Ids must be distinct among leases on the ledger.
     *
     * @throws IllegalArgumentException when from &gt; to, the id is already leased or the ledger is full
     */
    public void add(int id, long from, long to) {
        if (from > to || count >= MAX_LEASES) {
            throw new IllegalArgumentException("need from <= to and room on the ledger");
        }
        if (find(root, from, id) != null) {
            throw new IllegalArgumentException("lease " + id + " already on the ledger at " + from);
        }
        Node[] p = split(root, from, id);
        root = merge(merge(p[0], new Node(from, to, id, rng.nextLong())), p[1]);
        count++;
    }

    private static Node find(Node t, long f, int id) {
        Node c = t;
        while (c != null) {
            int k = cmp(f, id, c);
            if (k == 0) {
                return c;
            }
            c = k < 0 ? c.left : c.right;
        }
        return null;
    }

    /** Removes lease id that starts at from; returns whether it was on the ledger. */
    public boolean remove(int id, long from) {
        int before = count;
        root = remove(root, from, id);
        return count < before;
    }

    private Node remove(Node t, long f, int id) {
        if (t == null) {
            return null;
        }
        int k = cmp(f, id, t);
        if (k == 0) {
            count--;
            return merge(t.left, t.right);
        }
        if (k < 0) {
            t.left = remove(t.left, f, id);
        } else {
            t.right = remove(t.right, f, id);
        }
        pull(t);
        return t;
    }

    /** Ids of all leases holding tick x, in ascending id order. */
    public List<Integer> stab(long x) {
        List<Integer> out = new ArrayList<>();
        stab(root, x, out);
        Collections.sort(out);
        return Collections.unmodifiableList(out);
    }

    private static void stab(Node t, long x, List<Integer> out) {
        if (t == null || t.maxTo < x) {
            return;
        }
        stab(t.left, x, out);
        if (t.from <= x) {
            if (t.to >= x) {
                out.add(t.id);
            }
            stab(t.right, x, out);
        }
    }

    /** Number of leases holding tick x. */
    public int countAt(long x) {
        return stab(x).size();
    }

    /** Id of a lease clashing with span [from, to] (sharing at least one tick), or empty when the span is free. */
    public OptionalInt clash(long from, long to) {
        if (from > to) {
            throw new IllegalArgumentException("need from <= to");
        }
        Node t = root;
        while (t != null) {
            if (t.from <= to && t.to >= from) {
                return OptionalInt.of(t.id);
            }
            if (t.left != null && t.left.maxTo >= from) {
                t = t.left;
            } else if (t.from <= to) {
                t = t.right;
            } else {
                t = null;
            }
        }
        return OptionalInt.empty();
    }

    /** Quest answer for {@link #QUEST_ID}: how many leases hold the shown tick. */
    public int quest(long tick) {
        return countAt(tick);
    }
}
