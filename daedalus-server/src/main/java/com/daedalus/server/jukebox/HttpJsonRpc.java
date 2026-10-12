// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * {@link JsonRpc} over HTTP: read-only calls only, never a signed request. Takes one or more endpoints
 * ({@code rpc-url} is comma-separated) and fails over between them: a 429, a 5xx, a timeout or a refused connection
 * moves to the next endpoint after a jittered exponential backoff (honoring {@code Retry-After}), up to a bounded
 * number of attempts. A healthy endpoint stays current, so failover is sticky.
 */
public final class HttpJsonRpc implements JsonRpc {

    private static final ObjectMapper JSON = new ObjectMapper();
    private final List<URI> urls;
    private final AtomicInteger current = new AtomicInteger();
    private final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(4)).build();
    private final int attempts;
    private final long backoffMs;
    private final HttpStudioArranger.Sleeper sleeper;

    public HttpJsonRpc(String urls) {
        this(urls, 250, Thread::sleep);
    }

    public HttpJsonRpc(String urls, long backoffMs, HttpStudioArranger.Sleeper sleeper) {
        List<URI> list = new ArrayList<>();
        for (String u : urls.split(",")) {
            if (u.isBlank()) continue;
            URI uri = URI.create(u.trim());
            if (!"https".equals(uri.getScheme()) && !"http".equals(uri.getScheme())) throw new IllegalArgumentException("rpc-url must be http(s)");
            list.add(uri);
        }
        if (list.isEmpty()) throw new IllegalArgumentException("no rpc-url");
        this.urls = List.copyOf(list);
        this.attempts = 3 + 2 * this.urls.size();
        this.backoffMs = backoffMs;
        this.sleeper = sleeper;
    }

    @Override
    public List<String> ethCallBatch(String to, List<String> data) {
        if (data.isEmpty()) return List.of();
        ArrayNode batch = JSON.createArrayNode();
        for (int i = 0; i < data.size(); i++) {
            ObjectNode call = batch.addObject().put("jsonrpc", "2.0").put("id", i).put("method", "eth_call");
            ArrayNode params = call.putArray("params");
            params.addObject().put("to", to).put("data", data.get(i));
            params.add("latest");
        }
        JsonNode body = post(batch);
        if (!body.isArray()) throw new IllegalStateException("RPC did not answer the batch: " + abbreviate(body.toString()));
        String[] out = new String[data.size()];
        for (JsonNode r : body) {
            int id = r.path("id").asInt(-1);
            if (id < 0 || id >= out.length) continue;
            if (r.hasNonNull("result")) {
                out[id] = r.get("result").asText();
            } else if (!r.path("error").path("message").asText("").toLowerCase().contains("revert")) {
                // A rate limit or node error inside the batch is not "nobody owns it": fail, don't guess.
                throw new IllegalStateException("RPC error: " + abbreviate(r.path("error").toString()));
            }
        }
        return new ArrayList<>(Arrays.asList(out));
    }

    @Override
    public JsonNode call(String method, Object... params) {
        ObjectNode req = JSON.createObjectNode().put("jsonrpc", "2.0").put("id", 1).put("method", method);
        req.set("params", JSON.valueToTree(params));
        JsonNode body = post(req);
        if (body.hasNonNull("error")) {
            String msg = body.path("error").path("message").asText("").toLowerCase();
            if (msg.contains("range") || msg.contains("too many") || msg.contains("limit") || msg.contains("exceed")
                    || msg.contains("10000") || msg.contains("response size"))
                throw new RpcRangeException(abbreviate(body.path("error").toString()));
            throw new IllegalStateException("RPC error: " + abbreviate(body.path("error").toString()));
        }
        return body.path("result");
    }

    /** POSTs with failover + jittered backoff. Throws IllegalStateException once every attempt is spent. */
    private JsonNode post(JsonNode payload) {
        String bodyText;
        try {
            bodyText = JSON.writeValueAsString(payload);
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
        String last = "no attempt";
        for (int attempt = 0; attempt < attempts; attempt++) {
            URI url = urls.get(Math.floorMod(current.get(), urls.size()));
            long wait = 0;
            try {
                HttpRequest req = HttpRequest.newBuilder(url).timeout(Duration.ofSeconds(15))
                        .header("Content-Type", "application/json")
                        .POST(HttpRequest.BodyPublishers.ofString(bodyText)).build();
                HttpResponse<String> res = http.send(req, HttpResponse.BodyHandlers.ofString());
                int c = res.statusCode();
                if (c == 200) {
                    JsonNode body = JSON.readTree(res.body());
                    if (isRateLimited(body)) {
                        last = "rate limited in body";
                    } else {
                        return body;
                    }
                } else {
                    last = "HTTP " + c;
                    if (c != 429 && c < 500) throw new IllegalStateException("RPC answered " + last);
                    wait = res.headers().firstValue("Retry-After").map(HttpJsonRpc::seconds).orElse(0L);
                }
            } catch (IOException e) {
                last = e.getClass().getSimpleName();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new IllegalStateException("interrupted", e);
            }
            current.incrementAndGet();                         // fail over to the next endpoint
            long base = Math.min(4_000, backoffMs << Math.min(attempt, 4));
            long jittered = base / 2 + ThreadLocalRandom.current().nextLong(base + 1);
            try {
                sleeper.sleep(Math.min(10_000, Math.max(wait, jittered)));
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new IllegalStateException("interrupted", e);
            }
        }
        throw new IllegalStateException("RPC unavailable after " + attempts + " attempts (" + last + ")");
    }

    /** A JSON-RPC error that is a rate limit (some nodes answer 200 with code -32005 / "rate limit"). */
    private static boolean isRateLimited(JsonNode body) {
        JsonNode e = body.isArray() && !body.isEmpty() ? body.get(0).path("error") : body.path("error");
        String m = e.path("message").asText("").toLowerCase();
        return e.path("code").asInt() == -32005 || m.contains("rate limit") || m.contains("too many requests");
    }

    private static long seconds(String v) {
        try {
            return Math.max(0, Math.min(10, Long.parseLong(v.trim()))) * 1000;
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private static String abbreviate(String s) {
        return s.length() > 200 ? s.substring(0, 200) + "…" : s;
    }
}
