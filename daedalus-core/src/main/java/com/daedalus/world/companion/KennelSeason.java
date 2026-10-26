// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Kennel Isle season sim (contest gap G54). One daily tick runs the whole roster through the G17
 * {@link KennelWaterLoop}, the G26 {@link KennelPantry} and the G37 {@link KennelBond}: a pet the cistern couldn't
 * water or the bowls couldn't feed has a neglect day; everyone else gains bond, plus tonic and fetch where the keeper
 * gave them. Pure and deterministic.
 *
 * <p>Storyline chapter "Storm Season" ({@link #stormSeason}): the season passes when nobody had a neglect day and
 * every pet ends at least {@link KennelBond.Tier#FAMILIAR}.
 */
public final class KennelSeason {
    /** A pet with its kind in the water table, its kind in the food table, and its starting bond. */
    public record Member(String name, String waterKind, String foodKind, int bond) { }

    /** One day: weather and keeper choices for water and food, plus who got a tonic and how many fetch catches. */
    public record SeasonDay(KennelWaterLoop.Day water, KennelPantry.Day food, Set<String> tonics,
                            Map<String, Integer> fetch) {
        public SeasonDay {
            tonics = Set.copyOf(tonics);
            fetch = Map.copyOf(fetch);
        }

        public static SeasonDay plain(KennelWaterLoop.Day water, KennelPantry.Day food) {
            return new SeasonDay(water, food, Set.of(), Map.of());
        }
    }

    public record DayLog(Map<String, Integer> bonds, List<String> thirsty, List<String> hungry, double cisternL,
                         int kibble) {
        public DayLog {
            bonds = Collections.unmodifiableMap(new LinkedHashMap<>(bonds));
            thirsty = List.copyOf(thirsty);
            hungry = List.copyOf(hungry);
        }
    }

    public record SeasonResult(List<DayLog> days, Map<String, Integer> finalBonds, Map<String, Integer> neglectDays) {
        public SeasonResult {
            days = List.copyOf(days);
            finalBonds = Collections.unmodifiableMap(new LinkedHashMap<>(finalBonds));
            neglectDays = Collections.unmodifiableMap(new LinkedHashMap<>(neglectDays));
        }
    }

    private final KennelWaterLoop water;
    private final KennelPantry pantry;
    private final KennelBond.Rules bondRules;

    public KennelSeason(KennelWaterLoop water, KennelPantry pantry, KennelBond.Rules bondRules) {
        this.water = water;
        this.pantry = pantry;
        this.bondRules = bondRules;
    }

    /** Runs the season from an empty cistern and pantry. */
    public SeasonResult run(List<Member> roster, List<SeasonDay> days, int herbPlants) {
        List<KennelWaterLoop.Animal> animals = new ArrayList<>();
        List<KennelPantry.Pet> pack = new ArrayList<>();
        Map<String, Integer> bonds = new LinkedHashMap<>();
        Map<String, Integer> neglect = new LinkedHashMap<>();
        for (Member m : roster) {
            animals.add(new KennelWaterLoop.Animal(m.name(), m.waterKind()));
            pack.add(new KennelPantry.Pet(m.name(), m.foodKind()));
            bonds.put(m.name(), m.bond());
            neglect.put(m.name(), 0);
        }
        KennelWaterLoop.State ws = water.start(0);
        KennelPantry.State ps = pantry.empty();
        List<DayLog> log = new ArrayList<>();
        for (SeasonDay d : days) {
            KennelWaterLoop.DayReport wr = water.day(ws, d.water(), animals, herbPlants);
            KennelPantry.DayReport pr = pantry.day(ps, d.food(), pack);
            ws = wr.state();
            ps = pr.state();
            for (Member m : roster) {
                boolean watered = !wr.thirsty().contains(m.name());
                KennelBond.Care c = KennelBond.careFromPantry(pr, m.name(), watered, d.tonics().contains(m.name()),
                    d.fetch().getOrDefault(m.name(), 0));
                if (c.neglected()) {
                    neglect.merge(m.name(), 1, Integer::sum);
                }
                bonds.put(m.name(), KennelBond.step(bonds.get(m.name()), c, bondRules));
            }
            log.add(new DayLog(bonds, wr.thirsty(), pr.hungry(), ws.cisternL(), ps.kibble()));
        }
        return new SeasonResult(log, bonds, neglect);
    }

    /** "Storm Season" passes: no neglect day for anyone and every pet ends at least Familiar. */
    public static boolean stormSeason(SeasonResult r) {
        return r.neglectDays().values().stream().allMatch(n -> n == 0)
            && r.finalBonds().values().stream()
                .allMatch(b -> KennelBond.Tier.of(b).compareTo(KennelBond.Tier.FAMILIAR) >= 0);
    }

    /** The chapter's 7 days: 2 clear prep days with the given food plan, then a 3-day storm, then 2 clear days. */
    public static List<SeasonDay> stormWeek(KennelPantry.Day prep, KennelPantry.Day stormFood) {
        KennelWaterLoop.Day clear = new KennelWaterLoop.Day(false, true, false, false, 0);
        KennelWaterLoop.Day storm = new KennelWaterLoop.Day(true, false, true, true, 0);
        List<SeasonDay> out = new ArrayList<>();
        for (int i = 0; i < 7; i++) {
            boolean stormy = i >= 2 && i <= 4;
            out.add(SeasonDay.plain(stormy ? storm : clear, stormy ? stormFood : prep));
        }
        return out;
    }
}