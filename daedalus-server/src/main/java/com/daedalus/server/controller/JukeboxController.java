// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.server.config.JukeboxProperties;
import com.daedalus.server.jukebox.HttpStudioArranger;
import com.daedalus.server.jukebox.JukeboxService;
import com.daedalus.server.jukebox.RdSongReader;
import com.daedalus.server.jukebox.StudioArranger;
import com.daedalus.server.jukebox.radio.RadioArea;
import com.daedalus.server.jukebox.radio.RadioRanking;
import com.daedalus.server.jukebox.radio.RadioRelay;
import com.daedalus.server.jukebox.radio.RadioService;
import com.daedalus.server.jukebox.radio.RadioStation;
import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.server.web.ResourceNotFoundException;
import io.swagger.v3.oas.annotations.Operation;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.CacheControl;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.security.Principal;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Supplier;
import java.util.stream.Stream;

/**
 * The Reaction / Diffusion / Song jukebox on the realm (rd-jukebox). Read-only on chain. The holder list comes from
 * the signed-in principal (a wallet sign-in's subject is its address), so nobody can play "as" another wallet. Everything
 * the browser plays comes from this origin or a station's own https stream: rd-studio stays private and the radio
 * proxy only relays streams this server listed itself.
 */
@RestController
@RequestMapping("/api/v1/jukebox")
public class JukeboxController {

    private static final org.slf4j.Logger log = org.slf4j.LoggerFactory.getLogger(JukeboxController.class);

    private static final String WALLET = "0x[0-9a-f]{40}";
    private static final String STATION_ID = "[A-Za-z0-9-]{1,64}";
    private static final java.util.regex.Pattern PLACE = java.util.regex.Pattern.compile("[\\p{L}\\p{M}0-9 .,'()-]{1,100}");

    private final JukeboxService jukebox;

    public JukeboxController(JukeboxService jukebox) {
        this.jukebox = jukebox;
    }

    // ---------------------------------------------------------------- settings + guest songs

    @GetMapping("/config")
    @Operation(summary = "Whether the jukebox is on, which chain and RDSong contract it reads, the genres and whether rd-studio is connected.")
    public Map<String, Object> config() {
        JukeboxProperties p = jukebox.props();
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("enabled", p.enabled());
        m.put("onChain", jukebox.onChain());
        m.put("chainId", p.chainId());
        m.put("contract", p.contract());
        m.put("genres", StudioArranger.GENRES);
        m.put("studio", jukebox.studio());
        m.put("studioHealth", jukebox.studioHealth());
        m.put("holders", jukebox.holders());
        return m;
    }

    @GetMapping("/seeds")
    @Operation(summary = "Guest mode: the seed songs anyone can play without a wallet.")
    public Map<String, Object> seeds() {
        return Map.of("seeds", jukebox.seeds());
    }

    @GetMapping("/seeds/{file}")
    @Operation(summary = "One seed song's audio (.mp3) or cover (.webp).")
    public ResponseEntity<Resource> seed(@PathVariable String file) {
        return jukebox.seedFile(file)
                .<ResponseEntity<Resource>>map(p -> ResponseEntity.ok()
                        .cacheControl(CacheControl.maxAge(Duration.ofDays(1)).cachePublic())
                        .contentType(MediaType.parseMediaType(file.endsWith(".mp3") ? "audio/mpeg" : "image/webp"))
                        .body(new FileSystemResource(p)))
                .orElseThrow(() -> new ResourceNotFoundException("seed song", file, "no such seed song on this server"));
    }

    // ---------------------------------------------------------------- holders + tokens

    @GetMapping("/owned")
    @PerKeyRateLimit("jukebox")
    @Operation(summary = "The RDSong token ids the signed-in wallet holds now.")
    public ResponseEntity<Map<String, Object>> owned(Principal principal) {
        String who = principal == null ? "" : principal.getName().toLowerCase();
        if (!who.matches(WALLET)) {
            return ResponseEntity.status(HttpStatus.FORBIDDEN).body(Map.of("error", "sign in with a wallet to play your tokens"));
        }
        if (!jukebox.onChain()) {
            return ResponseEntity.ok(Map.of("address", who, "tokens", List.of(), "onChain", false));
        }
        try {
            return ResponseEntity.ok(Map.of("address", who, "tokens", jukebox.tokensOf(who), "onChain", true));
        } catch (RdSongReader.IndexWarmingException e) {
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).header("Retry-After", "30")
                    .body(Map.of("error", "the holder index is still building; try again in a minute"));
        } catch (RuntimeException e) {
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY).body(Map.of("error", "the chain did not answer; try again"));
        }
    }

    @GetMapping("/tokens/{id}/html")
    @PerKeyRateLimit("jukebox")
    @Operation(summary = "A revealed token's own on-chain HTML (its song and Turing coat), served sandboxed.")
    public ResponseEntity<byte[]> tokenHtml(@PathVariable long id) {
        byte[] html = onChain(() -> jukebox.tokenHtml(checkId(id)), id);
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType("text/html;charset=UTF-8"))
                // The token's script runs in an opaque origin: it can never read the realm's sign-in token.
                .header("Content-Security-Policy", "sandbox allow-scripts")
                .header("X-Content-Type-Options", "nosniff")
                .header("X-Frame-Options", "SAMEORIGIN")    // the jukebox panel frames it; nobody else
                .cacheControl(CacheControl.maxAge(Duration.ofDays(30)).cachePublic().immutable())
                .body(html);
    }

    @GetMapping("/tokens/{id}/hash")
    @PerKeyRateLimit("jukebox")
    @Operation(summary = "A revealed token's 32-byte hash (RDSong.tokenHash), which keys its Turing coat.")
    public ResponseEntity<Map<String, Object>> tokenHash(@PathVariable long id) {
        String hash = onChain(() -> jukebox.tokenHash(checkId(id)), id);
        return ResponseEntity.ok().cacheControl(CacheControl.maxAge(Duration.ofDays(30)).cachePublic().immutable())
                .body(Map.of("id", id, "hash", hash));
    }

    // ---------------------------------------------------------------- rd-studio (arrangements, audio, coats)

    @GetMapping("/arrangement")
    @PerKeyRateLimit("jukebox")
    @Operation(summary = "What to play for a song in a genre, studio-quality or not (rd-studio; the original when it has none).")
    public ResponseEntity<?> arrangement(@RequestParam String source,
                                         @RequestParam(defaultValue = "original") String genre,
                                         @RequestParam(defaultValue = "false") boolean studio,
                                         @RequestParam(defaultValue = "mp3") String format,
                                         @RequestParam(defaultValue = "neutral") String preset,
                                         @RequestParam(defaultValue = "0") int vinyl,
                                         @RequestParam(defaultValue = "off") String noise) {
        try {
            StudioArranger.Arrangement a = jukebox.arrange(source, genre, studio, new StudioArranger.Render(format, preset, vinyl, noise));
            ResponseEntity.BodyBuilder ok = ResponseEntity.ok().cacheControl(CacheControl.noStore());
            if (a.retryAfterMs() != null) ok.header("Retry-After", String.valueOf(Math.max(1, (a.retryAfterMs() + 999) / 1000)));
            return ok.body(a);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/studio/audio/{key}")
    @PerKeyRateLimit("jukebox")
    @Operation(summary = "An rd-studio render (MP3), relayed from the private studio service.")
    public void studioAudio(@PathVariable String key, @RequestHeader(value = "If-None-Match", required = false) String inm,
                            HttpServletResponse res) throws IOException {
        HttpStudioArranger.Upstream up = jukebox.studioAudio(key, inm)
                .orElseThrow(() -> new ResourceNotFoundException("studio render", key, "no such rd-studio render"));
        res.setHeader("Cache-Control", up.cacheControl());
        if (up.etag() != null) res.setHeader("ETag", up.etag());
        if (up.status() == 304) {
            res.setStatus(HttpStatus.NOT_MODIFIED.value());
            return;
        }
        if (up.length() > 0) res.setContentLengthLong(up.length());
        pipe(up.body(), res, up.contentType(), Duration.ofMinutes(10), HttpStudioArranger.MAX_AUDIO_BYTES);
    }

    @GetMapping("/coat.png")
    @PerKeyRateLimit("jukebox")
    @Operation(summary = "A token's real Turing coat: a seamless PNG for its hash (size 256, 512 or 1024).")
    public ResponseEntity<byte[]> coatPng(@RequestParam String hash, @RequestParam(defaultValue = "512") int size,
                                          @RequestHeader(value = "If-None-Match", required = false) String inm) {
        byte[] png = jukebox.coatPng(hash.toLowerCase(), size)
                .orElseThrow(() -> new ResourceNotFoundException("coat", hash, "no coat for that hash (need 0x + 64 hex; size 256|512|1024)"));
        String etag = "\"" + sha256(png) + "\"";      // the same strong ETag rd-studio sends: sha256 of the exact bytes
        CacheControl forever = CacheControl.maxAge(Duration.ofDays(365)).cachePublic().immutable();
        if (etag.equals(inm == null ? null : inm.trim()))
            return ResponseEntity.status(HttpStatus.NOT_MODIFIED).eTag(etag).cacheControl(forever).build();
        return ResponseEntity.ok().contentType(MediaType.IMAGE_PNG).header("X-Content-Type-Options", "nosniff")
                .eTag(etag).cacheControl(forever).body(png);
    }

    private static String sha256(byte[] b) {
        try {
            return java.util.HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(b));
        } catch (java.security.NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    @GetMapping("/coat")
    @PerKeyRateLimit("jukebox")
    @Operation(summary = "A token's coat genome (traits, Gray-Scott genome, kind) for its hash.")
    public ResponseEntity<String> coat(@RequestParam String hash) {
        return jukebox.coat(hash.toLowerCase())
                .map(json -> ResponseEntity.ok().contentType(MediaType.APPLICATION_JSON)
                        .cacheControl(CacheControl.maxAge(Duration.ofDays(30)).cachePublic().immutable()).body(json))
                .orElseThrow(() -> new ResourceNotFoundException("coat", hash, "no coat genome for that hash"));
    }

    // ---------------------------------------------------------------- radio

    @GetMapping("/radio/stations")
    @PerKeyRateLimit("jukebox")
    @Operation(summary = "Radio stations around the listener: local FM first, then other local options, then the rest.")
    public ResponseEntity<Map<String, Object>> radio(@RequestParam(required = false) Double lat,
                                                     @RequestParam(required = false) Double lon,
                                                     @RequestParam(required = false) String place,
                                                     @RequestParam(required = false) String country) {
        if (lat != null && !(lat >= -90 && lat <= 90) || lon != null && !(lon >= -180 && lon <= 180) || (lat == null) != (lon == null))
            return ResponseEntity.badRequest().body(Map.of("error", "lat must be -90..90 and lon -180..180, given together"));
        if (place != null && !place.isBlank() && !PLACE.matcher(place.strip()).matches())
            return ResponseEntity.badRequest().body(Map.of("error", "place: letters, digits, spaces and , . ' ( ) - only, up to 100"));
        if (country != null && !country.isBlank() && !country.strip().matches("[A-Za-z]{2}"))
            return ResponseEntity.badRequest().body(Map.of("error", "country is a 2-letter code"));
        RadioArea area = RadioArea.parse(place == null ? null : place.strip(), lat, lon, country == null ? null : country.strip());
        RadioService.Lineup lineup;
        try {
            lineup = jukebox.radio(area);
        } catch (IllegalStateException e) {
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY).body(Map.of("error", "can't reach the radio directory; try again"));
        }
        List<Map<String, Object>> rows = lineup.stations().stream().map(JukeboxController::row).toList();
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("area", area);
        out.put("note", lineup.note());
        out.put("stations", rows);
        return ResponseEntity.ok(out);
    }

    @GetMapping("/radio/stream/{id}")
    @PerKeyRateLimit("jukeboxRelay")
    @Operation(summary = "Relays a station this server listed, from this origin (WebAudio needs same-origin audio). Nothing else is relayed.")
    public void radioStream(@PathVariable String id, HttpServletRequest req, HttpServletResponse res) throws IOException {
        String url = (id.matches(STATION_ID) ? jukebox.radioStream(id) : Optional.<String>empty())
                .orElseThrow(() -> new ResourceNotFoundException("station", id, "list stations first; only listed stations play"));
        RadioRelay relay = jukebox.relay();
        String listener = req.getRemoteAddr();
        if (!relay.acquire(listener)) {
            res.setHeader("Retry-After", "10");
            res.sendError(HttpStatus.SERVICE_UNAVAILABLE.value(), "radio relay is full; try again");
            return;
        }
        try {
            RadioRelay.Opened up = relay.open(url);
            res.setContentType(up.contentType());
            res.setHeader("Cache-Control", "no-store");
            res.setHeader("X-Content-Type-Options", "nosniff");
            relay.pipe(up.body(), res.getOutputStream());
        } catch (RadioRelay.OffAir e) {
            log.info("radio relay: station {} is off the air ({})", id, e.getMessage());
            if (!res.isCommitted()) res.sendError(HttpStatus.BAD_GATEWAY.value(), "that station is off the air");
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } finally {
            relay.release(listener);
        }
    }

    // ---------------------------------------------------------------- helpers

    private static Map<String, Object> row(RadioRanking.Ranked r) {
        RadioStation s = r.station();
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", s.id());
        m.put("name", s.name());
        m.put("tags", s.tags());
        m.put("place", String.join(", ", Stream.of(s.city(), s.countrycode()).filter(x -> !x.isEmpty()).toList()));
        m.put("band", s.band());
        m.put("tier", r.tier());
        m.put("km", r.km() == null ? null : Math.round(r.km()));
        m.put("play", "/api/v1/jukebox/radio/stream/" + s.id());     // same-origin, so it can run through WebAudio
        return m;
    }

    private static long checkId(long id) {
        if (id < 0 || id > 1_000_000) throw new ResourceNotFoundException("token", String.valueOf(id), "no such token");
        return id;
    }

    /** Runs a chain read: empty → 404 (not minted / not revealed / jukebox off), RPC failure → 502. */
    private static <T> T onChain(Supplier<Optional<T>> read, long id) {
        Optional<T> v;
        try {
            v = read.get();
        } catch (ResourceNotFoundException e) {
            throw e;
        } catch (RuntimeException e) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "the chain did not answer; try again");
        }
        return v.orElseThrow(() -> new ResourceNotFoundException("token", String.valueOf(id), "not minted or not revealed yet"));
    }

    /** Copies {@code in} to the response until it ends, the client leaves, or {@code max} passes. */
    private static void pipe(InputStream in, HttpServletResponse res, String type, Duration max) throws IOException {
        pipe(in, res, type, max, Long.MAX_VALUE);
    }

    /** As above, and never more than {@code maxBytes} (rd-studio's 32 MiB file limit for audio). */
    private static void pipe(InputStream in, HttpServletResponse res, String type, Duration max, long maxBytes) throws IOException {
        res.setContentType(type);
        res.setHeader("X-Content-Type-Options", "nosniff");
        long stop = max == null ? Long.MAX_VALUE : System.nanoTime() + max.toNanos();
        try (in) {
            OutputStream out = res.getOutputStream();
            byte[] buf = new byte[16 * 1024];
            long total = 0;
            for (int n; (n = in.read(buf)) >= 0 && System.nanoTime() < stop && total < maxBytes; ) {
                n = (int) Math.min(n, maxBytes - total);
                out.write(buf, 0, n);
                out.flush();
                total += n;
            }
        } catch (IOException e) {
            // the listener left: nothing to answer
        }
    }
}
