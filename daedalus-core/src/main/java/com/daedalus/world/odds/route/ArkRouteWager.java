// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.route;

import com.daedalus.world.odds.BalanceLimits;
import com.daedalus.world.odds.OddsRng;
import com.daedalus.world.odds.weather.Sky;
import java.util.List;
import java.util.Locale;
import java.util.Objects;

/**
 * Quest q_ark_route_wager: the Odds Keeper chalks the {@link RouteOddsBoard} for the ark routes out of the belt, the
 * player stakes storm herbs on the route they think brings the most life home, and one real voyage (a fresh stream,
 * not a board trial) settles it. Herbs are in-game only; there is no real-money wagering.
 */
public final class ArkRouteWager {

    /** Keeper's house edge on the route board (clamped by {@link RouteOddsBoard#clampEdge}). */
    public static final double EDGE = 0.05;

    /** Quest stages, in order. */
    public enum Stage { ODDS_POSTED, STAKED, BACKED_WINNER, BACKED_LOSER }

    /** The three charted routes out of the asteroid belt above OddsReaper Island. */
    public static final List<ArkRoute> ODDSREAPER_ROUTES = List.of(
            new ArkRoute("Shard Narrows", List.of(
                    new RouteLeg("Shard Gate", Hazard.DEBRIS, 0.30),
                    new RouteLeg("Splinter Run", Hazard.DEBRIS, 0.20)), 120),
            new ArkRoute("Squall Lanes", List.of(
                    new RouteLeg("Glassfall", Hazard.SQUALL, 0.35),
                    new RouteLeg("Thunder Shelf", Hazard.SQUALL, 0.30),
                    new RouteLeg("Herb Reach", Hazard.DRIFT, 0.20)), 120),
            new ArkRoute("Long Drift", List.of(
                    new RouteLeg("Still Water", Hazard.DRIFT, 0.40),
                    new RouteLeg("Doldrum Ring", Hazard.DRIFT, 0.40),
                    new RouteLeg("Pale Sea", Hazard.DRIFT, 0.40),
                    new RouteLeg("Last Ember", Hazard.DEBRIS, 0.10)), 120));

    private final RouteOddsBoard board;
    private Stage stage;
    private int backed = -1;
    private int stake;
    private int winner = -1;

    public ArkRouteWager(List<ArkRoute> routes, Sky sky, long seed, int trials) {
        this.board = RouteOddsBoard.simulate(routes, sky, seed, trials);
        this.stage = Stage.ODDS_POSTED;
    }

    public RouteOddsBoard board() {
        return board;
    }

    public Stage stage() {
        return stage;
    }

    public int backed() {
        return backed;
    }

    /** Index of the route that won the real voyage, or -1 before sailing. */
    public int winner() {
        return winner;
    }

    /** Whether the board meets {@code limits} (the Keeper refuses to take bets on a lock). */
    public boolean postable(BalanceLimits limits) {
        return board.postable(limits);
    }

    /** Stakes {@code herbs} storm herbs on route {@code route}. */
    public void stake(int route, int herbs) {
        if (stage != Stage.ODDS_POSTED) {
            throw new IllegalStateException("already staked: " + stage);
        }
        Objects.checkIndex(route, board.routes().size());
        if (herbs < 1) {
            throw new IllegalArgumentException("stake must be >= 1 herb: " + herbs);
        }
        if (board.postedOdds(route, EDGE) == 0.0) {
            throw new IllegalArgumentException("route is off the board: " + board.routes().get(route).name());
        }
        this.backed = route;
        this.stake = herbs;
        this.stage = Stage.STAKED;
    }

    /**
     * Sails the real race once and settles the wager.
     *
     * @return storm herbs paid back (stake times posted odds, rounded down) or 0 on a loss
     */
    public int sail(long voyageSeed) {
        if (stage != Stage.STAKED) {
            throw new IllegalStateException("nothing staked: " + stage);
        }
        winner = RouteOddsBoard.race(board.routes(), board.sky(), new OddsRng(voyageSeed), null, null);
        if (winner == backed) {
            stage = Stage.BACKED_WINNER;
            return (int) Math.floor(stake * board.postedOdds(backed, EDGE));
        }
        stage = Stage.BACKED_LOSER;
        return 0;
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        return switch (stage) {
            case ODDS_POSTED -> String.format(Locale.ROOT,
                    "Chalk favours %s at %.0f%% to bring the most life home. The belt does not care who is aboard.",
                    board.routes().get(board.favourite()).name(), board.bestChance(board.favourite()) * 100);
            case STAKED -> "Herbs on the ledger. Ring the ark bell and let the belt decide.";
            case BACKED_WINNER -> "Your route brought the most souls home. That is what the arks were for.";
            case BACKED_LOSER -> String.format(Locale.ROOT,
                    "%s brought more life home this time. Read the glass before the next launch.",
                    board.routes().get(winner).name());
        };
    }
}
