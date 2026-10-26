// SPDX-License-Identifier: MIT

package com.daedalus.server.controller;

import com.daedalus.model.LeaderboardEntry;
import com.daedalus.server.service.LeaderboardService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.Size;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

/**
 * Leaderboard snapshot. Split from {@link MazeController} so the board's routing
 * (global / maze / generator) is not buried under generate and session.
 */
@RestController
@RequestMapping("/api/v1")
@Tag(name = "Leaderboard", description = "Completion-time boards.")
@Validated
public class LeaderboardController {

    private final LeaderboardService leaderboard;

    public LeaderboardController(LeaderboardService leaderboard) {
        this.leaderboard = leaderboard;
    }

    @GetMapping("/leaderboard")
    @Operation(summary = "Top-N completion times across active sessions.",
            tags = "Leaderboard",
            description = "Snapshot — backed by Redis when daedalus.redis.enabled=true, "
                    + "otherwise in-memory. Pass maze=<id> for that maze's own board — the "
                    + "partition behind the daily challenge's leaderboard — or generator=<id> "
                    + "for one algorithm's board. maze wins if both are given, being the more "
                    + "specific of the two.")
    public List<LeaderboardEntry> leaderboard(
            @RequestParam(defaultValue = "20")
            @Min(value = 1,   message = "n must be at least 1")
            @Max(value = 100, message = "n must be at most 100")
            int n,
            @RequestParam(required = false) UUID maze,
            @RequestParam(required = false)
            @Size(max = 64, message = "generator id must be at most 64 chars")
            String generator) {
        if (maze != null) {
            return leaderboard.top(n, maze);
        }
        return leaderboard.topByGenerator(n, generator);
    }
}
