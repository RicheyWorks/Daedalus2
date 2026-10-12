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
}
