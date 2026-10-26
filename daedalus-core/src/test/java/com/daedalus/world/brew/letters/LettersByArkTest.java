// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.letters;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.daedalus.world.brew.BrewBench;
import com.daedalus.world.brew.cellar.Preserve;
import com.daedalus.world.brew.cellar.Preserve.Method;
import com.daedalus.world.brew.cellar.RootCellar;
import com.daedalus.world.brew.supper.Guest;
import com.daedalus.world.colony.PlotState;
import com.daedalus.world.odds.insurance.ArkPolicy;
import com.daedalus.world.odds.weather.Sky;
import java.util.List;
import org.junit.jupiter.api.Test;

class LettersByArkTest {
    final PlotState plot = new PlotState();

    /** Puts one jar of this item in the cellar, kept this way, and returns its id. */
    static int jar(RootCellar c, PlotState plot, String item, Method m, String ev) {
        plot.add(item, 1);
        Preserve.cost(m).forEach((k, v) -> plot.add(k, v));
        assertEquals(RootCellar.Outcome.STORED, c.preserve(ev, item, m, plot));
        return c.jars().get(c.jars().size() - 1).id();
    }

    @Test
    void farIslandsRoutesAndUnderwriterQuotes() {
        LettersByArk x = new LettersByArk(new RootCellar(1, 50), Destination.island(), Sky.SQUALL, 3);
        assertEquals(List.of("kelp_harbour", "cinder_reach", "glass_shoals", "far_orchard"),
                x.destinations().stream().map(Destination::id).toList());
        assertEquals(List.of(3, 6, 9, 12), x.destinations().stream().map(d -> x.voyageDays(d.id())).toList());
        var guests = Guest.island().stream().map(Guest::id).toList();
        for (Destination d : x.destinations()) {
            assertTrue(guests.contains(d.friendOf()), d.friendOf() + " sits at the G85 supper");
            assertEquals(new ArkPolicy(d.route(), Sky.SQUALL, LettersByArk.COVER_PER_CRATE)
                    .premium(LettersByArk.LOADING), x.quote(d.id()));
            assertTrue(x.quote(d.id()) >= 1);
        }
        assertTrue(x.quote("far_orchard") > x.quote("kelp_harbour"), "longer, rougher runs cost more cover");
        LettersByArk storm = new LettersByArk(new RootCellar(1, 50), Destination.island(), Sky.STORM, 3);
        LettersByArk calm = new LettersByArk(new RootCellar(1, 50), Destination.island(), Sky.CALM, 3);
        assertTrue(storm.quote("cinder_reach") > calm.quote("cinder_reach"), "squalls price with the sky");
        assertEquals(0, x.quote("nowhere"));
        assertEquals(0, x.voyageDays("nowhere"));
    }

    @Test
    void shipGuardsAndSealedJarsLeaveWithoutSoaking() {
        RootCellar c = new RootCellar(2, 50);
        LettersByArk x = new LettersByArk(c, Destination.island(), Sky.SQUALL, 5);
        assertEquals(ReplyLines.GREETING, x.talk("t0"));
        int salted = jar(c, plot, "fish", Method.SALT, "j1");
        assertEquals(LettersByArk.Outcome.NO_JAR, x.ship("s0", 99, "kelp_harbour", false, plot));
        assertEquals(LettersByArk.Outcome.UNKNOWN_DESTINATION, x.ship("s1", salted, "nowhere", false, plot));
        assertEquals(LettersByArk.Outcome.NO_SALT, x.ship("s2", salted, "kelp_harbour", true, plot));
        assertEquals(LettersByArk.Outcome.IGNORED, x.ship("", salted, "kelp_harbour", false, plot));
        assertEquals(LettersByArk.Outcome.IGNORED, x.ship("s3", salted, "kelp_harbour", false, null));
        assertEquals(0, plot.count(BrewBench.WATER));
        assertEquals(LettersByArk.Outcome.SHIPPED, x.ship("s4", salted, "kelp_harbour", false, plot));
        assertEquals(LettersByArk.Outcome.DUPLICATE, x.ship("s4", salted, "kelp_harbour", false, plot));
        assertTrue(c.jars().isEmpty());
        assertEquals(0, plot.count("fish"), "a sealed jar goes out unopened, nothing into the store");
        assertEquals(1, x.afloat().size());
        assertNull(c.dispatch("again", salted));
        assertEquals(String.format(ReplyLines.SHIP, 3, "s"), x.talk("t1"));
    }

    @Test
    void shelfLifeMustBeatTheVoyage() {
        RootCellar c = new RootCellar(4, 50);
        LettersByArk x = new LettersByArk(c, Destination.island(), Sky.SQUALL, 8);
        int fresh = jar(c, plot, "fish", Method.FRESH, "f");
        int salted = jar(c, plot, "fish", Method.SALT, "s");
        int bacon = jar(c, plot, "Bacon", Method.SALT, "b");
        x.ship("p1", fresh, "kelp_harbour", false, plot);
        x.ship("p2", salted, "kelp_harbour", false, plot);
        x.ship("p3", bacon, "kelp_harbour", false, plot);
        for (LettersByArk.Parcel p : x.afloat()) {
            assertEquals(p.sent() + 3 + p.strikes() * LettersByArk.DELAY_PER_STRIKE, p.arrives());
        }
        LettersByArk.Parcel freshP = x.afloat().get(0);
        assertFalse(freshP.arrivesGood(), "fresh fish keeps 2 days, the run takes 3");
        List<LettersByArk.Arrival> all = new java.util.ArrayList<>();
        while (!x.afloat().isEmpty()) {
            all.addAll(x.nextDay(plot));
        }
        assertEquals(3, all.size());
        var byItem = all.stream().collect(java.util.stream.Collectors.groupingBy(a -> a.parcel().method()));
        assertEquals(LettersByArk.SPOILED, byItem.get(Method.FRESH).get(0).regard());
        int saltedFish = all.stream().filter(a -> a.parcel().id() == 2).findFirst().orElseThrow().regard();
        int saltedBacon = all.stream().filter(a -> a.parcel().id() == 3).findFirst().orElseThrow().regard();
        assertEquals(LettersByArk.GOOD + LettersByArk.FAVOURITE, saltedFish, "Nell loves fish");
        assertEquals(LettersByArk.GOOD, saltedBacon);
        assertEquals(LettersByArk.SPOILED + LettersByArk.GOOD + LettersByArk.FAVOURITE + LettersByArk.GOOD,
                x.regard("kelp_harbour"));
        assertEquals(3, x.landed().size());
    }

    @Test
    void coverIsPaidInSaltAndRefundsASpoiledParcel() {
        RootCellar c = new RootCellar(6, 50);
        LettersByArk x = new LettersByArk(c, Destination.island(), Sky.STORM, 2);
        int fresh = jar(c, plot, "Egg", Method.FRESH, "e");
        int q = x.quote("far_orchard");
        plot.add(Preserve.SALT, q + 1);
        assertEquals(LettersByArk.Outcome.SHIPPED, x.ship("p", fresh, "far_orchard", true, plot));
        assertEquals(1, plot.count(Preserve.SALT));
        assertTrue(x.afloat().get(0).covered());
        assertEquals(q, x.afloat().get(0).premium());
        while (!x.afloat().isEmpty()) {
            x.nextDay(plot);
        }
        LettersByArk.Arrival a = x.landed().get(0);
        assertFalse(a.good());
        assertEquals(0, a.regard(), "covered: the underwriter makes it right");
        assertEquals(0, x.regard("far_orchard"));
        assertTrue(x.replies().isEmpty(), "no reply to a spoiled parcel");
    }

    @Test
    void voyagesAreSeededAndRougherRunsStrikeMore() {
        int kelp = 0;
        int orchard = 0;
        for (long seed = 0; seed < 300; seed++) {
            RootCellar c = new RootCellar(seed, 50);
            PlotState p = new PlotState();
            LettersByArk x = new LettersByArk(c, Destination.island(), Sky.SQUALL, seed);
            x.ship("a", jar(c, p, "Groat", Method.FRESH, "g1"), "kelp_harbour", false, p);
            x.ship("b", jar(c, p, "Groat", Method.FRESH, "g2"), "far_orchard", false, p);
            kelp += x.afloat().get(0).strikes();
            orchard += x.afloat().get(1).strikes();
            if (seed == 7) {
                RootCellar c2 = new RootCellar(seed, 50);
                PlotState p2 = new PlotState();
                LettersByArk y = new LettersByArk(c2, Destination.island(), Sky.SQUALL, seed);
                y.ship("a", jar(c2, p2, "Groat", Method.FRESH, "g1"), "kelp_harbour", false, p2);
                y.ship("b", jar(c2, p2, "Groat", Method.FRESH, "g2"), "far_orchard", false, p2);
                assertEquals(x.afloat(), y.afloat());
            }
        }
        assertTrue(orchard > kelp * 3, "orchard " + orchard + " vs kelp " + kelp);
    }

    @Test
    void questShipFourThreeLandGoodTwoRepliesThenDovAndTheSupperEpilogue() {
        RootCellar c = new RootCellar(9, 50);
        LettersByArk x = new LettersByArk(c, Destination.island(), Sky.SQUALL, 13);
        assertNull(x.epilogue("dov"));
        x.ship("k", jar(c, plot, "fish", Method.SALT, "j1"), "kelp_harbour", false, plot);
        x.ship("c", jar(c, plot, "Bacon", Method.SMOKE, "j2"), "cinder_reach", false, plot);
        x.ship("g", jar(c, plot, "Egg", Method.PICKLE, "j3"), "glass_shoals", false, plot);
        x.ship("o", jar(c, plot, "Moonbean", Method.DRY, "j4"), "far_orchard", false, plot);
        assertEquals(1, x.quest().stepIndex());
        assertTrue(x.afloat().stream().allMatch(LettersByArk.Parcel::arrivesGood));
        assertEquals(String.format(ReplyLines.WAIT, 4, "s"), x.talk("t1"));
        int guard = 0;
        while (x.quest().stepIndex() < 3 && guard++ < 60) {
            x.nextDay(plot);
        }
        assertEquals(3, x.quest().stepIndex());
        assertTrue(x.replies().size() >= 2);
        assertTrue(x.replies().contains("kelp_harbour"), "the nearest run writes back first");
        assertEquals(String.format(ReplyLines.EPILOGUE, "Harbourmaster Nell"), x.epilogue("dov"));
        assertNull(x.epilogue("pell"));
        assertEquals(ReplyLines.THANKS, x.talk("dov"));
        assertTrue(x.quest().complete());
        assertTrue(x.quest().claimReward());
        assertEquals(ReplyLines.DONE, x.talk("after"));
        assertEquals(c.day(), x.day(), "one clock for the cellar and the post");
        for (String d : List.of("kelp_harbour", "cinder_reach", "glass_shoals", "far_orchard")) {
            assertTrue(x.regard(d) >= LettersByArk.GOOD);
        }
        assertEquals("q_letters_by_ark", LettersByArk.QUEST_ID);
    }
}
