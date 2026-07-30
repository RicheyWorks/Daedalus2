// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.MazeGrid;
import com.daedalus.theory.DifficultyGrader;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Campaign mode (ADR-006 idea #10) — the roadmap's finale, and deliberately a composition of
 * everything already built rather than a new subsystem.
 *
 * <p><b>Deterministic, so campaigns are shareable.</b> A campaign is identified by a seed;
 * stage {@code n}'s maze seed derives from {@code (campaignSeed, n)} alone. Two players with
 * the same link play byte-identical stages with no stored campaign state anywhere — the same
 * trick {@link DailyMazeService} uses, applied to a ladder.
 *
 * <p><b>Difficulty is steered by measurement, not asserted.</b> Each stage has a target score;
 * the service generates candidate mazes across three sizes, grades each with
 * {@link DifficultyGrader}, and keeps the one whose <em>measured</em> score lands closest to
 * the target while still clearing the previous stage. That is what makes the theory module
 * load-bearing here: delete the grading and the ladder stops being a ladder. The ordering is
 * measured, not assumed — see {@link #buildStage} for what each selection rule is actually
 * worth, and {@code CampaignServiceTest} for the pinned behaviour.
 *
 * <p><b>Hazards are declared, not applied.</b> Later stages carry {@code hazards} —
 * {@code living}, {@code traffic} — but this service never starts a ticker. The client turns
 * them on through the existing opt-in endpoints, so their capacity caps and rate limits keep
 * governing exactly as they do outside a campaign.
 *
 * <p><b>Bounded</b> (house rule): stage id maps are held per campaign in a bounded map and each
 * campaign holds at most {@code stages} entries; a full plan is computed once per seed and then
 * reused. Eviction is handled the way the daily maze handles it — if the maze cache dropped a
 * stage, the next request regenerates it from the same seed.
 */
@Service
public class CampaignService {

    private static final Logger log = LoggerFactory.getLogger(CampaignService.class);

    /**
     * The generator ladder: straight-and-biased first, winding later. Chosen for the shape of
     * the mazes they produce, which the grader then confirms or corrects per stage.
     */
    private static final String[] GENERATOR_LADDER = {
            "binary-tree", "sidewinder", "prims", "hunt-and-kill",
            "aldous-broder", "recursive-backtracker",
    };

    /** One stage of a campaign. */
    public record Stage(int index, String name, UUID mazeId, String generatorId,
                        int rows, int cols, long seed,
                        double targetScore, DifficultyGrader.Grade grade,
                        List<String> hazards) {}

    /** A whole campaign: its seed and its ladder. */
    public record Campaign(long seed, List<Stage> stages) {}

    private final MazeGenerationService gen;
    private final int stageCount;
    private final int candidates;
    private final int baseSize;
    private final int sizeStep;

    /** campaignSeed → its computed plan. */
    private final ConcurrentHashMap<Long, Campaign> plans = new ConcurrentHashMap<>();
    private final int maxCampaigns;

    public CampaignService(MazeGenerationService gen,
                           @Value("${daedalus.campaign.stages:6}") int stageCount,
                           @Value("${daedalus.campaign.candidates:3}") int candidates,
                           @Value("${daedalus.campaign.base-size:9}") int baseSize,
                           @Value("${daedalus.campaign.size-step:4}") int sizeStep,
                           @Value("${daedalus.campaign.max-campaigns:50}") int maxCampaigns) {
        this.gen = gen;
        this.stageCount = Math.max(1, stageCount);
        this.candidates = Math.max(1, candidates);
        this.baseSize = Math.max(7, baseSize);
        this.sizeStep = Math.max(1, sizeStep);
        this.maxCampaigns = Math.max(1, maxCampaigns);
    }

    /**
     * The campaign for a seed — computed on first request, then reused so stage maze ids stay
     * stable. Stable ids are what let the earlier batches compose for free: every stage gets
     * its own leaderboard partition and its own ghost, because those key off the maze id.
     */
    public Campaign campaign(long seed) {
        Campaign existing = plans.get(seed);
        if (existing != null && allStagesStillCached(existing)) {
            return existing;
        }
        if (plans.size() >= maxCampaigns) {
            plans.clear(); // crude but bounded: campaigns are cheap to recompute, and identical
        }
        Campaign fresh = plan(seed);
        plans.put(seed, fresh);
        return fresh;
    }

    /** One stage, or {@code null} when the index is outside the campaign. */
    public Stage stage(long seed, int index) {
        Campaign c = campaign(seed);
        if (index < 0 || index >= c.stages().size()) {
            return null;
        }
        return c.stages().get(index);
    }

    public int stageCount() {
        return stageCount;
    }

    private boolean allStagesStillCached(Campaign c) {
        for (Stage s : c.stages()) {
            if (gen.find(s.mazeId()) == null) {
                return false; // evicted — recompute the plan from the same seeds
            }
        }
        return true;
    }

    private Campaign plan(long seed) {
        List<Stage> stages = new ArrayList<>();
        double previousScore = 0.0;
        for (int i = 0; i < stageCount; i++) {
            Stage stage = buildStage(seed, i, previousScore);
            stages.add(stage);
            previousScore = stage.grade().score();
        }
        log.info("campaign {} planned: {}", seed, stages.stream()
                .map(s -> s.index() + ":" + s.grade().label() + "(" + s.grade().score() + ")")
                .toList());
        return new Campaign(seed, List.copyOf(stages));
    }

    /**
     * Build stage {@code index}. The candidate pool spans both {@code candidates} seeds and
     * three sizes around the stage's nominal size, and selection runs in two steps:
     *
     * <ol>
     *   <li>keep only candidates measuring strictly harder than the previous stage;</li>
     *   <li>among those, take the one nearest this stage's target score.</li>
     * </ol>
     *
     * <p><b>What each part actually buys, measured.</b> Selecting on target-closeness from a
     * single size produced a strictly rising ladder for only 25 of 40 seeds. Widening the pool
     * across three sizes fixed that by itself: at the default config the ladder is 60/60 with
     * step 1 <em>and</em> 60/60 without it, so on defaults step 1 never changes the outcome. It
     * earns its place at longer ladders, where stages crowd together and target-closeness stops
     * separating them — at ten stages it is the difference between 0/60 and 53/60.
     *
     * <p>Note the honest limit in that last figure: 53/60, not 60/60. A strictly rising ladder
     * is a measured property of the <em>default</em> configuration, not something this method can
     * guarantee for every setting of {@code stages} / {@code candidates} / {@code size-step}.
     * Push the stage count up or the candidate count down and rungs can still tie or dip.
     *
     * <p>If no candidate clears the previous stage, the hardest candidate wins, so the ladder
     * plateaus rather than dipping.
     */
    private Stage buildStage(long campaignSeed, int index, double previousScore) {
        String generatorId = GENERATOR_LADDER[Math.min(index, GENERATOR_LADDER.length - 1)];
        int nominal = baseSize + index * sizeStep;
        double target = targetFor(index);

        Candidate best = null;      // nearest target among those harder than the previous stage
        Candidate hardest = null;   // fallback when nothing clears the previous stage

        for (int sizeVariant = 0; sizeVariant < 3; sizeVariant++) {
            int size = Math.max(5, nominal + (sizeVariant - 1) * 2);
            for (int c = 0; c < candidates; c++) {
                long mazeSeed = seedFor(campaignSeed, index, sizeVariant * candidates + c);
                var cached = gen.generate(generatorId, size, size, mazeSeed);
                MazeGrid grid = cached.grid();
                var candidate = new Candidate(cached, DifficultyGrader.grade(grid), mazeSeed, size);

                if (hardest == null || candidate.grade.score() > hardest.grade.score()) {
                    hardest = candidate;
                }
                if (candidate.grade.score() > previousScore
                        && (best == null
                            || Math.abs(candidate.grade.score() - target)
                               < Math.abs(best.grade.score() - target))) {
                    best = candidate;
                }
            }
        }

        Candidate chosen = best != null ? best : hardest;
        return new Stage(index, nameFor(index), chosen.cached.metadata().id(), generatorId,
                chosen.size, chosen.size, chosen.seed, round(target), chosen.grade,
                hazardsFor(index));
    }

    private record Candidate(MazeGenerationService.Cached cached, DifficultyGrader.Grade grade,
                             long seed, int size) {}

    /**
     * Stage targets climb linearly, and are deliberately <b>conservative</b> — they sit below
     * what each stage's candidate pool can reach, so selection lands mid-pool.
     *
     * <p>That headroom is the point, and it was measured the hard way. Raising the range to
     * {@code 2.8 … 13} (nominally "more accurate", since the pool really does reach 13) made
     * every stage pick the hardest maze available to it, which left the <em>next</em> stage
     * nothing to beat — monotonicity collapsed from 60/60 campaign seeds to 34/60. Conservative
     * targets keep each rung below its ceiling so the rung above can clear it.
     *
     * <p>The visible cost, stated plainly: stage 1 grades a little above its target and the
     * finale a good deal below (the finale's pool reaches ~13 against a target of 11). Exact
     * target attainment is not what a campaign needs — ordering is.
     */
    private double targetFor(int index) {
        double t = stageCount == 1 ? 0.0 : index / (double) (stageCount - 1);
        return 2.5 + t * 8.5;
    }

    /** Hazards ramp in over the back half — the earlier batches, reused as difficulty. */
    private List<String> hazardsFor(int index) {
        List<String> hazards = new ArrayList<>();
        if (stageCount >= 3) {
            if (index >= (int) Math.ceil(stageCount * 0.5)) hazards.add("living");
            if (index >= (int) Math.ceil(stageCount * 0.75)) hazards.add("traffic");
        }
        return List.copyOf(hazards);
    }

    private static String nameFor(int index) {
        String[] names = {
                "The Threshold", "The Winding", "The Warrens", "The Shifting Halls",
                "The Crowded Deep", "The Labyrinth",
        };
        return index < names.length ? names[index] : "Depth " + (index + 1);
    }

    /**
     * {@code (campaignSeed, stage, candidate)} → maze seed. Spread by the 64-bit golden ratio
     * so neighbouring stages and candidates land far apart in seed space, the same construction
     * {@link DailyMazeService#seedFor} uses.
     */
    static long seedFor(long campaignSeed, int stage, int candidate) {
        long mixed = campaignSeed + (stage * 0x9E3779B97F4A7C15L)
                + (candidate * 0xC2B2AE3D27D4EB4FL);
        return mixed ^ Long.rotateLeft(mixed, 31);
    }

    private static double round(double v) {
        return Math.round(v * 100.0) / 100.0;
    }
}
