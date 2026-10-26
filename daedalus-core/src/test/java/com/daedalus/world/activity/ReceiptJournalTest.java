// SPDX-License-Identifier: MIT
package com.daedalus.world.activity;

import com.daedalus.world.activity.adapters.ActivityRouter;
import com.daedalus.world.activity.adapters.CatchRallyAdapter;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ReceiptJournalTest {

    static String example() throws Exception {
        Path p = Path.of("..", "docs", "contracts", "activity-result-v1", "example-receipt.json");
        if (!Files.exists(p)) p = Path.of("docs", "contracts", "activity-result-v1", "example-receipt.json");
        return Files.readString(p, StandardCharsets.UTF_8).strip();
    }

    static final ActivityParticipant PUP =
            new ActivityParticipant("life:inkpup-2", ActivityParticipant.Kind.LIFE, "animal", "fetching");

    static ActivityResultAdapter.Session session(String id) {
        return new ActivityResultAdapter.Session("sess-" + id, "res-" + id, "contest-host", "verify:" + id,
                List.of(PUP), List.of("evt:" + id), 1_760_872_000_000L);
    }

    static ActivityRouter router() {
        ActivityRouter r = ActivityRouter.contestAll(ActivityMode.AUTHORITATIVE);
        r.setPolicy(new AwardPolicy(CatchRallyAdapter.ACTIVITY_ID, 1, "mastery.play", Map.of("caught", 1L), 40));
        return r;
    }

    @Test
    void canonicalExampleRoundTripsWithTheSameDigest() throws Exception {
        String json = example();
        ActivityResultReceipt r = ReceiptCodec.parse(json);
        assertThat(r.toJson()).isEqualTo(json);
        assertThat(r.activityId()).isEqualTo("labyrinth.chalk-trail");
        assertThat(r.participants()).hasSize(2);
        assertThat(r.measures()).containsEntry("marks_kept", 3L);
    }

    @Test
    void anythingNotCanonicalIsRefused() throws Exception {
        String json = example();
        assertThatThrownBy(() -> ReceiptCodec.parse(json.replace("\"resultId\":", "\"resultId\" :")))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> ReceiptCodec.parse(json + " ")).hasMessageContaining("trailing");
        assertThatThrownBy(() -> ReceiptCodec.parse(json.replace("\"chalk_spent\":4,\"exit_reached\":1",
                "\"exit_reached\":1,\"chalk_spent\":4"))).hasMessageContaining("canonical");
        assertThatThrownBy(() -> ReceiptCodec.parse(json.replace("{\"schema\"", "{\"extra\":1,\"schema\"")))
                .hasMessageContaining("canonical");
        assertThatThrownBy(() -> ReceiptCodec.parse(json.replace("evt:chalk-run-0001", "evt:chalk\\u0041")))
                .hasMessageContaining("escapes");
        assertThatThrownBy(() -> ReceiptCodec.parse(json.replace("activity-result-v1", "activity-result-v2")))
                .hasMessageContaining("schema");
    }

    @Test
    void tamperedJournalLinesAreNamed() throws Exception {
        ActivityResultReceipt r = ReceiptCodec.parse(example());
        String good = ReceiptJournal.line(r);
        assertThat(ReceiptJournal.read(good, 1)).isEqualTo(r);
        String edited = good.replace("\"marks_kept\":3", "\"marks_kept\":9");
        assertThatThrownBy(() -> ReceiptJournal.readAll(List.of(good, "", edited)))
                .isInstanceOf(ReceiptJournal.TamperException.class).hasMessageContaining("line 3")
                .hasMessageContaining("digest mismatch");
        assertThatThrownBy(() -> ReceiptJournal.read("nodigest " + r.toJson(), 4))
                .isInstanceOf(ReceiptJournal.TamperException.class).hasMessageContaining("line 4");
    }

    @Test
    void journalFileAppendsAndReadsBack(@TempDir Path dir) throws Exception {
        Path f = dir.resolve("receipts.jsonl");
        assertThat(ReceiptJournal.read(f)).isEmpty();
        ActivityRouter a = router();
        a.settle(CatchRallyAdapter.ACTIVITY_ID, session("f1"), new CatchRallyAdapter.Rally(5, 4, 3, 5, false));
        a.settle(CatchRallyAdapter.ACTIVITY_ID, session("f2"), new CatchRallyAdapter.Rally(6, 6, 6, 8, false));
        for (String line : a.journal()) ReceiptJournal.append(f, ReceiptJournal.read(line, 1));
        assertThat(ReceiptJournal.read(f)).hasSize(2);
        assertThat(Files.readAllLines(f, StandardCharsets.UTF_8)).isEqualTo(a.journal());
    }

    @Test
    void replayRebuildsProgressionExactlyOnceAndAllOrNothing() {
        ActivityRouter before = router();
        before.settle(CatchRallyAdapter.ACTIVITY_ID, session("r1"), new CatchRallyAdapter.Rally(5, 4, 3, 5, false));
        before.settle(CatchRallyAdapter.ACTIVITY_ID, session("r2"), new CatchRallyAdapter.Rally(9, 7, 4, 8, false));
        before.settle(CatchRallyAdapter.ACTIVITY_ID, session("r2"), new CatchRallyAdapter.Rally(9, 7, 4, 8, false));
        List<String> journal = before.journal();
        assertThat(journal).hasSize(2);

        ActivityRouter after = router();
        assertThat(after.replay(journal)).isEqualTo(2);
        assertThat(after.replay(journal)).isZero();
        assertThat(after.total("life:inkpup-2", "mastery.play"))
                .isEqualTo(before.total("life:inkpup-2", "mastery.play")).isEqualTo(11);

        List<String> tampered = new ArrayList<>(journal);
        tampered.set(1, tampered.get(1).replace("\"caught\":7", "\"caught\":9"));
        ActivityRouter fresh = router();
        assertThatThrownBy(() -> fresh.replay(tampered)).isInstanceOf(ReceiptJournal.TamperException.class);
        assertThat(fresh.total("life:inkpup-2", "mastery.play")).isZero();
        assertThat(fresh.journal()).isEmpty();
    }

    @Test
    void creditRefusesAConflictingDigestAndAForeignRevision() {
        ActivityRouter r = router();
        r.settle(CatchRallyAdapter.ACTIVITY_ID, session("c1"), new CatchRallyAdapter.Rally(5, 4, 3, 5, false));
        ActivityResultReceipt other = r.receipt(CatchRallyAdapter.ACTIVITY_ID, session("c1"),
                new CatchRallyAdapter.Rally(5, 5, 5, 6, false));
        assertThatThrownBy(() -> r.credit(other)).isInstanceOf(ProgressionLedger.ConflictException.class);
        ActivityResultReceipt preview = r.receipt(CatchRallyAdapter.ACTIVITY_ID, session("c2"),
                new CatchRallyAdapter.Rally(1, 1, 1, 1, false));
        ActivityResultReceipt rev2 = new ActivityResultReceipt(preview.resultId(), preview.sessionId(),
                preview.activityId(), 2, preview.mode(), preview.issuer(), preview.verificationRef(), preview.outcome(),
                preview.participants(), preview.measures(), preview.sourceEventRefs(), preview.clockBoundaryMs());
        assertThatThrownBy(() -> r.credit(rev2)).hasMessageContaining("revision 2");
    }
}
