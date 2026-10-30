// SPDX-License-Identifier: MIT

package com.daedalus.world.assets;

import static org.assertj.core.api.Assertions.assertThat;

import com.daedalus.world.assets.AssetLodManifest.BudgetResult;
import com.daedalus.world.assets.AssetLodManifest.Instance;
import com.daedalus.world.assets.AssetLodManifest.Manifest;
import com.daedalus.world.assets.AssetLodManifest.ParseResult;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import org.junit.jupiter.api.Test;

/** BBA 1 and the LOD picker: the Java port must agree with the Unreal plugin's C++ byte for byte. */
class AssetLodParityTest {

    /** Written by engines/unreal/core-test/asset_lod_core_test.cpp --write. */
    private static final Path PARITY = Path.of("..", "engines", "unreal", "core-test", "asset_lod_parity.txt");

    /** Written by tools/islands/blenderboss/bba_manifest.py from the Blender LOD1 catalog. */
    private static final Path CATALOG = Path.of("..", "data", "assets", "catalog.bba");

    private static String unescape(String s) {
        return s.replace("\\r", "\r").replace("\\t", "\t").replace("\\n", "\n");
    }

    private static final String GOOD = "# from bba_manifest.py\nBBA 1\r\n"
            + "asset Prop_Rock_A lod0 1200 lod1 700 radius 90 switch 1800\n\n"
            + "asset Tree_Oak  lod0 5400 lod1 - radius 420 switch 8400\n";

    @Test
    void matchesTheCppOn40Manifests240SelectionsAnd120Budgets() throws IOException {
        List<String> lines = Files.readAllLines(PARITY);
        int cases = 0;
        int sels = 0;
        int budgets = 0;
        Manifest m = null;
        for (String line : lines) {
            if (line.startsWith("raw\t")) {
                ParseResult r = AssetLodManifest.parse(unescape(line.substring(4)));
                assertThat(r.ok()).as(r.error()).isTrue();
                m = r.manifest();
            } else if (line.startsWith("canon\t")) {
                String want = unescape(line.substring(6));
                assertThat(AssetLodManifest.write(m)).isEqualTo(want);
                assertThat(AssetLodManifest.write(AssetLodManifest.parse(want).manifest())).isEqualTo(want);
                cases++;
            } else if (line.startsWith("sel ")) {
                String[] p = line.split(" ");
                assertThat(AssetLodManifest.select(m.assets().get(Integer.parseInt(p[1])), Long.parseLong(p[2])))
                        .as(line).isEqualTo(Integer.parseInt(p[3]));
                sels++;
            } else if (line.startsWith("budget ")) {
                String[] halves = line.split(" = ");
                String[] in = halves[0].split(" ");
                List<Instance> inst = new ArrayList<>();
                for (int i = 2; i < in.length; i++) {
                    String[] ad = in[i].split(":");
                    inst.add(new Instance(Integer.parseInt(ad[0]), Long.parseLong(ad[1])));
                }
                BudgetResult b = AssetLodManifest.budget(m, inst, Long.parseLong(in[1]));
                assertThat(b.faces() + " " + b.lodString()).as(line).isEqualTo(halves[1]);
                budgets++;
            }
        }
        assertThat(cases).isEqualTo(40);
        assertThat(sels).isEqualTo(240);
        assertThat(budgets).isEqualTo(120);
    }

    @Test
    void refusesTheSameManifestsWithTheSameMessages() throws IOException {
        int bad = 0;
        for (String line : Files.readAllLines(PARITY)) {
            if (line.startsWith("bad\t")) {
                String[] p = line.split("\t", -1);
                ParseResult r = AssetLodManifest.parse(unescape(p[1]));
                assertThat(r.ok()).as(p[1]).isFalse();
                assertThat(r.error()).as(p[1]).isEqualTo(p[2]);
                assertThat(r.manifest()).isNull();
                bad++;
            }
        }
        assertThat(bad).isEqualTo(20);
    }

    @Test
    void readsAndWritesTheGoodManifest() {
        ParseResult r = AssetLodManifest.parse(GOOD);
        assertThat(r.ok()).as(r.error()).isTrue();
        assertThat(r.manifest().assets()).hasSize(2);
        assertThat(r.manifest().assets().get(1).lod1()).isEqualTo(-1);
        assertThat(AssetLodManifest.write(r.manifest())).isEqualTo("BBA 1\n"
                + "asset Prop_Rock_A lod0 1200 lod1 700 radius 90 switch 1800\n"
                + "asset Tree_Oak lod0 5400 lod1 - radius 420 switch 8400\n");
    }

    @Test
    void switchesAtTheSwitchDistance() {
        var a = AssetLodManifest.parse(GOOD).manifest().assets();
        assertThat(AssetLodManifest.select(a.get(0), 1799)).isZero();
        assertThat(AssetLodManifest.select(a.get(0), 1800)).isOne();
        assertThat(AssetLodManifest.select(a.get(1), 99_999_999)).isZero();
        assertThat(AssetLodManifest.switchFor(10)).isEqualTo(500);
        assertThat(AssetLodManifest.switchFor(90)).isEqualTo(1800);
    }

    @Test
    void budgetDropsTheFarthestFirst() {
        Manifest m = AssetLodManifest.parse(GOOD).manifest();
        List<Instance> in = List.of(new Instance(0, 100), new Instance(0, 900), new Instance(1, 50), new Instance(0, 900));
        assertThat(AssetLodManifest.budget(m, in, 100_000).lodString()).isEqualTo("0000");
        BudgetResult b = AssetLodManifest.budget(m, in, 8500);
        assertThat(b.faces()).isEqualTo(8500);
        assertThat(b.lodString()).isEqualTo("0100");
        assertThat(AssetLodManifest.budget(m, in, 0).lodString()).isEqualTo("1101");
    }

    @Test
    void theBlenderCatalogManifestParses() throws IOException {
        String text = Files.readString(CATALOG);
        ParseResult r = AssetLodManifest.parse(text);
        assertThat(r.ok()).as(r.error()).isTrue();
        assertThat(r.manifest().assets()).hasSizeGreaterThan(1000);
        assertThat(AssetLodManifest.write(r.manifest())).isEqualTo(text);
    }
}
