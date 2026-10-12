// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.server.config.JukeboxProperties;
import com.daedalus.server.jukebox.JukeboxService;
import com.daedalus.server.jukebox.StudioArranger;
import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.server.web.ResourceNotFoundException;
import io.swagger.v3.oas.annotations.Operation;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.CacheControl;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.security.Principal;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * The Reaction / Diffusion / Song jukebox on the realm's island (rd-jukebox). Read-only on chain.
 * The holder list comes from the signed-in principal (a wallet sign-in's subject is its address), so
 * nobody can ask the jukebox to play "as" another wallet; token HTML is public chain data anyway.
 */
@RestController
@RequestMapping("/api/v1/jukebox")
public class JukeboxController {

    private static final String WALLET = "0x[0-9a-f]{40}";
    private final JukeboxService jukebox;

    public JukeboxController(JukeboxService jukebox) {
        this.jukebox = jukebox;
    }

    @GetMapping("/config")
    @Operation(summary = "Whether the jukebox is on, which chain and RDSong contract it reads, and the genres.")
    public Map<String, Object> config() {
        JukeboxProperties p = jukebox.props();
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("enabled", p.enabled());
        m.put("onChain", jukebox.onChain());
        m.put("chainId", p.chainId());
        m.put("contract", p.contract());
        m.put("genres", StudioArranger.GENRES);
        m.put("studio", !p.studioUrl().isEmpty());
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
                        .contentType(file.endsWith(".mp3") ? MediaType.parseMediaType("audio/mpeg")
                                : MediaType.parseMediaType("image/webp"))
                        .body(new FileSystemResource(p)))
                .orElseThrow(() -> new ResourceNotFoundException("seed song", file, "no such seed song on this server"));
    }

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
        } catch (RuntimeException e) {
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY).body(Map.of("error", "the chain did not answer; try again"));
        }
    }

    @GetMapping("/tokens/{id}/html")
    @PerKeyRateLimit("jukebox")
    @Operation(summary = "A revealed token's own on-chain HTML (its song and Turing coat), served sandboxed.")
    public ResponseEntity<byte[]> tokenHtml(@PathVariable long id) {
        if (id < 0 || id > 1_000_000) throw new ResourceNotFoundException("token", String.valueOf(id), "no such token");
        try {
            return jukebox.tokenHtml(id)
                    .map(b -> ResponseEntity.ok()
                            .contentType(MediaType.parseMediaType("text/html;charset=UTF-8"))
                            // The token's script runs in an opaque origin: it can never read the realm's sign-in token.
                            .header("Content-Security-Policy", "sandbox allow-scripts")
                            .header("X-Content-Type-Options", "nosniff")
                            .header("X-Frame-Options", "SAMEORIGIN")    // the jukebox panel frames it; nobody else
                            .cacheControl(CacheControl.maxAge(Duration.ofDays(30)).cachePublic().immutable())
                            .body(b))
                    .orElseThrow(() -> new ResourceNotFoundException("token", String.valueOf(id), "not minted or not revealed yet"));
        } catch (ResourceNotFoundException e) {
            throw e;
        } catch (RuntimeException e) {
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY).build();
        }
    }

    @GetMapping("/arrangement")
    @Operation(summary = "What to play for a song in a genre, studio-quality or not (rd-studio seam; stubbed today).")
    public ResponseEntity<?> arrangement(@RequestParam String source,
                                         @RequestParam(defaultValue = "original") String genre,
                                         @RequestParam(defaultValue = "false") boolean studio) {
        try {
            return ResponseEntity.ok(jukebox.arrange(source, genre, studio));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("error", e.getMessage()));
        }
    }
}
