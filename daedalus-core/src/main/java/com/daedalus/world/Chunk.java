// SPDX-License-Identifier: MIT

package com.daedalus.world;

import java.util.Arrays;

/**
 * One {@code 16×16×16} payload. Worlds omit empty chunks; a missing chunk is AIR.
 *
 * <p>Stored the way Minecraft stores a chunk section (ADR-064 rule 1): a palette of the block kinds present plus the
 * fewest bits per cube that can index it.
 * <ul>
 *   <li><b>uniform</b> (one kind, e.g. solid stone under an island): no per-cube array at all, about 60 bytes;</li>
 *   <li><b>4 bits</b> (2 to 16 kinds, nearly every terrain chunk): 2 KiB instead of 4;</li>
 *   <li><b>8 bits</b> (more than 16 kinds): the dense 4 KiB array, as before.</li>
 * </ul>
 * Writes widen the storage when a new kind arrives and never narrow it; {@link #copy()} and loading from a payload
 * pick the narrowest form. Reads are lock-free, as {@link World} needs: a widen builds a new {@code Store} whose
 * fields are final (safe publication), and a 4-bit index can never point outside the 16-entry palette.
 */
public final class Chunk {

    public static final int SIZE = 16;
    public static final int VOLUME = SIZE * SIZE * SIZE;

    /** BlockType.values() clones its array on every call; get() is the hottest read in the engine, so keep one. */
    private static final BlockType[] TYPES = BlockType.values();
    private static final int NIBBLE_KINDS = 16;

    /** A storage form. {@code bits} 0 = uniform ({@code palette[0]}), 4 = nibbles into the palette, 8 = ordinals. */
    private static final class Store {
        final int bits;
        final byte[] palette;
        final byte[] data;
        int kinds;
        /** Chunk.runs() of this store, until an in-place write; volatile so a saver thread sees it whole. */
        volatile byte[] runs;

        Store(int bits, byte[] palette, byte[] data, int kinds) {
            this.bits = bits;
            this.palette = palette;
            this.data = data;
            this.kinds = kinds;
        }

        int ordinal(int i) {
            switch (bits) {
                case 0:
                    return palette[0] & 0xff;
                case 4:
                    return palette[(data[i >> 1] >> ((i & 1) << 2)) & 0x0f] & 0xff;
                default:
                    return data[i] & 0xff;
            }
        }

        long bytes() {
            // object headers + arrays, the way a heap dump counts them (16-byte header, 16-byte array header)
            return 32 + 16 + palette.length + (data == null ? 0 : 16 + data.length);
        }
    }

    /** Final fields in Store make a widened store safely visible to lock-free readers without volatile. */
    private Store store;
    /** True when another Chunk may hold the same store (a copy): the next write clones it first. */
    private boolean shared;
    private int occupied;
    private long revision;

    public Chunk() {
        this.store = uniform(0);
    }

    private Chunk(Store store, int occupied, long revision) {
        this.store = store;
        this.occupied = occupied;
        this.revision = revision;
    }

    private static Store cloneStore(Store s) {
        return new Store(s.bits, s.palette.clone(), s.data == null ? null : s.data.clone(), s.kinds);
    }

    private static Store uniform(int ordinal) {
        return new Store(0, new byte[] {(byte) ordinal}, null, 1);
    }

    public BlockType get(int localX, int localY, int localZ) {
        return TYPES[store.ordinal(index(localX, localY, localZ))];
    }

    public BlockType set(int localX, int localY, int localZ, BlockType type) {
        if (type == null) {
            throw new IllegalArgumentException("BlockType is required");
        }
        int i = index(localX, localY, localZ);
        Store s = store;
        int before = s.ordinal(i);
        int after = type.ordinal();
        revision++;
        if (before == after) {
            return TYPES[before];
        }
        if (shared) {
            // copy on write: a snapshot still reads the old store, so this chunk takes its own before changing it
            s = cloneStore(s);
            store = s;
            shared = false;
        }
        s.runs = null;
        write(s, i, after);
        if (before == 0) {
            occupied++;
        } else if (after == 0) {
            occupied--;
        }
        return TYPES[before];
    }

    private void write(Store s, int i, int ordinal) {
        if (s.bits == 8) {
            s.data[i] = (byte) ordinal;
            return;
        }
        if (s.bits == 0) {
            // widen: the old kind becomes palette slot 0, which an all-zero nibble array already means
            byte[] palette = new byte[NIBBLE_KINDS];
            palette[0] = s.palette[0];
            palette[1] = (byte) ordinal;
            byte[] data = new byte[VOLUME / 2];
            setNibble(data, i, 1);
            store = new Store(4, palette, data, 2);
            return;
        }
        int slot = slot(s, ordinal);
        if (slot < 0 && s.kinds < NIBBLE_KINDS) {
            slot = s.kinds;
            s.palette[slot] = (byte) ordinal;   // written before any nibble can name it
            s.kinds++;
        }
        if (slot >= 0) {
            setNibble(s.data, i, slot);
            return;
        }
        byte[] dense = dense(s);
        dense[i] = (byte) ordinal;
        store = new Store(8, new byte[0], dense, 0);
    }

    private static int slot(Store s, int ordinal) {
        for (int k = 0; k < s.kinds; k++) {
            if ((s.palette[k] & 0xff) == ordinal) {
                return k;
            }
        }
        return -1;
    }

    private static void setNibble(byte[] data, int i, int slot) {
        int shift = (i & 1) << 2;
        int b = data[i >> 1] & ~(0x0f << shift);
        data[i >> 1] = (byte) (b | (slot << shift));
    }

    private static byte[] dense(Store s) {
        byte[] out = new byte[VOLUME];
        if (s.bits == 8) {
            System.arraycopy(s.data, 0, out, 0, VOLUME);
        } else if (s.bits == 0) {
            Arrays.fill(out, s.palette[0]);
        } else {
            for (int i = 0; i < VOLUME; i++) {
                out[i] = (byte) s.ordinal(i);
            }
        }
        return out;
    }

    /** The narrowest store for a dense payload, and how many cubes are not AIR. */
    private static Chunk compact(byte[] dense, long revision) {
        int[] slotOf = new int[256];
        Arrays.fill(slotOf, -1);
        byte[] palette = new byte[NIBBLE_KINDS];
        int kinds = 0;
        int occupied = 0;
        for (byte b : dense) {
            int o = b & 0xff;
            if (o != 0) {
                occupied++;
            }
            if (slotOf[o] < 0) {
                if (kinds < NIBBLE_KINDS) {
                    palette[kinds] = b;
                }
                slotOf[o] = kinds++;
            }
        }
        if (kinds == 1) {
            return new Chunk(uniform(dense[0] & 0xff), occupied, revision);
        }
        if (kinds > NIBBLE_KINDS) {
            return new Chunk(new Store(8, new byte[0], dense.clone(), 0), occupied, revision);
        }
        byte[] data = new byte[VOLUME / 2];
        for (int i = 0; i < VOLUME; i++) {
            setNibble(data, i, slotOf[dense[i] & 0xff]);
        }
        return new Chunk(new Store(4, palette, data, kinds), occupied, revision);
    }

    public boolean isEmpty() {
        return occupied == 0;
    }

    /** Cubes that are not AIR. O(1): kept up to date by {@link #set}. */
    public int occupied() {
        return occupied;
    }

    public long revision() {
        return revision;
    }

    /** Bits per cube in the current storage: 0 (one kind), 4 or 8. */
    public int bitsPerBlock() {
        return store.bits;
    }

    /** Heap bytes this chunk's block storage holds (arrays and headers), for RAM reports. */
    public long storageBytes() {
        return 24 + store.bytes();
    }

    /**
     * A copy that shares this chunk's storage until either one is written (copy on write), so a world snapshot costs
     * one small object per chunk instead of 4 KiB. Saving a snapshot reuses each unchanged chunk's cached runs.
     */
    public Chunk copy() {
        shared = true;
        Chunk c = new Chunk(store, occupied, revision);
        c.shared = true;
        return c;
    }

    /** A copy in the narrowest storage form (writes widen and never narrow; this undoes that). */
    public Chunk compacted() {
        return compact(dense(store), revision);
    }

    /**
     * Dense ordinal payload, a copy: {@code index = x + 16 * (y + 16 * z)} in local coordinates,
     * each byte a {@link BlockType} ordinal. This is what a renderer meshes from; the chunk's own
     * storage never leaves the class.
     */
    public byte[] ordinals() {
        return dense(store);
    }

    /**
     * Dense ordinal payload for a later snapshot. Callers must not mutate the array.
     */
    byte[] payload() {
        return dense(store);
    }

    /**
     * Run-length form for the wire: triples of (ordinal, run length low byte, high byte) in index order
     * ({@code x + 16 * (y + 16 * z)}), runs 1..4096. A uniform chunk is 3 bytes; a terrain chunk a few hundred,
     * against 4,096 dense. {@link #ofRuns} reads it back.
     */
    public byte[] runs() {
        Store s = store;
        byte[] cached = s.runs;
        if (cached == null) {
            cached = encodeRuns(s);
            s.runs = cached;
        }
        return cached.clone();
    }

    /** {@link #runs()} without the defensive copy, for WorldStore; callers must not change the array. */
    byte[] runsView() {
        Store s = store;
        byte[] cached = s.runs;
        if (cached == null) {
            cached = encodeRuns(s);
            s.runs = cached;
        }
        return cached;
    }

    private static byte[] encodeRuns(Store s) {
        if (s.bits == 0) {
            return new byte[] {s.palette[0], (byte) (VOLUME & 0xff), (byte) (VOLUME >>> 8)};
        }
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream(256);
        int run = 0;
        int cur = s.ordinal(0);
        for (int i = 0; i <= VOLUME; i++) {
            int o = i < VOLUME ? s.ordinal(i) : -1;
            if (o == cur) {
                run++;
                continue;
            }
            out.write(cur);
            out.write(run & 0xff);
            out.write(run >>> 8);
            cur = o;
            run = 1;
        }
        return out.toByteArray();
    }

    /** Dense ordinals from {@link #runs()} output; refuses runs that don't cover exactly 4,096 cubes. */
    public static byte[] ofRuns(byte[] runs) {
        if (runs == null || runs.length % 3 != 0) {
            throw new IllegalArgumentException("runs must be whole (ordinal, lo, hi) triples");
        }
        byte[] dense = new byte[VOLUME];
        int at = 0;
        for (int k = 0; k < runs.length; k += 3) {
            int n = (runs[k + 1] & 0xff) | (runs[k + 2] & 0xff) << 8;
            if (n == 0 || at + n > VOLUME) {
                throw new IllegalArgumentException("run " + (k / 3) + " has length " + n + " at cube " + at);
            }
            Arrays.fill(dense, at, at + n, runs[k]);
            at += n;
        }
        if (at != VOLUME) {
            throw new IllegalArgumentException("runs cover " + at + " cubes, not " + VOLUME);
        }
        return dense;
    }

    static Chunk ofPayload(byte[] payload, long revision) {
        if (payload == null || payload.length != VOLUME) {
            throw new IllegalArgumentException("Chunk payload must be " + VOLUME + " bytes");
        }
        int kinds = TYPES.length;
        for (byte b : payload) {
            int ordinal = Byte.toUnsignedInt(b);
            if (ordinal >= kinds) {
                throw new IllegalArgumentException("Unknown block ordinal " + ordinal);
            }
        }
        return compact(payload, revision);
    }

    private static int index(int localX, int localY, int localZ) {
        if (localX < 0 || localX >= SIZE || localY < 0 || localY >= SIZE
                || localZ < 0 || localZ >= SIZE) {
            throw new IllegalArgumentException(
                    "Local coordinate out of chunk: (" + localX + "," + localY + "," + localZ + ")");
        }
        return localX + SIZE * (localY + SIZE * localZ);
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (!(o instanceof Chunk other)) {
            return false;
        }
        return revision == other.revision && Arrays.equals(dense(store), dense(other.store));
    }

    @Override
    public int hashCode() {
        return 31 * Arrays.hashCode(dense(store)) + Long.hashCode(revision);
    }
}
