// SPDX-License-Identifier: MIT

package com.daedalus.world.forge;

import com.daedalus.world.forge.TemperForge.Quench;
import com.daedalus.world.forge.TemperForge.Result;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.EnumSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SplittableRandom;

/**
 * Ark Drydock (contest gap G24): what the Great Forge is for. Hephaestus Island's arks leave the forge
 * shard carrying life to the other shards of the broken planet (data/islands/hephaestus/ISLAND.md, beat 4).
 *
 * <p>An ark's hull is a ring of stamped ark plates. Every plate is a {@link TemperForge} result, and each
 * seam joins two neighbouring plates with tempered rivets. A seam is as strong as the mean temper of its
 * two plates, less {@link #MISSING_RIVET_COST} for each missing rivet. The hull is as strong as its
 * weakest seam. The keepers' rule holds for hulls too: a hull of only magma-quenched plates is BRITTLE,
 * one of only spring-quenched plates is SOFT, and DUAL plates count as both.
 *
 * <p>The hold carries a life manifest of the island's livestock (in pairs), bee hives, pets (Kennel
 * Turing-coat pups) and seed crates, plus a crew, and enough water for every day of the voyage. The daily
 * water figures are the island's own (livestock.json); the test reads that file to keep them in step.
 *
 * <p>{@link #inspect} is pure. It returns every reason the ark cannot launch, and the Drydock Master's
 * line for the first of them, which is the dialogue of quest {@code q_ark_launch}.
 */
public final class ArkDrydock {

    public static final int RIVETS_PER_SEAM = 4;
    public static final int MISSING_RIVET_COST = 10;
    /** Weakest seam that survives the climb into the void. */
    public static final int MIN_INTEGRITY = 60;
    /** Water per crew member per day, decilitres. */
    public static final int CREW_DL = 20;

    /** The hulls the drydock lays down. */
    public enum ArkClass {
        SKIFF(6, 2, 12, 2_000),
        BARGE(10, 4, 24, 6_000),
        LONGARK(14, 6, 40, 12_000);

        private final int plates;
        private final int crew;
        private final int berths;
        private final int holdDl;

        ArkClass(int plates, int crew, int berths, int holdDl) {
            this.plates = plates;
            this.crew = crew;
            this.berths = berths;
            this.holdDl = holdDl;
        }

        public int plates() {
            return plates;
        }

        public int crew() {
            return crew;
        }

        public int berths() {
            return berths;
        }

        /** Water the hold can take, decilitres. */
        public int holdDl() {
            return holdDl;
        }
    }

    /** What can ride in the hold, with its water per day (decilitres) and whether it must travel in pairs. */
    public enum Life {
        EMBERHEN("emberhen", 5, true),
        ASHGOAT("ashgoat", 80, true),
        FORGEOX("forgeox", 120, true),
        LAVABOAR("lavaboar", 60, true),
        CINDERWOOL("cinderwool", 60, true),
        VENT_BEES("vent_bees", 10, false),
        PET("pet", 10, false),
        SEED_CRATE("seed_crate", 0, false);

        private final String id;
        private final int dlPerDay;
        private final boolean pairs;

        Life(String id, int dlPerDay, boolean pairs) {
            this.id = id;
            this.dlPerDay = dlPerDay;
            this.pairs = pairs;
        }

        /** The livestock.json id. */
        public String id() {
            return id;
        }

        public int dlPerDay() {
            return dlPerDay;
        }

        public boolean pairs() {
            return pairs;
        }
    }

    /** Why an ark cannot launch, in the order the Drydock Master raises them. */
    public enum Reason {
        HULL_INCOMPLETE, UNSTAMPED_PLATE, BRITTLE, SOFT, WEAK_SEAM, OVER_CAPACITY, UNPAIRED, THIRSTY_HOLD, OVER_HOLD
    }

    /** One plate in the hull ring: its temper, quench path, and whether it bears a stamp. */
    public record Plate(int temper, Quench quench, boolean stamped) {

        public Plate {
            if (temper < 0 || temper > 100) {
                throw new IllegalArgumentException("temper out of range: " + temper);
            }
        }

        /** A plate forged at the anvil. A cracked blank never bears a stamp. */
        public static Plate of(Result r) {
            return new Plate(r.temper(), r.quench(), !r.cracked() && r.temper() >= TemperForge.ARK_PLATE_TEMPER);
        }
    }

    /** Where the ark is bound and for how many days. */
    public record Voyage(String shard, int days) {
    }

    /** The ark on the slip: class, plate ring, rivets per seam, life manifest and water loaded. */
    public record Ark(ArkClass arkClass, List<Plate> plates, List<Integer> rivets, Map<Life, Integer> manifest,
                      int waterDl) {

        public Ark {
            plates = List.copyOf(plates);
            rivets = List.copyOf(rivets);
            EnumMap<Life, Integer> copy = new EnumMap<>(Life.class);
            copy.putAll(manifest);
            manifest = Map.copyOf(copy);
        }
    }

    /** The inspection: launch-ready or not, every reason, the numbers, and what the Drydock Master says. */
    public record Inspection(boolean ready, List<Reason> reasons, int integrity, int waterNeedDl, int berthsUsed,
                             String line) {

        public Inspection {
            reasons = List.copyOf(reasons);
        }

        /** ADK 1 single-line encoding, stable for the C++ parity test and the link. */
        public String encode() {
            StringBuilder r = new StringBuilder();
            for (Reason x : reasons) {
                if (r.length() > 0) {
                    r.append(',');
                }
                r.append(x.name());
            }
            return "ADK 1 ready=" + (ready ? 1 : 0) + " integrity=" + integrity + " water=" + waterNeedDl + " berths="
                    + berthsUsed + " reasons=" + (r.length() == 0 ? "-" : r) + " step=" + questStep(this) + " line=" + line;
        }
    }

    /** Shards an ark may sail for (the realm's other islands). */
    static final List<String> SHARDS = List.of("Kennel Isle", "Glass Reef", "Sky Orchard", "Storm Anchorage",
            "Cinder Shoal", "Whistle Atoll");

    private ArkDrydock() {
    }

    /** The voyage the harbour board posts for {@code seed}: one of the shards, 3..9 days out. */
    public static Voyage voyage(long seed) {
        SplittableRandom rng = new SplittableRandom(seed ^ 0xA4CL);
        return new Voyage(SHARDS.get(rng.nextInt(SHARDS.size())), 3 + rng.nextInt(7));
    }

    /** Strength of seam {@code i}, which joins plate {@code i} to the next plate round the ring. */
    public static int seamStrength(Ark ark, int i) {
        int n = ark.plates().size();
        Plate a = ark.plates().get(i);
        Plate b = ark.plates().get((i + 1) % n);
        int r = i < ark.rivets().size() ? ark.rivets().get(i) : 0;
        int missing = Math.max(0, RIVETS_PER_SEAM - r);
        return Math.max(0, (a.temper() + b.temper()) / 2 - MISSING_RIVET_COST * missing);
    }

    /** Water the voyage needs for the manifest and crew, decilitres. */
    public static int waterNeedDl(Ark ark, Voyage v) {
        long perDay = (long) ark.arkClass().crew() * CREW_DL;
        for (Map.Entry<Life, Integer> e : ark.manifest().entrySet()) {
            perDay += (long) e.getKey().dlPerDay() * e.getValue();
        }
        return (int) Math.min(Integer.MAX_VALUE, perDay * v.days());
    }

    /** Inspect the ark on the slip for {@code v}. Pure. */
    public static Inspection inspect(Ark ark, Voyage v) {
        Set<Reason> why = EnumSet.noneOf(Reason.class);
        ArkClass c = ark.arkClass();
        int n = ark.plates().size();
        if (n != c.plates() || ark.rivets().size() != n) {
            why.add(Reason.HULL_INCOMPLETE);
        }
        boolean heat = false;
        boolean water = false;
        for (Plate p : ark.plates()) {
            if (!p.stamped()) {
                why.add(Reason.UNSTAMPED_PLATE);
            }
            heat |= p.quench() != Quench.SPRING;
            water |= p.quench() != Quench.MAGMA;
        }
        if (n > 0 && !water) {
            why.add(Reason.BRITTLE);
        }
        if (n > 0 && !heat) {
            why.add(Reason.SOFT);
        }
        int integrity = n == 0 ? 0 : Integer.MAX_VALUE;
        for (int i = 0; i < n; i++) {
            integrity = Math.min(integrity, seamStrength(ark, i));
        }
        if (integrity < MIN_INTEGRITY) {
            why.add(Reason.WEAK_SEAM);
        }
        int berths = 0;
        for (Map.Entry<Life, Integer> e : ark.manifest().entrySet()) {
            if (e.getValue() < 0) {
                throw new IllegalArgumentException("negative count for " + e.getKey());
            }
            berths += e.getValue();
            if (e.getKey().pairs() && e.getValue() % 2 != 0) {
                why.add(Reason.UNPAIRED);
            }
        }
        if (berths > c.berths()) {
            why.add(Reason.OVER_CAPACITY);
        }
        int need = waterNeedDl(ark, v);
        if (ark.waterDl() < need) {
            why.add(Reason.THIRSTY_HOLD);
        }
        if (ark.waterDl() > c.holdDl()) {
            why.add(Reason.OVER_HOLD);
        }
        List<Reason> reasons = new ArrayList<>(why);
        return new Inspection(reasons.isEmpty(), reasons, integrity, need, berths,
                reasons.isEmpty() ? readyLine(v) : line(reasons.get(0)));
    }

    /** Drydock Master Brannoc Slagg's line for a launch blocker (q_ark_launch). */
    public static String line(Reason r) {
        return switch (r) {
            case HULL_INCOMPLETE -> "A ring with a gap is a funnel, not a hull. Every plate, every seam.";
            case UNSTAMPED_PLATE -> "No stamp, no trust. Take that plate back to the anvil and earn your mark.";
            case BRITTLE -> "All fire, no water. She'd shatter on the first cold gust. Heat alone breaks.";
            case SOFT -> "All spring, no fire. She'd sag like wet bread in the void. Water alone softens.";
            case WEAK_SEAM -> "One weak seam and the void finds it. Better plates there, or more rivets.";
            case OVER_CAPACITY -> "Hesper says the hold is bursting. Leave some for the next ark.";
            case UNPAIRED -> "Two by two, or the herd ends where it lands. Find that one a mate.";
            case THIRSTY_HOLD -> "Count the days, count the mouths. You're short of water for that run.";
            case OVER_HOLD -> "More water than tank. The rest will be ballast on the slipway floor.";
        };
    }

    /** The send-off when the ark is ready. */
    public static String readyLine(Voyage v) {
        return "Tempered both ways. Knock the chocks out. " + v.days() + " days to " + v.shard()
                + ", and the forge goes with you.";
    }

    /** The q_ark_launch step the player is on, from the first blocker. */
    public static String questStep(Inspection i) {
        if (i.ready()) {
            return "launch";
        }
        return switch (i.reasons().get(0)) {
            case HULL_INCOMPLETE, UNSTAMPED_PLATE, BRITTLE, SOFT -> "forge_plates";
            case WEAK_SEAM -> "rivet_seams";
            case OVER_CAPACITY, UNPAIRED -> "load_life";
            case THIRSTY_HOLD, OVER_HOLD -> "water_hold";
        };
    }
}
