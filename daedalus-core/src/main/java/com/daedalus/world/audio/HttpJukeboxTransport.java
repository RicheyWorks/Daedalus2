package com.daedalus.world.audio;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * JDK HttpClient transport with a hard per-request deadline. The JDK request timeout only covers the wait for
 * response headers, so the whole exchange (headers and body) is also bounded here: a server that sends headers
 * and then stalls is cancelled and surfaces as an {@link IOException}, which the client's retries and breaker see.
 */
public final class HttpJukeboxTransport implements JukeboxTransport {
    private final HttpClient client;
    private final Duration timeout;

    /** Creates a transport; {@code timeout} bounds connect, headers and the full body. */
    public HttpJukeboxTransport(Duration timeout) {
        this.timeout = timeout;
        this.client = HttpClient.newBuilder().connectTimeout(timeout).build();
    }

    @Override
    public Response get(String url) throws IOException {
        HttpRequest req = HttpRequest.newBuilder(URI.create(url)).timeout(timeout).GET().build();
        CompletableFuture<HttpResponse<byte[]>> f = client.sendAsync(req, HttpResponse.BodyHandlers.ofByteArray());
        try {
            HttpResponse<byte[]> r = f.get(timeout.toMillis(), TimeUnit.MILLISECONDS);
            return new Response(r.statusCode(), r.body());
        } catch (TimeoutException e) {
            f.cancel(true);
            HttpTimeoutException t = new HttpTimeoutException("jukebox request exceeded " + timeout.toMillis() + " ms");
            t.initCause(e);
            throw t;
        } catch (InterruptedException e) {
            f.cancel(true);
            Thread.currentThread().interrupt();
            throw new IOException("interrupted", e);
        } catch (ExecutionException e) {
            Throwable c = e.getCause();
            if (c instanceof IOException io) {
                throw io;
            }
            if (c instanceof RuntimeException re) {
                throw re;
            }
            throw new IOException(c);
        }
    }
}
