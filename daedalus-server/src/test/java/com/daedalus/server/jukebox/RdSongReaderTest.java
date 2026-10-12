// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.concurrent.atomic.AtomicLong;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class RdSongReaderTest {

    static final String A = "0x" + "a".repeat(40), B = "0x" + "b".repeat(40);

    @Test
    void findsEveryTokenAWalletHoldsAcrossBatches() {
        FakeRdSong chain = new FakeRdSong(List.of(A, B, A, A, B, A, B), 7);
        RdSongReader r = new RdSongReader(chain, "0xc", 3, 1000, 30_000, () -> 0);
        assertThat(r.tokensOf(A.toUpperCase().replace("0X", "0x"))).containsExactly(0L, 2L, 3L, 5L);
        assertThat(r.tokensOf(B)).containsExactly(1L, 4L, 6L);
        assertThat(r.tokensOf("0x" + "c".repeat(40))).isEmpty();
        assertThat(chain.batches).isEqualTo(1 + 3);       // totalSupply + ceil(7/3) ownerOf batches, once
    }

    @Test
    void aCrowdAtTheJukeboxCostsOneSweepPerCacheWindow() {
        FakeRdSong chain = new FakeRdSong(List.of(A, B), 2);
        AtomicLong now = new AtomicLong();
        RdSongReader r = new RdSongReader(chain, "0xc", 100, 1000, 30_000, now::get);
        for (int i = 0; i < 50; i++) r.tokensOf(A);
        assertThat(chain.batches).isEqualTo(2);
        now.addAndGet(30_001);
        r.tokensOf(A);
        assertThat(chain.batches).isEqualTo(4);
    }

    @Test
    void theScanNeverExceedsMaxScan() {
        FakeRdSong chain = new FakeRdSong(List.of(A, A, A, A, A), 5);
        RdSongReader r = new RdSongReader(chain, "0xc", 100, 2, 1, () -> 0);
        assertThat(r.tokensOf(A)).containsExactly(0L, 1L);
    }

    @Test
    void tokenHtmlIsDecodedOnlyAfterRevealAndCached() {
        FakeRdSong chain = new FakeRdSong(List.of(A, A, A), 2);
        RdSongReader r = new RdSongReader(chain, "0xc", 100, 1000, 1, () -> 0);
        assertThat(RdSongReader.text(r.tokenHtml(1))).isEqualTo("<html>token 1 ♪</html>");
        int calls = chain.calls;
        r.tokenHtml(1);
        assertThat(chain.calls).isEqualTo(calls);                    // immutable once revealed: cached
        assertThat(r.tokenHtml(2)).isNull();                         // minted, not revealed yet
        assertThat(r.tokenHtml(9)).isNull();                         // never minted
        assertThat(r.isRevealed(0)).isTrue();
    }

    @Test
    void abiHelpers() {
        assertThat(RdSongReader.uint(255)).hasSize(64).endsWith("ff");
        assertThat(RdSongReader.address("0x000000000000000000000000CB632E00227D4C717E468190DF1076C35528E447"))
                .isEqualTo("0xcb632e00227d4c717e468190df1076c35528e447");
        assertThat(RdSongReader.text(RdSongReader.decodeBytes(FakeRdSong.bytes("")))).isEmpty();
        assertThatThrownBy(() -> RdSongReader.uint(-1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> RdSongReader.word("0x12", 0)).isInstanceOf(IllegalStateException.class);
    }
}
