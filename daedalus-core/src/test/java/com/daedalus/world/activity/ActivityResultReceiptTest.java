// SPDX-License-Identifier: MIT
package com.daedalus.world.activity;

import com.daedalus.world.labyrinth.ChalkTrail;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ActivityResultReceiptTest {

    static final ActivityParticipant HOUND =
            new ActivityParticipant("life:mossback-hound-07", ActivityParticipant.Kind.LIFE, "animal", "scouting");
    static final ActivityParticipant HIVE =
            new ActivityParticipant("colony:emberbee-hive-2", ActivityParticipant.Kind.COLONY, "social_insect", "observation");

    static ActivityResultAdapter.Session session(String result, List<ActivityParticipant> who) {
        return new ActivityResultAdapter.Session("sess-lab-0001", result, "labyrinth-host", "verify:lab-0001",
                who, List.of("evt:chalk-run-0001"), 1_760_861_400_000L);
    }

    /** Trail with 3 marks kept after 4 chalk spent (one mark eaten by a Chalk Eater). */
    static ChalkTrailRunAdapter.Run run(boolean exit, boolean abandoned) {
        ChalkTrail t = new ChalkTrail(10, 32);
        t.mark(new ChalkTrail.Point(0, 0));
        t.mark(new ChalkTrail.Point(1, 0));
        t.mark(new ChalkTrail.Point(1, 1));
        t.mark(new ChalkTrail.Point(2, 1));
        t.erase(new ChalkTrail.Point(1, 0));
        return ChalkTrailRunAdapter.Run.of(t, 10, exit, abandoned);
    }

    static ActivityResultReceipt receipt() {
        return new ChalkTrailRunAdapter(ActivityMode.AUTHORITATIVE)
                .toReceipt(session("res-lab-0001", List.of(HOUND, HIVE)), run(true, false));
    }

    static Path contract(String file) {
        Path p = Path.of("..", "docs", "contracts", "activity-result-v1", file);
        return Files.exists(p) ? p : Path.of("docs", "contracts", "activity-result-v1", file);
    }

    @Test
    void chalkTrailAdapterMapsTrailFactsToBoundedMeasures() {
        ActivityResultReceipt r = receipt();
        assertThat(r.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(r.measures()).containsExactly(Map.entry("chalk_spent", 4L), Map.entry("exit_reached", 1L),
                Map.entry("marks_kept", 3L));
        assertThat(r.activityId()).isEqualTo(ChalkTrailRunAdapter.ACTIVITY_ID);
        assertThat(r.definitionRevision()).isEqualTo(1);
    }

    @Test
    void outcomesFollowTheRun() {
        ChalkTrailRunAdapter a = new ChalkTrailRunAdapter(ActivityMode.AUTHORITATIVE);
        assertThat(a.toReceipt(session("r2", List.of(HOUND)), run(false, false)).outcome()).isEqualTo(ActivityOutcome.FAILED);
        assertThat(a.toReceipt(session("r3", List.of(HOUND)), run(false, true)).outcome()).isEqualTo(ActivityOutcome.ABANDONED);
    }

    @Test
    void canonicalJsonMatchesTheContractExample() throws Exception {
        String expected = Files.readString(contract("example-receipt.json"), StandardCharsets.UTF_8).strip();
        assertThat(receipt().toJson()).isEqualTo(expected);
        assertThat(receipt().digest()).isEqualTo(receipt().digest()).hasSize(64);
    }

    @Test
    void definitionRejectsWrongProfileRoleAndOutOfBoundMeasures() {
        ChalkTrailRunAdapter a = new ChalkTrailRunAdapter(ActivityMode.AUTHORITATIVE);
        ActivityParticipant tree = new ActivityParticipant("life:oak-1", ActivityParticipant.Kind.LIFE, "plant", "scouting");
        ActivityParticipant guard = new ActivityParticipant("life:hound-2", ActivityParticipant.Kind.LIFE, "animal", "guarding");
        assertThatThrownBy(() -> a.toReceipt(session("r4", List.of(tree)), run(true, false)))
                .hasMessageContaining("profile not allowed");
        assertThatThrownBy(() -> a.toReceipt(session("r5", List.of(guard)), run(true, false)))
                .hasMessageContaining("role not allowed");
        assertThatThrownBy(() -> a.definition().checkMeasure("marks_kept", 513)).hasMessageContaining("out of bounds");
        assertThatThrownBy(() -> a.definition().checkMeasure("xp", 1)).hasMessageContaining("unknown measure");
    }

    @Test
    void receiptRejectsDuplicateParticipantsBadKeysAndTooMany() {
        ChalkTrailRunAdapter a = new ChalkTrailRunAdapter(ActivityMode.AUTHORITATIVE);
        assertThatThrownBy(() -> a.toReceipt(session("r6", List.of(HOUND, HOUND)), run(true, false)))
                .hasMessageContaining("duplicate participant");
        assertThatThrownBy(() -> new ActivityParticipant("Bad Id", ActivityParticipant.Kind.LIFE, "animal", "scouting"))
                .isInstanceOf(IllegalArgumentException.class);
        List<ActivityParticipant> five = List.of(HOUND, HIVE,
                new ActivityParticipant("life:a", ActivityParticipant.Kind.LIFE, "bird", "scouting"),
                new ActivityParticipant("life:b", ActivityParticipant.Kind.LIFE, "bird", "scouting"),
                new ActivityParticipant("life:c", ActivityParticipant.Kind.LIFE, "bird", "scouting"));
        assertThatThrownBy(() -> a.toReceipt(session("r7", five), run(true, false))).hasMessageContaining("too many");
        assertThatThrownBy(() -> new ActivityDefinition("x", "y", 0, "z", ActivityMode.DEVICE_LOCAL,
                Set.of("animal"), Set.of("scouting"), Map.of(), 1)).hasMessageContaining("revision");
    }
}
