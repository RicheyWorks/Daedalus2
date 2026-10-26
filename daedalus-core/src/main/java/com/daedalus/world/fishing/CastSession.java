// SPDX-License-Identifier: MIT

package com.daedalus.world.fishing;

import com.daedalus.world.odds.OddsRng;
import java.util.Optional;

/**
 * One cast of the line, as a deterministic state machine a host ticks: WAIT for a bite, then a BITE that lasts the fish's
 * window, then DONE with an {@link Outcome}. The rules are the Prismheart demo's ({@code castLine}/{@code fishTick}): the
 * wait is {@value #MIN_WAIT} + u * {@value #WAIT_SPREAD} seconds; striking during the wait scatters the ripple
 * (TOO_SOON); striking during the bite lands the fish (CAUGHT); a bite left past its window GOT_AWAY; reeling in ends it
 * empty-handed. All randomness comes from the Combat Odds Engine's {@link OddsRng} stream for (seed, cast), so a replay
 * of the same seed hooks the same fish at the same moment.
 */
public final class CastSession {

    /** Where the cast is. */
    public enum Phase { WAIT, BITE, DONE }

    /** How the cast ended; NONE until it is DONE. */
    public enum Outcome { NONE, TOO_SOON, GOT_AWAY, CAUGHT, REELED_IN }

    public static final double MIN_WAIT = 1.2;
    public static final double WAIT_SPREAD = 2.4;

    private final FishTable table;
    private final Conditions conditions;
    private final double waitSeconds;
    private final double pickDraw;
    private Phase phase = Phase.WAIT;
    private Outcome outcome = Outcome.NONE;
    private double t;
    private FishSpecies fish;

    /** Cast number {@code cast} of a run seeded {@code seed}. */
    public CastSession(FishTable table, Conditions conditions, long seed, long cast) {
        if (table == null || conditions == null) {
            throw new IllegalArgumentException("a cast needs a fish table and conditions");
        }
        this.table = table;
        this.conditions = conditions;
        OddsRng rng = OddsRng.forTrial(seed, cast);
        this.waitSeconds = (MIN_WAIT + rng.nextDouble() * WAIT_SPREAD) * conditions.waitFactor();
        this.pickDraw = rng.nextDouble();
    }

    /** Lets {@code dt} seconds pass. */
    public void tick(double dt) {
        if (!(dt >= 0) || Double.isInfinite(dt)) {
            throw new IllegalArgumentException("tick needs a finite dt >= 0, got " + dt);
        }
        if (phase == Phase.DONE) {
            return;
        }
        t += dt;
        if (phase == Phase.WAIT) {
            if (t >= waitSeconds) {
                fish = table.pick(pickDraw, conditions);
                phase = Phase.BITE;
                t = 0;
            }
        } else if (t > conditions.window(fish)) {
            finish(Outcome.GOT_AWAY);
        }
    }

    /** The angler strikes (A). Returns the outcome; striking after the cast is over changes nothing. */
    public Outcome strike() {
        if (phase == Phase.WAIT) {
            finish(Outcome.TOO_SOON);
        } else if (phase == Phase.BITE) {
            finish(Outcome.CAUGHT);
        }
        return outcome;
    }

    /** The angler reels in (B). Ends a cast that is still running with nothing. */
    public Outcome reelIn() {
        if (phase != Phase.DONE) {
            finish(Outcome.REELED_IN);
        }
        return outcome;
    }

    private void finish(Outcome o) {
        outcome = o;
        phase = Phase.DONE;
        t = 0;
    }

    public Phase phase() {
        return phase;
    }

    public Outcome outcome() {
        return outcome;
    }

    /** The fish that bit, once one has. */
    public Optional<FishSpecies> fish() {
        return Optional.ofNullable(fish);
    }

    /** Seconds from the cast to the bite. */
    public double waitSeconds() {
        return waitSeconds;
    }

    /** Seconds left to strike during a bite; 0 otherwise. */
    public double biteRemaining() {
        return phase == Phase.BITE ? Math.max(0, conditions.window(fish) - t) : 0;
    }

    public Conditions conditions() {
        return conditions;
    }
}
