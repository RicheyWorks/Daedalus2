// SPDX-License-Identifier: MIT

package com.daedalus.world.tactics;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.tactics.SquadDirector.Unit;
import com.daedalus.world.tactics.TacticalOrders.ParseResult;
import com.daedalus.world.tactics.TacticalOrders.Side;
import com.daedalus.world.tactics.TacticalOrders.Vec;
import com.daedalus.world.tactics.TacticalOrders.Verb;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;

import org.junit.jupiter.api.Test;

/** DTO 1 and the baseline director (ADR-060): the Java port must agree with the Unreal plugin's C++ byte for byte. */
class TacticsParityTest {

    /** Written by engines/unreal/core-test/tactics_core_test.cpp --write. */
    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "tactics_parity.txt");

    private static String unescape(String s) {
        return s.replace("\\r", "\r").replace("\\n", "\n");
    }

    @Test
    void decidesTheSame40SquadsAsCpp() throws IOException {
        List<String> lines = Files.readAllLines(PARITY);
        int cases = 0;
        for (int i = 0; i < lines.size(); i++) {
            String line = lines.get(i);
            if (!line.startsWith("case ")) {
                continue;
            }
            String[] c = line.split(" ");
            int id = Integer.parseInt(c[1]);
            Vec player = new Vec(Double.parseDouble(c[3]), Double.parseDouble(c[4]), Double.parseDouble(c[5]));
            List<Unit> units = new ArrayList<>();
            int j = i + 1;
            for (; lines.get(j).startsWith("unit "); j++) {
                String[] u = lines.get(j).split(" ");
                units.add(new Unit(u[1], new Vec(Double.parseDouble(u[2]), Double.parseDouble(u[3]), Double.parseDouble(u[4])),
                        Double.parseDouble(u[5]), Double.parseDouble(u[6]), u[7].equals("1")));
            }
            assertThat(lines.get(j)).isEqualTo("spec");
            StringBuilder want = new StringBuilder();
            for (j = j + 1; !lines.get(j).equals("end"); j++) {
                want.append(lines.get(j)).append('\n');
            }
            String got = TacticalOrders.write(SquadDirector.decide("sq-" + id, id, units, player));
            assertThat(got).as("case %d", id).isEqualTo(want.toString());
            // the same world in another order decides the same
            List<Unit> shuffled = new ArrayList<>(units);
            Collections.shuffle(shuffled, new Random(id));
            assertThat(TacticalOrders.write(SquadDirector.decide("sq-" + id, id, shuffled, player))).isEqualTo(got);
            // and its spec reads back to itself
            ParseResult again = TacticalOrders.parse(got);
            assertThat(again.ok()).as(again.error()).isTrue();
            assertThat(TacticalOrders.write(again.spec())).isEqualTo(got);
            cases++;
        }
        assertThat(cases).isEqualTo(40);
    }

    @Test
    void refusesTheSameSpecsWithTheSameMessages() throws IOException {
        int bad = 0;
        for (String line : Files.readAllLines(PARITY)) {
            if (line.startsWith("bad\t")) {
                String[] p = line.split("\t", -1);
                ParseResult r = TacticalOrders.parse(unescape(p[1]));
                assertThat(r.ok()).as(p[1]).isFalse();
                assertThat(r.error()).as(p[1]).isEqualTo(p[2]);
                assertThat(r.spec()).isNull();
                bad++;
            } else if (line.startsWith("good\t")) {
                ParseResult r = TacticalOrders.parse(unescape(line.substring(5)));
                assertThat(r.ok()).as(r.error()).isTrue();
                assertThat(r.spec().orders()).hasSize(3);
                assertThat(r.spec().orders().get(0).why()).isEqualTo("player keeps to the ridge");
                assertThat(r.spec().orders().get(0).side()).isEqualTo(Side.LEFT);
                assertThat(r.spec().orders().get(1).verb()).isEqualTo(Verb.RETREAT);
            }
        }
        assertThat(bad).isEqualTo(21);
    }

    @Test
    void writesNumbersLikeCPrintf() {
        assertThat(TacticalOrders.num(0.25)).isEqualTo("0.2");     // an exact tie goes to even, as printf does
        assertThat(TacticalOrders.num(0.35)).isEqualTo("0.3");     // 0.35 is really 0.34999..., so down
        assertThat(TacticalOrders.num(-0.04)).isEqualTo("-0.0");   // printf keeps the sign
        assertThat(TacticalOrders.num(-0.0)).isEqualTo("-0.0");
        assertThat(TacticalOrders.num(1234.56)).isEqualTo("1234.6");
    }

    @Test
    void writesEventsAsDte1() {
        String e = TacticalOrders.writeEvents(7, List.of(
                new TacticalOrders.Event(TacticalOrders.EventKind.HIT, "foe-a", new Vec(1, 2, 3), 12.5),
                new TacticalOrders.Event(TacticalOrders.EventKind.PLAYER, "player", new Vec(0, 0, 0), 80)));
        assertThat(e).isEqualTo("DTE 1\ntick 7\nevent HIT foe-a 1.0 2.0 3.0 12.5\nevent PLAYER player 0.0 0.0 0.0 80.0\n");
    }

    @Test
    void threeFoesOnePlayer() {
        List<Unit> three = List.of(new Unit("foe-a", new Vec(-600, 0, 0), 60, 60, true),
                new Unit("foe-b", new Vec(-900, 300, 0), 60, 60, true),
                new Unit("foe-c", new Vec(-1100, -200, 0), 10, 60, false));
        var spec = SquadDirector.decide("orr-1", 1, three, new Vec(0, 0, 0));
        assertThat(spec.orders()).extracting(o -> o.verb()).containsExactly(Verb.ATTACK, Verb.FLANK, Verb.RETREAT);
        assertThat(spec.orders().get(2).why()).isEqualTo("health 16%");
    }

    @Test
    void aDistanceTieGoesByName() {
        List<Unit> tie = List.of(new Unit("b", new Vec(-500, 0, 0), 1, 1, true), new Unit("a", new Vec(500, 0, 0), 1, 1, true));
        var spec = SquadDirector.decide("s", 1, tie, new Vec(0, 0, 0));
        assertThat(spec.orders().get(0).unit()).isEqualTo("a");
        assertThat(spec.orders().get(0).verb()).isEqualTo(Verb.ATTACK);
    }

    @Test
    void readsTheCppRosterAndRefusesBadOnes() throws IOException {
        String line = Files.readAllLines(PARITY).stream().filter(l -> l.startsWith("roster\t")).findFirst().orElseThrow();
        TacticalOrders.Roster r = TacticalOrders.parseRoster(unescape(line.substring(7)));
        assertThat(r.session()).isEqualTo("a1b2c3");
        assertThat(r.squad()).isEqualTo("pack-1");
        assertThat(r.tick()).isEqualTo(9);
        assertThat(r.units()).hasSize(2);
        assertThat(r.units().get(0).kind()).isEqualTo("BLIGHT_SLIME");
        assertThat(r.units().get(0).health()).isEqualTo(42.5);
        assertThat(r.units().get(0).seesPlayer()).isTrue();
        assertThat(r.units().get(1).maxHealth()).isEqualTo(120);
        assertThat(r.units().get(1).at().x()).isEqualTo(-4.2);
        for (String bad : List.of("", "DTO 1\n", "DTR 1\nsession s squad q\n", "DTR 1\nsession s squad q tick -1\n",
                "DTR 1\nsession s squad q tick 1\nunit a K -1 60 0 0 0 1\n", "DTR 1\nsession s squad q tick 1\nunit a K 1 60 0 0 0 2\n",
                "DTR 1\nsession s squad q tick 1\nunit a K 1 60 nan 0 0 1\n")) {
            org.assertj.core.api.Assertions.assertThatThrownBy(() -> TacticalOrders.parseRoster(bad))
                    .as(bad).isInstanceOf(IllegalArgumentException.class);
        }
    }

    @Test
    void aSquadOver256OrdersItsNearest256() {
        List<Unit> big = new ArrayList<>();
        for (int i = 0; i < 300; i++) {
            big.add(new Unit("b" + i, new Vec(-500.0 - i, 0, 0), 60, 60, true));
        }
        var spec = SquadDirector.decide("big", 1, big, new Vec(0, 0, 0));
        assertThat(spec.orders()).hasSize(TacticalOrders.MAX_ORDERS);
        assertThat(spec.orders()).anyMatch(o -> o.unit().equals("b0")).noneMatch(o -> o.unit().equals("b299"));
        assertThat(TacticalOrders.parse(TacticalOrders.write(spec)).ok()).isTrue();
    }
}
