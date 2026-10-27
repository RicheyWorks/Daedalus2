// SPDX-License-Identifier: MIT
package com.daedalus.server.realm.intake;

import static org.assertj.core.api.Assertions.*;

import com.daedalus.server.realm.CreatorRealmScaffold.Stage;
import com.daedalus.server.realm.intake.CreatorIntakeHostSession.HostReservations;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class CreatorIntakeChangesetCliTest {
    @TempDir Path tmp;
    private static final ObjectMapper JSON = new ObjectMapper();

    private static JsonNode applied(String... args) throws Exception {
        var out = new ByteArrayOutputStream();
        var err = new ByteArrayOutputStream();
        try (var stdout = new PrintStream(out, true, StandardCharsets.UTF_8);
             var stderr = new PrintStream(err, true, StandardCharsets.UTF_8)) {
            assertThat(CreatorIntakeChangesetCli.run(args, stdout, stderr)).as(err.toString(StandardCharsets.UTF_8)).isZero();
            assertThat(err.toString(StandardCharsets.UTF_8)).isEmpty();
        }
        return JSON.readTree(out.toByteArray());
    }

    @Test void actualCliAppliesSyntheticTypedBatchAndExactCompletedRetryAddsNoRevisions() throws Exception {
        String id = "deathhimself_changeset_fixture_asset", originalId = "deathhimself_changeset_fixture_original";
        Path root = tmp.resolve("private-intake"), attachments = Files.createDirectory(tmp.resolve("attachments"));
        Path receipts = tmp.resolve("private-operation-receipt"), contextFile = tmp.resolve("host.json"), requestFile = tmp.resolve("request.json");
        byte[] source = "SYNTHETIC local source; no creator artwork.\n".getBytes(StandardCharsets.US_ASCII);
        Files.write(attachments.resolve("synthetic.txt"), source);
        try (var store = CreatorIntakeStore.create(root, Set.of("deathhimself_source_reserved"))) {
            assertThat(store.current().revision()).isEqualTo(1);
        }
        byte[] header = Files.readAllBytes(root.resolve("header.json"));
        var host = new HostReservations("synthetic-target", "synthetic-snapshot-1", Set.of("deathhimself_target_reserved"));
        JSON.writeValue(contextFile.toFile(), host);
        var request = JSON.createObjectNode().put("schemaVersion", 1).put("operationId", "synthetic-changeset-1");
        try (var session = CreatorIntakeHostSession.open(root, host)) {
            request.put("expectedRevision", session.current().revision()).put("expectedSha256", session.current().sha256());
            request.set("host", JSON.valueToTree(session.binding()));
        }
        var operations = request.putArray("operations");
        var creator = JSON.createObjectNode().put("handle", "synthetic-fixture").put("basis", "SYNTHETIC")
                .putNull("legalIdentity").putNull("accountId");
        operations.addObject().put("type", "add").put("commandId", "synthetic-add").put("id", id).put("role", "ASSET")
                .putNull("supersedesId").set("creator", creator);
        operations.addObject().put("type", "idea").put("commandId", "synthetic-idea").put("id", id)
                .put("text", "SYNTHETIC brief for ordered local authoring only");
        operations.addObject().put("type", "attach").put("commandId", "synthetic-attach").put("id", id)
                .put("originalId", originalId).put("sourcePath", "synthetic.txt")
                .put("provenance", "SYNTHETIC ASCII fixture; no creator submission").put("useAsPreview", true);
        var edit = operations.addObject().put("type", "edit").put("commandId", "synthetic-edit").put("id", id).putObject("edit");
        edit.put("name", "SYNTHETIC source item").put("description", "Offline source fixture only")
                .put("previewOriginalId", originalId).put("saleIntent", "UNSET");
        edit.set("creator", creator);
        edit.putArray("componentIds");
        operations.addObject().put("type", "finalize-source").put("commandId", "synthetic-finalize").put("id", id);
        JSON.writerWithDefaultPrettyPrinter().writeValue(requestFile.toFile(), request);
        String[] args = {"apply", root.toString(), contextFile.toString(), requestFile.toString(), attachments.toString(), receipts.toString()};
        JsonNode completed = applied(args);
        assertThat(completed.get("status").asText()).isEqualTo("COMPLETE");
        assertThat(completed.get("replayed").asBoolean()).isFalse();
        assertThat(completed.get("steps")).hasSize(5);
        CreatorIntakeStore.Snapshot saved;
        try (var session = CreatorIntakeHostSession.open(root, host)) {
            saved = session.current();
            assertThat(saved.revision()).isEqualTo(6);
            assertThat(session.history()).hasSize(6);
            var entry = saved.manifest().entries().getFirst();
            assertThat(entry.stage()).isEqualTo(Stage.FINAL);
            assertThat(entry.ideas()).hasSize(1);
            assertThat(Files.readAllBytes(root.resolve("originals").resolve(entry.originals().getFirst().sha256()))).isEqualTo(source);
            assertThat(saved.manifest().ready()).isFalse();
            assertThat(session.review(6).saleReady()).isFalse();
        }
        JsonNode replayed = applied(args);
        assertThat(replayed.get("status").asText()).isEqualTo("COMPLETE");
        assertThat(replayed.get("replayed").asBoolean()).isTrue();
        try (var session = CreatorIntakeHostSession.open(root, host)) {
            assertThat(session.current()).isEqualTo(saved);
            assertThat(session.history()).hasSize(6);
        }
        assertThat(Files.readAllBytes(root.resolve("header.json"))).isEqualTo(header);
    }
}
