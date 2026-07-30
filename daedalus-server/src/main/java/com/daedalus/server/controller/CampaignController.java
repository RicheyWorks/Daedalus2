// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.server.ratelimit.PerKeyRateLimit;
import com.daedalus.server.service.CampaignService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDate;

/**
 * Campaign mode (ADR-006 idea #10).
 *
 * <p>One endpoint is enough, which is the point: a campaign response carries each stage's
 * {@code mazeId}, so a client walks the ladder using the endpoints that already exist —
 * {@code GET /maze/{id}} to load a stage, {@code POST /maze/{id}/session} to play it,
 * {@code GET /leaderboard?maze=} for that stage's own board, {@code GET /maze/{id}/ghost} for
 * its record holder, {@code POST /maze/{id}/live} and {@code /traffic} for the hazards the
 * stage declares. Nothing about campaigns needed a parallel API.
 */
@RestController
@RequestMapping("/api/v1")
@Tag(name = "Campaign", description = "A deterministic, difficulty-graded ladder of stages.")
public class CampaignController {

    private final CampaignService campaigns;

    public CampaignController(CampaignService campaigns) {
        this.campaigns = campaigns;
    }

    /**
     * Planning a campaign generates and grades {@code stages × candidates} mazes on first
     * request for a seed (then caches), so it shares the {@code mazeGenerate} budget.
     */
    @GetMapping("/campaign")
    @Operation(summary = "A campaign: a deterministic ladder of stages with measured difficulty.",
            description = "Same seed anywhere means byte-identical stages, so a campaign link is "
                    + "shareable with no stored state. Omit the seed for today's shared campaign "
                    + "(UTC date derived, like the daily maze). Each stage reports the measured "
                    + "grade behind its placement and the hazards it declares; the client "
                    + "activates those through the existing /live and /traffic endpoints. "
                    + "Rate-limited against the 'mazeGenerate' budget.")
    @PerKeyRateLimit("mazeGenerate")
    public ResponseEntity<CampaignService.Campaign> campaign(
            @RequestParam(required = false) Long seed) {
        long effective = seed != null ? seed : LocalDate.now(java.time.ZoneOffset.UTC).toEpochDay();
        return ResponseEntity.ok(campaigns.campaign(effective));
    }
}
