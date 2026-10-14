// SPDX-License-Identifier: MIT
package com.daedalus.world.land;

import org.junit.jupiter.api.Test;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HashSet;
import java.util.HexFormat;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class LandGridTest {
    @Test void agreesWithNativeForEveryCellAndEveryEstateCandidate() throws Exception {
        // Produced by compiling core-test/land_grid_parity.cpp against DaedalusLandGrid.h,
        // normalizing CRLF to LF. 10,000 addressing rows +40,000 estate candidates.
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        for (int n = 0; n < LandGrid.COUNT; n++) {
            var c = LandGrid.cell(n);
            var m = LandGrid.metres(n);
            String row = n + "," + c.x() + "," + c.y() + "," + LandGrid.number(c.x(), c.y())
                    + "," + LandGrid.ring(n) + "," + LandGrid.district(n)
                    + "," + (int) m.east() + "," + (int) m.north() + "\n";
            digest.update(row.getBytes(StandardCharsets.US_ASCII));
        }
        for (int y = 0; y < LandGrid.SIDE; y++) {
            for (int x = 0; x < LandGrid.SIDE; x++) {
                for (int size = 1; size <= 4; size++) {
                    String row = x + "," + y + "," + size + "," + LandGrid.estate(x, y, size) + "\n";
                    digest.update(row.getBytes(StandardCharsets.US_ASCII));
                }
            }
        }
        assertThat(HexFormat.of().formatHex(digest.digest()))
                .isEqualTo("182c90b14151708051576a1bb57feedb3442c7fbc4e12e8317bd244ee2aaee21");
    }

    @Test void coversEveryCellOnceAndRoundTripsWithBothPitches() {
        var seen = new HashSet<LandGrid.Cell>();
        for (int n = 0; n < LandGrid.COUNT; n++) {
            var cell = LandGrid.cell(n);
            assertThat(seen.add(cell)).isTrue();
            assertThat(LandGrid.number(cell.x(), cell.y())).isEqualTo(n);
            for (double pitch : new double[]{256, 512}) {
                var m = LandGrid.metres(n, pitch);
                assertThat(LandGrid.numberAtMetres(m.east(), m.north(), pitch)).isEqualTo(n);
            }
        }
        assertThat(seen).hasSize(10_000);
        assertThat(LandGrid.cell(0)).isEqualTo(new LandGrid.Cell(50, 50));
        assertThat(LandGrid.cell(1)).isEqualTo(new LandGrid.Cell(51, 50));
        assertThat(LandGrid.cell(9)).isEqualTo(new LandGrid.Cell(52, 49));
    }

    @Test void rejectsInvalidAddressesAndEstatesWithoutOverflow() {
        for (int n : new int[]{-1, 10_000, Integer.MIN_VALUE, Integer.MAX_VALUE}) {
            assertThat(LandGrid.valid(n)).isFalse();
            assertThat(LandGrid.cell(n)).isEqualTo(new LandGrid.Cell(-1, -1));
            assertThat(LandGrid.ring(n)).isEqualTo(-1);
            assertThat(LandGrid.district(n)).isEqualTo(-1);
            assertThatThrownBy(() -> LandGrid.metres(n)).isInstanceOf(IllegalArgumentException.class);
        }
        assertThat(LandGrid.number(-1, 0)).isEqualTo(-1);
        assertThat(LandGrid.number(0, 100)).isEqualTo(-1);
        assertThat(LandGrid.number(100, 0)).isEqualTo(-1);
        assertThat(LandGrid.number(0, -1)).isEqualTo(-1);
        assertThat(LandGrid.estate(49, 49, 2)).isEqualTo(-1);
        assertThat(LandGrid.estate(48, 48, 2)).isGreaterThanOrEqualTo(0);
        assertThat(LandGrid.estate(50, 50, 2)).isZero();
        for (int[] e : new int[][]{{-1,0,1},{0,-1,1},{0,0,0},{0,0,5},
                {Integer.MAX_VALUE,0,4},{0,Integer.MAX_VALUE,4},{98,98,4}}) {
            assertThat(LandGrid.estate(e[0], e[1], e[2])).isEqualTo(-1);
        }
    }

    @Test void handlesHalfCellEdgesAndRejectsNonFiniteInputs() {
        assertThat(LandGrid.numberAtMetres(-128, 0)).isZero();
        assertThat(LandGrid.numberAtMetres(128, 0)).isEqualTo(1);
        assertThat(LandGrid.numberAtMetres(-12928, 0)).isEqualTo(LandGrid.number(0, 50));
        assertThat(LandGrid.numberAtMetres(-12928.01, 0)).isEqualTo(-1);
        assertThat(LandGrid.numberAtMetres(12672, 0)).isEqualTo(-1);
        for (double bad : new double[]{Double.NaN, Double.POSITIVE_INFINITY, Double.NEGATIVE_INFINITY,
                Double.MAX_VALUE, -Double.MAX_VALUE}) {
            assertThat(LandGrid.numberAtMetres(bad, 0)).isEqualTo(-1);
            assertThat(LandGrid.numberAtMetres(0, bad)).isEqualTo(-1);
        }
        for (double pitch : new double[]{0, -1, Double.NaN, Double.POSITIVE_INFINITY, Double.MAX_VALUE}) {
            assertThatThrownBy(() -> LandGrid.metres(0, pitch)).isInstanceOf(IllegalArgumentException.class);
            assertThatThrownBy(() -> LandGrid.numberAtMetres(0, 0, pitch)).isInstanceOf(IllegalArgumentException.class);
        }
    }
}
