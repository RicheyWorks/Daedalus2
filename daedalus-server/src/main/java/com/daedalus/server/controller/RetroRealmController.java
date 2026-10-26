// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.world.retro.RetroCodec;
import com.daedalus.world.retro.RetroProgress;
import com.daedalus.world.retro.RetroRealm;
import com.daedalus.world.retro.RetroRealmGenerator;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * The realm behind a portal (ADR-052): the Java engines generate it whole from a seed (field, towns, castle, cave,
 * every chest and lock and monster table) and serve it as the "DRR 1" spec the C++ core plays. Read-only and
 * deterministic, so it is public like the maze reads; generating it costs a few milliseconds, so it shares the
 * maze generators' per-caller budget, and the last few realms are kept.
 */
@RestController
@RequestMapping("/api/v1/retro")
@Tag(name = "Retro realm", description = "The 8-bit realm behind a portal, generated from a seed.")
public class RetroRealmController {

    private static final int KEEP = 16;

    private final Map<Long, String> recent = new LinkedHashMap<>(KEEP, 0.75f, true) {
        @Override
        protected boolean removeEldestEntry(Map.Entry<Long, String> eldest) {
            return size() > KEEP;
        }
    };

    @GetMapping(value = "/{seed}", produces = MediaType.TEXT_PLAIN_VALUE)
    @PerKeyRateLimit("mazeGenerate")
    @Operation(summary = "The realm for a seed, as the DRR 1 spec (plain text, one fact per line).")
    public ResponseEntity<String> realm(@PathVariable long seed) {
        String spec;
        synchronized (recent) {
            spec = recent.get(seed);
        }
        if (spec == null) {
            spec = RetroCodec.write(RetroRealmGenerator.generate(seed));
            synchronized (recent) {
                recent.put(seed, spec);
            }
        }
        return ResponseEntity.ok().contentType(MediaType.TEXT_PLAIN).body(spec);
    }

    @GetMapping("/{seed}/check")
    @PerKeyRateLimit("mazeGenerate")
    @Operation(summary = "Walk the realm for a seed the way a party would and report whether it can be finished.")
    public ResponseEntity<Map<String, Object>> check(@PathVariable long seed) {
        RetroRealm realm = RetroRealmGenerator.generate(seed);
        RetroProgress.Report r = RetroProgress.check(realm);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("seed", seed);
        body.put("finishable", r.finishable());
        body.put("chests", r.chests());
        body.put("chestsReached", r.chestsReached());
        body.put("doors", r.doors());
        body.put("doorsOpened", r.doorsOpened());
        body.put("bosses", r.bosses());
        body.put("bossesBeaten", r.bossesBeaten());
        body.put("npcs", r.npcs());
        body.put("npcsReached", r.npcsReached());
        body.put("tilesReached", r.tilesReached());
        body.put("problems", r.problems());
        return ResponseEntity.ok(body);
    }
}
