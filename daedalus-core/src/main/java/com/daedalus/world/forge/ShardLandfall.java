// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.ArkDrydock.Life;
import com.daedalus.world.forge.VoidCrossing.Crossing;
import com.daedalus.world.forge.VoidCrossing.Outcome;

import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.SplittableRandom;

/**
 * Shard Landfall (contest gap G170): the far side of {@link VoidCrossing}. An ark that made its shard lands its hold on
 * the shard's quay, where Quaymistress Tessaly Brund keeps the pens and the market.
 *
 * <p>The shard's pasture is seeded: a forage cap (decilitres of water and grazing a day, the G24 {@link Life} rates)
 * and a price, in scrip, for each founding pair of each paired kind. Only a whole pair can found a herd, so a lone
 * survivor of a thirsty day in the void cannot. A seed crate always plants, a vent-bee hive lands on its own and a pet
 * stays with the crew. Every head that is not landed sells at the quay for a quarter of its pair price (at least one
 * scrip); a hive left aboard sells for one. Leftover water sells at one scrip per {@value #DL_PER_SCRIP} dl and each
 * spare rivet for one. Land more forage than the pasture holds and the new herds overgraze: they are worth nothing.
 *
 * <p>The best landing is a bounded knapsack over pairs and hives (weight = forage, gain = price less what the heads
 * would fetch at the quay), solved exactly by {@link #best}. A plan that matches it is {@link Grade#THRIVING}.
 */
public final class ShardLandfall {

    /** Scrip a seed crate earns when it plants. */
    public static final int SEED_CRATE_SCRIP = 5;
    /** Leftover water sells at one scrip per this many decilitres. */
    public static final int DL_PER_SCRIP = 100;
    /** The paired kinds the pasture prices, in {@link Life} order. */
    static final List<Life> PAIRED = List.of(Life.EMBERHEN, Life.ASHGOAT, Life.FORGEOX, Life.LAVABOAR, Life.CINDERWOOL);

    /** How the landing went. */
    public enum Grade { THRIVING, SETTLED, THIN, OVERGRAZED, NOTHING_ASHORE }

    /** What the ark brings to the quay: the shard, who is still aboard, water left, spare rivets, and whether it arrived. */
    public record Hold(String shard, Map<Life, Integer> aboard, int waterDl, int spares, boolean arrived) {

        public Hold {
            EnumMap<Life, Integer> copy = new EnumMap<>(Life.class);
            copy.putAll(aboard);
            aboard = Map.copyOf(copy);
        }

        /** The hold of a finished crossing. Only ARRIVED and ARRIVED_WITH_LOSSES reach the quay. */
        public static Hold of(Crossing c) {
            boolean in = c.outcome() == Outcome.ARRIVED || c.outcome() == Outcome.ARRIVED_WITH_LOSSES;
            return new Hold(c.voyage().shard(), c.aboard(), c.water(), c.spares(), in);
        }

        public int heads(Life k) {
            return aboard.getOrDefault(k, 0);
        }
    }

    /** The shard's seeded pasture: forage cap per day and the price of a founding pair of each paired kind. */
    public record Pasture(String shard, int forageCap, Map<Life, Integer> pairPrice, int hivePrice) {

        public Pasture {
            EnumMap<Life, Integer> copy = new EnumMap<>(Life.class);
            copy.putAll(pairPrice);
            pairPrice = Map.copyOf(copy);
        }

        public int price(Life k) {
            return pairPrice.getOrDefault(k, 0);
        }

        /** What one head of a paired kind fetches at the quay if it is not landed. */
        public int sell(Life k) {
            return Math.max(1, price(k) / 4);
        }
    }

    /** The landing order: founding pairs of each paired kind, and how many hives go ashore. */
    public record Plan(Map<Life, Integer> pairs, int hives) {

        public Plan {
            EnumMap<Life, Integer> copy = new EnumMap<>(Life.class);
            for (Map.Entry<Life, Integer> e : pairs.entrySet()) {
                if (!e.getKey().pairs()) {
                    throw new IllegalArgumentException(e.getKey().id() + " does not land in pairs");
                }
                if (e.getValue() < 0) {
                    throw new IllegalArgumentException("negative pairs of " + e.getKey().id());
                }
                if (e.getValue() > 0) {
                    copy.put(e.getKey(), e.getValue());
                }
            }
            if (hives < 0) {
                throw new IllegalArgumentException("negative hives");
            }
            pairs = Map.copyOf(copy);
        }

        public int pairs(Life k) {
            return pairs.getOrDefault(k, 0);
        }

        /** Land nothing; sell everything at the quay. */
        public static Plan none() {
            return new Plan(Map.of(), 0);
        }
    }

    /** The landing's result, with the best possible scrip for the same hold and pasture. */
    public record Landing(Grade grade, int forage, int herdScrip, int quayScrip, int scrip, int best, Plan plan,
                          Pasture pasture) {

        /** Quaymistress Tessaly Brund's line. */
        public String line() {
            return ShardLandfall.line(grade, pasture.shard());
        }

        /** The q_shard_landfall step this landing leaves the player on. */
        public String questStep() {
            return switch (grade) {
                case THRIVING, SETTLED -> "report_tessaly";
                case THIN, OVERGRAZED -> "replan_landing";
                case NOTHING_ASHORE -> "sail_again";
            };
        }

        /** SLF 1 single-line encoding, stable for the C++ parity test and the link. */
        public String encode() {
            StringBuilder p = new StringBuilder();
            for (Life k : PAIRED) {
                if (p.length() > 0) {
                    p.append(',');
                }
                p.append(k.id()).append(':').append(plan.pairs(k));
            }
            return "SLF 1 " + grade + " to=" + pasture.shard().replace(' ', '_') + " cap=" + pasture.forageCap() + " forage="
                    + forage + " pairs=" + p + " hives=" + plan.hives() + " herd=" + herdScrip + " quay=" + quayScrip
                    + " scrip=" + scrip + " best=" + best + " step=" + questStep() + " | " + line();
        }
    }

    private ShardLandfall() {
    }

    /** The pasture the shard offers for {@code seed}. The same shard and seed always give the same pasture. */
    public static Pasture pasture(String shard, long seed) {
        long h = 0;
        for (int i = 0; i < shard.length(); i++) {
            h = h * 31 + shard.charAt(i);
        }
        SplittableRandom rng = new SplittableRandom(seed ^ (h * 0x9E37L) ^ 0x51FL);
        int cap = 100 + 50 * rng.nextInt(9);
        Map<Life, Integer> price = new EnumMap<>(Life.class);
        for (Life k : PAIRED) {
            price.put(k, 4 + rng.nextInt(17));
        }
        int hive = 3 + rng.nextInt(4);
        return new Pasture(shard, cap, price, hive);
    }

    /** Land {@code plan} from {@code hold} onto {@code pasture}. A plan that lands heads the hold does not have is refused. */
    public static Landing land(Hold hold, Pasture pasture, Plan plan) {
        int best = hold.arrived() ? score(hold, pasture, best(hold, pasture)) : 0;
        if (!hold.arrived()) {
            return new Landing(Grade.NOTHING_ASHORE, 0, 0, 0, 0, 0, plan, pasture);
        }
        check(hold, plan);
        int forage = forage(plan);
        boolean over = forage > pasture.forageCap();
        int herd = over ? 0 : herdScrip(pasture, plan);
        int seeds = SEED_CRATE_SCRIP * hold.heads(Life.SEED_CRATE);
        int quay = quayScrip(hold, pasture, plan) + seeds;
        int scrip = herd + quay;
        Grade g = over ? Grade.OVERGRAZED : scrip == best ? Grade.THRIVING : 4 * scrip >= 3 * best ? Grade.SETTLED
                : Grade.THIN;
        return new Landing(g, forage, herd, quay, scrip, best, plan, pasture);
    }

    /** Land a finished crossing's hold on its shard's pasture for {@code seed}. */
    public static Landing land(Crossing c, long seed, Plan plan) {
        Hold h = Hold.of(c);
        return land(h, pasture(h.shard(), seed), plan);
    }

    /** The best plan for this hold and pasture (exact bounded knapsack over forage). */
    public static Plan best(Hold hold, Pasture pasture) {
        int cap = pasture.forageCap();
        int n = PAIRED.size() + 1;
        int[][] dp = new int[n + 1][cap + 1];
        int[][] take = new int[n + 1][cap + 1];
        for (int i = 1; i <= n; i++) {
            int w = weight(i - 1);
            int gain = gain(pasture, i - 1);
            int max = maxUnits(hold, i - 1);
            for (int c = 0; c <= cap; c++) {
                dp[i][c] = dp[i - 1][c];
                take[i][c] = 0;
                for (int t = 1; t <= max && t * w <= c; t++) {
                    int v = dp[i - 1][c - t * w] + t * gain;
                    if (v > dp[i][c]) {
                        dp[i][c] = v;
                        take[i][c] = t;
                    }
                }
            }
        }
        Map<Life, Integer> pairs = new EnumMap<>(Life.class);
        int hives = 0;
        int c = cap;
        for (int i = n; i >= 1; i--) {
            int t = take[i][c];
            if (i - 1 < PAIRED.size()) {
                pairs.put(PAIRED.get(i - 1), t);
            } else {
                hives = t;
            }
            c -= t * weight(i - 1);
        }
        return new Plan(pairs, hives);
    }

    /** Total scrip a plan earns (herds count nothing when overgrazed). */
    public static int score(Hold hold, Pasture pasture, Plan plan) {
        int herd = forage(plan) > pasture.forageCap() ? 0 : herdScrip(pasture, plan);
        return herd + quayScrip(hold, pasture, plan) + SEED_CRATE_SCRIP * hold.heads(Life.SEED_CRATE);
    }

    /** Forage a plan puts on the pasture each day, decilitres. */
    public static int forage(Plan plan) {
        int f = plan.hives() * Life.VENT_BEES.dlPerDay();
        for (Life k : PAIRED) {
            f += 2 * k.dlPerDay() * plan.pairs(k);
        }
        return f;
    }

    /** Most founding pairs (or hives) the hold can land of item {@code i} (paired kinds in order, then hives). */
    static int maxUnits(Hold hold, int i) {
        return i < PAIRED.size() ? hold.heads(PAIRED.get(i)) / 2 : hold.heads(Life.VENT_BEES);
    }

    private static int weight(int i) {
        return i < PAIRED.size() ? 2 * PAIRED.get(i).dlPerDay() : Life.VENT_BEES.dlPerDay();
    }

    private static int gain(Pasture p, int i) {
        return i < PAIRED.size() ? p.price(PAIRED.get(i)) - 2 * p.sell(PAIRED.get(i)) : p.hivePrice() - 1;
    }

    private static void check(Hold hold, Plan plan) {
        for (int i = 0; i <= PAIRED.size(); i++) {
            int want = i < PAIRED.size() ? plan.pairs(PAIRED.get(i)) : plan.hives();
            if (want > maxUnits(hold, i)) {
                String what = i < PAIRED.size() ? PAIRED.get(i).id() + " pairs" : "hives";
                throw new IllegalArgumentException("only " + maxUnits(hold, i) + " " + what + " aboard, not " + want);
            }
        }
    }

    private static int herdScrip(Pasture p, Plan plan) {
        int s = plan.hives() * p.hivePrice();
        for (Life k : PAIRED) {
            s += plan.pairs(k) * p.price(k);
        }
        return s;
    }

    private static int quayScrip(Hold hold, Pasture p, Plan plan) {
        int s = hold.waterDl() / DL_PER_SCRIP + hold.spares() + (hold.heads(Life.VENT_BEES) - plan.hives());
        for (Life k : PAIRED) {
            s += (hold.heads(k) - 2 * plan.pairs(k)) * p.sell(k);
        }
        return s;
    }

    static String line(Grade g, String shard) {
        return switch (g) {
            case THRIVING -> "Every pen on " + shard + " is full and grazing easy. Tessaly says no ark ever landed better.";
            case SETTLED -> "The herds will take on " + shard + ". Tessaly would have penned one more pair.";
            case THIN -> "Most of the hold went to the quay stalls. " + shard + " wanted founders, not scrip.";
            case OVERGRAZED -> "Too many mouths for the pasture. " + shard + " is bare by the second week.";
            case NOTHING_ASHORE -> "No ark moored at " + shard + ". Tessaly keeps the pens swept and waits.";
        };
    }
}
