// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.TextNode;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.TreeSet;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class TransferIndexerTest {

    static final String RDSONG = "0x286562588c32692e49befd2f7ec628a6cbef7162";
    static final String ZERO = "0x0000000000000000000000000000000000000000";
    private static final ObjectMapper JSON = new ObjectMapper();

    /** A simulated chain: RDSong deployed at {@code deploy}, Transfer events, a head, per-block hashes with a fork salt. */
    static class FakeChain implements JsonRpc {
        record Ev(long block, int logIndex, String from, String to, long id) {}
        final List<Ev> events = new ArrayList<>();
        long head, deploy;
        int maxRange = Integer.MAX_VALUE;           // the node refuses wider eth_getLogs ranges
        String salt = "a";
        final AtomicInteger getLogs = new AtomicInteger(), calls = new AtomicInteger();
        long lowestFromAsked = Long.MAX_VALUE;

        final Map<Long, Integer> perBlock = new HashMap<>();

        void transfer(long block, String from, String to, long id) {
            int idx = perBlock.merge(block, 1, Integer::sum) - 1;
            events.add(new Ev(block, idx, from, to, id));
            head = Math.max(head, block);
        }

        @Override public List<String> ethCallBatch(String to, List<String> data) { throw new UnsupportedOperationException(); }

        @Override
        public JsonNode call(String method, Object... params) {
            calls.incrementAndGet();
            switch (method) {
                case "eth_blockNumber": return TextNode.valueOf(TransferIndexer.hexOf(head));
                case "eth_getCode": {
                    long b = Long.decode(((String) params[1]));
                    return TextNode.valueOf(b >= deploy ? "0x6080" : "0x");
                }
                case "eth_getBlockByNumber": {
                    long b = Long.decode((String) params[0]);
                    return JSON.createObjectNode().put("hash", "0x" + salt + Long.toHexString(b));
                }
                case "eth_getLogs": {
                    getLogs.incrementAndGet();
                    JsonNode f = (JsonNode) params[0];
                    long from = Long.decode(f.get("fromBlock").asText()), to = Long.decode(f.get("toBlock").asText());
                    lowestFromAsked = Math.min(lowestFromAsked, from);
                    if (to - from + 1 > maxRange) throw new RpcRangeException("block range too large");
                    assertThat(f.get("address").asText()).isEqualTo(RDSONG);
                    ArrayNode out = JSON.createArrayNode();
                    for (Ev e : events) {
                        if (e.block < from || e.block > to) continue;
                        var l = out.addObject().put("blockNumber", TransferIndexer.hexOf(e.block)).put("logIndex", TransferIndexer.hexOf(e.logIndex));
                        l.putArray("topics").add(TransferIndexer.TRANSFER).add(topic(e.from)).add(topic(e.to)).add(String.format("0x%064x", e.id));
                    }
                    return out;
                }
                default: throw new IllegalStateException(method);
            }
        }

        static String topic(String addr) { return "0x" + "0".repeat(24) + addr.substring(2); }
    }

    static String wallet(int n) { return String.format("0x%040x", n + 1); }

    private static TransferIndexer indexer(FakeChain c, long deploy, int conf, int chunk, Path file) {
        return new TransferIndexer(c, RDSONG, 46630, deploy, conf, chunk, file, 5_000, () -> 0);
    }

    @Test
    void fiftyThousandTokensIndexFromLogsAndMatchGroundTruth(@TempDir Path dir) {
        FakeChain c = new FakeChain();
        c.deploy = 1_000;
        Random r = new Random(46630);
        Map<Long, String> truth = new HashMap<>();
        long block = 1_000;
        for (long id = 0; id < 50_000; id++) {                 // mints, ~25 per block
            if (id % 25 == 0) block++;
            String to = wallet(r.nextInt(5_000));
            c.transfer(block, ZERO, to, id);
            truth.put(id, to);
        }
        for (int i = 0; i < 20_000; i++) {                       // then 20k secondary transfers
            if (i % 10 == 0) block++;
            long id = r.nextInt(50_000);
            String to = wallet(r.nextInt(5_000));
            c.transfer(block, truth.get(id), to, id);
            truth.put(id, to);
        }
        for (int i = 0; i < 100; i++) {                          // and 100 burns
            long id = r.nextInt(50_000);
            if (truth.get(id) == null) continue;
            c.transfer(++block, truth.get(id), ZERO, id);
            truth.remove(id);
        }
        c.head = block + 20;                                      // everything is confirmed
        TransferIndexer ix = indexer(c, 0, 20, 2_000, dir.resolve("ix.json"));
        long t0 = System.nanoTime();
        ix.sync();
        long ms = (System.nanoTime() - t0) / 1_000_000;
        assertThat(ix.ready()).isTrue();
        assertThat(ix.size()).isEqualTo(truth.size());
        Map<String, TreeSet<Long>> byOwner = new HashMap<>();
        truth.forEach((id, w) -> byOwner.computeIfAbsent(w, k -> new TreeSet<>()).add(id));
        for (int n = 0; n < 5_000; n += 37) {
            String w = wallet(n);
            assertThat(ix.tokensOf(w)).containsExactlyElementsOf(byOwner.getOrDefault(w, new TreeSet<>()));
        }
        // ~5k blocks of logs at a 2k-block chunk is a handful of getLogs, vs 1,000 ownerOf batches for a 50k scan.
        assertThat(c.getLogs.get()).isLessThan(20);
        System.out.printf("indexed 50k tokens + 20k transfers + burns: %d ms, %d RPC calls (%d getLogs)%n", ms, c.calls.get(), c.getLogs.get());
    }

    @Test
    void onlyConfirmedBlocksAreIndexed() {
        FakeChain c = new FakeChain();
        c.transfer(10, ZERO, wallet(1), 0);
        c.transfer(30, wallet(1), wallet(2), 0);
        c.head = 40;
        TransferIndexer ix = indexer(c, 1, 20, 1000, null);
        ix.sync();                                                // safe = 20: the transfer at 30 is not confirmed yet
        assertThat(ix.tokensOf(wallet(1))).containsExactly(0L);
        c.head = 55;
        ix.sync();
        assertThat(ix.tokensOf(wallet(1))).isEmpty();
        assertThat(ix.tokensOf(wallet(2))).containsExactly(0L);
        assertThat(ix.indexedBlock()).isEqualTo(35);
    }

    @Test
    void aReorgDeeperThanTheConfirmationsRebuildsTheIndex() {
        FakeChain c = new FakeChain();
        c.transfer(10, ZERO, wallet(1), 0);
        c.head = 50;
        TransferIndexer ix = indexer(c, 1, 5, 1000, null);
        ix.sync();
        assertThat(ix.tokensOf(wallet(1))).containsExactly(0L);
        c.events.clear();                                          // the canonical chain changed under us
        c.perBlock.clear();
        c.transfer(10, ZERO, wallet(9), 0);
        c.salt = "b";
        c.head = 60;
        ix.sync();
        assertThat(ix.tokensOf(wallet(1))).isEmpty();
        assertThat(ix.tokensOf(wallet(9))).containsExactly(0L);
    }

    @Test
    void theIndexIsPersistedAndResumedIncrementally(@TempDir Path dir) {
        FakeChain c = new FakeChain();
        c.transfer(10, ZERO, wallet(1), 0);
        c.transfer(11, ZERO, wallet(2), 1);
        c.head = 100;
        Path file = dir.resolve("index.json");
        indexer(c, 1, 10, 1000, file).sync();
        c.transfer(120, wallet(2), wallet(3), 1);
        c.head = 140;
        c.lowestFromAsked = Long.MAX_VALUE;
        TransferIndexer resumed = indexer(c, 1, 10, 1000, file);
        assertThat(resumed.ready()).isTrue();                     // serves straight from disk
        assertThat(resumed.tokensOf(wallet(2))).containsExactly(1L);
        resumed.sync();
        assertThat(c.lowestFromAsked).isEqualTo(91);              // only the new blocks were read
        assertThat(resumed.tokensOf(wallet(3))).containsExactly(1L);
        // a file for another contract or chain is ignored
        TransferIndexer other = new TransferIndexer(c, RDSONG, 4663, 1, 10, 1000, file, 5_000, () -> 0);
        assertThat(other.ready()).isFalse();
    }

    @Test
    void tooWideRangesAreSplitUntilTheNodeAccepts() {
        FakeChain c = new FakeChain();
        c.maxRange = 300;
        for (int i = 0; i < 50; i++) c.transfer(10 + i * 100L, ZERO, wallet(i), i);
        c.head = 6000;
        TransferIndexer ix = indexer(c, 1, 0, 100_000, null);
        ix.sync();
        assertThat(ix.size()).isEqualTo(50);
        assertThat(ix.tokensOf(wallet(49))).containsExactly(49L);
    }

    @Test
    void aNodeThatRefusesEveryRangeFailsLoudlyInsteadOfGuessing() {
        FakeChain c = new FakeChain();
        c.maxRange = 1;
        c.transfer(10, ZERO, wallet(1), 0);
        c.head = 100;
        assertThatThrownBy(() -> indexer(c, 1, 0, 64, null).sync()).isInstanceOf(JsonRpc.RpcRangeException.class);
    }

    @Test
    void theDeployBlockIsFoundByBinarySearch() {
        FakeChain c = new FakeChain();
        c.deploy = 123_457;
        c.transfer(123_460, ZERO, wallet(1), 0);
        c.head = 2_000_000;
        TransferIndexer ix = indexer(c, 0, 0, 1_000_000, null);
        ix.sync();
        assertThat(c.lowestFromAsked).isEqualTo(123_457);
        assertThat(ix.tokensOf(wallet(1))).containsExactly(0L);
    }

    @Test
    void theReaderFallsBackToTheScanForSmallSupplyAndRefusesToSweepALargeOne() {
        FakeChain c = new FakeChain() {
            @Override public JsonNode call(String m, Object... p) { throw new IllegalStateException("logs unavailable"); }
        };
        JsonRpc small = new JsonRpc() {
            @Override public List<String> ethCallBatch(String to, List<String> data) {
                List<String> out = new ArrayList<>();
                for (String d : data) out.add(d.startsWith("0x18160ddd") ? String.format("0x%064x", 2)
                        : "0x" + "0".repeat(24) + wallet(1).substring(2));
                return out;
            }
            @Override public JsonNode call(String m, Object... p) { return c.call(m, p); }
        };
        RdSongReader reader = new RdSongReader(small, RDSONG, 50, 100, 1000, () -> 0)
                .withIndexer(indexer(c, 1, 0, 100, null), 10);
        assertThat(reader.tokensOf(wallet(1))).containsExactly(0L, 1L);         // index broken: 2 tokens ≤ 10 → scan
        assertThat(reader.holderSource()).isEqualTo("scan");
        RdSongReader big = new RdSongReader(small, RDSONG, 50, 100, 1000, () -> 0).withIndexer(indexer(c, 1, 0, 100, null), 1);
        assertThatThrownBy(() -> big.tokensOf(wallet(1))).isInstanceOf(RdSongReader.IndexWarmingException.class);
    }

    @Test
    void aNonArchiveNodeThatCantAnswerOldStateIndexesFromBlockZero() {
        FakeChain c = new FakeChain() {
            @Override public JsonNode call(String m, Object... p) {
                if (m.equals("eth_getCode")) throw new IllegalStateException("historical state is not available");
                return super.call(m, p);
            }
        };
        c.transfer(900_000, ZERO, wallet(1), 0);
        c.head = 1_000_000;
        TransferIndexer ix = indexer(c, 0, 0, 10_000_000, null);
        ix.sync();
        assertThat(c.lowestFromAsked).isZero();
        assertThat(ix.tokensOf(wallet(1))).containsExactly(0L);
    }
}
