// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;

/** An in-memory RDSong behind {@link JsonRpc}: owners by id, a reveal line and per-token HTML. */
final class FakeRdSong implements JsonRpc {
    final List<String> owners;
    final long revealedBelow;
    int calls;
    int batches;

    FakeRdSong(List<String> owners, long revealedBelow) {
        this.owners = owners;
        this.revealedBelow = revealedBelow;
    }

    static String word(long v) { return RdSongReader.uint(v); }

    static String bytes(String s) {
        byte[] b = s.getBytes(StandardCharsets.UTF_8);
        String hex = HexFormat.of().formatHex(b);
        int pad = (64 - hex.length() % 64) % 64;
        return "0x" + word(32) + word(b.length) + hex + "0".repeat(pad);
    }

    @Override
    public List<String> ethCallBatch(String to, List<String> data) {
        batches++;
        List<String> out = new ArrayList<>();
        for (String d : data) {
            calls++;
            String sel = d.substring(0, 10);
            long id = d.length() > 10 ? Long.parseLong(d.substring(10), 16) : -1;
            out.add(switch (sel) {
                case RdSongReader.TOTAL_SUPPLY -> "0x" + word(owners.size());
                case RdSongReader.OWNER_OF -> id < owners.size() ? "0x" + "0".repeat(24) + owners.get((int) id).substring(2) : null;
                case RdSongReader.IS_REVEALED -> "0x" + word(id < revealedBelow && id < owners.size() ? 1 : 0);
                case RdSongReader.TOKEN_HTML -> id < owners.size() ? bytes("<html>token " + id + " ♪</html>") : null;
                default -> null;
            });
        }
        return out;
    }

    static final Map<String, String> NONE = Map.of();
}
