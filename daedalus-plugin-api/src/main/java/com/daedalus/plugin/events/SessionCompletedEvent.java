// SPDX-License-Identifier: MIT

package com.daedalus.plugin.events;

import com.daedalus.model.GameSession;

/**
 * Fired when a session's opening player reaches the goal. Carries the completed session so
 * listeners can read what they need — score for leaderboards, the timed {@code trail()} for
 * ghost runs (ADR-006 idea #8) — without the publisher guessing every consumer's shape.
 * The session is completed and effectively frozen by the time this fires.
 */
public class SessionCompletedEvent extends PluginEvent {

    private final GameSession session;

    public SessionCompletedEvent(Object source, GameSession session) {
        super(source);
        this.session = session;
    }

    public GameSession session() { return session; }
}
