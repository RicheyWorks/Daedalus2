// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * Kennel Isle's food loop as a daily ledger (contest gap G26), from {@code data/islands/kennel-food-v1.json}. Pure and
 * deterministic. The water side is {@link KennelWaterLoop}.
 *
 * <p>Each day: goats that get their hay give milk; watered Starkibble plants give Starkibble; the kibble bin turns
 * milk + Starkibble into portions (as many batches as both allow). Milk doesn't keep: whatever isn't crafted spoils at
 * day's end. Kibble and Starkibble carry over. The bowls can serve at most {@code bowls * portionsPerBowl} portions a
 * day. Pets eat in pack order (the Cane Corso first, then dogs, then pups; ties keep roster order); anyone who can't
 * get a full ration goes up one hunger stage, and a full ration resets it.
 *
 * <p>Quest "Pack Order" ({@link #packOrder}): start with an empty pantry and keep the whole pack fed for the quest days.
 */
public final class KennelPantry {
    public record Rules(double milkPerGoat, int hayPerGoat, int starkibblePerPlant, double recipeMilkL,
                        int recipeStarkibble, int recipePortions, int bowls, int portionsPerBowl,
                        Map<String, Integer> portions, List<String> packOrder, int drainPerStage, int drainCap,
                        int questDays) {
        public Rules {
            portions = Collections.unmodifiableMap(new TreeMap<>(portions));
            packOrder = List.copyOf(packOrder);
            if (recipeMilkL <= 0 || recipeStarkibble <= 0 || recipePortions <= 0 || bowls < 0 || portionsPerBowl < 0
                || hayPerGoat <= 0 || questDays < 1) {
                throw new IllegalArgumentException("bad kennel food rules");
            }
            for (String k : packOrder) {
                if (!portions.containsKey(k)) {
                    throw new IllegalArgumentException("pack order names unknown kind " + k);
                }
            }
        }
    }

    public record Pet(String name, String kind) { }

    /** One day's inputs. */
    public record Day(int goats, int hayBales, int wateredStarkibble) { }

    public record State(int kibble, int starkibble, Map<String, Integer> hunger) {
        public State {
            if (kibble < 0 || starkibble < 0) {
                throw new IllegalArgumentException("negative stock");
            }
            hunger = Collections.unmodifiableMap(new TreeMap<>(hunger));
        }

        public int drainPct(Rules r, String pet) {
            return Math.min(r.drainCap(), r.drainPerStage() * hunger.getOrDefault(pet, 0));
        }
    }

    public record DayReport(State state, double milkL, double spoiledMilkL, int crafted, int served,
                            List<String> fedOrder, List<String> hungry) {
        public DayReport {
            fedOrder = List.copyOf(fedOrder);
            hungry = List.copyOf(hungry);
        }
    }

    private final Rules r;

    public KennelPantry(Rules rules) {
        this.r = rules;
    }

    public Rules rules() {
        return r;
    }

    public static KennelPantry load(Path p) throws IOException {
        return parse(Files.readString(p, StandardCharsets.UTF_8));
    }

    @SuppressWarnings("unchecked")
    public static KennelPantry parse(String json) {
        Map<String, Object> m = (Map<String, Object>) MiniJson.parse(json);
        if (!(m.get("version") instanceof Number v) || v.intValue() != 1) {
            throw new IllegalArgumentException("kennel food version must be 1");
        }
        Map<String, Object> rec = (Map<String, Object>) m.get("kibbleRecipe");
        Map<String, Integer> portions = new LinkedHashMap<>();
        for (Map.Entry<String, Object> e : ((Map<String, Object>) m.get("portionsPerDay")).entrySet()) {
            portions.put(e.getKey(), ((Number) e.getValue()).intValue());
        }
        List<String> order = new ArrayList<>();
        for (Object o : (List<Object>) m.get("packOrder")) {
            order.add((String) o);
        }
        return new KennelPantry(new Rules(n(m, "milkLPerFedGoat"), (int) n(m, "hayPerGoat"),
            (int) n(m, "starkibblePerWateredPlant"), n(rec, "milkL"), (int) n(rec, "starkibble"),
            (int) n(rec, "portions"), (int) n(m, "bowls"), (int) n(m, "portionsPerBowl"), portions, order,
            (int) n(m, "hungerDrainPctPerStage"), (int) n(m, "hungerDrainCapPct"),
            (int) n((Map<String, Object>) m.get("quest"), "days")));
    }

    private static double n(Map<String, Object> m, String k) {
        if (!(m.get(k) instanceof Number x)) {
            throw new IllegalArgumentException("kennel food missing number " + k);
        }
        return x.doubleValue();
    }

    public State empty() {
        return new State(0, 0, Map.of());
    }

    /** Daily portions the pack needs. */
    public int need(List<Pet> pack) {
        int t = 0;
        for (Pet p : pack) {
            t += ration(p);
        }
        return t;
    }

    private int ration(Pet p) {
        Integer n = r.portions().get(p.kind());
        if (n == null) {
            throw new IllegalArgumentException("unknown pet kind " + p.kind());
        }
        return n;
    }

    /** The pack sorted into eating order (stable for ties). */
    public List<Pet> eatingOrder(List<Pet> pack) {
        List<Pet> o = new ArrayList<>(pack);
        o.sort(Comparator.comparingInt(p -> {
            int i = r.packOrder().indexOf(p.kind());
            return i < 0 ? Integer.MAX_VALUE : i;
        }));
        return o;
    }

    public DayReport day(State s, Day d, List<Pet> pack) {
        int fedGoats = Math.max(0, Math.min(d.goats(), d.hayBales() / r.hayPerGoat()));
        double milk = fedGoats * r.milkPerGoat();
        int stark = s.starkibble() + Math.max(0, d.wateredStarkibble()) * r.starkibblePerPlant();
        int milkBatches = (int) Math.floor(milk / r.recipeMilkL() + 1e-9);
        int batches = Math.min(milkBatches, stark / r.recipeStarkibble());
        double spoiled = milk - batches * r.recipeMilkL();
        stark -= batches * r.recipeStarkibble();
        int kibble = s.kibble() + batches * r.recipePortions();
        int capacity = r.bowls() * r.portionsPerBowl();
        int served = 0;
        Map<String, Integer> hunger = new TreeMap<>(s.hunger());
        List<String> order = new ArrayList<>();
        List<String> hungry = new ArrayList<>();
        for (Pet p : eatingOrder(pack)) {
            order.add(p.name());
            int want = ration(p);
            if (kibble >= want && served + want <= capacity) {
                kibble -= want;
                served += want;
                hunger.remove(p.name());
            } else {
                hunger.merge(p.name(), 1, Integer::sum);
                hungry.add(p.name());
            }
        }
        return new DayReport(new State(kibble, stark, hunger), milk, spoiled, batches * r.recipePortions(), served,
            order, hungry);
    }

    public record QuestResult(String questId, boolean passed, List<DayReport> log) {
        public QuestResult {
            log = List.copyOf(log);
        }
    }

    /** "Pack Order": empty pantry, the same inputs every day; passes if nobody goes hungry on any quest day. */
    public QuestResult packOrder(List<Pet> pack, Day everyDay) {
        State s = empty();
        List<DayReport> log = new ArrayList<>();
        boolean ok = true;
        for (int i = 0; i < r.questDays(); i++) {
            DayReport rep = day(s, everyDay, pack);
            log.add(rep);
            ok &= rep.hungry().isEmpty();
            s = rep.state();
        }
        return new QuestResult("kennel_pack_order", ok, log);
    }

    /** Fewest hay-fed goats that pass "Pack Order" with plenty of Starkibble, or -1 if the bowls can't serve the pack. */
    public int minGoats(List<Pet> pack) {
        for (int g = 0; g <= 64; g++) {
            if (packOrder(pack, new Day(g, g * r.hayPerGoat(), 64)).passed()) {
                return g;
            }
        }
        return -1;
    }
}
