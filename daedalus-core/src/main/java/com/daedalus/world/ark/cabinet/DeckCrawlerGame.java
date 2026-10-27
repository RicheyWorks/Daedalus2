// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import com.daedalus.world.ark.DeckCrawler;
import java.util.List;

/**
 * Cabinet adapter for G409 The Deck Crawler (Langton's ant and turmites): a watch-the-crab toy rather than a contest.
 * Moves step the crab forward ({@code 1}, {@code 10} or {@code 100}) or undo one step ({@code back}); the show ends
 * when the step budget is used or the crab would walk off the deck. Finishing counts as a win for player 1.
 */
public final class DeckCrawlerGame implements ArkCabinetGame {

    private static final List<String> MOVES = List.of("1", "10", "100", "back");

    private final DeckCrawler crab;
    private final int side;
    private final long budget;
    private boolean fell;

    /** Langton's ant on a 21 x 21 deck for 300 steps. */
    public DeckCrawlerGame() {
        this("RL", 21, 300);
    }

    /** Any L/R rule on a side x side deck with a step budget. */
    public DeckCrawlerGame(String rule, int side, long budget) {
        this.crab = new DeckCrawler(rule, side);
        this.side = side;
        this.budget = budget;
    }

    @Override
    public String id() {
        return "crawler";
    }

    @Override
    public String title() {
        return "The Deck Crawler";
    }

    @Override
    public String rules() {
        return "Type 1, 10 or 100 to let the crab walk, or back to undo a step. Watch the pattern it paints.";
    }

    @Override
    public List<String> legalMoves() {
        return over() ? List.of() : MOVES;
    }

    @Override
    public boolean play(String move) {
        if (over() || move == null || !MOVES.contains(move.trim())) {
            return false;
        }
        String t = move.trim();
        if ("back".equals(t)) {
            if (crab.steps() == 0) {
                return false;
            }
            crab.back();
            return true;
        }
        long n = Math.min(Long.parseLong(t), budget - crab.steps());
        for (long i = 0; i < n; i++) {
            try {
                crab.step();
            } catch (IllegalStateException e) {
                fell = true;
                break;
            }
        }
        return true;
    }

    /** Steps walked. */
    public long steps() {
        return crab.steps();
    }

    /** Planks painted. */
    public int painted() {
        return crab.painted();
    }

    @Override
    public int toMove() {
        return over() ? 0 : 1;
    }

    @Override
    public boolean over() {
        return fell || crab.steps() >= budget;
    }

    @Override
    public int winner() {
        return over() ? 1 : 0;
    }

    @Override
    public String render() {
        StringBuilder sb = new StringBuilder();
        String palette = ".#o+*x%@=-~:;!?&";
        for (int y = 0; y < side; y++) {
            for (int x = 0; x < side; x++) {
                if (x == crab.x() && y == crab.y()) {
                    sb.append("^>v<".charAt(crab.dir()));
                } else {
                    sb.append(palette.charAt(crab.colour(x, y)));
                }
            }
            sb.append('\n');
        }
        return sb.append("steps ").append(crab.steps()).append(", painted ").append(crab.painted()).append('\n')
            .toString();
    }

    @Override
    public String hint() {
        return over() ? "" : "10";
    }
}
