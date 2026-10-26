// SPDX-License-Identifier: MIT

package com.daedalus.world.colony;

import static com.daedalus.world.colony.QuestProgress.Result.CAPACITY_REACHED;
import static com.daedalus.world.colony.QuestProgress.Result.COMPLETED;
import static com.daedalus.world.colony.QuestProgress.Result.DUPLICATE;
import static com.daedalus.world.colony.QuestProgress.Result.IGNORED;
import static com.daedalus.world.colony.QuestProgress.Result.PROGRESSED;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.colony.QuestProgress.Step;
import java.util.Collections;
import java.util.List;
import org.junit.jupiter.api.Test;

/** The same cases as engines/unreal/core-test/portal_quest_core_test.cpp (PORT09), so Java and C++ agree. */
class QuestProgressTest {

    @Test
    void rescueQuestMatchesTheCppCore() {
        QuestProgress rescue = new QuestProgress(List.of(new Step("talk", "king", 1), new Step("rescue", "traveller", 2), new Step("talk", "king", 1)));
        assertFalse(rescue.claimReward());
        assertEquals(IGNORED, rescue.apply("early", "rescue", "traveller"));
        assertEquals(PROGRESSED, rescue.apply("a", "talk", "king"));
        assertEquals(DUPLICATE, rescue.apply("a", "rescue", "traveller"));
        assertEquals(PROGRESSED, rescue.apply("b", "rescue", "traveller"));
        assertEquals(1, rescue.stepCount());
        assertEquals(PROGRESSED, rescue.apply("c", "rescue", "traveller", 4294967295L));
        assertTrue(rescue.stepIndex() == 2 && rescue.stepCount() == 0);
        assertEquals(COMPLETED, rescue.apply("d", "talk", "king"));
        assertTrue(rescue.claimReward());
        assertFalse(rescue.claimReward());
        assertEquals(IGNORED, rescue.apply("e", "talk", "king"));
    }

    @Test
    void eventIdsAndAmountsAreValidated() {
        QuestProgress unicorn = new QuestProgress(List.of(new Step("guide", "herd", 1)));
        assertEquals(IGNORED, unicorn.apply("", "guide", "herd"));
        assertEquals(IGNORED, unicorn.apply("x", "guide", "herd", 0));
        assertEquals(IGNORED, unicorn.apply("x".repeat(129), "guide", "herd"));
        assertEquals(COMPLETED, unicorn.apply("x", "guide", "herd"));
    }

    @Test
    void processedIdsAreBoundedAndNeverEvicted() {
        QuestProgress bounded = new QuestProgress(List.of(new Step("collect", "supplies", 513)));
        for (int i = 0; i < 512; i++) {
            assertEquals(PROGRESSED, bounded.apply(Integer.toString(i), "collect", "supplies"));
        }
        assertEquals(CAPACITY_REACHED, bounded.apply("overflow", "collect", "supplies"));
        assertTrue(bounded.stepCount() == 512 && !bounded.complete());
        assertEquals(DUPLICATE, bounded.apply("0", "collect", "supplies"));
    }

    @Test
    void invalidConfigsAreRejectedWithAReason() {
        List<List<Step>> bad = List.of(List.of(), List.of(new Step("", "king", 1)), List.of(new Step("talk", "", 1)),
                List.of(new Step("talk", "king", 0)), Collections.nCopies(33, new Step("talk", "king", 1)),
                List.of(new Step("talk", "king", 1), new Step("rescue", "traveller", 0)));
        for (List<Step> config : bad) {
            QuestProgress q = new QuestProgress(config);
            assertTrue(!q.valid() && !q.why().isEmpty());
            assertEquals(IGNORED, q.apply("a", "talk", "king"));
            assertFalse(q.complete());
            assertFalse(q.claimReward());
        }
        assertFalse(new QuestProgress(null).valid());
    }
}
