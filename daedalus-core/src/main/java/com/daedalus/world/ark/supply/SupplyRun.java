// SPDX-License-Identifier: MIT
package com.daedalus.world.ark.supply;

import com.daedalus.world.BlockCoordinate;
import com.daedalus.world.ark.ArkFleet;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.regex.Pattern;

/**
 * Ark Supply Run ("animals coordinate bounded cargo", the life-progression hook): load an ark's hold for one crossing
 * so every passenger stays fed and watered for the whole voyage and the destination island's requests arrive.
 *
 * <ul>
 *   <li>The voyage takes {@link ArkFleet#duration} between the two berths; passengers eat and drink per started
 *       minute, so rations come off the top before requests are counted.</li>
 *   <li>The hold has a weight and a volume limit; the animal crew has a carry limit (kg per trip x trips) and rests
 *       instead of overloading.</li>
 *   <li>{@link #deliver} settles exactly once: a second call returns the same {@link Delivery}.</li>
 * </ul>
 * Pure and clock-free; the host passes times, owns inventories and persistence. Not thread-safe (one run per host
 * session).
 */
public final class SupplyRun {

    /** Hold limits (proposed). */
    public static final int HOLD_KG = 1_000;
    public static final int HOLD_VOLUME = 120;
    /** One watch: rations are drawn per started 15 seconds of sailing (game time). */
    public static final long WATCH_MS = 15_000;

    static final Pattern KEY = Pattern.compile("[a-z0-9][a-z0-9_.:-]{0,95}");

    public enum LoadResult { LOADED, OVER_WEIGHT, OVER_VOLUME, CREW_TIRED }

    public enum Status { LOADING, SAILING, DELIVERED }

    /** What is missing before departure (empty lists mean ready). */
    public record Check(int waterShort, int fodderShort, List<String> requestsShort) {
        public Check {
            requestsShort = List.copyOf(requestsShort);
        }

        public boolean ready() { return waterShort == 0 && fodderShort == 0 && requestsShort.isEmpty(); }
    }

    /** The settled run. */
    public record Delivery(String arkId, int watches, int kgCarried, int requestsMet, int requestsTotal,
                           int passengersFed, int passengersTotal, long arrivedAtMs) {
        public boolean complete() { return requestsMet == requestsTotal && passengersFed == passengersTotal; }
    }

    private final String arkId;
    private final long durationMs;
    private final int watches;
    private final List<Passenger> passengers;
    private final List<CrewMember> crew;
    private final List<SupplyRequest> requests;
    private final EnumMap<Cargo, Integer> hold = new EnumMap<>(Cargo.class);
    private int kg;
    private int volume;
    private Status status = Status.LOADING;
    private long departAt;
    private Delivery delivery;

    public SupplyRun(String arkId, BlockCoordinate fromBerth, BlockCoordinate toBerth, List<Passenger> passengers,
                     List<CrewMember> crew, List<SupplyRequest> requests) {
        this.arkId = key(arkId, "arkId");
        if (fromBerth == null || toBerth == null) throw new IllegalArgumentException("berths required");
        this.passengers = List.copyOf(passengers);
        this.crew = List.copyOf(crew);
        this.requests = List.copyOf(requests);
        if (this.crew.isEmpty()) throw new IllegalArgumentException("an ark needs at least one crew member");
        if (this.passengers.size() > 64 || this.crew.size() > 16 || this.requests.size() > 16)
            throw new IllegalArgumentException("at most 64 passengers, 16 crew, 16 requests");
        this.durationMs = ArkFleet.duration(fromBerth, toBerth);
        this.watches = (int) Math.max(1, (durationMs + WATCH_MS - 1) / WATCH_MS);
    }

    /** Started watches (15 s each) of the crossing. */
    public int watches() { return watches; }

    public long durationMs() { return durationMs; }

    /** Water casks the passengers drink on this crossing. */
    public int waterNeeded() { return passengers.stream().mapToInt(p -> p.waterPerWatch() * watches).sum(); }

    /** Fodder bales the passengers eat on this crossing. */
    public int fodderNeeded() { return passengers.stream().mapToInt(p -> p.fodderPerWatch() * watches).sum(); }

    /** Kilograms the whole crew can carry before resting. */
    public int crewCapacityKg() { return crew.stream().mapToInt(CrewMember::capacityKg).sum(); }

    /** Carries {@code units} of a cargo aboard, all or nothing. */
    public LoadResult load(Cargo cargo, int units) {
        if (status != Status.LOADING) throw new IllegalStateException("the ark has sailed");
        if (cargo == null || units < 1 || units > 1_000) throw new IllegalArgumentException("cargo and units 1..1000");
        int addKg = cargo.kg() * units, addVol = cargo.volume() * units;
        if (kg + addKg > HOLD_KG) return LoadResult.OVER_WEIGHT;
        if (volume + addVol > HOLD_VOLUME) return LoadResult.OVER_VOLUME;
        if (kg + addKg > crewCapacityKg()) return LoadResult.CREW_TIRED;
        hold.merge(cargo, units, Integer::sum);
        kg += addKg;
        volume += addVol;
        return LoadResult.LOADED;
    }

    public int units(Cargo c) { return hold.getOrDefault(c, 0); }

    public int kg() { return kg; }

    public int volume() { return volume; }

    /** What is still missing: rations first, then each request after rations are set aside. */
    public Check check() {
        Map<Cargo, Integer> left = new EnumMap<>(hold);
        int waterShort = take(left, Cargo.WATER_CASK, waterNeeded());
        int fodderShort = take(left, Cargo.FODDER_BALE, fodderNeeded());
        List<String> shortReq = new ArrayList<>();
        for (SupplyRequest r : requests) if (take(left, r.cargo(), r.units()) > 0) shortReq.add(r.requestId());
        return new Check(waterShort, fodderShort, shortReq);
    }

    /** Casts off. A run can sail short (the captain's call); {@link #deliver} reports what arrived. */
    public void depart(long nowMs) {
        if (status != Status.LOADING) throw new IllegalStateException("already sailed");
        status = Status.SAILING;
        departAt = nowMs;
    }

    /** True once the ark has had time to cross. */
    public boolean arrived(long nowMs) { return status != Status.LOADING && nowMs >= departAt + durationMs; }

    /**
     * Settles the run once, on arrival: passengers eat and drink in list order, then requests are filled in list
     * order from what is left. A second call returns the same delivery.
     */
    public Optional<Delivery> deliver(long nowMs) {
        if (delivery != null) return Optional.of(delivery);
        if (!arrived(nowMs)) return Optional.empty();
        Map<Cargo, Integer> left = new EnumMap<>(hold);
        int fed = 0;
        for (Passenger p : passengers) {
            int w = p.waterPerWatch() * watches, f = p.fodderPerWatch() * watches;
            if (left.getOrDefault(Cargo.WATER_CASK, 0) >= w && left.getOrDefault(Cargo.FODDER_BALE, 0) >= f) {
                take(left, Cargo.WATER_CASK, w);
                take(left, Cargo.FODDER_BALE, f);
                fed++;
            }
        }
        int met = 0;
        for (SupplyRequest r : requests) {
            if (left.getOrDefault(r.cargo(), 0) >= r.units()) {
                take(left, r.cargo(), r.units());
                met++;
            }
        }
        status = Status.DELIVERED;
        delivery = new Delivery(arkId, watches, kg, met, requests.size(), fed, passengers.size(), departAt + durationMs);
        return Optional.of(delivery);
    }

    public Status status() { return status; }

    /** Takes up to {@code n} from the map; returns how many were missing. */
    private static int take(Map<Cargo, Integer> m, Cargo c, int n) {
        int have = m.getOrDefault(c, 0);
        int used = Math.min(have, n);
        m.put(c, have - used);
        return n - used;
    }

    static String key(String v, String name) {
        if (v == null || !KEY.matcher(v).matches()) throw new IllegalArgumentException(name + " must match " + KEY.pattern());
        return v;
    }
}
