// SPDX-License-Identifier: MIT

package com.daedalus.model;

import org.junit.jupiter.api.Test;

import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Session ownership and the join allowlist (ADR-012). The interceptor lives in the
 * server module; the decision it asks is here, so a core-only {@code mvn test} has
 * to pin it — the same hole {@link LeaderboardEntryOrderingTest} exists to close.
 */
class GameSessionTest {

    private static GameSession owned() {
        return new GameSession(UUID.randomUUID(), "Alice", new Point(0, 0), "alice");
    }

    @Test
    void unownedSessionsAdmitAnyone() {
        GameSession s = new GameSession(UUID.randomUUID(), "anon", new Point(0, 0));
        assertThat(s.maySubscribe(null)).isTrue();
        assertThat(s.maySubscribe("mallory")).isTrue();
    }

    @Test
    void anOwnedSessionAdmitsTheOwnerAndRefusesEveryoneElse() {
        GameSession s = owned();
        assertThat(s.maySubscribe("alice")).isTrue();
        assertThat(s.maySubscribe("mallory")).isFalse();
        assertThat(s.maySubscribe(null)).isFalse();
    }

    @Test
    void joiningWithASubjectGrantsSubscribe() {
        GameSession s = owned();
        assertThat(s.join("Bob", new Point(0, 0), "bob")).isTrue();
        assertThat(s.maySubscribe("bob")).isTrue();
        assertThat(s.maySubscribe("mallory")).isFalse();
    }

    @Test
    void anAnonymousJoinPutsAPieceOnTheBoardWithoutGrantingTheFeed() {
        GameSession s = owned();
        assertThat(s.join("Bob", new Point(0, 0))).isTrue();
        assertThat(s.players()).containsKey("Bob");
        assertThat(s.maySubscribe("bob")).isFalse();
    }

    @Test
    void rejoiningDoesNotTeleportAndDoesNotHandTheSeatToADifferentSubject() {
        GameSession s = owned();
        s.join("Bob", new Point(0, 0), "bob");
        s.move("Bob", new Point(1, 0));

        assertThat(s.join("Bob", new Point(0, 0), "mallory")).isTrue();
        assertThat(s.playerPosition("Bob")).isEqualTo(new Point(1, 0));
        assertThat(s.maySubscribe("bob")).isTrue();
        assertThat(s.maySubscribe("mallory")).isFalse();
    }

    @Test
    void aFullSessionRefusesANewNameAndStillAcceptsARejoin() {
        GameSession s = owned();
        for (int i = 1; i < GameSession.MAX_PLAYERS; i++) {
            assertThat(s.join("p" + i, new Point(0, 0), "s" + i)).isTrue();
        }
        assertThat(s.players()).hasSize(GameSession.MAX_PLAYERS);
        assertThat(s.join("overflow", new Point(0, 0), "overflow")).isFalse();
        assertThat(s.players()).doesNotContainKey("overflow");
        assertThat(s.maySubscribe("overflow")).isFalse();

        assertThat(s.join("p1", new Point(0, 0), "impostor")).isTrue();
        assertThat(s.maySubscribe("s1")).isTrue();
        assertThat(s.maySubscribe("impostor")).isFalse();
    }

    @Test
    void aJoinersHopsAreRecordedAndAreNotGhostMaterial() {
        GameSession s = owned();
        s.join("Bob", new Point(0, 0), "bob");
        s.move("Alice", new Point(0, 1));
        s.move("Bob", new Point(1, 0));
        s.move("Bob", new Point(1, 1));

        assertThat(s.trail()).extracting(GameSession.TimedMove::to)
                .containsExactly(new Point(0, 1));
        assertThat(s.walks()).containsOnlyKeys("Alice", "Bob");
        assertThat(s.walks().get("Bob")).extracting(GameSession.TimedMove::to)
                .containsExactly(new Point(1, 0), new Point(1, 1));
        assertThat(s.walks().get("Alice")).isEqualTo(s.trail());
    }
}
