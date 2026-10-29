// SPDX-License-Identifier: MIT
package com.daedalus.server.realm.intake;

import static org.assertj.core.api.Assertions.*;

import com.daedalus.server.realm.CreatorRealmScaffold.Attribution;
import com.daedalus.server.realm.CreatorRealmScaffold.Basis;
import com.daedalus.server.realm.CreatorRealmScaffold.Role;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class CreatorIntakeBundleCliTest {
    @TempDir Path tmp;

    private static JsonNode call(boolean bundle, String... args) throws IOException {
        var out = new ByteArrayOutputStream();
        var err = new ByteArrayOutputStream();
        try (var stdout = new PrintStream(out, true, StandardCharsets.UTF_8);
             var stderr = new PrintStream(err, true, StandardCharsets.UTF_8)) {
            int status = bundle ? CreatorIntakeBundleCli.run(args, stdout, stderr) : CreatorIntakeCli.run(args, stdout, stderr);
            assertThat(status).as(err.toString(StandardCharsets.UTF_8)).isZero();
            assertThat(err.toString(StandardCharsets.UTF_8)).isEmpty();
        }
        return new ObjectMapper().readTree(out.toByteArray());
    }

    @Test void cliTransfersSelectedSyntheticHistoryAndExistingCliContinuesRestoredIntake() throws Exception {
        String id = "deathhimself_bundle_synthetic_asset", originalId = "deathhimself_bundle_synthetic_original";
        Path root = tmp.resolve("source-intake"), archive = tmp.resolve("private-intake.zip"), restored = tmp.resolve("received-intake");
        byte[] bytes = "SYNTHETIC original bytes; no creator artwork.\n".getBytes(StandardCharsets.US_ASCII);
        Path source = Files.write(tmp.resolve("synthetic-source.txt"), bytes);
        Path reserved = Files.writeString(tmp.resolve("current-reserved.json"), "[\"labyrinth\",\"LABYRINTH\"]", StandardCharsets.UTF_8);
        CreatorIntakeStore.Snapshot selected;
        try (var store = CreatorIntakeStore.create(root, Set.of("labyrinth", "LABYRINTH"))) {
            store.addEntry(1, id, Role.ASSET, new Attribution("synthetic-fixture", Basis.SYNTHETIC, null, null), null);
            store.appendIdea(2, id, "SYNTHETIC brief for transfer verification only");
            selected = store.attachOriginal(3, id, originalId, source, "SYNTHETIC ASCII fixture; no creator submission", true);
            store.addEntry(4, "deathhimself_bundle_later_idea", Role.IDEA, null, null);
        }
        JsonNode packed = call(true, "pack", root.toString(), "4", archive.toString());
        assertThat(packed.get("realmId").asText()).isEqualTo("deathhimself");
        assertThat(packed.get("revision").asInt()).isEqualTo(4);
        assertThat(packed.get("snapshotSha256").asText()).isEqualTo(selected.sha256());
        JsonNode inspected = call(true, "validate", archive.toString(), reserved.toString());
        assertThat(inspected).isEqualTo(packed);
        JsonNode receipt = call(true, "receive", archive.toString(), restored.toString(), reserved.toString());
        assertThat(receipt.get("status").asText()).isEqualTo("CREATED");
        assertThat(receipt.get("bundle")).isEqualTo(packed);
        assertThat(call(true, "receive", archive.toString(), restored.toString(), reserved.toString()).get("status").asText())
                .isEqualTo("ALREADY_PRESENT_EXACT");
        assertThat(call(false, "history", restored.toString())).hasSize(4);
        JsonNode restoredSnapshot = call(false, "show", restored.toString());
        assertThat(restoredSnapshot.get("sha256").asText()).isEqualTo(selected.sha256());
        assertThat(restoredSnapshot.get("manifest").get("entries")).hasSize(1);
        String digest = selected.manifest().entries().getFirst().originals().getFirst().sha256();
        assertThat(Files.readAllBytes(restored.resolve("originals").resolve(digest))).isEqualTo(bytes);
        Path brief = Files.writeString(tmp.resolve("continued-brief.txt"), "SYNTHETIC second brief after restore", StandardCharsets.UTF_8);
        JsonNode continued = call(false, "idea", restored.toString(), "4", id, brief.toString());
        assertThat(continued.get("revision").asInt()).isEqualTo(5);
        assertThat(continued.get("manifest").get("entries").get(0).get("ideas")).hasSize(2);
        assertThat(continued.get("manifest").get("ready").asBoolean()).isFalse();
        assertThat(call(false, "review", restored.toString(), "5").get("saleReady").asBoolean()).isFalse();
        assertThat(call(false, "show", root.toString()).get("revision").asInt()).isEqualTo(5);
    }
}
