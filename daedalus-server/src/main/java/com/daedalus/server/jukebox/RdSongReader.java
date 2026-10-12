// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox;

import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.LongSupplier;

/**
 * Reads RDSong (Reaction / Diffusion / Song, an ERC721A) through read-only {@code eth_call}s.
 * ERC721A has no on-chain enumeration, so "which tokens does this wallet hold" is one batched
 * {@code ownerOf} sweep over {@code [0, totalSupply)}, cached for a few seconds so a crowd at the
 * jukebox costs the RPC one sweep, not one per visitor. A revealed token's HTML never changes after
 * mint (engine pinned per token), so it is cached for good, bounded by count.
 */
public final class RdSongReader {

    static final String TOTAL_SUPPLY = "0x18160ddd";
    static final String OWNER_OF = "0x6352211e";
    static final String IS_REVEALED = "0x5055fbc3";
    static final String TOKEN_HTML = "0xb79bebaf";
    static final String TOKEN_HASH = "0xa3864397";
    static final int HTML_CACHE = 64;

    private final JsonRpc rpc;
    private final String contract;
    private final int batch;
    private final int maxScan;
    private final long ttlMs;
    private final LongSupplier clock;

    private volatile Snapshot snapshot;
    private final Map<Long, byte[]> html = Collections.synchronizedMap(new LinkedHashMap<>(16, 0.75f, true) {
        @Override protected boolean removeEldestEntry(Map.Entry<Long, byte[]> e) { return size() > HTML_CACHE; }
    });

    private final Map<Long, String> hashes = Collections.synchronizedMap(new LinkedHashMap<>(16, 0.75f, true) {
        @Override protected boolean removeEldestEntry(Map.Entry<Long, String> e) { return size() > 4096; }
    });

    /** Who owned what at one moment: owners.get(id) is the lowercase owner address, or null. */
    record Snapshot(long at, List<String> owners) {}

    public RdSongReader(JsonRpc rpc, String contract, int batch, int maxScan, long ttlMs, LongSupplier clock) {
        this.rpc = rpc;
        this.contract = contract;
        this.batch = batch;
        this.maxScan = maxScan;
        this.ttlMs = ttlMs;
        this.clock = clock;
    }

    public long totalSupply() {
        String r = rpc.ethCallBatch(contract, List.of(TOTAL_SUPPLY)).get(0);
        if (r == null) throw new IllegalStateException("totalSupply reverted");
        return word(r, 0).longValueExact();
    }

    /** The token ids {@code address} holds now (ascending). */
    public List<Long> tokensOf(String address) {
        String who = address.toLowerCase();
        List<String> owners = owners().owners();
        List<Long> out = new ArrayList<>();
        for (int i = 0; i < owners.size(); i++) if (who.equals(owners.get(i))) out.add((long) i);
        return out;
    }

    public boolean isRevealed(long id) {
        String r = rpc.ethCallBatch(contract, List.of(IS_REVEALED + uint(id))).get(0);
        return r != null && word(r, 0).signum() != 0;
    }

    /** The token's own on-chain HTML (song, engine and coat), or null before reveal or for a missing id. */
    public byte[] tokenHtml(long id) {
        byte[] cached = html.get(id);
        if (cached != null) return cached;
        List<String> r = rpc.ethCallBatch(contract, List.of(IS_REVEALED + uint(id), TOKEN_HTML + uint(id)));
        if (r.get(0) == null || word(r.get(0), 0).signum() == 0 || r.get(1) == null) return null;
        byte[] bytes = decodeBytes(r.get(1));
        html.put(id, bytes);     // revealed + engine pinned per token: immutable from here on
        return bytes;
    }

    /** The token's 32-byte hash (keys its Turing coat), or null before reveal. Immutable once revealed: cached. */
    public String tokenHash(long id) {
        String cached = hashes.get(id);
        if (cached != null) return cached;
        List<String> r = rpc.ethCallBatch(contract, List.of(IS_REVEALED + uint(id), TOKEN_HASH + uint(id)));
        if (r.get(0) == null || word(r.get(0), 0).signum() == 0 || r.get(1) == null) return null;
        String hash = "0x" + strip(r.get(1)).substring(0, 64).toLowerCase();
        hashes.put(id, hash);
        return hash;
    }

    synchronized Snapshot owners() {
        Snapshot s = snapshot;
        long now = clock.getAsLong();
        if (s != null && now - s.at() < ttlMs) return s;
        long total = Math.min(totalSupply(), maxScan);
        List<String> owners = new ArrayList<>((int) total);
        for (long lo = 0; lo < total; lo += batch) {
            List<String> calls = new ArrayList<>();
            for (long id = lo; id < Math.min(total, lo + batch); id++) calls.add(OWNER_OF + uint(id));
            for (String r : rpc.ethCallBatch(contract, calls)) owners.add(r == null ? null : address(r));
        }
        snapshot = new Snapshot(now, List.copyOf(owners.stream().map(o -> o == null ? "" : o).toList()));
        return snapshot;
    }

    // ---- ABI helpers (only the shapes RDSong's read functions use) ----

    static String uint(long v) {
        if (v < 0) throw new IllegalArgumentException("negative token id");
        String h = Long.toHexString(v);
        return "0".repeat(64 - h.length()) + h;
    }

    static BigInteger word(String hex, int index) {
        String h = strip(hex);
        int from = index * 64;
        if (h.length() < from + 64) throw new IllegalStateException("short ABI result");
        return new BigInteger(h.substring(from, from + 64), 16);
    }

    static String address(String hex) {
        return "0x" + strip(hex).substring(24, 64).toLowerCase();
    }

    static byte[] decodeBytes(String hex) {
        String h = strip(hex);
        int offset = word(h, 0).intValueExact() * 2;
        int len = new BigInteger(h.substring(offset, offset + 64), 16).intValueExact();
        int start = offset + 64;
        if (h.length() < start + len * 2) throw new IllegalStateException("short ABI bytes");
        byte[] out = new byte[len];
        for (int i = 0; i < len; i++) out[i] = (byte) Integer.parseInt(h.substring(start + 2 * i, start + 2 * i + 2), 16);
        return out;
    }

    static String text(byte[] b) {
        return new String(b, StandardCharsets.UTF_8);
    }

    private static String strip(String hex) {
        return hex.startsWith("0x") || hex.startsWith("0X") ? hex.substring(2) : hex;
    }
}
