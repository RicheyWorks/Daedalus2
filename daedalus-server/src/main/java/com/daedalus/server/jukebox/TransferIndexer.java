// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.LongSupplier;

/**
 * Who holds which RDSong token, from the contract's ERC-721 {@code Transfer} logs instead of an {@code ownerOf} per token.
 * <ul>
 *   <li><b>Incremental:</b> starts at the deploy block (configured, or found by binary search on {@code eth_getCode}) and
 *       only ever reads new blocks, in {@code eth_getLogs} chunks that halve when the node says a range is too wide.</li>
 *   <li><b>Reorg-safe:</b> only blocks at least {@code confirmations} deep are indexed. The hash of the last indexed block
 *       is kept; if the chain later disagrees (a deeper reorg), the index is rebuilt from the deploy block.</li>
 *   <li><b>Persisted:</b> written atomically to {@code file} (if set) and reloaded on start when chain and contract match.</li>
 *   <li><b>Never blocks a request:</b> syncs run on one background thread; readers see the last complete state.
 *       {@link #ready()} is false until the first full sync, and callers fall back to the {@code ownerOf} scan meanwhile.</li>
 * </ul>
 */
public final class TransferIndexer {

    private static final Logger log = LoggerFactory.getLogger(TransferIndexer.class);
    static final String TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final int MIN_CHUNK = 8;

    private final JsonRpc rpc;
    private final String contract;
    private final long chainId;
    private final int confirmations;
    private final int maxChunk;
    private final Path file;
    private final LongSupplier clock;
    private final long staleMs;
    private final ExecutorService worker = Executors.newSingleThreadExecutor(r -> {
        Thread t = new Thread(r, "rd-jukebox-indexer");
        t.setDaemon(true);
        return t;
    });
    private final AtomicBoolean syncing = new AtomicBoolean();

    // State, guarded by this. Owners by token id; the reverse map makes tokensOf O(holding).
    private long deployBlock;
    private long block = -1;            // last indexed (confirmed) block; -1 = nothing yet
    private String blockHash = "";
    private final Map<Long, String> owners = new HashMap<>();
    private final Map<String, TreeSet<Long>> byOwner = new HashMap<>();
    private volatile boolean ready;
    private volatile long syncedAt;
    private volatile String lastError = "";
    private int chunk;

    public TransferIndexer(JsonRpc rpc, String contract, long chainId, long deployBlock, int confirmations, int maxChunk,
                           Path file, long staleMs, LongSupplier clock) {
        this.rpc = rpc;
        this.contract = contract.toLowerCase();
        this.chainId = chainId;
        this.deployBlock = Math.max(0, deployBlock);
        this.confirmations = Math.max(0, confirmations);
        this.maxChunk = Math.max(MIN_CHUNK, maxChunk);
        this.chunk = this.maxChunk;
        this.file = file;
        this.staleMs = staleMs;
        this.clock = clock;
        load();
    }

    public boolean ready() { return ready; }

    public synchronized long indexedBlock() { return block; }

    public synchronized int size() { return owners.size(); }

    public String lastError() { return lastError; }

    /** Token ids held by {@code address}, ascending, as of the last confirmed block. Kicks a background sync if stale. */
    public List<Long> tokensOf(String address) {
        if (clock.getAsLong() - syncedAt > staleMs) syncAsync();
        synchronized (this) {
            TreeSet<Long> s = byOwner.get(address.toLowerCase());
            return s == null ? List.of() : List.copyOf(s);
        }
    }

    /** Starts a sync on the indexer thread unless one is running. */
    public void syncAsync() {
        if (!syncing.compareAndSet(false, true)) return;
        worker.execute(() -> {
            try {
                sync();
            } catch (RuntimeException e) {
                lastError = String.valueOf(e.getMessage());
                log.warn("rd-jukebox indexer sync failed: {}", e.getMessage());
            } finally {
                syncing.set(false);
            }
        });
    }

    /** Brings the index up to {@code head - confirmations}. Runs on the caller's thread (tests; the worker otherwise). */
    public void sync() {
        long head = hex(rpc.call("eth_blockNumber"));
        long safe = head - confirmations;
        synchronized (this) {
            if (block >= 0 && !blockHash.isEmpty() && block <= safe) {
                String now = hashOf(block);
                if (!blockHash.equals(now)) {
                    log.warn("rd-jukebox indexer: block {} changed hash ({} -> {}): reorg deeper than {} confirmations, rebuilding",
                            block, blockHash, now, confirmations);
                    reset();
                }
            }
            if (block < 0 && deployBlock == 0) deployBlock = findDeployBlock(safe);
        }
        long from;
        synchronized (this) { from = block < 0 ? deployBlock : block + 1; }
        int chunks = 0;
        while (from <= safe) {
            long to = Math.min(safe, from + chunk - 1);
            JsonNode logs;
            try {
                ObjectNode filter = JSON.createObjectNode().put("address", contract).put("fromBlock", hexOf(from)).put("toBlock", hexOf(to));
                filter.putArray("topics").add(TRANSFER);
                logs = rpc.call("eth_getLogs", filter);
            } catch (JsonRpc.RpcRangeException e) {
                if (chunk <= MIN_CHUNK) throw e;
                chunk = Math.max(MIN_CHUNK, chunk / 2);
                continue;
            }
            synchronized (this) {
                apply(logs);
                block = to;
                blockHash = "";
            }
            from = to + 1;
            if (chunk < maxChunk && logs.size() < 1000) chunk = Math.min(maxChunk, chunk * 2);
            if (++chunks % 50 == 0) save();
        }
        synchronized (this) {
            if (block >= 0 && blockHash.isEmpty()) blockHash = hashOf(block);
        }
        ready = true;
        syncedAt = clock.getAsLong();
        lastError = "";
        save();
    }

    /** Applies Transfer logs in chain order (the node returns them ordered by block, then log index). */
    private void apply(JsonNode logs) {
        List<JsonNode> list = new ArrayList<>();
        logs.forEach(list::add);
        list.sort((a, b) -> {
            int c = Long.compare(hex(a.path("blockNumber")), hex(b.path("blockNumber")));
            return c != 0 ? c : Long.compare(hex(a.path("logIndex")), hex(b.path("logIndex")));
        });
        for (JsonNode l : list) {
            if (l.path("removed").asBoolean(false)) continue;
            JsonNode t = l.path("topics");
            if (t.size() != 4 || !TRANSFER.equalsIgnoreCase(t.get(0).asText())) continue;   // ERC-721 Transfer only
            String to = "0x" + t.get(2).asText().substring(26).toLowerCase();
            long id = new java.math.BigInteger(t.get(3).asText().substring(2), 16).longValueExact();
            String prev = owners.remove(id);
            if (prev != null) {
                TreeSet<Long> s = byOwner.get(prev);
                if (s != null && s.remove(id) && s.isEmpty()) byOwner.remove(prev);
            }
            if (!to.equals("0x0000000000000000000000000000000000000000")) {
                owners.put(id, to);
                byOwner.computeIfAbsent(to, k -> new TreeSet<>()).add(id);
            }
        }
    }

    private void reset() {
        owners.clear();
        byOwner.clear();
        block = -1;
        blockHash = "";
        ready = false;
    }

    /**
     * The first block where the contract has code (binary search; ~log2(head) calls, once). Non-archive nodes can't
     * answer {@code eth_getCode} for old state ("missing trie node"); then the index starts at block 0, which costs only
     * a few wide {@code eth_getLogs} ranges because logs, unlike state, are kept.
     */
    private long findDeployBlock(long head) {
        try {
            return searchDeployBlock(head);
        } catch (RuntimeException e) {
            log.info("rd-jukebox indexer: can't binary-search the deploy block ({}); indexing logs from block 0", e.getMessage());
            return 0;
        }
    }

    private long searchDeployBlock(long head) {
        long lo = 0, hi = head;
        if ("0x".equals(rpc.call("eth_getCode", contract, hexOf(hi)).asText("0x"))) return hi + 1;
        while (lo < hi) {
            long mid = lo + (hi - lo) / 2;
            if ("0x".equals(rpc.call("eth_getCode", contract, hexOf(mid)).asText("0x"))) lo = mid + 1; else hi = mid;
        }
        log.info("rd-jukebox indexer: {} deployed at block {}", contract, lo);
        return lo;
    }

    private String hashOf(long n) {
        return rpc.call("eth_getBlockByNumber", hexOf(n), false).path("hash").asText("");
    }

    // ---------------------------------------------------------------- persistence

    private synchronized void save() {
        if (file == null) return;
        ObjectNode root = JSON.createObjectNode().put("version", 1).put("chainId", chainId).put("contract", contract)
                .put("deployBlock", deployBlock).put("block", block).put("blockHash", blockHash);
        ArrayNode o = root.putArray("owners");
        owners.forEach((id, who) -> o.addArray().add(id).add(who));
        try {
            Files.createDirectories(file.toAbsolutePath().getParent());
            Path tmp = file.resolveSibling(file.getFileName() + ".tmp");
            JSON.writeValue(tmp.toFile(), root);
            Files.move(tmp, file, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException e) {
            log.warn("rd-jukebox indexer: could not persist {}: {}", file, e.getMessage());
        }
    }

    private synchronized void load() {
        if (file == null || !Files.isRegularFile(file)) return;
        try {
            JsonNode root = JSON.readTree(file.toFile());
            if (root.path("version").asInt() != 1 || root.path("chainId").asLong() != chainId
                    || !contract.equals(root.path("contract").asText())) return;
            deployBlock = root.path("deployBlock").asLong(deployBlock);
            block = root.path("block").asLong(-1);
            blockHash = root.path("blockHash").asText("");
            for (JsonNode p : root.path("owners")) {
                long id = p.get(0).asLong();
                String who = p.get(1).asText();
                if (!who.matches("0x[0-9a-f]{40}")) continue;
                owners.put(id, who);
                byOwner.computeIfAbsent(who, k -> new TreeSet<>()).add(id);
            }
            ready = block >= 0;
            syncedAt = 0;          // stale on purpose: the first read re-checks the tip (and the stored block hash)
            log.info("rd-jukebox indexer: resumed at block {} with {} tokens", block, owners.size());
        } catch (IOException | RuntimeException e) {
            log.warn("rd-jukebox indexer: ignoring unreadable {}: {}", file, e.getMessage());
            reset();
        }
    }

    // ---------------------------------------------------------------- hex

    static long hex(JsonNode n) {
        String s = n.asText("");
        if (!s.startsWith("0x")) throw new IllegalStateException("not a hex quantity: " + s);
        return Long.parseLong(s.substring(2), 16);
    }

    static String hexOf(long n) {
        return "0x" + Long.toHexString(n);
    }
}
