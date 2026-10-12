// SPDX-License-Identifier: MIT

package com.daedalus.server.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.ConstructorBinding;

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
 * @param indexer       look holders up from Transfer logs (incremental, persisted) instead of an ownerOf sweep
 * @param deployBlock   the RDSong deploy block; 0 = find it once by binary search on eth_getCode
 * @param confirmations index only blocks this deep (reorg safety)
 * @param logChunk      the widest eth_getLogs range asked for (halved automatically when a node refuses)
 * @param indexFile     where the index is persisted; empty = the temp dir, keyed by chain and contract
 * @param scanFallbackMax while the index warms up (or fails), sweep ownerOf only if supply is at most this
 */
@ConfigurationProperties("daedalus.jukebox")
public record JukeboxProperties(boolean enabled, long chainId, String rpcUrl, String contract, String seedSongsDir,
                                int scanBatch, int maxScan, int cacheSeconds, String studioUrl,
                                boolean indexer, long deployBlock, int confirmations, int logChunk, String indexFile,
                                int scanFallbackMax) {
    @ConstructorBinding
    public JukeboxProperties {
        chainId = chainId <= 0 ? 46_630L : chainId;
        rpcUrl = rpcUrl == null || rpcUrl.isBlank() ? "https://rpc.testnet.chain.robinhood.com" : rpcUrl.trim();
        contract = contract == null ? "" : contract.trim().toLowerCase();
        seedSongsDir = seedSongsDir == null ? "" : seedSongsDir.trim();
        scanBatch = scanBatch <= 0 ? 50 : Math.min(scanBatch, 200);
        maxScan = maxScan <= 0 ? 60_000 : maxScan;
        cacheSeconds = cacheSeconds <= 0 ? 30 : cacheSeconds;
        studioUrl = studioUrl == null ? "" : studioUrl.trim();
        deployBlock = Math.max(0, deployBlock);
        confirmations = confirmations <= 0 ? 20 : Math.min(confirmations, 10_000);
        logChunk = logChunk <= 0 ? 5_000_000 : Math.min(logChunk, 50_000_000);
        indexFile = indexFile == null ? "" : indexFile.trim();
        scanFallbackMax = scanFallbackMax <= 0 ? 2_000 : scanFallbackMax;
    }

    /** The original shape (no indexer): tests and callers that only need the scan. */
    public JukeboxProperties(boolean enabled, long chainId, String rpcUrl, String contract, String seedSongsDir,
                             int scanBatch, int maxScan, int cacheSeconds, String studioUrl) {
        this(enabled, chainId, rpcUrl, contract, seedSongsDir, scanBatch, maxScan, cacheSeconds, studioUrl,
                false, 0, 0, 0, "", 0);
    }

    /** True when there is a contract to read. */
    public boolean hasContract() {
        return contract.matches("0x[0-9a-f]{40}");
    }
}
