// SPDX-License-Identifier: MIT

package com.daedalus.world.ark.supply;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.BlockCoordinate;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;

/**
 * C++ = Java, line for line (G29 native binding): engines/unreal/core-test/ark_supply_parity.txt is written by
 * ark_supply_core_test.cpp --write from DaedalusArkSupplyCore.h. Here the same lines come from the real
 * {@link SupplyRun}, {@link SupplyRequest#forIsland} and ArkFleet.duration.
 */
class ArkSupplyParityTest {

    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "ark_supply_parity.txt");

    static long islandSeed(int s) {
        return s % 2 == 0 ? s * 1_000_003L : -s * 1_000_003L - 1;
    }

    static List<String> scenario(int s) {
        List<String> out = new ArrayList<>();
        long isle = islandSeed(s);
        List<SupplyRequest> reqs = SupplyRequest.forIsland(isle);
        List<Passenger> p = new ArrayList<>();
        for (int i = 0; i < s % 5; i++) {
            p.add(new Passenger("p" + i, "sheep", 1 + i % 3, (i % 2) * 2));
        }
        List<CrewMember> c = new ArrayList<>();
        for (int i = 0; i < 1 + s % 3; i++) {
            c.add(new CrewMember("c" + i, "deckhand", 40 + 15 * i, 2 + (s + i) % 4));
        }
        SupplyRun r = new SupplyRun("ark-" + s, new BlockCoordinate(0, 64, 0),
                new BlockCoordinate(s * 37 % 500, 64 + s % 7, s * 53 % 400), p, c, reqs);
        StringBuilder l = new StringBuilder("run s=" + s + " isle=" + isle + " ok=1 dur=" + r.durationMs() + " watches="
                + r.watches() + " water=" + r.waterNeeded() + " fodder=" + r.fodderNeeded() + " cap="
                + r.crewCapacityKg() + " reqs=");
        for (SupplyRequest q : reqs) {
            l.append(q.requestId()).append(":").append(q.cargo()).append(":").append(q.units()).append("|");
        }
        out.add(l.toString());
        StringBuilder ld = new StringBuilder("load s=" + s);
        List<Object[]> plan = new ArrayList<>();
        plan.add(new Object[] {Cargo.WATER_CASK, r.waterNeeded()});
        plan.add(new Object[] {Cargo.FODDER_BALE, r.fodderNeeded()});
        for (SupplyRequest q : reqs) {
            plan.add(new Object[] {q.cargo(), q.units()});
        }
        plan.add(new Object[] {Cargo.TIMBER_BUNDLE, 3});
        plan.add(new Object[] {Cargo.SALVE_JAR, 50});
        plan.add(new Object[] {Cargo.WATER_CASK, 60});
        for (Object[] step : plan) {
            Cargo x = (Cargo) step[0];
            int n = (Integer) step[1];
            if (n > 0) {
                ld.append(" ").append(x).append("x").append(n).append("=").append(r.load(x, n));
            }
        }
        SupplyRun.Check k = r.check();
        ld.append(" kg=").append(r.kg()).append(" vol=").append(r.volume()).append(" check=").append(k.waterShort())
                .append(",").append(k.fodderShort()).append(" short=");
        k.requestsShort().forEach(x -> ld.append(x).append("|"));
        ld.append(" ready=").append(k.ready() ? "1" : "0");
        out.add(ld.toString());
        r.depart(1000);
        long at = 1000 + r.durationMs();
        String early = (r.arrived(at - 1) ? "1" : "0") + "," + (r.deliver(at - 1).isPresent() ? "1" : "0");
        StringBuilder dv = new StringBuilder("sail s=" + s + " status=" + r.status() + " early=" + early);
        Optional<SupplyRun.Delivery> got = r.deliver(at);
        SupplyRun.Delivery d = got.orElseThrow();
        dv.append(" got=1 ark=").append(d.arkId()).append(" watches=").append(d.watches()).append(" kg=")
                .append(d.kgCarried()).append(" met=").append(d.requestsMet()).append("/").append(d.requestsTotal())
                .append(" fed=").append(d.passengersFed()).append("/").append(d.passengersTotal()).append(" at=")
                .append(d.arrivedAtMs()).append(" complete=").append(d.complete() ? "1" : "0");
        dv.append(" again=").append(r.deliver(at + 99_999).orElseThrow().arrivedAtMs()).append(" status=").append(r.status());
        out.add(dv.toString());
        return out;
    }

    @Test
    void cppCoreMatchesJavaSupplyRunLineForLine() throws Exception {
        List<String> want = new ArrayList<>();
        for (int s = 0; s < 20; s++) {
            want.addAll(scenario(s));
        }
        List<String> got = Files.readAllLines(PARITY, StandardCharsets.UTF_8).stream()
                .filter(l -> !l.startsWith("#")).toList();
        assertThat(got).containsExactlyElementsOf(want);
    }
}