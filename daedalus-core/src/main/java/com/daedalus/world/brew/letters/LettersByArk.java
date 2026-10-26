// SPDX-License-Identifier: MIT

package com.daedalus.world.brew.letters;

import com.daedalus.world.brew.cellar.Preserve;
import com.daedalus.world.brew.cellar.RootCellar;
import com.daedalus.world.colony.PlotState;
import com.daedalus.world.colony.QuestProgress;
import com.daedalus.world.odds.OddsRng;
import com.daedalus.world.odds.insurance.ArkPolicy;
import com.daedalus.world.odds.weather.Sky;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Chapter 10 of the Youtube Master Island story, "Letters by Ark" (quest {@code q_letters_by_ark}). A sealed cellar
 * jar (G73) goes with a letter to a far {@link Destination}. Voyage days are {@link #DAYS_PER_LEG} per leg of the
 * route plus {@link #DELAY_PER_STRIKE} for each hazard that strikes (one seeded G47 {@code ArkRoute.sail} per
 * parcel). The jar arrives good only if its last good day is on or after the arrival day. Good: +2 regard with that
 * NPC (+1 more for their favourite food). Spoiled: -2, unless the parcel was covered: the premium is quoted
 * read-only from the G80 {@link ArkPolicy} for the route and today's sky, paid in salt, and a covered spoil refunds
 * the lost regard. A good parcel brings a reply on the return ark (base voyage days later), and each reply unlocks
 * the epilogue line of the supper guest (G85) who is that NPC's old friend. One clock: {@link #nextDay} also ends
 * the cellar's day.
 */
public final class LettersByArk {
    public static final String QUEST_ID = "q_letters_by_ark";
    public static final String POSTMASTER = "dov";
    public static final int DAYS_PER_LEG = 3;
    public static final int DELAY_PER_STRIKE = 2;
    public static final int GOOD = 2;
    public static final int FAVOURITE = 1;
    public static final int SPOILED = -2;
    public static final double COVER_PER_CRATE = 1.0;
    public static final double LOADING = 0.20;

    public enum Outcome { SHIPPED, NO_JAR, UNKNOWN_DESTINATION, NO_SALT, DUPLICATE, IGNORED }

    /** A jar on its way: when it left, when it lands, its last good day, whether it is covered. */
    public record Parcel(int id, String destination, String item, Preserve.Method method, int sent, int arrives,
            int goodUntil, int strikes, boolean covered, int premium) {
        public boolean arrivesGood() {
            return goodUntil >= arrives;
        }
    }

    /** A parcel landing: good or spoiled, and the regard it changed. */
    public record Arrival(Parcel parcel, boolean good, int regard) {
    }

    private final RootCellar cellar;
    private final Map<String, Destination> destinations = new LinkedHashMap<>();
    private final long seed;
    private final Sky sky;
    private final List<Parcel> afloat = new ArrayList<>();
    private final List<Arrival> landed = new ArrayList<>();
    private final Map<String, Integer> regard = new HashMap<>();
    private final List<Map.Entry<Integer, String>> repliesDue = new ArrayList<>();
    private final Set<String> replied = new HashSet<>();
    private final Set<String> events = new HashSet<>();
    private final QuestProgress quest = new QuestProgress(List.of(
            new QuestProgress.Step("ship", "parcel", 4),
            new QuestProgress.Step("arrive_good", "parcel", 3),
            new QuestProgress.Step("reply", "letter", 2),
            new QuestProgress.Step("talk", POSTMASTER, 1)));
    private int nextId = 1;

    public LettersByArk(RootCellar cellar, List<Destination> destinations, Sky sky, long seed) {
        this.cellar = cellar;
        this.sky = sky;
        this.seed = seed;
        destinations.forEach(d -> this.destinations.put(d.id(), d));
    }

    public int day() {
        return cellar.day();
    }

    public QuestProgress quest() {
        return quest;
    }

    public List<Destination> destinations() {
        return List.copyOf(destinations.values());
    }

    public List<Parcel> afloat() {
        return List.copyOf(afloat);
    }

    public List<Arrival> landed() {
        return List.copyOf(landed);
    }

    public int regard(String destinationId) {
        return regard.getOrDefault(destinationId, 0);
    }

    /** Destinations whose reply letter has come home. */
    public Set<String> replies() {
        return Set.copyOf(replied);
    }

    /** Days out on a clean voyage. */
    public int voyageDays(String destinationId) {
        Destination d = destinations.get(destinationId);
        return d == null ? 0 : d.route().legs().size() * DAYS_PER_LEG;
    }

    /** Cover premium in salt for one parcel to this destination under today's sky (G80 underwriter, read-only). */
    public int quote(String destinationId) {
        Destination d = destinations.get(destinationId);
        return d == null ? 0 : new ArkPolicy(d.route(), sky, COVER_PER_CRATE).premium(LOADING);
    }

    /** Ships one cellar jar with a letter; {@code cover} pays the quoted premium in salt from the store. */
    public Outcome ship(String eventId, int jarId, String destinationId, boolean cover, PlotState plot) {
        if (eventId == null || eventId.isBlank() || eventId.length() > QuestProgress.MAX_EVENT_ID || plot == null) {
            return Outcome.IGNORED;
        }
        if (events.contains(eventId)) {
            return Outcome.DUPLICATE;
        }
        Destination d = destinations.get(destinationId);
        if (d == null) {
            return Outcome.UNKNOWN_DESTINATION;
        }
        if (cellar.jars().stream().noneMatch(j -> j.id() == jarId)) {
            return Outcome.NO_JAR;
        }
        int premium = cover ? quote(destinationId) : 0;
        if (plot.count(Preserve.SALT) < premium) {
            return Outcome.NO_SALT;
        }
        RootCellar.Jar jar = cellar.dispatch("letters:" + eventId, jarId);
        if (jar == null) {
            return Outcome.NO_JAR;
        }
        events.add(eventId);
        if (premium > 0) {
            plot.take(Preserve.SALT, premium);
        }
        int id = nextId++;
        int strikes = d.route().sail(sky, new OddsRng(seed * 1_000_003L + id)).strikes();
        int arrives = day() + voyageDays(destinationId) + strikes * DELAY_PER_STRIKE;
        afloat.add(new Parcel(id, destinationId, jar.item(), jar.method(), day(), arrives, jar.goodUntil(), strikes,
                cover, premium));
        quest.apply(eventId, "ship", "parcel");
        return Outcome.SHIPPED;
    }

    /** Ends the day (and the cellar's day): parcels land, replies come home. Returns today's landings. */
    public List<Arrival> nextDay(PlotState plot) {
        cellar.nextDay(plot);
        int today = day();
        List<Arrival> out = new ArrayList<>();
        for (Parcel p : List.copyOf(afloat)) {
            if (p.arrives() > today) {
                continue;
            }
            afloat.remove(p);
            Destination d = destinations.get(p.destination());
            int delta;
            if (p.arrivesGood()) {
                delta = GOOD + (d.favourite().equals(p.item()) ? FAVOURITE : 0);
                quest.apply("arrive-" + p.id(), "arrive_good", "parcel");
                repliesDue.add(Map.entry(today + voyageDays(p.destination()), p.destination()));
            } else {
                delta = p.covered() ? 0 : SPOILED;
            }
            regard.merge(p.destination(), delta, Integer::sum);
            Arrival a = new Arrival(p, p.arrivesGood(), delta);
            landed.add(a);
            out.add(a);
        }
        for (var e : List.copyOf(repliesDue)) {
            if (e.getKey() <= today) {
                repliesDue.remove(e);
                if (replied.add(e.getValue())) {
                    quest.apply("reply-" + e.getValue(), "reply", "letter");
                }
            }
        }
        return out;
    }

    /** The epilogue line a supper guest (G85) says once their old friend's reply has come home, or null. */
    public String epilogue(String guestId) {
        for (Destination d : destinations.values()) {
            if (d.friendOf().equals(guestId) && replied.contains(d.id())) {
                return String.format(ReplyLines.EPILOGUE, d.name());
            }
        }
        return null;
    }

    /** Talks to Fisher Dov at the ark post: his line, and the quest's talk step when it is due. */
    public String talk(String eventId) {
        QuestProgress.Step due = quest.currentStep();
        if (due != null && due.type().equals("talk")) {
            quest.apply(eventId, "talk", POSTMASTER);
            return ReplyLines.THANKS;
        }
        return ReplyLines.line(this);
    }
}
