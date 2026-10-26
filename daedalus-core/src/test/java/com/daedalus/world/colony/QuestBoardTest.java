// SPDX-License-Identifier: MIT

package com.daedalus.world.colony;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashSet;
import java.util.List;
import org.junit.jupiter.api.Test;

/** Day-book requests bound to PORT09 quest progress, end to end on a real fixture island (PORTAL deed 7). */
class QuestBoardTest {
    static final Cast.QuestDef KINGS_ROAD = new Cast.QuestDef("Portal_KingsRoad", "King",
            List.of("Speak to royal steward", "Locate stranded caravan", "Escort survivors home", "Report to the king"),
            "Proposed royal favour and realm equipment");

    @Test
    void stepsAreDeliverThenTheStoryInOrder() {
        var s = QuestBoard.stepsOf(KINGS_ROAD);
        assertEquals(5, s.size());
        assertEquals(new QuestProgress.Step("deliver", "King", 1), s.get(0));
        assertEquals(new QuestProgress.Step("story", "Portal_KingsRoad#4", 1), s.get(4));
    }

    @Test
    void fillingTheKingsRequestOpensAndAdvancesHisQuestExactlyOnce() {
        Cast cast = new Cast(List.of("King"), List.of(KINGS_ROAD));
        QuestBoard board = new QuestBoard(cast);
        PlotState plot = new PlotState();
        DayBook.Request king = new DayBook.Request("King", List.of("gold"), "crystal", "Portal_KingsRoad");

        assertEquals(QuestBoard.Fill.MISSING_ITEMS, board.fill("daybook:7:3:King", king, plot).fill());
        plot.add("gold", 2);
        var r = board.fill("daybook:7:3:King", king, plot);
        assertEquals(QuestBoard.Fill.FILLED, r.fill());
        assertEquals(QuestProgress.Result.PROGRESSED, r.quest());
        assertEquals(1.0, plot.count("gold"));
        assertEquals(1.0, plot.count("crystal"));
        assertEquals(QuestBoard.Fill.DUPLICATE, board.fill("daybook:7:3:King", king, plot).fill());
        assertEquals(1.0, plot.count("gold"), "a duplicate fill moves nothing");

        QuestProgress q = board.open().get("Portal_KingsRoad");
        assertEquals(1, q.stepIndex());
        assertEquals(QuestProgress.Result.IGNORED, board.story("s3", "Portal_KingsRoad", 3), "story beats stay in order");
        for (int n = 1; n <= 3; n++) {
            assertEquals(QuestProgress.Result.PROGRESSED, board.story("s" + n + "x", "Portal_KingsRoad", n));
        }
        assertEquals(QuestProgress.Result.COMPLETED, board.story("s4", "Portal_KingsRoad", 4));
        assertTrue(q.claimReward());
        assertFalse(q.claimReward());
    }

    @Test
    void requestsWithoutAQuestStillTradeButOpenNothing() {
        QuestBoard board = new QuestBoard(Cast.NONE);
        PlotState plot = new PlotState();
        plot.add("plank", 1);
        var r = board.fill("e1", new DayBook.Request("Carpenter", List.of("plank"), "iron", null), plot);
        assertEquals(QuestBoard.Fill.FILLED, r.fill());
        assertNull(r.quest());
        assertTrue(board.open().isEmpty());
        assertEquals(QuestBoard.Fill.IGNORED, board.fill("", new DayBook.Request("Carpenter", List.of("plank"), "iron", null), plot).fill());
    }

    @Test
    void realFixtureIslandCarriesTheKingsQuestToCompletion() throws Exception {
        String[] caseRow = Fixture.rows("CASE").stream().filter(c -> c[1].equals("PORTAL") && c[2].equals("7")).findFirst().orElseThrow();
        IslandFacts island = new IslandFacts(7, Fixture.list(caseRow[3]), caseRow[4].equals("1"), Fixture.list(caseRow[5]),
                new HashSet<>(Fixture.list(caseRow[6])), caseRow[7], Fixture.list(caseRow[8]));
        Cast cast = new Cast(Fixture.list(caseRow[9]), List.of(KINGS_ROAD));
        PlotState plot = new PlotState();
        QuestBoard board = new QuestBoard(cast);
        DayBook.Request king = null;
        int day = 0;
        for (int d = 1; d <= 30 && king == null; d++) {
            for (DayBook.Request r : DayBook.today(island, plot, cast, d, 8, DayBook.Ecology.DEFAULT).requests()) {
                if ("Portal_KingsRoad".equals(r.questId())) {
                    king = r;
                    day = d;
                }
            }
        }
        assertNotNull(king, "the King posts a request within 30 days");
        king.wants().forEach(w -> plot.add(w, 1));
        assertEquals(QuestBoard.Fill.FILLED, board.fill("daybook:7:" + day + ":King", king, plot).fill());
        for (int n = 1; n <= 4; n++) {
            board.story("beat" + n, "Portal_KingsRoad", n);
        }
        assertTrue(board.open().get("Portal_KingsRoad").complete());
    }
}
