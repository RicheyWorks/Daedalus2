// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.lockers;

import com.daedalus.world.odds.OddsRng;
import java.util.Locale;

/**
 * Quest q_salvage_lockers: the wreck's brass compass is in one of {@link #LOCKERS} sealed lockers, a fresh wall each
 * round for {@link #ROUNDS} rounds. You pick locker 0; then {@link #OPENED} others are opened, by the Keeper (who knows)
 * or by the blind deckhand (even odds each round). In the first {@link #TOLD_ROUNDS} rounds you are told who opened;
 * after that you are not. Find the compass {@link #GOAL} times. No wagering.
 */
public final class LockerQuest {

    public static final int LOCKERS = 4;
    public static final int OPENED = 2;
    public static final int ROUNDS = 5;
    public static final int TOLD_ROUNDS = 2;
    public static final int GOAL = 3;
    public static final double KEEPER_PRIOR = 0.5;

    /** Quest stages. */
    public enum Stage { READY, OFFER, FOUND_ENOUGH, CAME_UP_SHORT }

    private final LockerOdds odds = new LockerOdds(LOCKERS, OPENED);
    private final OddsRng rng;
    private Stage stage = Stage.READY;
    private int round;
    private int found;
    private int voids;
    private LockerRound current;
    private LockerRound.Opener opener;
    private LockerRound.Outcome last;

    public LockerQuest(long seed) {
        this.rng = new OddsRng(seed);
    }

    public Stage stage() {
        return stage;
    }

    /** Rounds dealt so far. */
    public int round() {
        return round;
    }

    public int found() {
        return found;
    }

    public int voids() {
        return voids;
    }

    /** Outcome of the last finished round, or null. */
    public LockerRound.Outcome last() {
        return last;
    }

    /** Whether you are told who opened in the current round. */
    public boolean told() {
        return round <= TOLD_ROUNDS;
    }

    /** Who opened this round; only when told. */
    public LockerRound.Opener opener() {
        if (stage != Stage.OFFER || !told()) {
            throw new IllegalStateException("you were not told who opened");
        }
        return opener;
    }

    /** Deals the next round; returns false when the deckhand showed the compass (round void). */
    public boolean deal() {
        if (stage != Stage.READY) {
            throw new IllegalStateException("cannot deal now: " + stage);
        }
        round++;
        opener = rng.chance(KEEPER_PRIOR) ? LockerRound.Opener.KEEPER : LockerRound.Opener.DECKHAND;
        current = LockerRound.deal(odds, 0, opener, rng);
        if (current.voided()) {
            voids++;
            finishRound(LockerRound.Outcome.VOID);
            return false;
        }
        stage = Stage.OFFER;
        return true;
    }

    /** Exact chance of finding the compass if you switch now. */
    public double chanceIfSwitch() {
        requireOffer();
        if (!told()) {
            return odds.switchUntold(KEEPER_PRIOR);
        }
        return opener == LockerRound.Opener.KEEPER ? odds.switchKeeper() : odds.switchBlind();
    }

    /** Exact chance of finding the compass if you stay now. */
    public double chanceIfStay() {
        requireOffer();
        if (!told()) {
            return odds.stayUntold(KEEPER_PRIOR);
        }
        return opener == LockerRound.Opener.KEEPER ? odds.stayKeeper() : odds.stayBlind();
    }

    /** Stay or switch; returns the round outcome. */
    public LockerRound.Outcome decide(boolean switchPick) {
        requireOffer();
        LockerRound.Outcome o = current.resolve(switchPick, rng);
        if (o == LockerRound.Outcome.FOUND) {
            found++;
        }
        finishRound(o);
        return o;
    }

    private void finishRound(LockerRound.Outcome o) {
        last = o;
        current = null;
        if (round >= ROUNDS) {
            stage = found >= GOAL ? Stage.FOUND_ENOUGH : Stage.CAME_UP_SHORT;
        } else {
            stage = Stage.READY;
        }
    }

    private void requireOffer() {
        if (stage != Stage.OFFER) {
            throw new IllegalStateException("no offer on the table: " + stage);
        }
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        return switch (stage) {
            case READY -> String.format(Locale.ROOT, "Round %d of %d, %d compasses so far. Pick locker one.",
                    round + 1, ROUNDS, found);
            case OFFER -> String.format(Locale.ROOT, "%s Stay: %.0f%%. Switch: %.0f%%.",
                    !told() ? "You didn't see who opened them."
                            : opener == LockerRound.Opener.KEEPER ? "I opened those, and I know where it is."
                            : "The deckhand pried those blind.",
                    chanceIfStay() * 100, chanceIfSwitch() * 100);
            case FOUND_ENOUGH -> String.format(Locale.ROOT, "%d compasses in %d rounds. The arks can steer.", found,
                    ROUNDS);
            case CAME_UP_SHORT -> String.format(Locale.ROOT, "%d compasses in %d rounds, %d broken open. Not enough.",
                    found, ROUNDS, voids);
        };
    }
}
