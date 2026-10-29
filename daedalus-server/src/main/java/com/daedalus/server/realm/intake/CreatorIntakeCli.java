// SPDX-License-Identifier: MIT
package com.daedalus.server.realm.intake;

import com.daedalus.server.realm.CreatorRealmScaffold.Attribution;
import com.daedalus.server.realm.CreatorRealmScaffold.Basis;
import com.daedalus.server.realm.CreatorRealmScaffold.Manifest;
import com.daedalus.server.realm.CreatorRealmScaffold.Role;
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

/** Explicit local authoring commands; starts no server, network request, native runtime or publication. */
public final class CreatorIntakeCli {
    private static final int MAX_INPUT_BYTES = 8 * 1024 * 1024;
    private static final ObjectMapper JSON = new ObjectMapper()
            .enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION)
            .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);
    private static final String USAGE = """
            Usage: CreatorIntakeCli COMMAND ROOT ...
              init ROOT [RESERVED_IDS_JSON]
              show ROOT [REVISION]
              history ROOT
              new ROOT EXPECTED ID ROLE [CREATOR_HANDLE] [SUPERSEDES_ID]
              revise ROOT EXPECTED NEW_ID PREDECESSOR_ID [CREATOR_HANDLE]
              edit ROOT EXPECTED ID EDIT_JSON
              idea ROOT EXPECTED ID TEXT_FILE
              attach ROOT EXPECTED ENTRY_ID ORIGINAL_ID LOCAL_FILE PROVENANCE_TEXT_FILE [--preview]
              finalize-source ROOT EXPECTED ID
              save ROOT EXPECTED MANIFEST_JSON
              export ROOT REVISION OUTPUT_JSON
              review ROOT REVISION
            ROLE is ASSET, ASSEMBLY, COMPONENT or IDEA. EXPECTED is the current positive revision.
            All operations are local. Final source content and exported metadata do not approve a sale.
            """;

    private CreatorIntakeCli() { }

    /** Return the command's exit status to the shell; the reusable run method does not terminate its caller. */
    public static void main(String[] args) { System.exit(run(args, System.out, System.err)); }

    /** JSON goes to out, useful errors to err. Neither caller-owned stream is closed. */
    public static int run(String[] args, PrintStream out, PrintStream err) {
        try {
            Object result = execute(args);
            out.println(JSON.writerWithDefaultPrettyPrinter().writeValueAsString(result));
            return 0;
        } catch (IOException | RuntimeException failure) {
            String message = failure.getMessage();
            err.println("creator-intake: " + failure.getClass().getSimpleName()
                    + (message == null || message.isBlank() ? "" : ": " + message));
            return 2;
        }
    }

    private static Object execute(String[] args) throws IOException {
        if (args == null || args.length == 0) throw new IllegalArgumentException(USAGE);
        return switch (args[0]) {
            case "init" -> {
                count(args, 2, 3);
                Set<String> reserved = args.length == 3 ? reservedIds(args[2]) : Set.of();
                try (var store = CreatorIntakeStore.create(Path.of(args[1]), reserved)) { yield store.current(); }
            }
            case "show" -> {
                count(args, 2, 3);
                yield use(args[1], store -> args.length == 3 ? store.read(revision(args[2])) : store.current());
            }
            case "history" -> {
                count(args, 2, 2);
                yield use(args[1], CreatorIntakeStore::history);
            }
            case "new" -> {
                count(args, 5, 7);
                Attribution creator = new Attribution(null, null, null, null);
                if (args.length >= 6) {
                    if (args[5].isBlank()) throw new IllegalArgumentException("CREATOR_HANDLE must be nonempty when supplied");
                    creator = new Attribution(args[5], Basis.USER_ASSERTED, null, null);
                }
                Attribution supplied = creator;
                yield use(args[1], store -> store.addEntry(revision(args[2]), args[3], role(args[4]), supplied,
                        args.length == 7 ? args[6] : null));
            }
            case "edit" -> {
                count(args, 5, 5);
                var edit = readJson(args[4], CreatorIntakeStore.DraftEdit.class);
                yield use(args[1], store -> store.editDraft(revision(args[2]), args[3], edit));
            }
            case "revise" -> {
                count(args, 5, 6);
                Attribution creator = args.length == 6 ? new Attribution(args[5], Basis.USER_ASSERTED, null, null) : null;
                yield use(args[1], store -> store.reviseEntry(revision(args[2]), args[3], args[4], creator));
            }
            case "idea" -> {
                count(args, 5, 5);
                String brief = readText(args[4]);
                yield use(args[1], store -> store.appendIdea(revision(args[2]), args[3], brief));
            }
            case "attach" -> {
                count(args, 7, 8);
                if (args.length == 8 && !"--preview".equals(args[7])) {
                    throw new IllegalArgumentException("attach accepts only the optional --preview flag");
                }
                String provenance = readText(args[6]);
                yield use(args[1], store -> store.attachOriginal(revision(args[2]), args[3], args[4], Path.of(args[5]),
                        provenance, args.length == 8));
            }
            case "finalize-source" -> {
                count(args, 4, 4);
                yield use(args[1], store -> store.finalizeSourceContent(revision(args[2]), args[3]));
            }
            case "save" -> {
                count(args, 4, 4);
                Manifest candidate = readJson(args[3], Manifest.class);
                yield use(args[1], store -> store.save(revision(args[2]), candidate));
            }
            case "export" -> {
                count(args, 4, 4);
                yield use(args[1], store -> store.export(revision(args[2]), Path.of(args[3])));
            }
            case "review" -> {
                count(args, 3, 3);
                yield use(args[1], store -> store.review(revision(args[2])));
            }
            default -> throw new IllegalArgumentException("Unknown command: " + args[0] + "\n" + USAGE);
        };
    }

    @FunctionalInterface
    private interface Action { Object apply(CreatorIntakeStore store) throws IOException; }

    private static Object use(String root, Action action) throws IOException {
        try (var store = CreatorIntakeStore.open(Path.of(root))) { return action.apply(store); }
    }

    private static void count(String[] args, int minimum, int maximum) {
        if (args.length < minimum || args.length > maximum) throw new IllegalArgumentException(USAGE);
    }

    private static int revision(String value) {
        try {
            int parsed = Integer.parseInt(value);
            if (parsed > 0) return parsed;
        } catch (NumberFormatException ignored) { /* Report the argument's purpose below. */ }
        throw new IllegalArgumentException("REVISION/EXPECTED must be a positive integer: " + value);
    }

    private static Role role(String value) {
        try { return Role.valueOf(value); }
        catch (IllegalArgumentException failure) { throw new IllegalArgumentException("ROLE must be ASSET, ASSEMBLY, COMPONENT or IDEA"); }
    }

    private static Set<String> reservedIds(String file) throws IOException {
        JsonNode array = JSON.readTree(readInput(file));
        if (array == null || !array.isArray()) throw new IllegalArgumentException("Reserved IDs must be a JSON array of strings");
        Set<String> ids = new HashSet<>();
        for (JsonNode value : array) {
            if (!value.isTextual() || value.textValue().isBlank()) {
                throw new IllegalArgumentException("Each reserved ID must be a nonempty JSON string");
            }
            if (!ids.add(value.textValue())) throw new IllegalArgumentException("Duplicate reserved ID: " + value.textValue());
        }
        return Set.copyOf(ids);
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
