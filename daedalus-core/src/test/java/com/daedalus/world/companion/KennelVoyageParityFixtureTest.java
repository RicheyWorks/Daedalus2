// SPDX-License-Identifier: MIT

package com.daedalus.world.companion;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.companion.KennelArkLandfall.Landfall;
import com.daedalus.world.companion.KennelArkVoyage.Trouble;
import com.daedalus.world.companion.KennelArkVoyage.Voyage;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.SplittableRandom;

import org.junit.jupiter.api.Test;

/**
 * Contest gap G154: the Java G140 storm-belt legs ({@link KennelArkVoyage#crossRolls}) and G147 Cinder Shelf repair days
 * ({@link KennelArkLandfall#repairRolls}) written as a parity table that the header-only C++ twin
 * {@code DaedalusKennelVoyageCore.h} replays in {@code engines/unreal/core-test/kennel_voyage_core_test.cpp}. Post odds,
 * troubles and rolls come from a 64-bit LCG that both sides share. Regenerated into target/ every run and must match
 * the committed copy byte for byte.
 */
class KennelVoyageParityFixtureTest {
    static final int CROSSINGS = 300;
    static final int REPAIRS = 300;
    static final long SEED = 20261019154L;

    private long x = SEED;

    private long next() {
        x = x * 6364136223846793005L + 1442695040888963407L;
        return x >>> 33;
    }

    private int[] pcts() {
        int[] p = new int[KennelArkMuster.ROLES.size()];
        for (int i = 0; i < p.length; i++) {
            p[i] = next() % 4 == 0 ? -1 : (int) (next() % 101);
        }
        return p;
    }

    static KennelArkMuster.Roster roster(int[] pcts) {
        List<KennelArkMuster.Post> posts = new ArrayList<>();
        List<String> unfilled = new ArrayList<>();
        int total = 0;
        for (int i = 0; i < pcts.length; i++) {
            String role = KennelArkMuster.ROLES.get(i);
            if (pcts[i] < 0) {
                unfilled.add(role);
            } else {
                posts.add(new KennelArkMuster.Post(role, "h" + i, pcts[i]));
                total += pcts[i];
            }
        }
        return new KennelArkMuster.Roster(posts, unfilled, total);
    }

    private static void appendPcts(StringBuilder b, int[] p) {
        for (int v : p) {
            b.append(' ').append(Math.max(0, v));
        }
    }

    static int voyageFail(String reason) {
        return reason == null ? 0 : "the hull gave way".equals(reason) ? 1 : 2;
    }

    static int landfallFail(String reason) {
        return reason == null ? 0 : "the casks ran dry on the shelf".equals(reason) ? 1 : 2;
    }

    List<String> table() {
        List<String> out = new ArrayList<>();
        out.add("VOYAGE 1");
        x = SEED;
        for (int k = 0; k < CROSSINGS; k++) {
            int[] p = pcts();
            int n = (int) (next() % (KennelArkVoyage.LEGS + 1));
            List<Trouble> ts = new ArrayList<>();
            int[] rolls = new int[n];
            StringBuilder b = new StringBuilder("cross");
            appendPcts(b, p);
            b.append(' ').append(n);
            for (int i = 0; i < n; i++) {
                ts.add(Trouble.values()[(int) (next() % Trouble.values().length)]);
                b.append(' ').append(ts.get(i).ordinal());
            }
            for (int i = 0; i < n; i++) {
                rolls[i] = (int) (next() % 100);
                b.append(' ').append(rolls[i]);
            }
            Voyage v = KennelArkVoyage.crossRolls(roster(p), ts, rolls);
            b.append(" = ").append(v.arrived() ? 1 : 0).append(' ').append(v.legs().size()).append(' ').append(v.hull())
                .append(' ').append(v.water()).append(' ').append(voyageFail(v.failReason()));
            v.legs().forEach(l -> b.append(' ').append(l.answered() ? 1 : 0));
            out.add(b.toString());
        }
        for (int k = 0; k < REPAIRS; k++) {
            int[] p = pcts();
            int hull = 1 + (int) (next() % KennelArkLandfall.HULL_FULL);
            int water = 1 + (int) (next() % KennelArkVoyage.START_WATER);
            int stranded = (int) (next() % (KennelArkLandfall.STRANDED_COUNT + 1));
            int[] rolls = new int[KennelArkLandfall.ROLLS_PER_DAY * KennelArkLandfall.DAYS];
            StringBuilder b = new StringBuilder("repair");
            appendPcts(b, p);
            b.append(' ').append(hull).append(' ').append(water).append(' ').append(stranded);
            for (int i = 0; i < rolls.length; i++) {
                rolls[i] = (int) (next() % 100);
                b.append(' ').append(rolls[i]);
            }
            Landfall l = KennelArkLandfall.repairRolls(roster(p), hull, water,
                KennelArkLandfall.STRANDED.subList(0, stranded), rolls);
            b.append(" = ").append(l.seaworthy() ? 1 : 0).append(' ').append(l.days().size()).append(' ').append(l.hull())
                .append(' ').append(l.water()).append(' ').append(l.rescued().size()).append(' ')
                .append(landfallFail(l.failReason()));
            l.days().forEach(d -> b.append(' ').append(d.planks()).append(d.rescued() == null ? "" : "r"));
            out.add(b.toString());
        }
        return out;
    }

    @Test
    void committedVoyageParityTableMatchesJava() throws Exception {
        String want = String.join("\n", table()) + "\n";
        Path target = Path.of("target", "kennel_voyage_parity.txt");
        Files.createDirectories(target.getParent());
        Files.writeString(target, want, StandardCharsets.UTF_8);
        Path committed = Path.of("..", "engines", "unreal", "core-test", "kennel_voyage_parity.txt");
        assertThat(Files.exists(committed)).as("committed kennel_voyage_parity.txt").isTrue();
        assertThat(Files.readString(committed, StandardCharsets.UTF_8).replace("\r\n", "\n")).isEqualTo(want);
    }

    @Test
    void tableCoversArrivalsWrecksAndEveryRepairEnding() {
        List<String> t = table();
        assertThat(t).hasSize(1 + CROSSINGS + REPAIRS);
        assertThat(t).anyMatch(s -> s.startsWith("cross") && s.contains(" = 1 6 "));
        assertThat(t).anyMatch(s -> s.startsWith("cross") && s.matches(".* = 0 \\d \\d+ \\d+ 1.*"));
        assertThat(t).anyMatch(s -> s.startsWith("cross") && s.matches(".* = 0 \\d \\d+ \\d+ 2.*"));
        for (String end : new String[] {" 0( |$)", " 1( |$)", " 2( |$)"}) {
            assertThat(t).anyMatch(s -> s.startsWith("repair") && s.matches(".* = [01] \\d \\d+ \\d+ \\d" + end + ".*"));
        }
        assertThat(t).anyMatch(s -> s.startsWith("repair") && s.matches(".* = .* \\d+r( |$).*"));
    }

    @Test
    void rollDrivenRulesMatchTheSeededOnes() {
        KennelArkMuster.Roster full = KennelArkVoyageTest.FULL;
        for (long s = 0; s < 50; s++) {
            List<Trouble> ts = KennelArkVoyage.storms(s);
            SplittableRandom r = new SplittableRandom(s + 7);
            int[] cr = new int[ts.size()];
            for (int i = 0; i < cr.length; i++) {
                cr[i] = r.nextInt(100);
            }
            assertThat(KennelArkVoyage.crossRolls(full, ts, cr)).isEqualTo(KennelArkVoyage.cross(full, ts, s + 7));
            SplittableRandom q = new SplittableRandom(s);
            int[] rr = new int[KennelArkLandfall.ROLLS_PER_DAY * KennelArkLandfall.DAYS];
            for (int i = 0; i < rr.length; i++) {
                rr[i] = q.nextInt(100);
            }
            List<String> st = KennelArkLandfall.stranded(s);
            assertThat(KennelArkLandfall.repairRolls(full, 3, 7, st, rr)).isEqualTo(KennelArkLandfall.repair(full, 3, 7, st, s));
        }
    }
}