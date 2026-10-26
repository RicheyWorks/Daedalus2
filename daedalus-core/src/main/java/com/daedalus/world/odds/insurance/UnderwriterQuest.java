// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.insurance;

import com.daedalus.world.odds.OddsRng;
import com.daedalus.world.odds.route.ArkRoute;
import com.daedalus.world.odds.route.ArkRouteWager;
import com.daedalus.world.odds.weather.Sky;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Quest q_ark_underwriter: the Odds Keeper asks the player to cover a season's arks. The player sets the premium
 * loading; the Keeper checks the season board. Fair to the survivors means loading at most {@link #FAIR_LOADING};
 * safe for the pool means simulated insolvency at most {@link #MAX_INSOLVENCY}. If both hold the season sails once:
 * SOLVENT or BUST. Herbs are in-game only.
 */
public final class UnderwriterQuest {

    public static final int RESERVE = 80;
    public static final double COVER_PER_SOUL = 1.0;
    public static final double FAIR_LOADING = 0.25;
    public static final double MAX_INSOLVENCY = 0.05;
    public static final int BOARD_TRIALS = 2_000;

    /** Quest stages. */
    public enum Stage { QUOTING, REJECTED, APPROVED, SOLVENT, BUST }

    private final Sky sky;
    private final long seed;
    private Stage stage = Stage.QUOTING;
    private UnderwritingPool pool;
    private UnderwritingPool.Board board;
    private double close;
    private String reason = "";

    public UnderwriterQuest(Sky sky, long seed) {
        this.sky = sky;
        this.seed = seed;
    }

    /** The season fleet: two arks on each of the three OddsReaper belt routes. */
    public static List<ArkPolicy> fleet(Sky sky) {
        List<ArkPolicy> out = new ArrayList<>();
        for (ArkRoute r : ArkRouteWager.ODDSREAPER_ROUTES) {
            out.add(new ArkPolicy(r, sky, COVER_PER_SOUL));
            out.add(new ArkPolicy(r, sky, COVER_PER_SOUL));
        }
        return out;
    }

    public Stage stage() {
        return stage;
    }

    public UnderwritingPool.Board board() {
        return board;
    }

    /** Closing pool balance after the real season. */
    public double close() {
        return close;
    }

    /** Proposes a loading; the Keeper approves or rejects it. */
    public Stage quote(double loading) {
        if (stage != Stage.QUOTING && stage != Stage.REJECTED) {
            throw new IllegalStateException("season already approved: " + stage);
        }
        pool = new UnderwritingPool(RESERVE, fleet(sky), loading);
        board = pool.simulate(seed, BOARD_TRIALS);
        if (loading > FAIR_LOADING) {
            reason = "too dear";
            stage = Stage.REJECTED;
        } else if (board.insolvency() > MAX_INSOLVENCY) {
            reason = "too thin";
            stage = Stage.REJECTED;
        } else {
            stage = Stage.APPROVED;
        }
        return stage;
    }

    /** Sails the real season once on a fresh stream. */
    public Stage sail(long seasonSeed) {
        if (stage != Stage.APPROVED) {
            throw new IllegalStateException("no approved quote: " + stage);
        }
        close = pool.season(new OddsRng(seasonSeed));
        stage = close >= 0 ? Stage.SOLVENT : Stage.BUST;
        return stage;
    }

    /** The Keeper's line for the current stage. */
    public String keeperLine() {
        return switch (stage) {
            case QUOTING -> "Six arks, one season. Price the cover fair to them and safe for us.";
            case REJECTED -> "too dear".equals(reason)
                    ? "Survivors cannot pay that. Bring the loading down."
                    : String.format(Locale.ROOT, "%.0f%% of seasons break the pool. Price it thicker.",
                            board.insolvency() * 100);
            case APPROVED -> String.format(Locale.ROOT,
                    "Approved: %.1f%% bust risk, about %.0f herbs expected profit. Ring the bell.",
                    board.insolvency() * 100, board.meanProfit());
            case SOLVENT -> String.format(Locale.ROOT,
                    "Season closed with %.0f herbs in the pool. Every lost soul's family was paid.", close);
            case BUST -> "The pool broke. The arks paid for it once already; never again.";
        };
    }
}
