// SPDX-License-Identifier: MIT
package com.daedalus.world.exploration;

/**
 * Explicit opt-in seam for an existing authoritative host, not a second inventory/session/store.
 * An instance constructed normally is disabled. No Spring bean, endpoint, scheduler or native binding is installed.
 */
public final class ExplorationHostAdapter {
    public enum Publication { SAVED, CONFLICT, UNCONFIRMED }
    public enum Status { DISABLED, REFUSED, REPLAY, REJECTED, COMMITTED, CONFLICT, UNCONFIRMED }

    public interface Host {
        /** Check the approved canonical session identity and host-resolved subject on every call. */
        boolean authorized(String canonicalRealm, String canonicalSubject);
        /** Validate source-world position/ownership and the actual movement or pickup; client assertions are insufficient. */
        boolean witnessed(ExplorationDefinition definition, ExplorationProgress.Snapshot before,
                          ExplorationProgress.Event event);
        /** Existing durable host CAS. SAVED means exact candidate publication is confirmed, including all replay IDs. */
        Publication publish(ExplorationProgress.Snapshot expected, ExplorationProgress.Snapshot candidate);
    }

    public record Outcome(Status status, ExplorationProgress.Snapshot confirmed,
                          ExplorationProgress.Decision decision) { }

    private final ExplorationDefinition definition;
    private final String realm;
    private final Host host;

    /** Default off; the host has not allocated/approved any realm identity. */
    public ExplorationHostAdapter(ExplorationDefinition definition) {
        this(definition, null, null);
    }

    private ExplorationHostAdapter(ExplorationDefinition definition, String canonicalRealm, Host host) {
        ExplorationDefinition.require(definition != null, "definition required");
        this.definition = definition; this.realm = canonicalRealm; this.host = host;
    }

    /** Only the owning integration host may opt in after canonical realm allocation and authority review. */
    public ExplorationHostAdapter bind(String approvedCanonicalRealm, Host authoritativeHost) {
        ExplorationProgress.identity(approvedCanonicalRealm);
        ExplorationDefinition.require(authoritativeHost != null, "authoritative host required");
        return new ExplorationHostAdapter(definition, approvedCanonicalRealm, authoritativeHost);
    }

    public boolean enabled() { return host != null; }

    /** Host reads the snapshot from its store and derives canonicalSubject from its authenticated principal. */
    public Outcome apply(String canonicalSubject, ExplorationProgress.Snapshot before, ExplorationProgress.Event event) {
        if (!enabled()) return new Outcome(Status.DISABLED, before, null);
        if (before == null || !realm.equals(before.realm()) || !before.subject().equals(canonicalSubject)
                || !host.authorized(realm, canonicalSubject)) return new Outcome(Status.REFUSED, before, null);
        ExplorationProgress.Decision decision = ExplorationProgress.prepare(definition, before, event);
        if (decision.status() == ExplorationProgress.Status.REPLAY) return new Outcome(Status.REPLAY, before, decision);
        if (!decision.candidate()) return new Outcome(Status.REJECTED, before, decision);
        if (!host.witnessed(definition, before, event)) return new Outcome(Status.REFUSED, before, decision);
        Publication publication;
        try {
            publication = host.publish(before, decision.snapshot());
        } catch (RuntimeException uncertain) {
            return new Outcome(Status.UNCONFIRMED, before, decision);
        }
        if (publication == Publication.SAVED) return new Outcome(Status.COMMITTED, decision.snapshot(), decision);
        if (publication == Publication.CONFLICT) return new Outcome(Status.CONFLICT, before, decision);
        // No automatic retry after an uncertain durable result; re-read exact host state before reusing event ID.
        return new Outcome(Status.UNCONFIRMED, before, decision);
    }
}
