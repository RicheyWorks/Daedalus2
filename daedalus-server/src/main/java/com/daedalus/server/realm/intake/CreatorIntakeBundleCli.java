// SPDX-License-Identifier: MIT
package com.daedalus.server.realm.intake;

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
 * Local whole-intake transfer using the server runtime classpath, without starting Spring.
 *
 * <pre>
 * CreatorIntakeBundleCli pack PRIVATE_STORE REVISION NEW_ARCHIVE
 * CreatorIntakeBundleCli validate ARCHIVE CURRENT_RESERVED_IDS_JSON
 * CreatorIntakeBundleCli receive ARCHIVE NEW_PRIVATE_ROOT CURRENT_RESERVED_IDS_JSON
 * </pre>
 *
 * Current reserved IDs are always supplied explicitly as a JSON array; [] means no external IDs.
 * That file must be a regular, non-symlink file of at most 8 MiB. Bundle verification and new-only
 * local publication belong to CreatorIntakeBundle. There is no remote transfer, native activation,
 * token allocation or marketplace publication. Use CreatorIntakeCli to inspect or continue a received store.
 */
public final class CreatorIntakeBundleCli {
    private static final int MAX_INPUT_BYTES = 8 * 1024 * 1024;
    private static final ObjectMapper JSON = new ObjectMapper()
            .enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION)
            .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);
    private static final String USAGE = """
            Usage: CreatorIntakeBundleCli COMMAND ...
              pack STORE REVISION NEW_ARCHIVE
              validate ARCHIVE CURRENT_RESERVED_IDS_JSON
              receive ARCHIVE NEW_PRIVATE_ROOT CURRENT_RESERVED_IDS_JSON
            CURRENT_RESERVED_IDS_JSON is an explicit array of unique nonempty strings; [] is allowed.
            Archives and stores stay local. A restored intake does not enable a realm or approve a sale.
            """;

    private CreatorIntakeBundleCli() { }

    public static void main(String[] args) { System.exit(run(args, System.out, System.err)); }

    /** Print JSON or a categorized error and return 0 or 2, leaving caller-owned streams open. */
    public static int run(String[] args, PrintStream out, PrintStream err) {
        try {
            Object result = execute(args);
            out.println(JSON.writerWithDefaultPrettyPrinter().writeValueAsString(result));
            return 0;
        } catch (IOException | RuntimeException failure) {
            String message = failure.getMessage();
            err.println("creator-intake-bundle: " + failure.getClass().getSimpleName()
                    + (message == null || message.isBlank() ? "" : ": " + message));
            return 2;
        }
    }

    private static Object execute(String[] args) throws IOException {
        if (args == null || args.length == 0) throw new IllegalArgumentException(USAGE);
        return switch (args[0]) {
            case "pack" -> {
                count(args, 4);
                yield CreatorIntakeBundle.pack(Path.of(args[1]), revision(args[2]), Path.of(args[3]));
            }
            case "validate" -> {
                count(args, 3);
                yield CreatorIntakeBundle.validate(Path.of(args[1]), reservedIds(args[2]));
            }
            case "receive" -> {
                count(args, 4);
                Set<String> reserved = reservedIds(args[3]);
                yield CreatorIntakeBundle.receive(Path.of(args[1]), Path.of(args[2]), reserved);
            }
            default -> throw new IllegalArgumentException("Unknown command: " + args[0] + "\n" + USAGE);
        };
    }

    private static void count(String[] args, int expected) {
        if (args.length != expected) throw new IllegalArgumentException(USAGE);
    }

    private static int revision(String value) {
        try {
            int parsed = Integer.parseInt(value);
            if (parsed > 0) return parsed;
        } catch (NumberFormatException ignored) { /* Explain the argument below. */ }
        throw new IllegalArgumentException("REVISION must be a positive integer: " + value);
    }

    private static Set<String> reservedIds(String file) throws IOException {
        Path path = Path.of(file);
        if (!Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS)) throw new IOException("Reserved IDs must be a regular file: " + file);
        byte[] bytes;
        try (var input = Files.newInputStream(path, LinkOption.NOFOLLOW_LINKS)) {
            bytes = input.readNBytes(MAX_INPUT_BYTES + 1);
        }
        if (bytes.length > MAX_INPUT_BYTES) throw new IOException("Reserved IDs exceed 8 MiB: " + file);
        JsonNode array = JSON.readTree(bytes);
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
}
