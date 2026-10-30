// SPDX-License-Identifier: MIT
package com.daedalus.server.realm.intake;

import com.daedalus.server.realm.CreatorRealmScaffold;
import com.daedalus.server.realm.CreatorRealmScaffold.Attribution;
import com.daedalus.server.realm.CreatorRealmScaffold.Manifest;
import com.daedalus.server.realm.CreatorRealmScaffold.Role;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;

/**
 * Local authoring under one explicit receiving-host reservation snapshot. This wrapper privately owns the
 * existing intake writer lock and adds host-ID checks before delegating authoring to the existing store.
 * It never rewrites the source header or archived history, creates access credentials, or discovers a host.
 * Host/snapshot labels are caller assertions. Their digest binds input bytes semantically, not legal identity
 * or live freshness; later host changes require an explicitly supplied new snapshot and a newly opened session.
 * A session also pins the last successful intake revision/digest and refuses externally changed state.
 * The original CLI remains available; callers must deliberately use this host-bound API/CLI for its overlay.
 */
public final class CreatorIntakeHostSession implements AutoCloseable {
    /** Caller-supplied local labels plus external IDs; no authenticated host, account or ownership mapping. */
    public record HostReservations(String hostId, String snapshotId, Set<String> reservedIds) {
        public HostReservations { reservedIds = Set.copyOf(reservedIds); }
    }
    /** Reproducible description of the supplied context, not a credential or continuing authorization. */
    public record HostBinding(String hostId, String snapshotId, String sha256) { }

    @FunctionalInterface private interface Mutation { CreatorIntakeStore.Snapshot apply() throws IOException; }
    private final CreatorIntakeStore store;
    private final HostReservations host;
    private final HostBinding binding;
    private final Object monitor = new Object();
    private CreatorIntakeStore.Snapshot pinned;
    private boolean closed;

    public static CreatorIntakeHostSession open(Path root, HostReservations host) throws IOException {
        validateHost(host);
        HostBinding binding = bind(host);
        CreatorIntakeStore store = CreatorIntakeStore.open(root);
        try {
            return new CreatorIntakeHostSession(store, host, binding);
        } catch (IOException | RuntimeException failure) {
            try { store.close(); }
            catch (IOException closeFailure) { failure.addSuppressed(closeFailure); }
            throw failure;
        }
    }

    private CreatorIntakeHostSession(CreatorIntakeStore store, HostReservations host, HostBinding binding) throws IOException {
        this.store = store;
        this.host = host;
        this.binding = binding;
        pinned = store.current();
        validateManifest(pinned.manifest());
    }

    public HostBinding binding() { return binding; }

    /** Refuse rebinding an existing session to a changed caller-supplied host snapshot; does not query live state. */
    public void requireHost(HostReservations supplied) throws IOException {
        synchronized (monitor) {
            if (!host.equals(supplied)) throw new IOException("Host reservation snapshot changed; close and reopen the session");
            checked();
        }
    }

    public CreatorIntakeStore.Snapshot current() throws IOException {
        synchronized (monitor) { return checked(); }
    }

    public CreatorIntakeStore.Snapshot read(int revision) throws IOException {
        synchronized (monitor) {
            checked();
            var snapshot = store.read(revision);
            validateManifest(snapshot.manifest());
            return snapshot;
        }
    }

    public List<CreatorIntakeStore.Revision> history() throws IOException {
        synchronized (monitor) {
            checked();
            return store.history();
        }
    }

    /** Complete imported candidates are checked against the receiving-host overlay before any store commit. */
    public CreatorIntakeStore.Snapshot save(int expectedRevision, Manifest candidate) throws IOException {
        return mutate(expectedRevision, () -> {
            validateManifest(candidate);
            return store.save(expectedRevision, candidate);
        });
    }

    public CreatorIntakeStore.Snapshot addEntry(int expectedRevision, String id, Role role, Attribution creator,
                                               String supersedesId) throws IOException {
        return mutate(expectedRevision, () -> {
            available(id);
            return store.addEntry(expectedRevision, id, role, creator, supersedesId);
        });
    }

    public CreatorIntakeStore.Snapshot reviseEntry(int expectedRevision, String newId, String predecessorId,
                                                  Attribution creator) throws IOException {
        return mutate(expectedRevision, () -> {
            available(newId);
            return store.reviseEntry(expectedRevision, newId, predecessorId, creator);
        });
    }

    public CreatorIntakeStore.Snapshot editDraft(int expectedRevision, String entryId,
                                                CreatorIntakeStore.DraftEdit edit) throws IOException {
        return mutate(expectedRevision, () -> store.editDraft(expectedRevision, entryId, edit));
    }

    public CreatorIntakeStore.Snapshot appendIdea(int expectedRevision, String entryId, String text) throws IOException {
        return mutate(expectedRevision, () -> store.appendIdea(expectedRevision, entryId, text));
    }

    /** Host-reserved original IDs refuse before the underlying store can copy any supplied bytes. */
    public CreatorIntakeStore.Snapshot attachOriginal(int expectedRevision, String entryId, String originalId,
                                                      Path source, String provenance, boolean useAsPreview) throws IOException {
        return mutate(expectedRevision, () -> {
            available(originalId);
            return store.attachOriginal(expectedRevision, entryId, originalId, source, provenance, useAsPreview);
        });
    }

    public CreatorIntakeStore.Snapshot finalizeSourceContent(int expectedRevision, String entryId) throws IOException {
        return mutate(expectedRevision, () -> store.finalizeSourceContent(expectedRevision, entryId));
    }

    public CreatorIntakeStore.ExportBundle review(int revision) throws IOException {
        synchronized (monitor) {
            read(revision);
            return store.review(revision);
        }
    }

    public CreatorIntakeStore.ExportBundle export(int revision, Path destination) throws IOException {
        synchronized (monitor) {
            read(revision);
            return store.export(revision, destination);
        }
    }

    private CreatorIntakeStore.Snapshot mutate(int expectedRevision, Mutation mutation) throws IOException {
        synchronized (monitor) {
            var previous = checked();
            if (previous.revision() != expectedRevision) {
                throw new IOException("Stale intake revision: expected " + expectedRevision + ", current " + previous.revision());
            }
            CreatorIntakeStore.Snapshot next = mutation.apply();
            pinned = next;
            return next;
        }
    }

    private CreatorIntakeStore.Snapshot checked() throws IOException {
        if (closed) throw new IOException("Host authoring session is closed");
        CreatorIntakeStore.Snapshot current = store.current();
        if (current.revision() != pinned.revision() || !current.sha256().equals(pinned.sha256())) {
            throw new IOException("Stale host authoring session: intake changed outside the session; close and reopen");
        }
        validateManifest(current.manifest());
        return current;
    }

    private void available(String id) throws IOException {
        if (id != null && host.reservedIds().contains(id)) throw new IOException("Current host ID collision: " + id);
    }

    private void validateManifest(Manifest manifest) throws IOException {
        if (manifest == null) throw new IOException("Missing intake manifest");
        List<String> errors = CreatorRealmScaffold.validate(manifest, host.reservedIds());
        if (!errors.isEmpty()) throw new IOException("Current host reservations: " + String.join("; ", errors));
    }

    private static void validateHost(HostReservations host) throws IOException {
        if (host == null || !label(host.hostId()) || !label(host.snapshotId())
                || host.reservedIds().size() > 100_000
                || host.reservedIds().stream().anyMatch(id -> id.isBlank() || id.length() > 256
                || id.chars().anyMatch(Character::isISOControl))) {
            throw new IOException("Explicit hostId, snapshotId and bounded external reserved IDs are required");
        }
        List<String> errors = CreatorRealmScaffold.validate(CreatorRealmScaffold.empty(), host.reservedIds());
        if (!errors.isEmpty()) throw new IOException("Current host reservations: " + String.join("; ", errors));
    }

    private static boolean label(String text) {
        return text != null && !text.isBlank() && text.length() <= 128 && text.chars().noneMatch(Character::isISOControl);
    }

    private static HostBinding bind(HostReservations host) throws IOException {
        byte[] canonical = new ObjectMapper().writeValueAsBytes(List.of(host.hostId(), host.snapshotId(), new TreeSet<>(host.reservedIds())));
        try {
            String sha256 = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(canonical));
            return new HostBinding(host.hostId(), host.snapshotId(), sha256);
        } catch (NoSuchAlgorithmException failure) { throw new IllegalStateException("SHA-256 unavailable", failure); }
    }

    @Override public void close() throws IOException {
        synchronized (monitor) {
            closed = true;
            store.close();
        }
    }
}
