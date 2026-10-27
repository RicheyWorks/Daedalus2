// SPDX-License-Identifier: MIT
package com.daedalus.server.realm.intake;

import com.daedalus.server.realm.intake.CreatorIntakeHostSession.HostReservations;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.Set;

/**
 * Apply one typed local changeset through one host-bound session, with durable private receipt evidence.
 *
 * <pre>
 * CreatorIntakeChangesetCli apply ROOT HOST_CONTEXT_JSON CHANGESET_JSON ATTACHMENT_BASE PRIVATE_RECEIPT_DIRECTORY
 * </pre>
 *
 * A synthetic request shape (replace SHA placeholders with the actual show output):
 * <pre>
 * {"schemaVersion":1,"operationId":"synthetic-batch","expectedRevision":1,
 *  "expectedSha256":"ACTUAL_STARTING_SHA256",
 *  "host":{"hostId":"synthetic-host","snapshotId":"synthetic-context","sha256":"ACTUAL_CONTEXT_SHA256"},
 *  "operations":[
 *  {"type":"add","commandId":"synthetic-add","id":"deathhimself_fixture_asset","role":"ASSET"},
 *  {"type":"idea","commandId":"synthetic-idea","id":"deathhimself_fixture_asset","text":"SYNTHETIC brief"},
 *  {"type":"attach","commandId":"synthetic-source","id":"deathhimself_fixture_asset",
 *   "originalId":"deathhimself_fixture_original","sourcePath":"synthetic.txt",
 *   "provenance":"SYNTHETIC local bytes; no creator artwork","useAsPreview":false}]}
 * </pre>
 *
 * Copy the actual starting revision/digest and host binding from CreatorIntakeHostCli show output.
 * Attachment paths are explicit relative paths beneath ATTACHMENT_BASE. No URLs or live host lookup occur.
 * Prior committed steps and copied bytes survive a later failure. This is not an atomic transaction and
 * supplies no rollback or universal exactly-once guarantee. Only a verified completed receipt may replay;
 * partial or uncertain effects require explicit reconciliation. Native and NFT publication holds remain.
 */
public final class CreatorIntakeChangesetCli {
    private static final int MAX_INPUT_BYTES = 8 * 1024 * 1024;
    private static final ObjectMapper JSON = new ObjectMapper()
            .enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION)
            .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);
    private static final String USAGE = """
            Usage: CreatorIntakeChangesetCli apply ROOT HOST_CONTEXT_JSON CHANGESET_JSON ATTACHMENT_BASE PRIVATE_RECEIPT_DIRECTORY
            Host context contains exactly hostId, snapshotId and reservedIds (an explicit unique-string array).
            Request and context must be regular non-symlink JSON files of at most 8 MiB each.
            Exit 0 means COMPLETE, including verified completed replay. PARTIAL or UNCERTAIN JSON returns 2.
            Prior effects are retained on failure; no automatic replay of partial or uncertain operations occurs.
            """;

    private CreatorIntakeChangesetCli() { }

    public static void main(String[] args) { System.exit(run(args, System.out, System.err)); }

    /** Print actual Outcome JSON or a categorized error, preserving caller-owned streams. */
    public static int run(String[] args, PrintStream out, PrintStream err) {
        try {
            if (args == null || args.length != 6 || !"apply".equals(args[0])) throw new IllegalArgumentException(USAGE);
            HostReservations host = readHost(args[2]);
            var request = JSON.readValue(readInput(args[3]), CreatorIntakeChangeset.Request.class);
            if (request == null) throw new IllegalArgumentException("Changeset request must not be null");
            try (var session = CreatorIntakeHostSession.open(Path.of(args[1]), host)) {
                var outcome = CreatorIntakeChangeset.apply(session, request, Path.of(args[4]), Path.of(args[5]));
                out.println(JSON.writerWithDefaultPrettyPrinter().writeValueAsString(outcome));
                return "COMPLETE".equals(outcome.status().name()) ? 0 : 2;
            }
        } catch (IOException | RuntimeException failure) {
            String message = failure.getMessage();
            err.println("creator-intake-changeset: " + failure.getClass().getSimpleName()
                    + (message == null || message.isBlank() ? "" : ": " + message));
            return 2;
        }
    }

    private static HostReservations readHost(String file) throws IOException {
        JsonNode context = JSON.readTree(readInput(file));
        if (context == null || !context.isObject() || context.size() != 3
                || !context.has("hostId") || !context.has("snapshotId") || !context.has("reservedIds")) {
            throw new IllegalArgumentException("Host context must contain exactly hostId, snapshotId and reservedIds");
        }
        for (String field : new String[] {"hostId", "snapshotId"}) {
            if (!context.get(field).isTextual() || context.get(field).textValue().isBlank()) {
                throw new IllegalArgumentException(field + " must be a nonempty string");
            }
        }
        JsonNode array = context.get("reservedIds");
        if (!array.isArray()) throw new IllegalArgumentException("reservedIds must be an explicit JSON array of strings");
        Set<String> ids = new HashSet<>();
        for (JsonNode value : array) {
            if (!value.isTextual() || value.textValue().isBlank()) throw new IllegalArgumentException("Reserved IDs must be nonempty strings");
            if (!ids.add(value.textValue())) throw new IllegalArgumentException("Duplicate reserved ID: " + value.textValue());
        }
        return new HostReservations(context.get("hostId").textValue(), context.get("snapshotId").textValue(), Set.copyOf(ids));
    }

    private static byte[] readInput(String file) throws IOException {
        Path path = Path.of(file);
        if (!Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS)) throw new IOException("Input must be a regular file: " + file);
        try (var input = Files.newInputStream(path, LinkOption.NOFOLLOW_LINKS)) {
            byte[] bytes = input.readNBytes(MAX_INPUT_BYTES + 1);
            if (bytes.length > MAX_INPUT_BYTES) throw new IOException("Input exceeds 8 MiB: " + file);
            return bytes;
        }
    }
}
