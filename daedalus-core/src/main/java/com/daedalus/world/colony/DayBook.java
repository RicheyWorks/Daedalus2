// SPDX-License-Identifier: MIT

package com.daedalus.world.colony;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * The Colony Ledger day book (WZ14, "Animal Crossing" finds) and its news-board requests, ported from
 * {@code tools/economy/colony_ledger.py} ({@code Ledger.day_book} and {@code Ledger.requests}) with the same seeds,
 * so a Java server and the Python core agree item for item ({@code DayBookParityTest}).
 *
 * <p>Pure and clock-free: every call takes the day and hour. Finds go into the {@link PlotState} store; first-of-kind
 * finds go to the museum collection (bonus 5 each, charm +0.1). Requests come from the realm's {@link Cast}: each NPC
 * asks for what this island can make and pays in something it cannot, and quest-giver roles carry their PORT09
 * quest id, which {@link QuestBoard} turns into ordered quest progress.
 */
public final class DayBook {
    public static final double FIRST_FIND_BONUS = 5.0;
    public static final double FIRST_FIND_CHARM = 0.1;

    private DayBook() {
    }

    /** Season and seral stage of the island today ({@code ecology} in the Python core). */
    public record Ecology(int seral, String season) {
        public static final Ecology DEFAULT = new Ecology(1, "summer");

        public Ecology {
            Objects.requireNonNull(season, "season");
        }
    }

    /** One news-board request. {@code questId} is null when the role gives no quest in this realm. */
    public record Request(String npc, List<String> wants, String pays, String questId) {
        public Request {
            wants = List.copyOf(wants);
        }
    }

    /** What the day book returns for one day. */
    public record Day(List<String> finds, List<String> newInCollection, double bonus, List<Request> requests) {
        public Day {
            finds = List.copyOf(finds);
            newInCollection = List.copyOf(newInCollection);
            requests = List.copyOf(requests);
        }
    }

    static boolean biteHour(int hour) {
        return (6 <= hour && hour <= 10) || (17 <= hour && hour <= 21);
    }

    /** {@code Ledger.day_book(deed, day, hour, ecology)}: finds, museum update, store update, then requests. */
    public static Day today(IslandFacts island, PlotState plot, Cast cast, int day, int hour, Ecology ecology) {
        Ecology eco = ecology == null ? Ecology.DEFAULT : ecology;
        PyRandom rng = new PyRandom((long) island.deed() * 100003L + day);
        List<String> finds = new ArrayList<>();
        for (String f : island.fish()) {
            List<String> seasons = ColonyTables.FISH_SEASON.get(f);
            if (seasons != null && seasons.contains(eco.season()) && biteHour(hour)) {
                finds.add(f);
            }
        }
        finds.addAll(ColonyTables.BUGS_BY_SERAL.getOrDefault(eco.seral(), List.of()));
        if (rng.random() < 0.3) {
            finds.add(island.starmetalCrater() ? "starmetal_shard" : rng.choice(ColonyTables.FOSSILS.subList(0, 2)));
        }
        if (eco.season().equals("summer") || eco.season().equals("autumn")) {
            finds.addAll(island.orchardFruits());
        }
        List<String> fresh = new ArrayList<>();
        for (String f : finds) {
            if (!plot.collection().contains(f)) {
                fresh.add(f);
            }
        }
        fresh.forEach(plot::collect);
        for (String f : finds) {
            plot.add(f, 1);
        }
        plot.addCharm(FIRST_FIND_CHARM * fresh.size());
        return new Day(finds, fresh, FIRST_FIND_BONUS * fresh.size(), requests(island, plot, cast, day));
    }

    /** {@code Ledger.requests(deed, day)}: up to three NPCs from the cast, seeded by deed and day. */
    public static List<Request> requests(IslandFacts island, PlotState plot, Cast cast, int day) {
        PyRandom rng = new PyRandom((long) island.deed() * 7L + day * 13L);
        List<String> roles = new ArrayList<>();
        for (String t : cast.roles()) {
            if (ColonyTables.NPC_WANTS.containsKey(t)) {
                roles.add(t);
            }
        }
        if (roles.isEmpty()) {
            roles.addAll(ColonyTables.NPC_WANTS.keySet());
            roles.sort(null);
        }
        List<String> cannot = new ArrayList<>();
        for (String it : island.catalog()) {
            if (!plot.hasLine(it) && ColonyTables.familyOf(it).equals(island.need())) {
                cannot.add(it);
            }
        }
        List<Request> out = new ArrayList<>();
        for (String role : rng.sample(roles, Math.min(3, roles.size()))) {
            List<String> all = ColonyTables.NPC_WANTS.get(role);
            List<String> wants = new ArrayList<>();
            for (String it : all) {
                if (island.makeable().contains(it)) {
                    wants.add(it);
                }
            }
            if (wants.isEmpty()) {
                wants.add(all.get(0));
            }
            String quest = cast.questOf(role).map(Cast.QuestDef::id).orElse(null);
            String pays = cannot.isEmpty() ? "gold" : rng.choice(cannot);
            out.add(new Request(role, wants.subList(0, Math.min(2, wants.size())), pays, quest));
        }
        return out;
    }
}
