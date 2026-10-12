// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox;

import java.util.List;

/** A JSON-RPC transport: {@code eth_call}s, sent as one batch. Swappable so tests need no network. */
@FunctionalInterface
public interface JsonRpc {
    /** Runs every call ({@code to}, {@code data}) at "latest" and returns each hex result, or null on a revert. */
    List<String> ethCallBatch(String to, List<String> data);
}
