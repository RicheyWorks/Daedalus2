// SPDX-License-Identifier: MIT
import com.daedalus.world.land.RealmLayout;
import com.daedalus.world.land.RealmLayoutStore;
import java.io.IOException;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/** Operator-only importer: validates through the canonical core, never rewrites existing snapshots. */
public final class ProvisionEditorLayouts {
    private static final Set<Integer> HUB = Set.of(0,1,2,3,4,5,6,7,8);
    private record Capture(String digest, String namespace, Map<String, RealmLayout> layouts) {}

    private static Capture read(Path input) throws IOException {
        if (Files.size(input) > 3_000_000) throw new IOException("Normalized capture exceeds byte bound");
        List<String> lines = Files.readAllLines(input, StandardCharsets.UTF_8);
        if (lines.size() < 4 || !lines.getFirst().equals("DLAY_IMPORT 1")) throw new IOException("Unsupported capture");
        if (!lines.get(1).startsWith("# capture-sha256=") || !lines.get(2).startsWith("# seed-namespace=")) {
            throw new IOException("Missing provenance header keys");
        }
        String digest = lines.get(1).replace("# capture-sha256=", "");
        String namespace = lines.get(2).replace("# seed-namespace=", "");
        if (!digest.matches("[0-9a-f]{64}") || !namespace.matches("[A-Za-z0-9._-]{1,100}")) {
            throw new IOException("Invalid provenance headers");
        }
        Map<String, List<RealmLayout.Estate>> rows = new TreeMap<>();
        try {
            for (String line : lines.subList(3, lines.size())) {
                if (line.isBlank()) continue;
                String[] fields = line.split("\\t", -1);
                if (fields.length != 6) throw new IllegalArgumentException("Six columns required");
                RealmLayout.requireRealm(fields[0]);
                rows.computeIfAbsent(fields[0], key -> new ArrayList<>()).add(new RealmLayout.Estate(
                    Integer.parseInt(fields[1]), Integer.parseInt(fields[2]), Integer.parseInt(fields[3]),
                    Integer.parseInt(fields[4]), Long.parseLong(fields[5])));
            }
            if (rows.isEmpty()) throw new IllegalArgumentException("No estates supplied");
            Map<String, RealmLayout> layouts = new TreeMap<>();
            for (var entry : rows.entrySet()) {
                // Core validates hub reservations, duplicates, occupancy and district boundaries.
                layouts.put(entry.getKey(), new RealmLayout(entry.getKey(), 0, HUB, entry.getValue()));
            }
            return new Capture(digest, namespace, layouts);
        } catch (IllegalArgumentException ex) { throw new IOException("Invalid editor placement capture", ex); }
    }

    private static String sha(Path file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (var in = Files.newInputStream(file)) {
            byte[] bytes = new byte[65536];
            for (int read; (read = in.read(bytes)) >= 0;) digest.update(bytes, 0, read);
        }
        return HexFormat.of().formatHex(digest.digest());
    }

    private static String publish(Capture capture, Path destination) throws Exception {
        Path target = destination.toAbsolutePath().normalize();
        Path parent = target.getParent();
        if (parent == null) throw new IOException("Destination requires a parent directory");
        Files.createDirectories(parent);
        // All instances use the same operator-directory lock. Never touch a live store in place.
        try (var channel = FileChannel.open(parent.resolve(".editor-layout-provision.lock"),
                    StandardOpenOption.CREATE, StandardOpenOption.WRITE);
             FileLock lock = channel.lock()) {
            if (!lock.isValid() || !Files.notExists(target)) throw new IOException("Destination exists or is inaccessible");
            Path stage = Files.createTempDirectory(parent, ".editor-layout-stage-");
            boolean published = false;
            try {
                RealmLayoutStore store = new RealmLayoutStore(stage);
                List<String> entries = new ArrayList<>();
                for (var layout : capture.layouts().values()) {
                    store.save(layout, -1);
                    RealmLayout reloaded = store.load(layout.realm()).orElseThrow();
                    if (!reloaded.equals(layout)) throw new IOException("Reload differs from supplied layout");
                    Path file = stage.resolve(layout.realm() + ".dlay");
                    entries.add("{\"realm\":\"" + layout.realm() + "\",\"lands\":" + layout.estates().size()
                        + ",\"revision\":0,\"sha256\":\"" + sha(file) + "\"}");
                }
                String manifest = "{\"schemaVersion\":1,\"captureSha256\":\"" + capture.digest()
                    + "\",\"developmentSeedNamespace\":\"" + capture.namespace()
                    + "\",\"reservedCells\":[0,1,2,3,4,5,6,7,8],\"realms\":[" + String.join(",", entries)
                    + "],\"authority\":\"physical-layout-only\"}";
                Files.writeString(stage.resolve("provisioning.json"), manifest, StandardCharsets.UTF_8,
                                  StandardOpenOption.CREATE_NEW);
                // Single directory publish avoids a half-visible five-realm candidate bundle.
                if (!Files.notExists(target)) throw new IOException("Destination appeared during preparation");
                Files.move(stage, target, StandardCopyOption.ATOMIC_MOVE);
                published = true;
                return manifest;
            } finally {
                if (!published) {
                    // Stage is newly created, flat and private. Never recurse or touch destination.
                    try (var files = Files.newDirectoryStream(stage)) {
                        for (Path file : files) Files.deleteIfExists(file);
                    }
                    Files.deleteIfExists(stage);
                }
            }
        }
    }

    public static void main(String[] args) throws Exception {
        Map<String, String> options = new HashMap<>();
        boolean write = false;
        for (int i = 0; i < args.length; i++) {
            if (args[i].equals("--write")) write = true;
            else if ((args[i].equals("--input") || args[i].equals("--out")) && i + 1 < args.length) {
                if (options.put(args[i], args[++i]) != null) throw new IllegalArgumentException("Duplicate option");
            } else throw new IllegalArgumentException("Use --input FILE [--out NEW_DIRECTORY --write]");
        }
        if (!options.containsKey("--input")) throw new IllegalArgumentException("--input is required");
        Capture capture = read(Path.of(options.get("--input")));
        int total = capture.layouts().values().stream().mapToInt(layout -> layout.estates().size()).sum();
        if (!write) System.out.println("VALIDATED realms=" + capture.layouts().size() + " lands=" + total + " (no files written)");
        else {
            if (!options.containsKey("--out")) throw new IllegalArgumentException("--out required for --write");
            System.out.println(publish(capture, Path.of(options.get("--out"))));
        }
    }
}
