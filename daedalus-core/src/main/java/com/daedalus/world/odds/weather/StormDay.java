// SPDX-License-Identifier: MIT

package com.daedalus.world.odds.weather;

import com.daedalus.world.fishing.AnglerSkill;
import com.daedalus.world.fishing.Conditions;
import com.daedalus.world.fishing.FishTable;
import com.daedalus.world.odds.parlay.ParlayBoard;
import com.daedalus.world.odds.parlay.ParlayTicket;
import java.util.List;

/**
 * Glue from the weather to the games: an island day's sky becomes G07 fishing {@link Conditions} and the G18 Storm
 * Parlay board for that day. Island day 0 starts CALM on OddsReaper Island.
 */
public final class StormDay {

    private StormDay() {
    }

    /** Fishing conditions at {@code hour} on a day with sky {@code sky}: only a full STORM counts as a storm. */
    public static Conditions conditions(Sky sky, int hour) {
        return Conditions.atHour(hour, sky == Sky.STORM);
    }

    /** OddsReaper Island's sky on {@code day}. */
    public static Sky sky(long islandSeed, int day) {
        return StormChain.ODDSREAPER.skyOn(islandSeed, Sky.CALM, day);
    }

    /** The Odds Keeper's board for {@code day}, priced for that day's real sky at the morning rise (08:00). */
    public static List<ParlayTicket> board(FishTable table, long islandSeed, int day, int tickets, int maxLegs) {
        return ParlayBoard.daily(table, islandSeed, day, conditions(sky(islandSeed, day), 8), AnglerSkill.STEADY,
                tickets, maxLegs);
    }
}
