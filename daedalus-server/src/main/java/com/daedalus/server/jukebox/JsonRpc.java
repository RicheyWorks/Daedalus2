// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox;

import com.fasterxml.jackson.databind.JsonNode;

import java.util.List;

/** A JSON-RPC transport: read-only calls only. Swappable so tests need no network. */
@FunctionalInterface
public interface JsonRpc {
    /** Runs every call ({@code to}, {@code data}) at "latest" and returns each hex result, or null on a revert. */
    List<String> ethCallBatch(String to, List<String> data);

    /**
     * One read-only call ({@code eth_blockNumber}, {@code eth_getLogs}, {@code eth_getCode}, {@code eth_getBlockByNumber})
     * returning its {@code result}. Throws on an RPC error; {@link RpcRangeException} when a log range is too wide.
     */
    default JsonNode call(String method, Object... params) {
        throw new UnsupportedOperationException(method + " is not supported by this transport");
    }

    /** The node refused an {@code eth_getLogs} range as too large / too many results: the caller should split it. */
    final class RpcRangeException extends IllegalStateException {
        public RpcRangeException(String message) { super(message); }
    }
}
