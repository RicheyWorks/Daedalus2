// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** {@link JsonRpc} over HTTP: read-only {@code eth_call}s only, never a signed request. */
public final class HttpJsonRpc implements JsonRpc {

    private static final ObjectMapper JSON = new ObjectMapper();
    private final URI url;
    private final HttpClient http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();

    public HttpJsonRpc(String url) {
        this.url = URI.create(url);
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
        try {
            HttpRequest req = HttpRequest.newBuilder(url).timeout(Duration.ofSeconds(20))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(JSON.writeValueAsString(batch))).build();
            HttpResponse<String> res = http.send(req, HttpResponse.BodyHandlers.ofString());
            for (int retry = 1; res.statusCode() == 429 && retry <= 3; retry++) {   // public RPCs rate-limit bursts
                Thread.sleep(400L * retry);
                res = http.send(req, HttpResponse.BodyHandlers.ofString());
            }
            if (res.statusCode() != 200) throw new IllegalStateException("RPC answered HTTP " + res.statusCode());
            JsonNode body = JSON.readTree(res.body());
            if (!body.isArray()) throw new IllegalStateException("RPC did not answer the batch: " + abbreviate(res.body()));
            String[] out = new String[data.size()];
            for (JsonNode r : body) {
                int id = r.path("id").asInt(-1);
                if (id < 0 || id >= out.length) continue;
                if (r.hasNonNull("result")) {
                    out[id] = r.get("result").asText();
                } else if (!r.path("error").path("message").asText("").toLowerCase().contains("revert")) {
                    // A rate limit or node error inside the batch is not "nobody owns it": fail, don't guess.
                    throw new IllegalStateException("RPC error: " + r.path("error"));
                }
            }
            return new ArrayList<>(Arrays.asList(out));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("interrupted", e);
        }
    }

    private static String abbreviate(String s) {
        return s.length() > 200 ? s.substring(0, 200) + "…" : s;
    }
}
