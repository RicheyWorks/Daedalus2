// SPDX-License-Identifier: MIT
package com.daedalus.server.service;

import org.junit.jupiter.api.Test;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import static org.assertj.core.api.Assertions.*;

class PresenceServiceTest {
    private final AtomicLong clock = new AtomicLong(1000);
    private final List<PresenceService.Frame> events = new ArrayList<>();
    private final PresenceService service = new PresenceService(clock::get, events::add);
    private PresenceService.Report report(String name) {
        return new PresenceService.Report(name, 1.0, 2.0, 3.0, null, null, null);
    }

    @Test void snapshotsCannotBeChangedAfterValidationOrPublication() {
        var look = new HashMap<>(Map.of("skin", "#AaBBcc", "hat", "wizard"));
        var input = new PresenceService.Report("Alice", 1.0, 2.0, 3.0, 4 * Math.PI, "walk", look);
        look.put("hat", "forged");
        assertThatThrownBy(() -> input.look().clear()).isInstanceOf(UnsupportedOperationException.class);
        var result = service.report("world-zero", "p-1", input);
        assertThat(result.ok()).isTrue();
        assertThat(result.player().look()).containsEntry("hat", "wizard").containsEntry("skin", "#aabbcc");
        assertThat(result.player().yaw()).isZero();
        assertThat(result.player().anim()).isEqualTo(PresenceService.Anim.WALK);
        assertThat(events.getFirst().player()).isEqualTo(result.player());
        assertThatThrownBy(() -> result.player().look().clear()).isInstanceOf(UnsupportedOperationException.class);
        var directLook = new HashMap<>(Map.of("hat", "cap"));
        var direct = new PresenceService.Player("p", "name", 0, 0, 0, 0, PresenceService.Anim.IDLE, directLook, 0);
        directLook.clear();
        assertThat(direct.look()).containsEntry("hat", "cap");
    }

    @Test void invalidReportsNeverReplaceOrPublishAValidPlayer() {
        var initial = service.report("w", "p", report("Alice")).player();
        var invalid = new ArrayList<PresenceService.Report>();
        invalid.add(null);
        invalid.add(new PresenceService.Report("x", null, 0.0, 0.0, null, null, null));
        invalid.add(new PresenceService.Report("x", 0.0, null, 0.0, null, null, null));
        invalid.add(new PresenceService.Report("x", 0.0, 0.0, null, null, null, null));
        for (int axis = 0; axis < 4; axis++) {
            Double[] values = {0.0, 0.0, 0.0, 0.0};
            values[axis] = Double.NaN;
            invalid.add(new PresenceService.Report("x", values[0], values[1], values[2], values[3], null, null));
        }
        for (int axis = 0; axis < 3; axis++) {
            Double[] values = {0.0, 0.0, 0.0};
            values[axis] = PresenceService.MAX_COORD + 1;
            invalid.add(new PresenceService.Report("x", values[0], values[1], values[2], null, null, null));
        }
        invalid.add(new PresenceService.Report("x", 0.0, 0.0, 0.0, null, "unknown", null));
        var nullValue = new HashMap<String, String>(); nullValue.put("hat", null);
        var nullKey = new HashMap<String, String>(); nullKey.put(null, "cap");
        for (var look : List.of(Map.of("bogus", "x"), Map.of("skin", "red"), nullValue, nullKey)) {
            invalid.add(new PresenceService.Report("x", 0.0, 0.0, 0.0, null, null, look));
        }
        for (var input : invalid) {
            var result = service.report("w", "p", input);
            assertThat(result.ok()).isFalse();
            assertThat(result.refused()).isNotBlank();
            assertThat(result.player()).isNull();
            assertThat(service.who("w")).containsExactly(initial);
        }
        assertThat(events).hasSize(1);
    }

    @Test void expiryBoundaryAndRepeatedLeavePublishExactlyOnce() {
        assertThat(service.who("missing")).isEmpty();
        assertThat(service.leave("missing", "p")).isFalse();
        service.report("w", "first", report("first"));
        clock.addAndGet(1);
        service.report("w", "second", report("second"));
        clock.set(1000 + PresenceService.STALE_MS);
        assertThat(service.sweep("w")).isZero();
        clock.incrementAndGet();
        assertThat(service.sweep("w")).isEqualTo(1);
        assertThat(service.who("w")).extracting(PresenceService.Player::id).containsExactly("second");
        assertThat(service.leave("w", "first")).isFalse();
        assertThat(service.leave("w", "second")).isTrue();
        assertThat(service.leave("w", "second")).isFalse();
        assertThat(events).extracting(PresenceService.Frame::kind).containsExactly(
                PresenceService.Kind.MOVE, PresenceService.Kind.MOVE, PresenceService.Kind.LEAVE, PresenceService.Kind.LEAVE);
    }

    @Test void fullWorldAllowsExistingPlayerUpdatesAndReusesExpiredCapacity() {
        for (int i = 0; i < PresenceService.MAX_PER_WORLD; i++) assertThat(service.report("w", "p" + i, report("p")).ok()).isTrue();
        assertThat(service.report("w", "new", report("new")).ok()).isFalse();
        assertThat(service.report("w", "p0", report("updated")).ok()).isTrue();
        assertThat(service.who("w").getFirst().name()).isEqualTo("updated");
        assertThat(service.report("other", "new", report("new")).ok()).isTrue();
        clock.addAndGet(PresenceService.STALE_MS + 1);
        assertThat(service.report("w", "new", report("new")).ok()).isTrue();
        assertThat(service.who("w")).hasSize(1);
    }

    @Test void displayNamesAndIdentityAreStableAndDoNotExposeSubjects() {
        assertThat(PresenceService.playerId("alice@example.test", "tab-a"))
                .matches("p-[0-9a-f]{12}").doesNotContain("alice")
                .isEqualTo(PresenceService.playerId("alice@example.test", "tab-a"))
                .isNotEqualTo(PresenceService.playerId("alice@example.test", "tab-b"));
        assertThat(PresenceService.playerId(null, null)).isEqualTo(PresenceService.playerId(" ", ""));
        assertThat(PresenceService.cleanName(null)).isEqualTo("guest");
        assertThat(PresenceService.cleanName(" <>&\"'`\n ")).isEqualTo("guest");
        assertThat(PresenceService.cleanName("  Alice\t<admin>  ")).isEqualTo("Aliceadmin");
        assertThat(PresenceService.cleanName("🙂".repeat(30))).isEqualTo("🙂".repeat(24));
    }

    @Test void animationParsingIsIndependentOfServerLocale() {
        Locale old = Locale.getDefault();
        try {
            Locale.setDefault(Locale.forLanguageTag("tr-TR"));
            assertThat(service.report("w", "p", new PresenceService.Report("p", 0.0, 0.0, 0.0, null, " swim ", null))
                    .player().anim()).isEqualTo(PresenceService.Anim.SWIM);
        } finally { Locale.setDefault(old); }
    }
}
