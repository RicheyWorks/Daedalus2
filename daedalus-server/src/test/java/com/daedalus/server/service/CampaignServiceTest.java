// SPDX-License-Identifier: MIT

package com.daedalus.server.service;

import com.daedalus.engine.generators.*;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Campaign mode's two load-bearing promises (ADR-006 idea #10).
 *
 * <p><b>Determinism</b> — the same seed produces the same ladder anywhere, which is the whole
 * mechanism behind a shareable campaign link with no stored state.
 *
 * <p><b>The ladder actually climbs</b> — and it climbs because difficulty is <em>measured</em>
 * per candidate maze, not assumed from size. That distinction is the reason the theory module
 * exists in this feature, so it gets a real assertion: measured grades must rise across stages.
 */
class CampaignServiceTest {

    private MazeGenerationService gen;

    @BeforeEach
    void setUp() {
        gen = new MazeGenerationService(new GeneratorRegistry(List.of(
                new BinaryTreeGenerator(), new SidewinderGenerator(), new PrimsGenerator(),
                new HuntAndKillGenerator(), new AldousBroderGenerator(),
                new RecursiveBacktrackerGenerator())),
                event -> { }, new SimpleMeterRegistry());
    }

    private CampaignService service() {
        return new CampaignService(gen, 6, 3, 9, 4, 50);
    }

    /**
     * Several seeds, not one. Asserting monotonicity on a single seed is how this test first
     * passed while the ladder walked backwards on 15 of 40 seeds. A 150-seed sweep during
     * development is strictly rising at this (default) config; five seeds here keep that honest
     * without a slow suite.
     */
    @ParameterizedTest
    @ValueSource(longs = {1L, 7L, 42L, 1234L, 99999L})
    void theMeasuredDifficultyClimbsAcrossStages(long seed) {
        var campaign = service().campaign(seed);
        assertThat(campaign.stages()).hasSize(6);

        var scores = campaign.stages().stream()
                .map(s -> s.grade().score())
                .toList();
        for (int i = 1; i < scores.size(); i++) {
            assertThat(scores.get(i))
                    .as("seed %d: stage %d (%.2f) must measure harder than stage %d (%.2f) — a "
                            + "ladder whose rungs are not ordered is not a ladder",
                            seed, i, scores.get(i), i - 1, scores.get(i - 1))
                    .isGreaterThan(scores.get(i - 1));
        }
        // And it spans a real range, not six near-identical mazes (measured span is ~8+).
        assertThat(scores.get(scores.size() - 1) - scores.get(0)).isGreaterThan(4.0);
        assertThat(campaign.stages().get(0).grade().label()).isIn("gentle", "moderate");
        assertThat(campaign.stages().get(5).grade().label()).isIn("punishing", "brutal");
    }

    /**
     * Pins the "must clear the previous stage" selection rule, at a config where it is
     * load-bearing.
     *
     * <p>This test exists because the default config cannot pin it: measured across 60 seeds,
     * defaults are 60/60 monotone with the rule and 60/60 without it, so a default-config test
     * passes with the rule deleted — a guarantee in name only (verified by deleting it). At ten
     * stages the rungs crowd together and the rule becomes the whole story: 0/60 monotone
     * without it, 53/60 with. These seeds are among the ones it rescues.
     */
    @ParameterizedTest
    @ValueSource(longs = {1L, 2L})
    void theClearThePreviousRuleIsWhatOrdersLongerLadders(long seed) {
        var campaign = new CampaignService(gen, 10, 2, 9, 3, 50).campaign(seed);
        var scores = campaign.stages().stream().map(s -> s.grade().score()).toList();
        for (int i = 1; i < scores.size(); i++) {
            assertThat(scores.get(i))
                    .as("seed %d: stage %d (%.2f) vs %d (%.2f) — without the clear-the-previous "
                            + "rule this ten-stage ladder is non-monotone on every seed measured",
                            seed, i, scores.get(i), i - 1, scores.get(i - 1))
                    .isGreaterThan(scores.get(i - 1));
        }
    }

    @Test
    void theSameSeedPlansTheSameCampaignAnywhere() {
        // A second service instance with a fresh maze cache stands in for another replica.
        var first = service().campaign(99L);
        var other = new MazeGenerationService(new GeneratorRegistry(List.of(
                new BinaryTreeGenerator(), new SidewinderGenerator(), new PrimsGenerator(),
                new HuntAndKillGenerator(), new AldousBroderGenerator(),
                new RecursiveBacktrackerGenerator())), event -> { }, new SimpleMeterRegistry());
        var second = new CampaignService(other, 6, 3, 9, 4, 50).campaign(99L);

        for (int i = 0; i < first.stages().size(); i++) {
            var a = first.stages().get(i);
            var b = second.stages().get(i);
            assertThat(b.seed()).as("stage %d chose a different maze seed", i).isEqualTo(a.seed());
            assertThat(b.generatorId()).isEqualTo(a.generatorId());
            assertThat(b.rows()).isEqualTo(a.rows());
            assertThat(b.grade().score()).isEqualTo(a.grade().score());
            // Same seed + same generator ⇒ same topology (ids differ; they are per-instance).
            assertThat(other.find(b.mazeId()).grid().toTileGrid())
                    .isDeepEqualTo(gen.find(a.mazeId()).grid().toTileGrid());
        }
        assertThat(second.stages().get(0).mazeId()).isNotEqualTo(first.stages().get(0).mazeId());
    }

    @Test
    void stageMazeIdsAreStableSoLeaderboardsAndGhostsCompose() {
        var svc = service();
        var first = svc.campaign(7L);
        var again = svc.campaign(7L);
        // Stable ids are what make per-maze leaderboards and ghosts work per stage: they key
        // off the maze id, so a wobbling id would silently reset a stage's board every request.
        assertThat(again.stages().stream().map(CampaignService.Stage::mazeId).toList())
                .isEqualTo(first.stages().stream().map(CampaignService.Stage::mazeId).toList());
        assertThat(svc.stage(7L, 3).mazeId()).isEqualTo(first.stages().get(3).mazeId());
        assertThat(svc.stage(7L, 99)).isNull();
        assertThat(svc.stage(7L, -1)).isNull();
    }

    @Test
    void hazardsRampInOverTheBackHalfAndAreOnlyDeclared() {
        var campaign = service().campaign(5L);
        assertThat(campaign.stages().get(0).hazards()).isEmpty();
        assertThat(campaign.stages().get(5).hazards()).contains("living", "traffic");
        // Declared, never started: planning a campaign must not mutate any maze. A living
        // ticker would have eroded stage 5's grid; its topology still matches its seed.
        var stage = campaign.stages().get(5);
        var replayed = gen.generate(stage.generatorId(), stage.rows(), stage.cols(), stage.seed());
        assertThat(gen.find(stage.mazeId()).grid().toTileGrid())
                .as("planning a campaign started a hazard ticker — stages must be inert")
                .isDeepEqualTo(replayed.grid().toTileGrid());
    }
}
