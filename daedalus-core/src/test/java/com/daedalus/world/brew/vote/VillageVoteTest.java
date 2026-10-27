// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.vote;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;

import com.daedalus.world.brew.vote.VillageVote.Outcome;
import java.util.List;
import org.junit.jupiter.api.Test;

class VillageVoteTest {
    /** Brute force: tally every choice. */
    static int brute(List<Integer> s) {
        for (int c : s) {
            long n = s.stream().filter(x -> x == c).count();
            if (2 * n > s.size()) {
                return c;
            }
        }
        return VillageVote.NONE;
    }

    /** Shells 2, 2, 1, 0, 0, 2, 1: choice 2 leads with 3 of 7, but that is not more than half. */
    static VillageVote noWinner() {
        return new VillageVote(List.of(2, 2, 1, 0, 0, 2, 1));
    }

    /** Shells 1, 0, 1, 0, 1: choice 1 has 3 of 5. */
    static VillageVote winner() {
        return new VillageVote(List.of(1, 0, 1, 0, 1));
    }

    @Test
    void seededVoteIsDeterministic() {
        assertEquals(VillageVote.seeded(7).shells(), VillageVote.seeded(7).shells());
        assertThrows(IllegalArgumentException.class, () -> new VillageVote(List.of()));
        assertThrows(IllegalArgumentException.class, () -> new VillageVote(List.of(-2)));
    }

    @Test
    void majorityMatchesBruteForce() {
        int seen = 0;
        for (long seed = 0; seed < 30; seed++) {
            VillageVote v = VillageVote.seeded(seed);
            assertEquals(brute(v.shells()), v.majority(), "Boyer-Moore == brute force, seed " + seed);
            seen += v.majority() == VillageVote.NONE ? 0 : 1;
        }
        assertEquals(true, seen > 0 && seen < 30, "seeds cover both kinds of vote");
    }

    @Test
    void leadingIsNotWinning() {
        VillageVote v = noWinner();
        assertEquals(VillageVote.NONE, v.majority());
        assertEquals(Outcome.WRONG, v.name("n0", 2));
        assertEquals(String.format(KeeperVoteLines.WRONG, KeeperVoteLines.NO_WINNER), v.talk("t0"));
    }

    @Test
    void wrongEarnsNoCredit() {
        VillageVote v = winner();
        v.open("o");
        assertEquals(Outcome.WRONG, v.name("n1", VillageVote.NONE));
        assertEquals(String.format(KeeperVoteLines.WRONG, String.format(KeeperVoteLines.WINNER, 1)), v.talk("t1"));
        assertEquals("name", v.quest().currentStep().type(), "no credit for a wrong answer");
    }

    @Test
    void guards() {
        VillageVote v = winner();
        assertEquals(Outcome.IGNORED, v.name("", 1));
        assertEquals(Outcome.IGNORED, v.name("e0", -2));
        assertEquals(Outcome.RIGHT, v.name("e1", 1));
        assertEquals(Outcome.DUPLICATE, v.name("e1", 1));
        assertEquals(Outcome.RIGHT, noWinner().name("e2", VillageVote.NONE));
    }

    @Test
    void questWrongThenRightThenKeeper() {
        VillageVote v = winner();
        assertEquals(String.format(KeeperVoteLines.GREETING, 5), v.talk("t0"));
        v.open("o0");
        assertEquals(Outcome.WRONG, v.name("n1", 0));
        assertEquals(Outcome.RIGHT, v.name("n2", 1));
        assertEquals(KeeperVoteLines.THANKS, v.talk("t2"));
        assertNull(v.quest().currentStep());
        assertEquals(KeeperVoteLines.DONE, v.talk("t3"));
    }
}
