// SPDX-License-Identifier: MIT

package com.daedalus.util;

/**
 * Disjoint-set union (a.k.a. Union-Find) over a fixed range of integer keys
 * {@code [0, size)}, with both standard optimizations:
 *
 * <ul>
 *   <li><b>Path compression</b> via a two-pass {@link #find}: first walk to the root, then
 *       point every node on the walked path directly at the root. Amortized cost stays
 *       inverse-Ackermann (effectively constant) per operation.</li>
 *   <li><b>Union by rank</b>: smaller tree's root is reparented under the taller tree's
 *       root; rank only increments on a tie. Keeps trees flat, complements path compression.</li>
 * </ul>
 *
 * <p>Keys are integers — callers that work with 2-D coordinates (the maze generators do)
 * should flatten via {@code r * cols + c}. This avoids the boxing + map overhead of the
 * earlier {@code HashMap<Point, Point>} approach that lived inline inside the Kruskal and
 * Borůvka generators.
 *
 * <p>Not thread-safe. Maze generation is single-threaded; the redundancy of safety on a
 * fast inner loop isn't worth paying for.
 *
 * @since 1.0
 */
public final class DSU {

    /** {@code parent[i]} is i's parent; the invariant is that the root r satisfies {@code parent[r] == r}. */
    private final int[] parent;

    /**
     * Upper bound on the height of the tree rooted at i. Stored as {@code byte} because
     * for any plausible {@code size} the tallest possible tree (no path compression) is
     * {@code log2(size)} ≤ ~31, which fits in a byte twice over.
     */
    private final byte[] rank;

    /**
     * Number of nodes in the set rooted at i. Only meaningful when i is a root (i.e.
     * {@code parent[i] == i}); values at non-root indices are stale and never read by this
     * class — callers must funnel through {@link #find} via {@link #sizeOf}.
     *
     * <p>Stored as {@code int} because the maximum size — {@code parent.length} — can be up
     * to {@code 512 * 512 = 262_144} in the largest validated maze grid, well past
     * {@code short} range.
     */
    private final int[] componentSize;

    /** Number of disjoint sets currently represented. Decremented on every successful union. */
    private int components;

    /**
     * Running maximum of {@code componentSize[r]} across every current root r. Updated on
     * every successful {@link #union}; never decreases (sets only grow under merging).
     * Tracked here so {@link #largestComponent} stays O(1) — the alternative is a full
     * {@code O(size)} sweep on every query.
     */
    private int largestSize;

    /**
     * Create a fresh DSU with {@code size} singleton sets {@code {0}, {1}, ..., {size-1}}.
     *
     * @throws IllegalArgumentException if {@code size < 0}
     */
    public DSU(int size) {
        if (size < 0) {
            throw new IllegalArgumentException("size must be >= 0, got " + size);
        }
        this.parent = new int[size];
        this.rank = new byte[size];
        this.componentSize = new int[size];
        for (int i = 0; i < size; i++) {
            parent[i] = i;
            componentSize[i] = 1;
        }
        this.components = size;
        this.largestSize = (size == 0 ? 0 : 1);
    }

    /** Total number of keys this structure was constructed for. */
    public int size() {
        return parent.length;
    }

    /** Number of disjoint sets currently represented (starts at {@link #size()}). */
    public int components() {
        return components;
    }

    /**
     * Number of nodes in the same set as {@code x}. Always {@code >= 1}; equals
     * {@link #size} when {@link #isFullyConnected} is true.
     *
     * <p>Path-compresses on the way to the root, so amortized cost is the same as
     * {@link #find}.
     *
     * @throws IndexOutOfBoundsException if {@code x} is not in {@code [0, size)}
     */
    public int sizeOf(int x) {
        return componentSize[find(x)];
    }

    /**
     * Size of the largest component currently in the structure (or {@code 0} on an
     * empty DSU). Maintained incrementally — O(1).
     */
    public int largestComponent() {
        return largestSize;
    }

    /**
     * {@code true} when every key is in a single set ({@code components() == 1}). False on
     * an empty DSU, matching the convention that "no components" is not "one component".
     */
    public boolean isFullyConnected() {
        return components == 1;
    }

    /**
     * Return the canonical representative of {@code x}'s set. Two-pass path compression:
     * first walk up to find the root, then walk up again rewriting every {@code parent[i]}
     * along the path to point directly at the root.
     *
     * @throws IndexOutOfBoundsException if {@code x} is not in {@code [0, size)}
     */
    public int find(int x) {
        // Pass 1: locate the root.
        int root = x;
        while (parent[root] != root) {
            root = parent[root];
        }
        // Pass 2: rewrite every parent pointer on the walked path to the root.
        int cur = x;
        while (parent[cur] != root) {
            int next = parent[cur];
            parent[cur] = root;
            cur = next;
        }
        return root;
    }

    /** {@code true} if {@code a} and {@code b} are in the same set. */
    public boolean connected(int a, int b) {
        return find(a) == find(b);
    }

    /**
     * Union the sets containing {@code a} and {@code b}. Reparents the shorter tree's
     * root under the taller tree's root; on a tie, the tree rooted at {@code find(a)}
     * becomes the new parent and its rank ticks up by one.
     *
     * <p>The new root absorbs the old root's component size; {@code largestSize} is
     * advanced if the merged component is now the biggest.
     *
     * @return {@code true} if a merge actually happened, {@code false} if the two were
     *         already in the same set
     */
    public boolean union(int a, int b) {
        int ra = find(a);
        int rb = find(b);
        if (ra == rb) return false;

        // Pick the new root using rank, then route the size accumulation to whichever side
        // wins. Done as separate branches (rather than computing newRoot/oldRoot first) so
        // the rank-tie path can keep its pre-existing "ra wins, rank ticks up" semantics
        // unchanged — preserving bit-for-bit Boruvka seed mapping.
        int merged;
        if (rank[ra] < rank[rb]) {
            parent[ra] = rb;
            componentSize[rb] += componentSize[ra];
            merged = componentSize[rb];
        } else if (rank[rb] < rank[ra]) {
            parent[rb] = ra;
            componentSize[ra] += componentSize[rb];
            merged = componentSize[ra];
        } else {
            parent[rb] = ra;
            rank[ra]++;
            componentSize[ra] += componentSize[rb];
            merged = componentSize[ra];
        }
        components--;
        if (merged > largestSize) largestSize = merged;
        return true;
    }
}
