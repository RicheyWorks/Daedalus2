package com.daedalus.world.audio;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.TreeMap;

/**
 * Client for the jukebox service (/api/v1/jukebox, owned by art-master-flex). Retries transient failures
 * and opens a simple breaker after repeated failures so a dead service never stalls the game loop.
 */
public final class JukeboxClient {
    /** Raised when the call fails or the breaker is open. */
    public static final class JukeboxException extends IOException {
        private static final long serialVersionUID = 1L;
        private final int status;

        /** Creates an exception. */
        public JukeboxException(String msg, int status) {
            super(msg);
            this.status = status;
        }

        /** HTTP status, or -1 for network/breaker. */
        public int status() {
            return status;
        }
    }

    private final String base;
    private final JukeboxTransport transport;
    private final int retries;
    private final int breakerThreshold;
    private int consecutiveFailures;

    /** Creates a client; base like http://host:8080 (path is appended). */
    public JukeboxClient(String base, JukeboxTransport transport, int retries, int breakerThreshold) {
        if (base == null || transport == null || retries < 0 || breakerThreshold < 1) {
            throw new IllegalArgumentException("bad client config");
        }
        this.base = base.endsWith("/") ? base.substring(0, base.length() - 1) : base;
        this.transport = transport;
        this.retries = retries;
        this.breakerThreshold = breakerThreshold;
    }

    /** Whether the breaker is open (call {@link #reset()} to close it). */
    public boolean breakerOpen() {
        return consecutiveFailures >= breakerThreshold;
    }

    /** Closes the breaker. */
    public void reset() {
        consecutiveFailures = 0;
    }

    /** GET /config as JSON text. */
    public String config() throws IOException {
        return text("/config", Map.of());
    }

    /** GET /seeds as JSON text. */
    public String seeds() throws IOException {
        return text("/seeds", Map.of());
    }

    /** GET /arrangement?source=... as JSON text. */
    public String arrangement(String source) throws IOException {
        return text("/arrangement", Map.of("source", source));
    }

    /** GET /tokens/{id}/hash as JSON text. */
    public String tokenHash(long id) throws IOException {
        return text("/tokens/" + id + "/hash", Map.of());
    }

    /** GET /studio/note with query params as JSON text. */
    public String studioNote(Map<String, String> params) throws IOException {
        return text("/studio/note", params);
    }

    /** GET /seeds/{file} as raw bytes (audio). */
    public byte[] seedFile(String file) throws IOException {
        return bytes("/seeds/" + enc(file), Map.of());
    }

    /** Builds the absolute URL; query keys are sorted so URLs are stable (cacheable). */
    public String url(String path, Map<String, String> query) {
        StringBuilder sb = new StringBuilder(base).append("/api/v1/jukebox").append(path);
        char sep = '?';
        for (Map.Entry<String, String> e : new TreeMap<>(query).entrySet()) {
            sb.append(sep).append(enc(e.getKey())).append('=').append(enc(e.getValue()));
            sep = '&';
        }
        return sb.toString();
    }

    private String text(String path, Map<String, String> q) throws IOException {
        return new String(bytes(path, q), StandardCharsets.UTF_8);
    }

    private byte[] bytes(String path, Map<String, String> q) throws IOException {
        if (breakerOpen()) {
            throw new JukeboxException("jukebox breaker open", -1);
        }
        String u = url(path, q);
        JukeboxException last = null;
        for (int attempt = 0; attempt <= retries; attempt++) {
            try {
                JukeboxTransport.Response r = transport.get(u);
                if (r.status() >= 200 && r.status() < 300) {
                    consecutiveFailures = 0;
                    return r.body();
                }
                last = new JukeboxException("jukebox " + path + " -> " + r.status(), r.status());
                if (r.status() < 500 && r.status() != 429) {
                    break;
                }
            } catch (JukeboxException e) {
                last = e;
            } catch (IOException e) {
                last = new JukeboxException("jukebox " + path + " network: " + e.getMessage(), -1);
            }
        }
        consecutiveFailures++;
        throw last;
    }

    private static String enc(String s) {
        return URLEncoder.encode(s, StandardCharsets.UTF_8).replace("+", "%20");
    }
}
