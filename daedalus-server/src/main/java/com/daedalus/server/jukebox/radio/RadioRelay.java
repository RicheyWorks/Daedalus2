// SPDX-License-Identifier: MIT

package com.daedalus.server.jukebox.radio;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Streams a listed station to the browser from this origin, so the jukebox can route it through WebAudio (no CORS
 * taint) and plain-http stations play on https pages. Bounded every way that matters:
 * <ul>
 *   <li>{@link RelayGuard} on the station URL and on each redirect hop (followed by hand, at most 3);</li>
 *   <li>only {@code audio/*} or {@code application/ogg} answers are relayed (no HTML pages, playlists, or JSON);</li>
 *   <li>a global and a per-listener concurrency cap, a wall-clock cap, a byte cap and an idle (stalled upstream) cap.</li>
 * </ul>
 */
public final class RadioRelay {

    public record Limits(int maxRelays, int perListener, Duration maxTime, long maxBytes, Duration idle, Duration connect) {
        public static final Limits DEFAULT = new Limits(64, 3, Duration.ofHours(4), 640L << 20, Duration.ofSeconds(20),
                Duration.ofSeconds(5));
    }

    /** An upstream audio stream that passed every check. */
    public record Opened(InputStream body, String contentType) {}

    /** The station can't be relayed (refused, dead, not audio). Listeners only ever see "off the air". */
    public static final class OffAir extends Exception {
        public OffAir(String why) { super(why); }
    }

    private final UrlCheck guard;
    private final Limits limits;
    private final HttpClient http;
    private final Semaphore slots;
    private final Map<String, AtomicInteger> perListener = new ConcurrentHashMap<>();
    private final ScheduledExecutorService watchdog = Executors.newSingleThreadScheduledExecutor(r -> {
        Thread t = new Thread(r, "rd-jukebox-relay-watchdog");
        t.setDaemon(true);
        return t;
    });

    public RadioRelay(UrlCheck guard, Limits limits) {
        this.guard = guard;
        this.limits = limits;
        this.slots = new Semaphore(limits.maxRelays());
        this.http = HttpClient.newBuilder().connectTimeout(limits.connect()).followRedirects(HttpClient.Redirect.NEVER).build();
    }

    /** Takes a relay slot for {@code listener}; false when the relay or this listener is at its cap. */
    public boolean acquire(String listener) {
        AtomicInteger n = perListener.computeIfAbsent(listener, k -> new AtomicInteger());
        if (n.incrementAndGet() > limits.perListener()) {
            release0(listener, n);
            return false;
        }
        if (!slots.tryAcquire()) {
            release0(listener, n);
            return false;
        }
        return true;
    }

    public void release(String listener) {
        slots.release();
        AtomicInteger n = perListener.get(listener);
        if (n != null) release0(listener, n);
    }

    private void release0(String listener, AtomicInteger n) {
        if (n.decrementAndGet() <= 0) perListener.remove(listener, n);
    }

    public int available() { return slots.availablePermits(); }

    /** Opens {@code url}, following up to {@link RelayGuard#MAX_REDIRECTS} redirects, each re-checked. */
    public Opened open(String url) throws OffAir, InterruptedException {
        String next = url;
        for (int hop = 0; hop <= RelayGuard.MAX_REDIRECTS; hop++) {
            URI u;
            try {
                u = guard.check(next);
            } catch (RelayGuard.Refused e) {
                throw new OffAir("refused: " + e.getMessage());
            }
            HttpResponse<InputStream> res;
            try {
                res = http.send(HttpRequest.newBuilder(u).timeout(Duration.ofSeconds(10))
                        .header("Icy-MetaData", "0").header("User-Agent", "Daedalus-rd-jukebox/1.0").GET().build(),
                        HttpResponse.BodyHandlers.ofInputStream());
            } catch (IOException | IllegalArgumentException e) {
                throw new OffAir("unreachable: " + e.getClass().getSimpleName());
            }
            int c = res.statusCode();
            if (c >= 300 && c < 400) {
                close(res.body());
                String loc = res.headers().firstValue("Location").orElse("");
                if (loc.isEmpty()) throw new OffAir("redirect without Location");
                try {
                    next = u.resolve(loc).toString();
                } catch (IllegalArgumentException e) {
                    throw new OffAir("bad redirect");
                }
                continue;
            }
            String type = res.headers().firstValue("Content-Type").orElse("").toLowerCase(Locale.ROOT).split(";")[0].trim();
            if (c != 200 || !(type.startsWith("audio/") || type.equals("application/ogg"))) {
                close(res.body());
                throw new OffAir("HTTP " + c + " " + type);
            }
            if (!type.matches("[a-z]+/[a-z0-9.+-]{1,40}")) type = "audio/mpeg";
            return new Opened(res.body(), type);
        }
        throw new OffAir("too many redirects");
    }

    /**
     * Copies {@code in} to {@code out} until the stream ends, the listener leaves, the time or byte cap is reached,
     * or the upstream stalls for {@code idle}. Returns the bytes relayed.
     */
    public long pipe(InputStream in, OutputStream out) {
        AtomicLong lastRead = new AtomicLong(System.nanoTime());
        long idleNs = limits.idle().toNanos();
        ScheduledFuture<?> dog = watchdog.scheduleAtFixedRate(() -> {
            if (System.nanoTime() - lastRead.get() > idleNs) close(in);      // unblocks the read below
        }, 1, 1, TimeUnit.SECONDS);
        long stop = System.nanoTime() + limits.maxTime().toNanos();
        long total = 0;
        try (in) {
            byte[] buf = new byte[16 * 1024];
            for (int n; (n = in.read(buf)) >= 0; ) {
                lastRead.set(System.nanoTime());
                if (total + n > limits.maxBytes()) n = (int) (limits.maxBytes() - total);
                out.write(buf, 0, n);
                out.flush();
                total += n;
                if (total >= limits.maxBytes() || System.nanoTime() > stop) break;
            }
        } catch (IOException e) {
            // the listener left or the upstream died/stalled: nothing more to send
        } finally {
            dog.cancel(false);
        }
        return total;
    }

    private static void close(InputStream in) {
        try {
            in.close();
        } catch (IOException ignored) {
            // already gone
        }
    }
}
