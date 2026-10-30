// SPDX-License-Identifier: MIT
package com.daedalus.server.realm.intake;

import com.daedalus.server.realm.CreatorRealmScaffold.Attribution;
import com.daedalus.server.realm.CreatorRealmScaffold.Basis;
import com.daedalus.server.realm.CreatorRealmScaffold.Manifest;
import com.daedalus.server.realm.CreatorRealmScaffold.Role;
import com.daedalus.server.realm.intake.CreatorIntakeHostSession.HostBinding;
import com.daedalus.server.realm.intake.CreatorIntakeHostSession.HostReservations;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.Set;

/**
 * Local authoring under an explicit caller-supplied host reservation snapshot.
 * The context labels are not authenticated host, creator, legal or native identities.
 * Every invocation requires a context object containing exactly hostId, snapshotId and reservedIds.
 * Later host changes require a new supplied snapshot; this CLI does not discover or query a live host.
 * Source headers/history stay intact and native readiness and publication remain unchanged.
 */
public final class CreatorIntakeHostCli {
    private static final int MAX_INPUT_BYTES = 8 * 1024 * 1024;
    private static final ObjectMapper JSON = new ObjectMapper()
            .enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION)
            .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);
    private static final String USAGE = """
            Usage: CreatorIntakeHostCli COMMAND ROOT HOST_CONTEXT_JSON ...
              show ROOT HOST_CONTEXT_JSON [REVISION]
              history ROOT HOST_CONTEXT_JSON
              new ROOT HOST_CONTEXT_JSON EXPECTED ID ROLE [CREATOR_HANDLE] [SUPERSEDES_ID]
              revise ROOT HOST_CONTEXT_JSON EXPECTED NEW_ID PREDECESSOR_ID [CREATOR_HANDLE]
              edit ROOT HOST_CONTEXT_JSON EXPECTED ID EDIT_JSON
              idea ROOT HOST_CONTEXT_JSON EXPECTED ID TEXT_FILE
              attach ROOT HOST_CONTEXT_JSON EXPECTED ENTRY_ID ORIGINAL_ID LOCAL_FILE PROVENANCE_TEXT_FILE [--preview]
              finalize-source ROOT HOST_CONTEXT_JSON EXPECTED ID
              save ROOT HOST_CONTEXT_JSON EXPECTED MANIFEST_JSON
              review ROOT HOST_CONTEXT_JSON REVISION
              export ROOT HOST_CONTEXT_JSON REVISION OUTPUT_JSON
            Context: {"hostId":"caller-label","snapshotId":"caller-snapshot","reservedIds":[]}
            Supply an existing private intake and explicit current reservations. No init or live host query occurs.
            """;

    /** Each success identifies the exact supplied context alongside the normal intake result. */
    public record Result(HostBinding host, Object result) { }

    private CreatorIntakeHostCli() { }

    public static void main(String[] args) { System.exit(run(args, System.out, System.err)); }

    /** JSON on out, categorized errors on err, exit status 0 or 2; caller-owned streams remain open. */
    public static int run(String[] args, PrintStream out, PrintStream err) {
        try {
            Object result = execute(args);
            out.println(JSON.writerWithDefaultPrettyPrinter().writeValueAsString(result));
            return 0;
        } catch (IOException | RuntimeException failure) {
            String message = failure.getMessage();
            err.println("creator-intake-host: " + failure.getClass().getSimpleName()
                    + (message == null || message.isBlank() ? "" : ": " + message));
            return 2;
        }
    }

    private static Result execute(String[] args) throws IOException {
        if (args == null || args.length < 3) throw new IllegalArgumentException(USAGE);
        switch (args[0]) {
            case "show" -> count(args, 3, 4);
            case "history" -> count(args, 3, 3);
            case "new" -> count(args, 6, 8);
            case "revise" -> count(args, 6, 7);
            case "edit", "idea" -> count(args, 6, 6);
            case "attach" -> count(args, 8, 9);
            case "finalize-source", "save", "export" -> count(args, 5, 5);
            case "review" -> count(args, 4, 4);
            default -> throw new IllegalArgumentException("Unknown command: " + args[0] + "\n" + USAGE);
        }
        HostReservations host = readHost(args[2]);
        return use(args[1], host, session -> switch (args[0]) {
            case "show" -> args.length == 4 ? session.read(revision(args[3])) : session.current();
            case "history" -> session.history();
            case "new" -> session.addEntry(revision(args[3]), args[4], role(args[5]),
                    args.length >= 7 ? creator(args[6]) : new Attribution(null, null, null, null), args.length == 8 ? args[7] : null);
            case "revise" -> session.reviseEntry(revision(args[3]), args[4], args[5], args.length == 7 ? creator(args[6]) : null);
            case "edit" -> session.editDraft(revision(args[3]), args[4], readJson(args[5], CreatorIntakeStore.DraftEdit.class));
            case "idea" -> session.appendIdea(revision(args[3]), args[4], readText(args[5]));
            case "attach" -> {
                if (args.length == 9 && !"--preview".equals(args[8])) {
                    throw new IllegalArgumentException("attach accepts only the optional --preview flag");
                }
                yield session.attachOriginal(revision(args[3]), args[4], args[5], Path.of(args[6]), readText(args[7]), args.length == 9);
            }
            case "finalize-source" -> session.finalizeSourceContent(revision(args[3]), args[4]);
            case "save" -> session.save(revision(args[3]), readJson(args[4], Manifest.class));
            case "review" -> session.review(revision(args[3]));
            case "export" -> session.export(revision(args[3]), Path.of(args[4]));
            default -> throw new IllegalArgumentException(USAGE);
        });
    }

    @FunctionalInterface
    private interface Action { Object apply(CreatorIntakeHostSession session) throws IOException; }

    private static Result use(String root, HostReservations host, Action action) throws IOException {
        try (var session = CreatorIntakeHostSession.open(Path.of(root), host)) {
            return new Result(session.binding(), action.apply(session));
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

    private static Attribution creator(String handle) {
        if (handle.isBlank()) throw new IllegalArgumentException("CREATOR_HANDLE must be nonempty when supplied");
        return new Attribution(handle, Basis.USER_ASSERTED, null, null);
    }

    private static void count(String[] args, int minimum, int maximum) {
        if (args.length < minimum || args.length > maximum) throw new IllegalArgumentException(USAGE);
    }

    private static int revision(String value) {
        try {
            int parsed = Integer.parseInt(value);
            if (parsed > 0) return parsed;
        } catch (NumberFormatException ignored) { /* Explain the argument below. */ }
        throw new IllegalArgumentException("REVISION/EXPECTED must be a positive integer: " + value);
    }

    private static Role role(String value) {
        try { return Role.valueOf(value); }
        catch (IllegalArgumentException failure) { throw new IllegalArgumentException("ROLE must be ASSET, ASSEMBLY, COMPONENT or IDEA"); }
    }

    private static <T> T readJson(String file, Class<T> type) throws IOException {
        T value = JSON.readValue(readInput(file), type);
        if (value == null) throw new IllegalArgumentException("JSON input must not be null: " + file);
        return value;
    }

    private static String readText(String file) throws IOException {
        return StandardCharsets.UTF_8.newDecoder().decode(ByteBuffer.wrap(readInput(file))).toString();
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
