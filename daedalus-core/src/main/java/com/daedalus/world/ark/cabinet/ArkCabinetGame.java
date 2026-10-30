// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.cabinet;

import java.util.List;

/**
 * One playable turn game on the Ark Games Cabinet. An adapter keeps the live position and delegates every rule and
 * every solver call to an already-merged ark piece; it never re-implements the game. Players are 1 and 2, moves are
 * short text tokens so a keyboard, a script or an in-world UI can drive the same game.
 */
public interface ArkCabinetGame {

    /** Stable slot id, for example {@code "chalk"}. */
    String id();

    /** Menu title. */
    String title();

    /** One or two lines telling the player how to move and how to win. */
    String rules();

    /** Moves the player to move may make now, as an unmodifiable list; empty when the game is over. */
    List<String> legalMoves();

    /**
     * Plays one move for the player to move.
     *
     * @return true when the move was legal and played; false (and no change) otherwise
     */
    boolean play(String move);

    /** Player to move (1 or 2), or 0 when the game is over. */
    int toMove();

    /** True when the game has ended. */
    boolean over();

    /** Winning player (1 or 2), or 0 for a draw or a game still running. */
    int winner();

    /** Text picture of the position for a terminal or an in-world sign. */
    String render();

    /** The cabinet's suggested move from the wrapped piece's solver, or an empty string when the game is over. */
    String hint();
}
