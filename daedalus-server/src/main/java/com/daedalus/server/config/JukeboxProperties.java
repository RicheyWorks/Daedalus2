// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * The Reaction / Diffusion / Song jukebox (rd-jukebox). Read-only: the realm never signs or sends a
 * transaction for it; it asks a public RPC which RDSong tokens a signed-in wallet holds and serves the
 * token's own on-chain HTML (the song and its Turing coat) back to the browser.
 *
 * @param enabled       off unless {@code DAEDALUS_JUKEBOX_ENABLED=true}
 * @param chainId       Robinhood Chain: 46630 testnet (default), 4663 mainnet
 * @param rpcUrl        a read-only JSON-RPC endpoint for that chain
 * @param contract      the RDSong address on that chain (mainnet is not deployed yet: leave it empty)
 * @param seedSongsDir  a directory of guest seed songs ({@code name.mp3} + optional {@code name.webp}); empty = none
 * @param scanBatch     ownerOf calls per JSON-RPC batch when scanning holders
 * @param maxScan       never scan more than this many token ids (ERC721A has no on-chain enumeration)
 * @param cacheSeconds  how long a holder scan stays fresh
 * @param studioUrl     Prometheus's rd-studio arrangement service; empty = genre/studio requests are stubbed
 */
@ConfigurationProperties("daedalus.jukebox")
public record JukeboxProperties(boolean enabled, long chainId, String rpcUrl, String contract, String seedSongsDir,
                                int scanBatch, int maxScan, int cacheSeconds, String studioUrl) {
    public JukeboxProperties {
        chainId = chainId <= 0 ? 46_630L : chainId;
        rpcUrl = rpcUrl == null || rpcUrl.isBlank() ? "https://rpc.testnet.chain.robinhood.com" : rpcUrl.trim();
        contract = contract == null ? "" : contract.trim().toLowerCase();
        seedSongsDir = seedSongsDir == null ? "" : seedSongsDir.trim();
        scanBatch = scanBatch <= 0 ? 50 : Math.min(scanBatch, 200);
        maxScan = maxScan <= 0 ? 60_000 : maxScan;
        cacheSeconds = cacheSeconds <= 0 ? 30 : cacheSeconds;
        studioUrl = studioUrl == null ? "" : studioUrl.trim();
    }

    /** True when there is a contract to read. */
    public boolean hasContract() {
        return contract.matches("0x[0-9a-f]{40}");
    }
}
