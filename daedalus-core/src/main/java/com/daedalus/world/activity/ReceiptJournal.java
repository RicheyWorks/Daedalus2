// SPDX-License-Identifier: MIT
package com.daedalus.world.activity;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/**
 * Append-only journal of settled receipts, one per line as {@code <sha256> <canonical json>}.
 *
 * <p>Reading checks every line: the digest must be the SHA-256 of the JSON and the JSON must be canonical. Any
 * mismatch is a {@link TamperException} naming the line, so a hand-edited receipt can never be replayed into a
 * life's progression. Blank lines are ignored; nothing in the journal is ever rewritten or removed.
 */
public final class ReceiptJournal {

    private static final Pattern DIGEST = Pattern.compile("[0-9a-f]{64}");

    /** A journal line that failed its digest or canonical check. */
    public static final class TamperException extends RuntimeException {
        private static final long serialVersionUID = 1L;
        private final int line;

        public TamperException(int line, String reason) {
            super("journal line " + line + ": " + reason);
            this.line = line;
        }

        public int line() { return line; }
    }

    private ReceiptJournal() { }

    /** The journal line for a receipt. */
    public static String line(ActivityResultReceipt r) {
        return r.digest() + " " + r.toJson();
    }

    /** Reads one line (1-based {@code lineNo} for error messages). */
    public static ActivityResultReceipt read(String line, int lineNo) {
        int sp = line.indexOf(' ');
        if (sp != 64 || !DIGEST.matcher(line.substring(0, sp)).matches())
            throw new TamperException(lineNo, "expected '<sha256> <json>'");
        ActivityResultReceipt r;
        try {
            r = ReceiptCodec.parse(line.substring(sp + 1));
        } catch (IllegalArgumentException e) {
            throw new TamperException(lineNo, e.getMessage());
        }
        if (!r.digest().equals(line.substring(0, sp))) throw new TamperException(lineNo, "digest mismatch");
        return r;
    }

    /** Reads every non-blank line, oldest first. */
    public static List<ActivityResultReceipt> readAll(List<String> lines) {
        List<ActivityResultReceipt> out = new ArrayList<>();
        for (int n = 0; n < lines.size(); n++) {
            String l = lines.get(n);
            if (!l.isBlank()) out.add(read(l, n + 1));
        }
        return List.copyOf(out);
    }

    /** Appends one receipt line to a UTF-8 journal file, creating it if needed. */
    public static void append(Path file, ActivityResultReceipt r) throws IOException {
        Files.writeString(file, line(r) + "\n", StandardCharsets.UTF_8, StandardOpenOption.CREATE,
                StandardOpenOption.APPEND);
    }

    /** Reads a UTF-8 journal file; a missing file is an empty journal. */
    public static List<ActivityResultReceipt> read(Path file) throws IOException {
        if (!Files.exists(file)) return List.of();
        return readAll(Files.readAllLines(file, StandardCharsets.UTF_8));
    }
}
