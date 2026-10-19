// SPDX-License-Identifier: MIT

package com.daedalus.world.activity.learned;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

import org.junit.jupiter.api.Test;

/** Exactly-once crediting: duplicate, replay, retry, and a different subject. */
class ActivityResultReceiptTest {

    @Test
    void issueCreditsOnceAndRefusesASecondDelivery() {
        ActivityCreditLedger ledger = new ActivityCreditLedger();
        ActivityResult result = learned("duneback", "cast-windmere-7");

        ActivityResultReceipt first = ActivityResultReceipt.issue(ledger, result);

        assertThat(first.receiptId()).isEqualTo(ActivityResultReceipt.idOf(result));
        assertThat(first.result()).isEqualTo(result);
        assertThat(ledger.size()).isEqualTo(1);
        assertThat(ledger.find("prismheart.pond-fishing", "cast-windmere-7", "duneback")).contains(first);
        assertThatThrownBy(() -> ActivityResultReceipt.issue(ledger, result))
                .isInstanceOf(ActivityCreditException.class)
                .hasMessageContaining("duplicate credit for prismheart.pond-fishing cast-windmere-7 duneback")
                .satisfies(error -> {
                    ActivityCreditException ex = (ActivityCreditException) error;
                    assertThat(ex.reason()).isEqualTo(ActivityCreditException.Reason.DUPLICATE);
                    assertThat(ex.prior()).isEqualTo(first);
                });
        assertThat(ledger.size()).isEqualTo(1);
    }

    @Test
    void aReplayOfTheSameBytesIsTheSameReceipt() {
        ActivityCreditLedger ledger = new ActivityCreditLedger();
        ActivityResult result = learned("duneback", "cast-windmere-7");
        ActivityResultReceipt first = ledger.credit(result);
        ActivityResult replay = ActivityResult.parse(result.serialize());

        assertThat(replay).isEqualTo(result).isNotSameAs(result);
        assertThatThrownBy(() -> ledger.credit(replay))
                .isInstanceOf(ActivityCreditException.class)
                .satisfies(error -> assertThat(((ActivityCreditException) error).reason())
                        .isEqualTo(ActivityCreditException.Reason.DUPLICATE));
        assertThat(ActivityResultReceipt.idOf(replay)).isEqualTo(first.receiptId());
    }

    @Test
    void aRetryThatChangesTheOutcomeDoesNotReplaceTheCredit() {
        ActivityCreditLedger ledger = new ActivityCreditLedger();
        ActivityResult caught = learned("duneback", "cast-windmere-7");
        ActivityResultReceipt first = ledger.credit(caught);
        ActivityResult retry = new ActivityResult(
                ActivityResult.VERSION, caught.activityId(), caught.attemptId(), caught.subjectId(),
                ActivityResult.SubjectKind.CREATURE, ActivityResult.Outcome.MISSED, "reedling",
                Map.of("finish", "got-away"));

        assertThatThrownBy(() -> ledger.credit(retry))
                .isInstanceOf(ActivityCreditException.class)
                .satisfies(error -> {
                    ActivityCreditException ex = (ActivityCreditException) error;
                    assertThat(ex.reason()).isEqualTo(ActivityCreditException.Reason.CONFLICT);
                    assertThat(ex.prior()).isEqualTo(first);
                });
        assertThat(ledger.size()).isEqualTo(1);
        assertThat(ledger.find(caught.activityId(), caught.attemptId(), caught.subjectId())).contains(first);

        ActivityResult otherKind = new ActivityResult(
                ActivityResult.VERSION, caught.activityId(), caught.attemptId(), caught.subjectId(),
                ActivityResult.SubjectKind.PLANT, caught.outcome(), caught.learned(), caught.detail());
        assertThatThrownBy(() -> ledger.credit(otherKind))
                .satisfies(error -> assertThat(((ActivityCreditException) error).reason())
                        .isEqualTo(ActivityCreditException.Reason.CONFLICT));
    }

    @Test
    void aDifferentSubjectAttemptOrActivityIsItsOwnCredit() {
        ActivityCreditLedger ledger = new ActivityCreditLedger();
        ActivityResult mount = learned("duneback", "cast-windmere-7");
        ActivityResult plant = new ActivityResult(
                ActivityResult.VERSION, mount.activityId(), mount.attemptId(), "sunroot",
                ActivityResult.SubjectKind.PLANT, ActivityResult.Outcome.LEARNED, "reedling", mount.detail());
        ActivityResult nextCast = learned("duneback", "cast-windmere-8");
        ActivityResult otherGame = new ActivityResult(
                ActivityResult.VERSION, "other.game", mount.attemptId(), mount.subjectId(),
                mount.subjectKind(), mount.outcome(), mount.learned(), Map.of());

        ActivityResultReceipt a = ledger.credit(mount);
        ActivityResultReceipt b = ledger.credit(plant);
        ActivityResultReceipt c = ledger.credit(nextCast);
        ActivityResultReceipt d = ledger.credit(otherGame);

        assertThat(ledger.size()).isEqualTo(4);
        assertThat(a.receiptId()).isNotEqualTo(b.receiptId()).isNotEqualTo(c.receiptId()).isNotEqualTo(d.receiptId());
        assertThat(ledger.find(mount.activityId(), mount.attemptId(), "sunroot")).contains(b);
        assertThat(ledger.find(mount.activityId(), mount.attemptId(), "missing")).isEmpty();
    }

    @Test
    void theReceiptIdDoesNotDependOnWhichLedgerIssuedIt() {
        ActivityResult result = learned("duneback", "cast-windmere-7");
        ActivityCreditLedger one = new ActivityCreditLedger();
        ActivityCreditLedger two = new ActivityCreditLedger();

        ActivityResultReceipt left = one.credit(result);
        ActivityResultReceipt right = two.credit(result);
        ActivityResult replay = ActivityResult.parse(result.serialize());
        assertThat(left.receiptId()).isEqualTo(right.receiptId()).isEqualTo(ActivityResultReceipt.idOf(replay));
        assertThat(left).isEqualTo(right);
        assertThat(left.result()).isEqualTo(replay);
    }

    @Test
    void rememberRestoresTheGuardAndRefusesAConflictingReload() {
        ActivityResult caught = learned("duneback", "cast-windmere-7");
        ActivityResult missed = new ActivityResult(
                ActivityResult.VERSION, caught.activityId(), caught.attemptId(), caught.subjectId(),
                caught.subjectKind(), ActivityResult.Outcome.FAILED, "ripple-scattered",
                Map.of("finish", "too-soon"));
        ActivityResultReceipt kept = new ActivityCreditLedger().credit(caught);
        ActivityResultReceipt rival = new ActivityCreditLedger().credit(missed);

        ActivityCreditLedger restarted = new ActivityCreditLedger();
        restarted.remember(kept);
        restarted.remember(kept);
        assertThat(restarted.size()).isEqualTo(1);
        assertThatThrownBy(() -> restarted.credit(caught))
                .satisfies(error -> assertThat(((ActivityCreditException) error).reason())
                        .isEqualTo(ActivityCreditException.Reason.DUPLICATE));
        assertThatThrownBy(() -> restarted.remember(rival))
                .satisfies(error -> assertThat(((ActivityCreditException) error).reason())
                        .isEqualTo(ActivityCreditException.Reason.CONFLICT));
        assertThat(restarted.find(caught.activityId(), caught.attemptId(), caught.subjectId())).contains(kept);
    }

    @Test
    void aReceiptIdMustMatchTheEnvelope() {
        ActivityResult result = learned("duneback", "cast-windmere-7");
        assertThatThrownBy(() -> new ActivityResultReceipt("0".repeat(64), result))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("receipt id does not match");
        assertThatThrownBy(() -> ActivityResultReceipt.issue(null, result)).isInstanceOf(NullPointerException.class);
        assertThatThrownBy(() -> new ActivityCreditLedger().credit(null)).isInstanceOf(NullPointerException.class);
        assertThatThrownBy(() -> new ActivityCreditLedger().remember(null)).isInstanceOf(NullPointerException.class);
        assertThatThrownBy(() -> new ActivityCreditLedger().find("NOPE", "try-1", "sunroot"))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("bad activityId");
    }

    @Test
    void twoDeliveriesAtOnceCreditOnce() throws Exception {
        ActivityCreditLedger ledger = new ActivityCreditLedger();
        ActivityResult result = learned("duneback", "cast-windmere-7");
        CountDownLatch start = new CountDownLatch(1);
        AtomicReference<ActivityResultReceipt> won = new AtomicReference<>();
        AtomicInteger duplicates = new AtomicInteger();
        AtomicReference<Throwable> failure = new AtomicReference<>();
        Runnable job = () -> {
            try {
                start.await();
                ActivityResultReceipt receipt = ledger.credit(result);
                won.compareAndSet(null, receipt);
            } catch (ActivityCreditException ex) {
                if (ex.reason() == ActivityCreditException.Reason.DUPLICATE) {
                    duplicates.incrementAndGet();
                } else {
                    failure.set(ex);
                }
            } catch (Exception ex) {
                failure.set(ex);
            }
        };
        Thread a = new Thread(job);
        Thread b = new Thread(job);
        a.start();
        b.start();
        start.countDown();
        a.join(5000);
        b.join(5000);

        assertThat(failure.get()).isNull();
        assertThat(a.isAlive()).isFalse();
        assertThat(b.isAlive()).isFalse();
        assertThat(ledger.size()).isEqualTo(1);
        assertThat(duplicates).hasValue(1);
        assertThat(won.get().receiptId()).isEqualTo(ActivityResultReceipt.idOf(result));
    }

    private static ActivityResult learned(String subject, String attempt) {
        ActivityResult.SubjectKind kind = "sunroot".equals(subject)
                ? ActivityResult.SubjectKind.PLANT
                : ActivityResult.SubjectKind.CREATURE;
        return new ActivityResult(
                ActivityResult.VERSION, "prismheart.pond-fishing", attempt, subject, kind,
                ActivityResult.Outcome.LEARNED, "reedling",
                Map.of("effect", "heal 20 HP", "finish", "caught", "rarity", "COMMON", "species", "Reedling"));
    }
}
