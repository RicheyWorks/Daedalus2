// SPDX-License-Identifier: MIT
package com.daedalus.server.realm.intake;

import static org.assertj.core.api.Assertions.*;

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

class CreatorIntakeHostCliTest {
    @TempDir Path tmp;

    private record Called(int status, String output, String error) { }

    private static Called call(String... args) {
        var out = new ByteArrayOutputStream();
        var err = new ByteArrayOutputStream();
        int status;
        try (var stdout = new PrintStream(out, true, StandardCharsets.UTF_8);
             var stderr = new PrintStream(err, true, StandardCharsets.UTF_8)) {
            status = CreatorIntakeHostCli.run(args, stdout, stderr);
        }
        return new Called(status, out.toString(StandardCharsets.UTF_8), err.toString(StandardCharsets.UTF_8));
    }

    private static JsonNode success(String... args) throws IOException {
        Called result = call(args);
        assertThat(result.status()).as(result.error()).isZero();
        assertThat(result.error()).isEmpty();
        return new ObjectMapper().readTree(result.output());
    }

    private static void refused(String... args) {
        Called result = call(args);
        assertThat(result.status()).isEqualTo(2);
        assertThat(result.output()).isEmpty();
        assertThat(result.error()).startsWith("creator-intake-host: ").doesNotContain("\tat ");
    }

    @Test void explicitHostAuthoringPreservesSourceHeaderAndRefusesReservationsBeforeCopyOrHistoryChange() throws Exception {
        String id = "deathhimself_host_synthetic_asset", oldReserved = "deathhimself_source_reserved";
        String targetReserved = "deathhimself_target_reserved", targetOriginal = "deathhimself_target_original";
        Path root = tmp.resolve("old-header-intake");
        try (var store = CreatorIntakeStore.create(root, Set.of(oldReserved))) {
            assertThat(store.current().revision()).isEqualTo(1);
        }
        byte[] header = Files.readAllBytes(root.resolve("header.json"));
        byte[] firstSnapshot = Files.readAllBytes(root.resolve("snapshots/00000001.json"));
        Path context = Files.writeString(tmp.resolve("synthetic-host.json"), """
                {"hostId":"synthetic-target","snapshotId":"synthetic-snapshot-1",
                 "reservedIds":["deathhimself_target_reserved","deathhimself_target_original"]}
                """, StandardCharsets.UTF_8);
        String directory = root.toString(), host = context.toString();
        JsonNode created = success("new", directory, host, "1", id, "ASSET");
        assertThat(created.get("host").get("hostId").asText()).isEqualTo("synthetic-target");
        assertThat(created.get("host").get("snapshotId").asText()).isEqualTo("synthetic-snapshot-1");
        assertThat(created.get("host").get("sha256").asText()).matches("[0-9a-f]{64}");
        assertThat(created.get("result").get("revision").asInt()).isEqualTo(2);
        assertThat(created.get("result").get("manifest").get("entries").get(0).get("creator").get("handle").isNull()).isTrue();
        Path source = Files.writeString(tmp.resolve("synthetic-source.txt"), "SYNTHETIC bytes; no creator artwork", StandardCharsets.UTF_8);
        Path provenance = Files.writeString(tmp.resolve("provenance.txt"), "SYNTHETIC local fixture only", StandardCharsets.UTF_8);
        refused("new", directory, host, "2", targetReserved, "ASSET");
        refused("new", directory, host, "2", oldReserved, "ASSET");
        refused("new", directory, host, "1", "deathhimself_stale_synthetic", "ASSET");
        refused("attach", directory, host, "2", id, targetOriginal, source.toString(), provenance.toString(), "--preview");
        assertThat(success("history", directory, host).get("result")).hasSize(2);
        assertThat(success("show", directory, host).get("result").get("revision").asInt()).isEqualTo(2);
        try (var files = Files.list(root.resolve("originals"))) { assertThat(files.toList()).isEmpty(); }
        JsonNode attached = success("attach", directory, host, "2", id, "deathhimself_allowed_original",
                source.toString(), provenance.toString(), "--preview");
        assertThat(attached.get("result").get("revision").asInt()).isEqualTo(3);
        assertThat(attached.get("host")).isEqualTo(created.get("host"));
        Path brief = Files.writeString(tmp.resolve("brief.txt"), "SYNTHETIC brief after host validation", StandardCharsets.UTF_8);
        JsonNode edited = success("idea", directory, host, "3", id, brief.toString());
        assertThat(edited.get("result").get("revision").asInt()).isEqualTo(4);
        assertThat(edited.get("result").get("manifest").get("ready").asBoolean()).isFalse();
        assertThat(success("review", directory, host, "4").get("result").get("saleReady").asBoolean()).isFalse();
        assertThat(Files.readAllBytes(root.resolve("header.json"))).isEqualTo(header);
        assertThat(Files.readAllBytes(root.resolve("snapshots/00000001.json"))).isEqualTo(firstSnapshot);
    }
}
