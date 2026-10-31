// SPDX-License-Identifier: MIT

package com.daedalus.world.almanac;

import com.daedalus.world.pilot.PyStringRandom;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Prism Almanac Daily: every calendar day deals the same three Prismheart cabinets, difficulties and game seeds to
 * every player, plus one weathervane modifier that nudges the day's pars. The draw is CPython
 * {@code random.Random("prism-almanac:YYYY-MM-DD")} (via {@link PyStringRandom}), so Python, Java and the C++ core
 * (DaedalusPrismAlmanacCore.h) deal the same day. Pars come from the Fair Par fixture (prism_fair_par_parity.txt,
 * Pythagoras' lane); the almanac only reads it. Draw order: weather, then for each of three cabinets the game (from
 * the games not yet dealt), its difficulty and its 32-bit game seed.
 */
public final class PrismAlmanac {

    /** Prismheart cabinets in Fair Par order. */
    public static final List<String> GAMES = List.of("glowmoss", "spiritkite", "glimmerloom", "lumenpath", "wardens_accord",
            "facetlock", "prismvault", "shardfall", "prismcairn", "shadewatch", "shardring");
    public static final List<String> DIFFICULTIES = List.of("easy", "normal", "hard");
    public static final int CABINETS_PER_DAY = 3;
    public static final String SEED_PREFIX = "prism-almanac:";
    public static final int RIBBON_DAYS = 7;

    /** The day's weathervane: percent applied to silver and gold pars, and whether cabinet hints are shown. */
    public enum Weather {
        CLEAR_SKIES(90, true), CALM(100, true), FOG(100, false), GALE(110, true);

        private final int parPercent;
        private final boolean hints;

        Weather(int parPercent, boolean hints) {
            this.parPercent = parPercent;
            this.hints = hints;
        }

        public int parPercent() {
            return parPercent;
        }

        public boolean hints() {
            return hints;
        }
    }

    /** One dealt cabinet: game id, difficulty and the unsigned 32-bit seed for that game's own core. */
    public record Pick(String game, String difficulty, long seed) { }

    /** A dealt day. */
    public record Day(LocalDate date, Weather weather, List<Pick> picks) {
        public Day {
            picks = List.copyOf(picks);
        }
    }

    /** Bronze, silver and gold score pars. */
    public record Par(int bronze, int silver, int gold) {
        /** False when Fair Par's bot never won this game and difficulty (silver and gold 0): no fair par to post. */
        public boolean calibrated() {
            return silver > 0 && gold >= silver;
        }
    }

    /** A cabinet as posted on the day: the pick, the difficulty actually played and its weather-adjusted par. */
    public record Posted(Pick pick, String difficulty, Par par) { }

    private PrismAlmanac() { }

    /** Seed string for a date, e.g. {@code prism-almanac:2026-10-30}. */
    public static String seedOf(LocalDate date) {
        return SEED_PREFIX + date;
    }

    /** Deals a day. */
    public static Day day(LocalDate date) {
        PyStringRandom rnd = new PyStringRandom(seedOf(date));
        Weather w = Weather.values()[rnd.below(Weather.values().length)];
        List<String> pool = new ArrayList<>(GAMES);
        List<Pick> picks = new ArrayList<>();
        for (int i = 0; i < CABINETS_PER_DAY; i++) {
            String game = pool.remove(rnd.below(pool.size()));
            String diff = DIFFICULTIES.get(rnd.below(DIFFICULTIES.size()));
            picks.add(new Pick(game, diff, rnd.nextU32()));
        }
        return new Day(date, w, picks);
    }

    /**
     * Pars keyed {@code game/difficulty}, read from Fair Par fixture lines ({@code game=.. difficulty=.. bronze=..
     * silver=.. gold=..}); comments and other lines are skipped.
     */
    public static Map<String, Par> parsFrom(List<String> fairParLines) {
        Map<String, Par> out = new HashMap<>();
        for (String line : fairParLines) {
            if (!line.startsWith("game=")) {
                continue;
            }
            Map<String, String> kv = new HashMap<>();
            for (String tok : line.trim().split(" ")) {
                int eq = tok.indexOf('=');
                if (eq > 0) {
                    kv.put(tok.substring(0, eq), tok.substring(eq + 1));
                }
            }
            if (kv.containsKey("difficulty") && kv.containsKey("bronze") && kv.containsKey("silver") && kv.containsKey("gold")) {
                out.put(kv.get("game") + "/" + kv.get("difficulty"), new Par(Integer.parseInt(kv.get("bronze")),
                        Integer.parseInt(kv.get("silver")), Integer.parseInt(kv.get("gold"))));
            }
        }
        return out;
    }

    /** The day's par for a cabinet: silver and gold scaled by the weather (integer floor), bronze kept. */
    public static Par parFor(Par base, Weather w) {
        return new Par(base.bronze(), base.silver() * w.parPercent() / 100, base.gold() * w.parPercent() / 100);
    }

    /**
     * Posts a dealt day against the Fair Par table: a pick whose difficulty has no calibrated par is played one
     * difficulty easier (repeat until calibrated; easy is always calibrated in the fixture). The seed is unchanged,
     * so the dealt day never moves. Throws when a cabinet has no par at all.
     */
    public static List<Posted> post(Day day, Map<String, Par> pars) {
        List<Posted> out = new ArrayList<>();
        for (Pick p : day.picks()) {
            int d = DIFFICULTIES.indexOf(p.difficulty());
            Par base = pars.get(p.game() + "/" + DIFFICULTIES.get(d));
            while (d > 0 && (base == null || !base.calibrated())) {
                d--;
                base = pars.get(p.game() + "/" + DIFFICULTIES.get(d));
            }
            if (base == null || !base.calibrated()) {
                throw new IllegalArgumentException("no fair par for " + p.game());
            }
            out.add(new Posted(p, DIFFICULTIES.get(d), parFor(base, day.weather())));
        }
        return out;
    }

    /**
     * Current streak in days: consecutive cleared days ending today, or ending yesterday when today is not cleared yet
     * (the streak is still alive until the day ends). Days are {@link LocalDate#toEpochDay()} numbers.
     */
    public static int streak(Set<Long> cleared, long today) {
        long d = cleared.contains(today) ? today : today - 1;
        int n = 0;
        while (cleared.contains(d)) {
            n++;
            d--;
        }
        return n;
    }

    /** Seven-day calendar ribbon: bit i set when day {@code today - 6 + i} is cleared. */
    public static int ribbon(Set<Long> cleared, long today) {
        int mask = 0;
        for (int i = 0; i < RIBBON_DAYS; i++) {
            if (cleared.contains(today - (RIBBON_DAYS - 1) + i)) {
                mask |= 1 << i;
            }
        }
        return mask;
    }
}
