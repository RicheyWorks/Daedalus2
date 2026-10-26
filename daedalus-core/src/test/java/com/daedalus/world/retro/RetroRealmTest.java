// SPDX-License-Identifier: MIT

package com.daedalus.world.retro;

import com.daedalus.world.retro.RetroRealm.Chest;
import com.daedalus.world.retro.RetroRealm.Door;
import com.daedalus.world.retro.RetroRealm.Entry;
import com.daedalus.world.retro.RetroRealm.Loot;
import com.daedalus.world.retro.RetroRealm.Npc;
import com.daedalus.world.retro.RetroRealm.Place;
import com.daedalus.world.retro.RetroRealm.Zone;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SplittableRandom;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** The realm behind a portal (ADR-052): generated whole, the same every time, and always finishable. */
class RetroRealmTest {

    @Test
    void theSameSeedIsTheSameRealmAndOthersDiffer() {
        String a = RetroCodec.write(RetroRealmGenerator.generate(42));
        assertEquals(a, RetroCodec.write(RetroRealmGenerator.generate(42)));
        assertNotEquals(a, RetroCodec.write(RetroRealmGenerator.generate(43)));
    }

    @Test
    void everyRealmOfTwoHundredSeedsCanBeFinished() {
        for (long seed = 0; seed < 200; seed++) {
            RetroRealm r = RetroRealmGenerator.generate(seed);
            RetroProgress.Report rep = RetroProgress.check(r);
            assertTrue(rep.finishable(), "seed " + seed + ": " + rep.problems());
            assertEquals(rep.chests(), rep.chestsReached());
            assertEquals(4, rep.doors());
            assertEquals(1, rep.bossesBeaten());
            assertEquals(rep.npcs(), rep.npcsReached());
        }
    }

    @Test
    void theStoryKeysArePlacedNeverRolledAndTheVaultHoldsTheLegends() {
        for (long seed = 0; seed < 40; seed++) {
            RetroRealm r = RetroRealmGenerator.generate(seed);
            assertEquals(1, countItem(r, RetroItem.SILVER_KEY), "seed " + seed);
            assertEquals(1, countItem(r, RetroItem.STAR_KEY), "seed " + seed);
            assertTrue(chestAt(r, "CASTLE", 16, 2).loot().item() == RetroItem.STAR_BLADE);
            assertTrue(chestAt(r, "CASTLE", 16, 4).loot().item() == RetroItem.METEOR_MAIL);
            Chest silver = r.chests().stream().filter(c -> c.loot().item() == RetroItem.SILVER_KEY).findFirst()
                    .orElseThrow();
            assertEquals("CAVE2", silver.at().map());
            Chest star = r.chests().stream().filter(c -> c.loot().item() == RetroItem.STAR_KEY).findFirst()
                    .orElseThrow();
            assertEquals("CAVE3", star.at().map());
            // The tyrant stands in the only way to the star key.
            RetroRealm.Boss boss = r.bosses().get(0);
            assertEquals(1, Math.abs(boss.at().x() - star.at().x()) + Math.abs(boss.at().y() - star.at().y()));
            assertEquals(RetroMonster.SHARD_TYRANT, boss.monster());
            Set<Integer> tiers = new HashSet<>();
            for (Door d : r.doors()) {
                tiers.add(d.tier());
            }
            assertEquals(Set.of(1, 2, 3), tiers);
        }
    }

    @Test
    void theStarKeyIsOnlyReachedThroughTheTyrant() {
        RetroRealm r = RetroRealmGenerator.generate(5);
        RetroMap cave = r.mapOrThrow("CAVE3");
        Place boss = r.bosses().get(0).at();
        Place star = r.chests().stream().filter(c -> c.loot().item() == RetroItem.STAR_KEY).findFirst().orElseThrow()
                .at();
        Place up = r.links().stream().filter(l -> l.from().map().equals("CAVE3")).findFirst().orElseThrow().from();
        int w = cave.width();
        int[] d = RetroRealmGenerator.walk(cave, up.x(), up.y(), i -> i != boss.y() * w + boss.x());
        int[][] steps = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
        for (int[] s : steps) {
            int x = star.x() + s[0];
            int y = star.y() + s[1];
            if (cave.inside(x, y)) {
                assertTrue(d[y * w + x] < 0, "the star key is reachable around the tyrant");
            }
        }
    }

    @Test
    void placesStringOutAlongTheWalkAndTheFieldIsZonedByIt() {
        RetroRealm r = RetroRealmGenerator.generate(7);
        RetroMap field = r.mapOrThrow("FIELD");
        Map<Place, Place> links = r.linkMap();
        Place town1 = gate(r, "TOWN1");
        Place castle = gate(r, "CASTLE");
        Place cave = r.links().stream().filter(l -> l.to().map().equals("CAVE1")).findFirst().orElseThrow().from();
        int[] d = RetroRealmGenerator.walk(field, r.spawn().x(), r.spawn().y(), i -> true);
        assertTrue(d(d, town1) < d(d, castle) && d(d, castle) < d(d, cave), "town1, castle, cave in order");
        assertEquals(RetroTile.PORTAL, field.at(r.portal().x(), r.portal().y()));
        assertEquals('.', field.zoneAt(r.spawn().x(), r.spawn().y()), "no ambush at the portal");
        assertTrue(links.containsKey(town1));
        Set<Character> seen = new HashSet<>();
        for (int y = 0; y < field.height(); y++) {
            for (int x = 0; x < field.width(); x++) {
                seen.add(field.zoneAt(x, y));
                if (field.at(x, y) == RetroTile.WATER) {
                    assertEquals('.', field.zoneAt(x, y));
                }
            }
        }
        assertTrue(seen.containsAll(List.of('0', '1', '2')), "three rings: " + seen);
        for (String cv : List.of("CAVE1", "CAVE2", "CAVE3")) {
            RetroMap m = r.mapOrThrow(cv);
            assertTrue(m.dark());
            assertTrue(m.hasEncounters());
        }
        assertFalse(r.mapOrThrow("TOWN1").hasEncounters());
    }

    @Test
    void townsfolkGiveDirectionsFromTheRealMap() {
        RetroRealm r = RetroRealmGenerator.generate(7);
        Npc guard = r.npcs().stream().filter(n -> n.lines().get(0).startsWith("GUARD: THE CAVE")).findFirst()
                .orElseThrow();
        Place cave = r.links().stream().filter(l -> l.to().map().equals("CAVE1")).findFirst().orElseThrow().from();
        String said = guard.lines().get(1);
        assertTrue(said.contains(RetroRealmGenerator.compass(gate(r, "TOWN1"), cave)), said);
        assertEquals("NORTH", RetroRealmGenerator.compass(new Place("F", 5, 5), new Place("F", 5, 0)));
        assertEquals("SOUTHEAST", RetroRealmGenerator.compass(new Place("F", 0, 0), new Place("F", 5, 5)));
        assertEquals("WEST", RetroRealmGenerator.compass(new Place("F", 9, 5), new Place("F", 0, 6)));
        assertEquals("NEAR", RetroRealmGenerator.compass(new Place("F", 1, 1), new Place("F", 1, 1)));
    }

    @Test
    void theSpecRoundTrips() {
        for (long seed : new long[] {0, 7, 99}) {
            RetroRealm r = RetroRealmGenerator.generate(seed);
            String text = RetroCodec.write(r);
            RetroRealm back = RetroCodec.read(text);
            assertEquals(text, RetroCodec.write(back));
            assertTrue(RetroProgress.check(back).finishable());
            assertTrue(text.startsWith("DRR 1\n"));
        }
    }

    /**
     * The Unreal plugin ships seed 7's spec as its offline realm, and the C++ core's test plays it. If the generator
     * changes, regenerate it: {@code RetroCodec.write(RetroRealmGenerator.generate(7))} into that file.
     */
    @Test
    void theRealmTheUnrealPluginShipsIsTheOneThisGeneratorMakes() throws Exception {
        java.nio.file.Path shipped = java.nio.file.Path.of("..", "engines", "unreal", "DaedalusLink", "Content", "Realm",
                "realm-7.drr");
        org.junit.jupiter.api.Assumptions.assumeTrue(java.nio.file.Files.exists(shipped), "not in a full checkout");
        String offline = java.nio.file.Files.readString(shipped).replace("\r\n", "\n");
        // Offline fixture carries explicit demo deeds, not live ownership.
        // Every map, item, chest, encounter and configured land must still match exactly.
        var configuredLands = RetroCodec.read(offline).lands();
        assertEquals(RetroCodec.write(RetroRealmGenerator.generate(7).withLands(configuredLands)), offline,
                "Content/Realm/realm-7.drr is stale: regenerate it from RetroRealmGenerator.generate(7)");
    }

    @Test
    void theCodecRefusesWhatItCannotTrust() {
        String good = RetroCodec.write(RetroRealmGenerator.generate(1));
        assertThrows(IllegalArgumentException.class, () -> RetroCodec.read("hello\n"));
        assertThrows(IllegalArgumentException.class, () -> RetroCodec.read(good.replace("item HERB USE 10 25",
                "item HERB USE 11 25")));
        assertThrows(IllegalArgumentException.class, () -> RetroCodec.read(good.replace("\nportal ", "\nportel ")));
        assertThrows(IllegalArgumentException.class, () -> RetroCodec.read(good.replaceFirst("row ~", "row ")));
        assertThrows(IllegalArgumentException.class, () -> RetroCodec.read(good.replaceFirst("monster BLIGHT_SLIME 0 "
                + "58d840 188c10 6", "monster BLIGHT_SLIME 0 58d840 188c10 60")));
        assertThrows(IllegalArgumentException.class, () -> RetroCodec.read("DRR 1\nseed 1\n"));
        assertThrows(IllegalArgumentException.class, () -> RetroTile.of('?'));
    }

    @Test
    void theWalkCatchesARealmThatCannotBeFinished() {
        RetroRealm r = RetroRealmGenerator.generate(3);
        // Swap the silver key for gold: the treasury can no longer open.
        List<Chest> chests = new ArrayList<>();
        for (Chest c : r.chests()) {
            chests.add(c.loot().item() == RetroItem.SILVER_KEY ? new Chest(c.at(), Loot.gold(5)) : c);
        }
        RetroRealm noSilver = with(r, chests);
        RetroProgress.Report rep = RetroProgress.check(noSilver);
        assertFalse(rep.finishable());
        assertTrue(rep.problems().stream().anyMatch(p -> p.contains("tier 2")), rep.problems().toString());
        assertTrue(rep.problems().stream().anyMatch(p -> p.contains("CASTLE")), "treasury chests unreached");

        // A chest line pointing at bare floor is a lie the walk reports.
        List<Chest> lying = new ArrayList<>(r.chests());
        lying.add(new Chest(r.spawn(), Loot.gold(1)));
        assertTrue(RetroProgress.check(with(r, lying)).problems().stream().anyMatch(p -> p.contains("chest line")));
    }

    @Test
    void lootTablesWeighAsWritten() {
        SplittableRandom rng = new SplittableRandom(9);
        int n = 20000;
        int[] mimics = new int[4];
        long[] gold = new long[4];
        int[] golds = new int[4];
        for (int tier = 1; tier <= 3; tier++) {
            for (int i = 0; i < n; i++) {
                Loot l = RetroLoot.roll(tier, rng);
                if (l.kind() == Loot.Kind.MIMIC) {
                    mimics[tier]++;
                }
                if (l.kind() == Loot.Kind.GOLD) {
                    gold[tier] += l.gold();
                    golds[tier]++;
                }
            }
            Loot honest = RetroLoot.rollHonest(tier, rng);
            assertNotEquals(Loot.Kind.MIMIC, honest.kind());
        }
        assertEquals(0, mimics[1], "nothing bites near home");
        assertEquals(0.13, mimics[2] / (double) n, 0.015);
        assertEquals(0.14, mimics[3] / (double) n, 0.015);
        assertTrue(gold[1] / golds[1] < gold[2] / golds[2] && gold[2] / golds[2] < gold[3] / golds[3]);
        assertThrows(IllegalArgumentException.class, () -> RetroLoot.table(4));
    }

    @Test
    void encounterTablesRollGroupsByWeight() {
        Zone middle = RetroEncounters.zones().stream().filter(z -> z.id() == RetroEncounters.MIDDLE).findFirst()
                .orElseThrow();
        SplittableRandom rng = new SplittableRandom(4);
        Map<RetroMonster, Integer> leads = new EnumMap<>(RetroMonster.class);
        int fights = 30000;
        for (int i = 0; i < fights; i++) {
            List<RetroMonster> g = RetroEncounters.roll(middle, rng);
            assertTrue(g.size() >= 1 && g.size() <= 3);
            leads.merge(g.get(0), 1, Integer::sum);
        }
        double drip = leads.getOrDefault(RetroMonster.LUCKY_DRIP, 0) / (double) fights;
        assertEquals(2.0 / middle.totalWeight(), drip, 0.006);
        for (Zone z : RetroEncounters.zones()) {
            for (Entry e : z.entries()) {
                assertNotEquals(RetroMonster.Rarity.LEGENDARY, e.monster().rarity(), "guardians are placed, not met");
            }
        }
        assertThrows(IllegalArgumentException.class, () -> new Entry(RetroMonster.BLIGHT_SLIME, 1, 2, 4));
        assertThrows(IllegalArgumentException.class, () -> new Zone('x', 10, List.of()));
        assertThrows(IllegalArgumentException.class, () -> new Zone('x', 1,
                List.of(new Entry(RetroMonster.BLIGHT_SLIME, 1, 1, 1))));
    }

    @Test
    void itemsAndMonstersHoldTheirShape() {
        for (RetroItem i : RetroItem.values()) {
            assertTrue(i.title().length() <= 12, i.title());
            assertEquals(i.title(), i.title().toUpperCase());
        }
        assertEquals(150, RetroItem.STAR_SHARD.sellValue() / 2);
        assertEquals(5, RetroItem.HERB.sellValue());
        assertTrue(RetroItem.STAR_KEY.foundOnly());
        assertFalse(RetroItem.BRONZE_KEY.foundOnly());
        for (RetroMonster m : RetroMonster.values()) {
            assertTrue(m.title().length() <= 12, m.title());
            assertTrue(m.shape() >= 0 && m.shape() <= 7);
            assertTrue(m.dropOneIn() >= 1);
        }
        assertTrue(RetroMonster.LUCKY_DRIP.has(RetroMonster.Trait.HARD));
        assertTrue(RetroMonster.SHARD_TYRANT.traits().contains(RetroMonster.Trait.BOSS));
        assertTrue(RetroMonster.SHARDBACK.traits().isEmpty());
    }

    @Test
    void mapsAnswerOutsideTheirEdges() {
        RetroRealm r = RetroRealmGenerator.generate(2);
        assertEquals(RetroTile.WATER, r.mapOrThrow("FIELD").at(-1, 0));
        assertEquals(RetroTile.GRASS, r.mapOrThrow("TOWN1").at(0, -1));
        assertEquals(RetroTile.WALL, r.mapOrThrow("CAVE1").at(999, 0));
        assertEquals('.', r.mapOrThrow("FIELD").zoneAt(-1, -1));
        assertThrows(IllegalArgumentException.class, () -> r.mapOrThrow("MOON"));
        assertThrows(IllegalArgumentException.class, () -> new RetroMap("X", "X", 0, 1, "FIELD", false, null,
                RetroTile.GRASS));
        assertTrue(r.mapOrThrow("CASTLE").count(RetroTile.LOCKED) == 2);
    }

    // ---- helpers

    private static RetroRealm with(RetroRealm r, List<Chest> chests) {
        return new RetroRealm(r.seed(), r.name(), r.maps(), r.zones(), r.links(), chests, r.doors(), r.npcs(),
                r.shops(), r.bosses(), r.spawn(), r.portal(), r.news());
    }

    private static int countItem(RetroRealm r, RetroItem item) {
        return (int) r.chests().stream().filter(c -> c.loot().item() == item).count();
    }

    private static Chest chestAt(RetroRealm r, String map, int x, int y) {
        return r.chests().stream().filter(c -> c.at().equals(new Place(map, x, y))).findFirst().orElseThrow();
    }

    private static Place gate(RetroRealm r, String map) {
        return r.links().stream().filter(l -> l.to().map().equals(map)).findFirst().orElseThrow().from();
    }

    private static int d(int[] d, Place p) {
        return d[p.y() * RetroRealmGenerator.FIELD_SIZE + p.x()];
    }
}
