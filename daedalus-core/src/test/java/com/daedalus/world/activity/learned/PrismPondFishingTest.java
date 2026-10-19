// SPDX-License-Identifier: MIT

package com.daedalus.world.activity.learned;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

import org.junit.jupiter.api.Test;

/** Windmere pond casts become one envelope and one receipt. */
class PrismPondFishingTest {

    private static final Path FISH = Path.of("..", "data", "rpg", "prism-fish.json");
    private static final Path DEMO = Path.of("..", "tools", "rpg_demo", "index.html");
    private static final Path CANONICAL = Path.of(
            "..", "docs", "contracts", "activity-result-v1", "prism-pond-caught.canonical.json");

    @Test
    void theShippedPondTableCreditsADunebackOnce() throws IOException {
        PrismPondFishing.Catalog catalog = PrismPondFishing.catalog(Files.readString(FISH, StandardCharsets.UTF_8));
        assertThat(catalog.fish()).extracting(PrismPondFishing.Species::name).containsExactly(
                "Reedling", "Pond Perch", "Mudskipper Eel", "Glassfin Minnow", "Sunscale Carp", "Prismscale Koi");

        PrismPondFishing.Species reedling = catalog.require("Reedling");
        assertThat(reedling.rarity()).isEqualTo("COMMON");
        assertThat(reedling.weight()).isEqualTo(40);
        assertThat(reedling.windowSeconds()).isEqualTo(0.9);
        assertThat(reedling.effect()).isEqualTo("heal 20 HP");
        assertThat(reedling.price()).isEqualTo(6);
        assertThat(reedling.note()).contains("reed beds");
        assertThat(reedling.nightWeight()).isNull();
        assertThat(catalog.require("Glassfin Minnow").nightWeight()).isEqualTo(14);
        assertThat(catalog.require("Prismscale Koi").price()).isEqualTo(400);
        assertThat(reedling.stockLine()).startsWith("Reedling|COMMON|40|");

        PrismPondFishing.Cast cast = new PrismPondFishing.Cast(
                "cast-windmere-7", "duneback", ActivityResult.SubjectKind.CREATURE, "done",
                "NEW! CAUGHT A REEDLING (COMMON).", "Reedling");
        ActivityResult result = PrismPondFishing.fromCast(cast, catalog);
        String canonical = Files.readString(CANONICAL, StandardCharsets.UTF_8).strip();

        assertThat(result.serialize()).isEqualTo(canonical);
        assertThat(result.activityId()).isEqualTo(PrismPondFishing.ACTIVITY_ID);
        assertThat(result.outcome()).isEqualTo(ActivityResult.Outcome.LEARNED);
        assertThat(result.learned()).isEqualTo("reedling");
        assertThat(PrismPondFishing.caughtBanner(reedling, true)).isEqualTo("NEW! CAUGHT A REEDLING (COMMON).");
        assertThat(PrismPondFishing.caughtBanner(reedling, false)).isEqualTo("CAUGHT A REEDLING (COMMON).");
        assertThat(PrismPondFishing.fromCast(new PrismPondFishing.Cast(
                cast.attemptId(), cast.subjectId(), cast.subjectKind(), "done",
                "CAUGHT A REEDLING (COMMON).", "Reedling"), catalog)).isEqualTo(result);

        ActivityCreditLedger ledger = new ActivityCreditLedger();
        ActivityResultReceipt receipt = PrismPondFishing.credit(ledger, cast, catalog);
        assertThat(receipt.receiptId()).isEqualTo(ActivityResultReceipt.idOf(result));
        assertThatThrownBy(() -> PrismPondFishing.credit(ledger, cast, catalog))
                .isInstanceOf(ActivityCreditException.class)
                .satisfies(error -> assertThat(((ActivityCreditException) error).reason())
                        .isEqualTo(ActivityCreditException.Reason.DUPLICATE));
        assertThat(ledger.size()).isEqualTo(1);

        String demo = Files.readString(DEMO, StandardCharsets.UTF_8);
        assertThat(demo).contains("\"IT GOT AWAY.\"");
        assertThat(demo).contains("\"TOO SOON. THE RIPPLE SCATTERS.\"");
        assertThat(demo).contains("\"CAUGHT A \" + k.toUpperCase() + \" (\" + f.fish.rarity + \").\"");
        assertThat(demo).contains("\"NEW! \"");
    }

    @Test
    void everyPondSpeciesCanTeachAndOneCastCannotTeachTwoFish() throws IOException {
        PrismPondFishing.Catalog catalog = PrismPondFishing.catalog(Files.readString(FISH, StandardCharsets.UTF_8));
        ActivityCreditLedger ledger = new ActivityCreditLedger();
        int n = 0;
        for (PrismPondFishing.Species species : catalog.fish()) {
            n++;
            PrismPondFishing.Cast cast = new PrismPondFishing.Cast(
                    "cast-" + n, "sunroot", ActivityResult.SubjectKind.PLANT, "done",
                    PrismPondFishing.caughtBanner(species, n == 1), species.name());
            ActivityResult result = PrismPondFishing.fromCast(cast, catalog);
            assertThat(result.subjectKind()).isEqualTo(ActivityResult.SubjectKind.PLANT);
            assertThat(result.learned()).isEqualTo(PrismPondFishing.lesson(species.name()));
            assertThat(result.detail()).containsEntry("species", species.name()).containsEntry("rarity", species.rarity());
            ledger.credit(result);
        }
        assertThat(ledger.size()).isEqualTo(6);
        assertThat(PrismPondFishing.lesson("Pond Perch")).isEqualTo("pond-perch");
        assertThat(PrismPondFishing.lesson("Prismscale Koi")).isEqualTo("prismscale-koi");

        PrismPondFishing.Cast reedling = new PrismPondFishing.Cast(
                "cast-shared", "duneback", ActivityResult.SubjectKind.CREATURE, "done",
                "CAUGHT A REEDLING (COMMON).", "Reedling");
        ledger.credit(PrismPondFishing.fromCast(reedling, catalog));
        PrismPondFishing.Cast perch = new PrismPondFishing.Cast(
                "cast-shared", "duneback", ActivityResult.SubjectKind.CREATURE, "done",
                "CAUGHT A POND PERCH (COMMON).", "Pond Perch");
        assertThatThrownBy(() -> ledger.credit(PrismPondFishing.fromCast(perch, catalog)))
                .satisfies(error -> assertThat(((ActivityCreditException) error).reason())
                        .isEqualTo(ActivityCreditException.Reason.CONFLICT));
    }

    @Test
    void gotAwayAndTooSoonAreLessonsToo() throws IOException {
        PrismPondFishing.Catalog catalog = PrismPondFishing.catalog(Files.readString(FISH, StandardCharsets.UTF_8));
        ActivityResult away = PrismPondFishing.fromCast(new PrismPondFishing.Cast(
                "cast-away", "duneback", ActivityResult.SubjectKind.CREATURE, "done",
                "IT GOT AWAY.", "Sunscale Carp"), catalog);
        assertThat(away.outcome()).isEqualTo(ActivityResult.Outcome.MISSED);
        assertThat(away.learned()).isEqualTo("sunscale-carp");
        assertThat(away.detail()).containsEntry("finish", "got-away").containsEntry("rarity", "RARE")
                .containsEntry("effect", "heal 120 HP");

        ActivityResult soon = PrismPondFishing.fromCast(new PrismPondFishing.Cast(
                "cast-soon", "duneback", ActivityResult.SubjectKind.CREATURE, "done",
                "TOO SOON. THE RIPPLE SCATTERS.", null), catalog);
        assertThat(soon.outcome()).isEqualTo(ActivityResult.Outcome.FAILED);
        assertThat(soon.learned()).isEqualTo("ripple-scattered");
        assertThat(soon.detail()).containsExactly(Map.entry("finish", "too-soon"));
    }

    @Test
    void unfinishedAndDishonestCastsAreRefused() throws IOException {
        PrismPondFishing.Catalog catalog = PrismPondFishing.catalog(Files.readString(FISH, StandardCharsets.UTF_8));
        assertThatThrownBy(() -> PrismPondFishing.fromCast(null, catalog)).hasMessageContaining("required");
        assertThatThrownBy(() -> PrismPondFishing.fromCast(cast("done", "CAUGHT A REEDLING (COMMON).", "Reedling"), null))
                .hasMessageContaining("required");
        assertThatThrownBy(() -> PrismPondFishing.fromCast(cast("wait", "WAITING", null), catalog))
                .hasMessageContaining("not finished");
        assertThatThrownBy(() -> PrismPondFishing.fromCast(cast("bite", "!", "Reedling"), catalog))
                .hasMessageContaining("not finished");
        assertThatThrownBy(() -> PrismPondFishing.fromCast(cast("done", "TOO SOON. THE RIPPLE SCATTERS.", "Reedling"), catalog))
                .hasMessageContaining("no species");
        assertThatThrownBy(() -> PrismPondFishing.fromCast(cast("done", "IT GOT AWAY.", null), catalog))
                .hasMessageContaining("species is required");
        assertThatThrownBy(() -> PrismPondFishing.fromCast(cast("done", "IT GOT AWAY.", "Dragonfish"), catalog))
                .hasMessageContaining("unknown species");
        assertThatThrownBy(() -> PrismPondFishing.fromCast(cast("done", "CAUGHT A REEDLING (LEGENDARY).", "Reedling"), catalog))
                .hasMessageContaining("banner does not match");
        assertThatThrownBy(() -> PrismPondFishing.fromCast(cast("done", "NEW!CAUGHT A REEDLING (COMMON).", "Reedling"), catalog))
                .hasMessageContaining("banner does not match");
        assertThatThrownBy(() -> PrismPondFishing.fromCast(
                new PrismPondFishing.Cast("cast-1", "duneback", ActivityResult.SubjectKind.CREATURE, null, "IT GOT AWAY.", null),
                catalog)).hasMessageContaining("phase and message");
    }

    @Test
    void theCatalogRefusesATableThatIsNotThePond() {
        assertThatThrownBy(() -> PrismPondFishing.catalog(null)).hasMessageContaining("json is required");
        assertThatThrownBy(() -> PrismPondFishing.catalog("x".repeat(PrismPondFishing.MAX_JSON + 1)))
                .hasMessageContaining("exceeds");
        assertThatThrownBy(() -> PrismPondFishing.catalog(pond("[]").replace("[]", "")))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> PrismPondFishing.catalog(pond("[]").replace(PrismPondFishing.SCHEMA, "daedalus.rpg-fish/v2")))
                .hasMessageContaining("schema must be");
        assertThatThrownBy(() -> PrismPondFishing.catalog(pond("[]").replace("\"prism\"", "\"portal\"")))
                .hasMessageContaining("realm must be");
        assertThatThrownBy(() -> PrismPondFishing.catalog(pond("[]"))).hasMessageContaining("fish must be");
        assertThatThrownBy(() -> PrismPondFishing.catalog("{\"schema\":\"daedalus.rpg-fish/v1\",\"realm\":\"prism\"}"))
                .hasMessageContaining("fish must be");
        assertThatThrownBy(() -> PrismPondFishing.catalog(pond("[1]"))).hasMessageContaining("fish must be an object");
        assertThatThrownBy(() -> PrismPondFishing.catalog(pond("[" + reedling() + "," + reedling() + "]")))
                .hasMessageContaining("duplicate species");
        assertThatThrownBy(() -> PrismPondFishing.catalog(pond("[" + reedling().replace("COMMON", "MYTHIC") + "]")))
                .hasMessageContaining("bad rarity");
        assertThatThrownBy(() -> PrismPondFishing.catalog(pond("[" + reedling().replace("40", "0") + "]")))
                .hasMessageContaining("weight");
        assertThatThrownBy(() -> PrismPondFishing.catalog(pond("[" + reedling().replace("40", "1.5") + "]")))
                .hasMessageContaining("weight must be an integer");
        assertThatThrownBy(() -> PrismPondFishing.catalog(pond("[" + reedling().replace("0.9", "0") + "]")))
                .hasMessageContaining("window_s");
        assertThatThrownBy(() -> PrismPondFishing.catalog(pond("[" + reedling().replace("0.9", "\"fast\"") + "]")))
                .hasMessageContaining("window_s must be a number");
        assertThatThrownBy(() -> PrismPondFishing.catalog(pond("[" + reedling().replace("0.9", "61") + "]")))
                .hasMessageContaining("window_s");
        assertThatThrownBy(() -> PrismPondFishing.catalog(pond("[" + reedling().replace("\"price\":6", "\"price\":-1") + "]")))
                .hasMessageContaining("price");
        assertThatThrownBy(() -> PrismPondFishing.catalog(pond("[" + reedling().replace("Reedling", "reedling") + "]")))
                .hasMessageContaining("bad species name");
        assertThatThrownBy(() -> PrismPondFishing.catalog(
                pond("[" + reedling().replace("}", ",\"night_weight\":0}") + "]")))
                .hasMessageContaining("night_weight");
        assertThatThrownBy(() -> PrismPondFishing.catalog(
                pond("[" + reedling().replace("}", ",\"bait\":1}") + "]")))
                .hasMessageContaining("unknown fish field");
        String note = reedling().replace("a thin silver fish", "a thin silver fish\\u0001");
        assertThatThrownBy(() -> PrismPondFishing.catalog(pond("[" + note + "]")))
                .hasMessageContaining("printable ASCII");
        assertThatThrownBy(() -> PrismPondFishing.catalog(
                "{\"schema\":\"daedalus.rpg-fish/v1\",\"realm\":\"prism\",\"extra\":1,\"fish\":[" + reedling() + "]}"))
                .hasMessageContaining("unknown catalog field");
        assertThatThrownBy(() -> PrismPondFishing.catalog(pond(
                "[" + reedling().replace(",\"note\":\"a thin silver fish\"", "") + "]")))
                .hasMessageContaining("missing note");

        PrismPondFishing.Catalog whole = PrismPondFishing.catalog(pond(
                "[" + reedling().replace("40", "40.0").replace("0.9", "1") + "]"));
        assertThat(whole.require("Reedling").weight()).isEqualTo(40);
        assertThat(whole.require("Reedling").windowSeconds()).isEqualTo(1.0);
        assertThatThrownBy(() -> PrismPondFishing.catalog("not json")).isInstanceOf(IllegalArgumentException.class);
    }

    private static PrismPondFishing.Cast cast(String phase, String message, String species) {
        return new PrismPondFishing.Cast(
                "cast-1", "duneback", ActivityResult.SubjectKind.CREATURE, phase, message, species);
    }

    private static String pond(String fish) {
        return "{\"schema\":\"daedalus.rpg-fish/v1\",\"realm\":\"prism\",\"fish\":" + fish + "}";
    }

    private static String reedling() {
        return "{\"name\":\"Reedling\",\"rarity\":\"COMMON\",\"weight\":40,\"window_s\":0.9,"
                + "\"effect\":\"heal 20 HP\",\"price\":6,\"note\":\"a thin silver fish\"}";
    }
}
