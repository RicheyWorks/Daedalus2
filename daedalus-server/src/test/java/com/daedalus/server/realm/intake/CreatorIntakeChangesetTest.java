// SPDX-License-Identifier: MIT
package com.daedalus.server.realm.intake;

import static com.daedalus.server.realm.CreatorRealmScaffold.*;
import static com.daedalus.server.realm.intake.CreatorIntakeChangeset.*;
import static org.assertj.core.api.Assertions.*;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class CreatorIntakeChangesetTest {
    private static final String ID = "deathhimself_changeset_asset";
    private static final String ORIGINAL = "deathhimself_changeset_original";
    private static final String VARIANT = "deathhimself_changeset_variant";
    private static final String BYTES = "SYNTHETIC changeset original; no creator art.\n";
    private static final Attribution CREATOR = new Attribution("synthetic-fixture", Basis.SYNTHETIC, null, null);
    @TempDir Path tmp;

    private CreatorIntakeHostSession session(Set<String> reserved) throws IOException {
        Path root = tmp.resolve("intake");
        try (var ignored = CreatorIntakeStore.create(root, Set.of())) { }
        return CreatorIntakeHostSession.open(root,
                new CreatorIntakeHostSession.HostReservations("synthetic-host", "synthetic-snapshot", reserved));
    }
    private Path inputs() throws IOException {
        Path inputs = Files.createDirectory(tmp.resolve("inputs"));
        Files.writeString(inputs.resolve("synthetic.txt"), BYTES, StandardCharsets.US_ASCII);
        return inputs;
    }
    private static Request request(String id, CreatorIntakeHostSession session, List<Operation> operations) throws IOException {
        var base = session.current();
        return new Request(1, id, base.revision(), base.sha256(), session.binding(), operations);
    }
    private static String originalHash() throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(BYTES.getBytes(StandardCharsets.US_ASCII)));
    }

    @Test void orderedBatchUsesFrozenOriginalsAndExactCompletedRetryDoesNotApplyAgain() throws Exception {
        Path inputs = inputs(), receipts = tmp.resolve("receipts");
        try (var session = session(Set.of())) {
            Request request = request("synthetic-complete", session, List.of(
                    new Add("add", ID, Role.ASSET, CREATOR, null),
                    new Attach("attach", ID, ORIGINAL, "synthetic.txt", "Synthetic ASCII input", true),
                    new Edit("edit", ID, new CreatorIntakeStore.DraftEdit("Synthetic item", "No creator concept", ORIGINAL,
                            CREATOR, SaleIntent.UNSET, List.of())),
                    new Finalize("finalize", ID),
                    new Revise("revise", VARIANT, ID, CREATOR),
                    new Idea("idea", VARIANT, "Synthetic new iteration brief")));
            Outcome result = apply(session, request, inputs, receipts, (index, snapshot) -> {
                if (index == 0) Files.writeString(inputs.resolve("synthetic.txt"), "Changed after frozen capture", StandardCharsets.US_ASCII);
            });
            assertThat(result.status()).isEqualTo(Status.COMPLETE);
            assertThat(result.replayed()).isFalse();
            assertThat(result.steps()).hasSize(6).allSatisfy(step -> assertThat(step.status()).isEqualTo(StepStatus.APPLIED));
            assertThat(result.base().revision()).isEqualTo(1);
            assertThat(result.end().revision()).isEqualTo(7);
            var current = session.current();
            assertThat(current.manifest().entries().getFirst().stage()).isEqualTo(Stage.FINAL);
            assertThat(current.manifest().entries().get(1).supersedesId()).isEqualTo(ID);
            assertThat(current.manifest().entries().get(1).ideas()).hasSize(1);
            assertThat(Files.readString(tmp.resolve("intake/originals").resolve(originalHash()))).isEqualTo(BYTES);
            Outcome replay = apply(session, request, inputs, receipts);
            assertThat(replay.replayed()).isTrue();
            assertThat(replay.status()).isEqualTo(Status.COMPLETE);
            assertThat(replay.steps()).isEqualTo(result.steps());
            assertThat(session.current()).isEqualTo(current);
            Request conflict = new Request(1, request.operationId(), request.expectedRevision(), request.expectedSha256(), request.host(),
                    List.of(new Idea("changed-command", VARIANT, "Different request must not reuse the receipt")));
            assertThatThrownBy(() -> apply(session, conflict, inputs, receipts)).isInstanceOf(IOException.class);
            Request stale = new Request(1, "synthetic-stale", request.expectedRevision(), request.expectedSha256(), request.host(),
                    List.of(new Idea("stale", VARIANT, "Must not apply against old base")));
            assertThatThrownBy(() -> apply(session, stale, inputs, tmp.resolve("stale-receipt"))).isInstanceOf(IOException.class);
            assertThat(Files.exists(tmp.resolve("stale-receipt"))).isFalse();
            assertThat(session.current()).isEqualTo(current);
        }
    }

    @Test void laterHostCollisionStopsAtActualPrefixAndNeverRunsFollowingOperation() throws Exception {
        Path inputs = inputs(), receipts = tmp.resolve("receipts");
        String collision = "deathhimself_host_reserved";
        try (var session = session(Set.of(collision))) {
            byte[] prefix = Files.readAllBytes(tmp.resolve("intake/snapshots/00000001.json"));
            Request request = request("synthetic-partial", session, List.of(
                    new Add("add", ID, Role.ASSET, CREATOR, null),
                    new Attach("attach", ID, ORIGINAL, "synthetic.txt", "Synthetic ASCII input", true),
                    new Add("collision", collision, Role.IDEA, CREATOR, null),
                    new Idea("unexecuted", ID, "Must never be appended after refusal")));
            Outcome result = apply(session, request, inputs, receipts);
            assertThat(result.status()).isEqualTo(Status.PARTIAL);
            assertThat(result.end().revision()).isEqualTo(3);
            assertThat(result.steps()).extracting(StepResult::status)
                    .containsExactly(StepStatus.APPLIED, StepStatus.APPLIED, StepStatus.REFUSED);
            assertThat(result.uncertainStepIndex()).isNull();
            assertThat(result.nextUnexecutedIndex()).isEqualTo(3);
            var current = session.current();
            assertThat(current.manifest().entries()).hasSize(1);
            assertThat(current.manifest().entries().getFirst().ideas()).isEmpty();
            assertThat(Files.readAllBytes(tmp.resolve("intake/snapshots/00000001.json"))).isEqualTo(prefix);
            assertThat(Files.readString(tmp.resolve("intake/originals").resolve(originalHash()))).isEqualTo(BYTES);
            assertThatThrownBy(() -> apply(session, request, inputs, receipts)).isInstanceOf(IOException.class);
            assertThat(session.current()).isEqualTo(current);
        }
    }

    @Test void committedStepWithoutDurableResultIsUncertainAndCannotReplay() throws Exception {
        Path inputs = inputs(), receipts = tmp.resolve("receipts");
        try (var session = session(Set.of())) {
            Request request = request("synthetic-uncertain", session, List.of(
                    new Add("commit-then-fail", ID, Role.IDEA, CREATOR, null),
                    new Idea("unexecuted", ID, "Must not execute after the uncertain boundary")));
            Outcome result = apply(session, request, inputs, receipts, (index, snapshot) -> {
                if (index == 0) throw new IOException("Synthetic failure after commit before result persistence");
            });
            assertThat(result.status()).isEqualTo(Status.UNCERTAIN);
            assertThat(result.uncertainStepIndex()).isZero();
            assertThat(result.nextUnexecutedIndex()).isEqualTo(1);
            assertThat(result.steps()).hasSize(1);
            assertThat(result.steps().getFirst().status()).isEqualTo(StepStatus.UNCERTAIN);
            var current = session.current();
            assertThat(current.revision()).isEqualTo(2);
            assertThat(current.manifest().entries().getFirst().ideas()).isEmpty();
            Path evidence = Path.of(result.receiptDirectory().toString());
            assertThat(Files.exists(evidence.resolve("request.json"))).isTrue();
            assertThat(Files.exists(evidence.resolve("0001-intent.json"))).isTrue();
            assertThat(Files.exists(evidence.resolve("0001-result.json"))).isFalse();
            assertThatThrownBy(() -> apply(session, request, inputs, receipts)).isInstanceOf(IOException.class);
            assertThat(session.current()).isEqualTo(current);
            assertThat(session.history()).hasSize(2);
        }
    }
}
