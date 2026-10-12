// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox;

import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** Against the real Robinhood Chain testnet RDSong. Off by default (network); run with RD_JUKEBOX_LIVE=1. */
@EnabledIfEnvironmentVariable(named = "RD_JUKEBOX_LIVE", matches = "1")
class RdSongReaderLiveTest {

    static final String RDSONG = "0x286562588c32692e49befd2f7ec628a6cbef7162";

    @Test
    void readsTheTestnetCollection() {
        RdSongReader r = new RdSongReader(new HttpJsonRpc("https://rpc.testnet.chain.robinhood.com"), RDSONG, 50, 60_000,
                30_000, System::currentTimeMillis);
        long total = r.totalSupply();
        assertThat(total).isPositive();
        String owner5 = r.owners().owners().get(5);
        List<Long> held = r.tokensOf(owner5);
        System.out.println("totalSupply=" + total + " owner(5)=" + owner5 + " holds " + held.size() + " tokens");
        assertThat(held).contains(5L);
        byte[] html = r.tokenHtml(5);
        assertThat(RdSongReader.text(html)).startsWith("<!DOCTYPE html>");
        // rd-coat's DAEDALUS.md regex for tokenData.hash, checked against the real HTML: same value as tokenHash(id).
        Matcher m = Pattern.compile("tokenData\\s*=\\s*\\{[^}]*?hash\\s*:\\s*[\"'](0x[0-9a-fA-F]{64})").matcher(RdSongReader.text(html));
        assertThat(m.find()).isTrue();
        assertThat(m.group(1).toLowerCase()).isEqualTo(r.tokenHash(5));
    }

    /** The Transfer-log index, built from the deploy block (found by binary search), agrees with the ownerOf sweep. */
    @Test
    void theTransferIndexMatchesTheScan() {
        HttpJsonRpc rpc = new HttpJsonRpc("https://rpc.testnet.chain.robinhood.com");
        RdSongReader scan = new RdSongReader(rpc, RDSONG, 50, 60_000, 30_000, System::currentTimeMillis);
        TransferIndexer ix = new TransferIndexer(rpc, RDSONG, 46630, Long.getLong("rd.deployBlock", 0), 20, 5_000_000, null,
                5_000, System::currentTimeMillis);
        long t0 = System.nanoTime();
        ix.sync();
        long ixMs = (System.nanoTime() - t0) / 1_000_000;
        t0 = System.nanoTime();
        List<String> owners = scan.owners().owners();
        long scanMs = (System.nanoTime() - t0) / 1_000_000;
        java.util.Set<String> holders = new java.util.TreeSet<>(owners);
        holders.remove("");
        for (String h : holders) assertThat(ix.tokensOf(h)).as(h).isEqualTo(scan.tokensOf(h));
        System.out.printf("index: %d tokens to block %d in %d ms; scan of %d tokens: %d ms; %d holders agree%n",
                ix.size(), ix.indexedBlock(), ixMs, owners.size(), scanMs, holders.size());
    }
}
