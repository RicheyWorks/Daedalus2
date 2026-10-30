// SPDX-License-Identifier: MIT

package com.daedalus.world.ark;

import java.util.ArrayList;
import java.util.List;
import java.util.NoSuchElementException;

/**
 * G511 The Ration Heap: the quartermaster hands out ration tickets in order of need, lowest number first (ties go to
 * the earlier ticket). Tickets can be raised in priority while waiting and two galleys can merge their queues. Kept
 * as a pairing heap: insert and meld in O(1), decrease-key by cutting the subtree and relinking it, delete-min by two-pass pairing in
 * O(log n) amortised, all without recursion.
 *
 * <p>Daedalus hook: the galley hatch serves the crew from this heap; quest {@link #QUEST_ID} asks the player which
 * ticket is called next after a run of hatch orders.
 */
public final class RationHeap {

    public static final String QUEST_ID = "q_ration_heap";

    /** A ration ticket; keep it to raise its priority later. */
    public static final class Ticket {
        private long need;
        private final long seq;
        private final String name;
        private Ticket child;
        private Ticket sibling;
        private Ticket prev;
        private boolean waiting = true;
        private RationHeap home;

        Ticket(long need, long seq, String name, RationHeap home) {
            this.need = need;
            this.seq = seq;
            this.name = name;
            this.home = home;
        }

        /** Current need, lower is served first. */
        public long need() {
            return need;
        }

        /** Crew member's name on the ticket. */
        public String name() {
            return name;
        }

        /** True until the ticket has been served. */
        public boolean waiting() {
            return waiting;
        }
    }

    /** An immutable record of a ticket at the hatch. */
    public static final class Served {
        private final String name;
        private final long need;

        Served(String name, long need) {
            this.name = name;
            this.need = need;
        }

        /** Crew member's name. */
        public String name() {
            return name;
        }

        /** Need when called. */
        public long need() {
            return need;
        }
    }

    private Ticket root;
    private int size;
    private long nextSeq;

    /** An empty queue. */
    public RationHeap() {
        // empty heap
    }

    private static boolean before(Ticket a, Ticket b) {
        return a.need < b.need || a.need == b.need && a.seq < b.seq;
    }

    /** Links two roots, returns the new root (both non-null, both with no siblings). */
    private static Ticket link(Ticket a, Ticket b) {
        Ticket top = a;
        Ticket low = b;
        if (before(b, a)) {
            top = b;
            low = a;
        }
        low.sibling = top.child;
        if (top.child != null) {
            top.child.prev = low;
        }
        low.prev = top;
        top.child = low;
        top.sibling = null;
        top.prev = null;
        return top;
    }

    private Ticket meldRoots(Ticket a, Ticket b) {
        if (a == null) {
            return b;
        }
        if (b == null) {
            return a;
        }
        return link(a, b);
    }

    /** Adds a ticket with the given need for the named crew member. */
    public Ticket issue(long need, String name) {
        Ticket t = new Ticket(need, nextSeq++, name == null ? "" : name, this);
        root = meldRoots(root, t);
        size++;
        return t;
    }

    /** Tickets waiting. */
    public int size() {
        return size;
    }

    /** True when nobody is waiting. */
    public boolean isEmpty() {
        return size == 0;
    }

    /** The ticket served next, without serving it. */
    public Served peek() {
        if (root == null) {
            throw new NoSuchElementException("no tickets waiting");
        }
        return new Served(root.name, root.need);
    }

    /** Serves and removes the next ticket. */
    public Served serve() {
        if (root == null) {
            throw new NoSuchElementException("no tickets waiting");
        }
        Ticket top = root;
        root = top.child == null ? null : pairUp(top.child);
        if (root != null) {
            root.prev = null;
        }
        top.child = null;
        top.waiting = false;
        top.home = null;
        size--;
        return new Served(top.name, top.need);
    }

    /** Two-pass pairing of a sibling list, iterative. */
    private static Ticket pairUp(Ticket first) {
        List<Ticket> pairs = new ArrayList<>();
        Ticket cur = first;
        while (cur != null) {
            Ticket a = cur;
            Ticket b = a.sibling;
            if (b == null) {
                a.sibling = null;
                a.prev = null;
                pairs.add(a);
                break;
            }
            cur = b.sibling;
            a.sibling = null;
            a.prev = null;
            b.sibling = null;
            b.prev = null;
            pairs.add(link(a, b));
        }
        Ticket acc = pairs.get(pairs.size() - 1);
        for (int i = pairs.size() - 2; i >= 0; i--) {
            acc = link(pairs.get(i), acc);
        }
        return acc;
    }

    /** Raises a waiting ticket's priority to a need no higher than its current one. */
    public void raise(Ticket t, long need) {
        if (t == null || !t.waiting || t.home != this) {
            throw new IllegalArgumentException("ticket is not waiting in this queue");
        }
        if (need > t.need) {
            throw new IllegalArgumentException("need can only go down");
        }
        t.need = need;
        if (t == root) {
            return;
        }
        if (t.prev.child == t) {
            t.prev.child = t.sibling;
        } else {
            t.prev.sibling = t.sibling;
        }
        if (t.sibling != null) {
            t.sibling.prev = t.prev;
        }
        t.sibling = null;
        t.prev = null;
        root = link(root, t);
    }

    /** Moves every ticket from the other galley's queue into this one; the other queue is left empty. */
    public void merge(RationHeap other) {
        if (other == null || other == this || other.root == null) {
            return;
        }
        List<Ticket> stack = new ArrayList<>();
        stack.add(other.root);
        while (!stack.isEmpty()) {
            Ticket x = stack.remove(stack.size() - 1);
            x.home = this;
            for (Ticket c = x.child; c != null; c = c.sibling) {
                stack.add(c);
            }
        }
        root = meldRoots(root, other.root);
        size += other.size;
        other.root = null;
        other.size = 0;
    }

    /** Hatch sign text. */
    public String hatchSign() {
        if (root == null) {
            return "The Ration Heap: hatch closed, nobody waiting.";
        }
        return "The Ration Heap: " + size + " waiting; next up " + root.name + " (need " + root.need + ").";
    }

    /**
     * Quest q_ration_heap: replays hatch orders and checks the player's answer for who is served next. Orders are
     * {@code "issue NAME NEED"} or {@code "serve"}.
     */
    public static boolean quest(List<String> orders, String answer) {
        RationHeap h = new RationHeap();
        for (String o : orders) {
            String[] p = o.trim().split("\\s+");
            if (p.length == 3 && "issue".equals(p[0])) {
                h.issue(Long.parseLong(p[2]), p[1]);
            } else if (p.length == 1 && "serve".equals(p[0]) && !h.isEmpty()) {
                h.serve();
            } else {
                return false;
            }
        }
        return !h.isEmpty() && h.peek().name().equals(answer);
    }
}