// SPDX-License-Identifier: MIT
package com.daedalus.world.activity;

import com.daedalus.world.labyrinth.ChalkTrail;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ProgressionLedgerTest {

    static final String TRACK = "mastery.scouting";
    static final AwardPolicy POLICY = new AwardPolicy(ChalkTrailRunAdapter.ACTIVITY_ID, 1, TRACK,
            Map.of("marks_kept", 2L, "exit_reached", 10L), 50);

    @Test
    void creditsEachParticipantExactlyOnceAndRetryReturnsEarlierAward() {
        ProgressionLedger ledger = new ProgressionLedger();
        ActivityResultReceipt r = ActivityResultReceiptTest.receipt();
        List<ProgressionLedger.Award> first = ledger.credit(r, POLICY);
        assertThat(first).hasSize(2).allSatisfy(a -> assertThat(a.points()).isEqualTo(16)); // 3*2 + 1*10
        List<ProgressionLedger.Award> again = ledger.credit(ActivityResultReceiptTest.receipt(), POLICY);
        assertThat(again).isEqualTo(first);
        assertThat(ledger.total("life:mossback-hound-07", TRACK)).isEqualTo(16);
        assertThat(ledger.history("colony:emberbee-hive-2")).hasSize(1);
    }

    @Test
    void newPolicyRevisionDoesNotPayTheSameEventAgain() {
        ProgressionLedger ledger = new ProgressionLedger();
        ledger.credit(ActivityResultReceiptTest.receipt(), POLICY);
        AwardPolicy rev2 = new AwardPolicy(ChalkTrailRunAdapter.ACTIVITY_ID, 2, TRACK, Map.of("marks_kept", 100L), 500);
        List<ProgressionLedger.Award> out = ledger.credit(ActivityResultReceiptTest.receipt(), rev2);
        assertThat(out).allSatisfy(a -> assertThat(a.policyRevision()).isEqualTo(1));
        assertThat(ledger.total("life:mossback-hound-07", TRACK)).isEqualTo(16);
    }

    @Test
    void conflictingPayloadForSameResultIdFailsAndChangesNothing() {
        ProgressionLedger ledger = new ProgressionLedger();
        ledger.credit(ActivityResultReceiptTest.receipt(), POLICY);
        ChalkTrail t = new ChalkTrail(10, 32);
        t.mark(new ChalkTrail.Point(5, 5));
        ActivityResultReceipt forged = new ChalkTrailRunAdapter(ActivityMode.AUTHORITATIVE).toReceipt(
                ActivityResultReceiptTest.session("res-lab-0001", List.of(ActivityResultReceiptTest.HOUND)),
                new ChalkTrailRunAdapter.Run(t, 10, true, false));
        assertThatThrownBy(() -> ledger.credit(forged, POLICY)).isInstanceOf(ProgressionLedger.ConflictException.class);
        assertThat(ledger.total("life:mossback-hound-07", TRACK)).isEqualTo(16);
    }

    @Test
    void capInactivePolicyLocalModeAndAbandonmentPayNothingButAreRecorded() {
        ProgressionLedger ledger = new ProgressionLedger();
        AwardPolicy capped = new AwardPolicy(ChalkTrailRunAdapter.ACTIVITY_ID, 1, TRACK, Map.of("chalk_spent", 100L), 25);
        assertThat(capped.points(ActivityResultReceiptTest.receipt())).isEqualTo(25);

        AwardPolicy inactive = AwardPolicy.inactive(ChalkTrailRunAdapter.ACTIVITY_ID, TRACK);
        assertThat(ledger.credit(ActivityResultReceiptTest.receipt(), inactive))
                .allSatisfy(a -> assertThat(a.points()).isZero());
        assertThat(ledger.history("life:mossback-hound-07")).hasSize(1);

        ActivityResultReceipt local = new ChalkTrailRunAdapter(ActivityMode.DEVICE_LOCAL).toReceipt(
                ActivityResultReceiptTest.session("res-local-1", List.of(ActivityResultReceiptTest.HOUND)),
                ActivityResultReceiptTest.run(true, false));
        assertThat(POLICY.points(local)).isZero();

        ActivityResultReceipt quit = new ChalkTrailRunAdapter(ActivityMode.AUTHORITATIVE).toReceipt(
                ActivityResultReceiptTest.session("res-quit-1", List.of(ActivityResultReceiptTest.HOUND)),
                ActivityResultReceiptTest.run(false, true));
        assertThat(POLICY.points(quit)).isZero();
    }

    @Test
    void separateRunsAccumulateAndPolicyMustMatchActivity() {
        ProgressionLedger ledger = new ProgressionLedger();
        ChalkTrailRunAdapter a = new ChalkTrailRunAdapter(ActivityMode.AUTHORITATIVE);
        ledger.credit(a.toReceipt(ActivityResultReceiptTest.session("run-1", List.of(ActivityResultReceiptTest.HOUND)),
                ActivityResultReceiptTest.run(true, false)), POLICY);
        List<ProgressionLedger.Award> second = ledger.credit(a.toReceipt(
                ActivityResultReceiptTest.session("run-2", List.of(ActivityResultReceiptTest.HOUND)),
                ActivityResultReceiptTest.run(false, false)), POLICY);
        assertThat(second.get(0).before()).isEqualTo(16);
        assertThat(second.get(0).after()).isEqualTo(22); // failed run: 3 marks * 2
        AwardPolicy other = new AwardPolicy("labyrinth.echo-bell", 1, TRACK, Map.of(), 10);
        assertThatThrownBy(() -> ledger.credit(ActivityResultReceiptTest.receipt(), other))
                .hasMessageContaining("policy is for");
    }
}
