// SPDX-License-Identifier: MIT
package com.daedalus.world.land;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.nio.channels.Channels;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.Optional;

/** Versioned bounded snapshots with cross-process writer locks and optimistic revisions. */
public final class RealmLayoutStore {
    private static final int MAGIC = 0x444c4159; // DLAY
    private static final int VERSION = 1;
    private static final long MAX_BYTES = 1_000_000;
    private final Path folder;

    public RealmLayoutStore(Path folder) { this.folder = folder.toAbsolutePath().normalize(); }

    private Path path(String realm) {
        RealmLayout.requireRealm(realm);
        return folder.resolve(realm + ".dlay");
    }

    public Optional<RealmLayout> load(String realm) throws IOException {
        Path file = path(realm);
        if (!Files.exists(file)) return Optional.empty();
        if (Files.size(file) > MAX_BYTES) throw new IOException("Layout file exceeds bounded format");
        try (DataInputStream in = new DataInputStream(new BufferedInputStream(Files.newInputStream(file)))) {
            if (in.readInt() != MAGIC || in.readInt() != VERSION) throw new IOException("Unsupported layout format");
            String storedRealm = in.readUTF();
            if (!realm.equals(storedRealm)) throw new IOException("Layout realm mismatch");
            long revision = in.readLong();
            int reservedCount = count(in);
            var reserved = new HashSet<Integer>();
            for (int n = 0; n < reservedCount; n++) {
                if (!reserved.add(in.readInt())) throw new IOException("Duplicate reserved cell");
            }
            int estateCount = count(in);
            var estates = new ArrayList<RealmLayout.Estate>(estateCount);
            for (int n = 0; n < estateCount; n++) {
                estates.add(new RealmLayout.Estate(in.readInt(), in.readInt(), in.readInt(), in.readInt(), in.readLong()));
            }
            if (in.read() != -1) throw new IOException("Unexpected trailing layout data");
            return Optional.of(new RealmLayout(realm, revision, reserved, estates));
        } catch (IllegalArgumentException ex) {
            throw new IOException("Invalid layout data", ex);
        }
    }

    private static int count(DataInputStream in) throws IOException {
        int count = in.readInt();
        if (count < 0 || count > LandGrid.COUNT) throw new IOException("Invalid layout row count");
        return count;
    }

    /** expectedRevision=-1 creates a revision-zero snapshot; existing updates must advance exactly once. */
    public void save(RealmLayout layout, long expectedRevision) throws IOException {
        Path file = path(layout.realm());
        if (expectedRevision < -1 || expectedRevision == Long.MAX_VALUE || layout.revision() != expectedRevision + 1) {
            throw new IllegalArgumentException("Layout must advance the expected revision exactly once");
        }
        Files.createDirectories(folder);
        try (FileChannel lockChannel = FileChannel.open(folder.resolve(layout.realm() + ".lock"),
                StandardOpenOption.CREATE, StandardOpenOption.WRITE);
             FileLock writer = lockChannel.lock()) {
            if (!writer.isValid()) throw new IOException("Layout writer lock unavailable");
            long actual = load(layout.realm()).map(RealmLayout::revision).orElse(-1L);
            if (actual != expectedRevision) throw new IOException("Layout revision conflict");
            Path temporary = Files.createTempFile(folder, layout.realm() + ".", ".tmp");
            try {
                try (FileChannel channel = FileChannel.open(temporary, StandardOpenOption.WRITE);
                     DataOutputStream out = new DataOutputStream(new BufferedOutputStream(Channels.newOutputStream(channel)))) {
                    out.writeInt(MAGIC);
                    out.writeInt(VERSION);
                    out.writeUTF(layout.realm());
                    out.writeLong(layout.revision());
                    out.writeInt(layout.reservedCells().size());
                    for (int cell : layout.reservedCells().stream().sorted().toList()) out.writeInt(cell);
                    out.writeInt(layout.estates().size());
                    for (var e : layout.estates()) {
                        out.writeInt(e.landNumber()); out.writeInt(e.x()); out.writeInt(e.y());
                        out.writeInt(e.size()); out.writeLong(e.seed());
                    }
                    out.flush();
                    channel.force(true);
                }
                // Refuse unsupported atomic replacement rather than risking the prior good snapshot.
                Files.move(temporary, file, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            } finally {
                Files.deleteIfExists(temporary);
            }
        } catch (OverlappingFileLockException ex) {
            throw new IOException("Layout writer is busy", ex);
        }
    }
}
