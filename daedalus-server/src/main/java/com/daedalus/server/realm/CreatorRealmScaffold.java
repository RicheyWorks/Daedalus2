// SPDX-License-Identifier: MIT
package com.daedalus.server.realm;

import com.daedalus.api.dto.IslandTokenMetadata;
import com.daedalus.api.dto.TokenAttribute;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;

/**
 * Version 1 source-only intake for deathhimself. No service registration, I/O, world generation,
 * native travel, token allocation or publication occurs here. The team implements submitted art/ideas.
 */
public final class CreatorRealmScaffold {
    public static final String REALM_ID = "deathhimself";
    public static final String DISPLAY_NAME = "deathhimself";
    public static final Identity IDENTITY = new Identity(REALM_ID, DISPLAY_NAME, "DEATHHIMSELF", REALM_ID);
    public static final Endpoint LABYRINTH = new Endpoint("labyrinth", "LABYRINTH", "labyrinth");
    public static final Endpoint DESTINATION = new Endpoint(REALM_ID, "DEATHHIMSELF", REALM_ID);

    public enum Basis { USER_ASSERTED, SYNTHETIC }
    public enum Role { ASSET, ASSEMBLY, COMPONENT, IDEA }
    public enum Stage { DRAFT, FINAL }
    public enum SaleIntent { UNSET, NOT_FOR_SALE, REVIEW_REQUESTED }
    public enum SaleEligibility { UNREVIEWED, INELIGIBLE, REVIEW_REQUIRED }

    public record Identity(String realmId, String displayName, String proposedSessionId, String catalogStem) { }
    /** A proposed session/catalog reference is not native registration or an installed content catalog. */
    public record Endpoint(String realmId, String sessionId, String catalogStem) { }
    public record Connection(Endpoint from, Endpoint to, String relationship, boolean enabled, String nativeAdapter) { }
    /** User-asserted creative attribution only; not authenticated identity or a legal ownership claim. */
    public record Attribution(String handle, Basis basis, String legalIdentity, String accountId) { }
    public record Creative(String theme, String visualDirection, String lore, String gameplay, String presentation) { }
    /** Reserved choices, deliberately unconfigured in this scaffold. No inferred financial or license terms. */
    public record Marketplace(String chain, String contract, String tokenId, String wallet, String royalty,
                              String marketplace, String price, String license) { }
    /** Content-addressed original, preserved independently of team edits and creator brief revisions. */
    public record Original(String id, String originalUri, String sha256, String provenance) { }
    public record BriefRevision(int version, String text) { }
    /** Each final creative iteration gets a new ID and retains its predecessor via supersedesId. */
    public record Entry(String id, Role role, Stage stage, String supersedesId, String name, String description,
                        String previewUri, Attribution creator, SaleIntent saleIntent, List<String> componentIds,
                        List<Original> originals, List<BriefRevision> ideas) {
        public Entry {
            componentIds = copy(componentIds);
            originals = copy(originals);
            ideas = copy(ideas);
        }
    }
    public record Manifest(int schemaVersion, Identity identity, Attribution realmAttribution, boolean enabled,
                           boolean ready, Creative creative, Connection connection, Marketplace marketplace, List<Entry> entries) {
        public Manifest { entries = copy(entries); }
    }

    private CreatorRealmScaffold() { }

    public static Manifest empty() {
        return new Manifest(1, IDENTITY, new Attribution(DISPLAY_NAME, Basis.USER_ASSERTED, null, null), false, false,
                new Creative(null, null, null, null, null),
                new Connection(LABYRINTH, DESTINATION, "CONNECTED_SEPARATE", false, "PENDING"),
                new Marketplace(null, null, null, null, null, null, null, null), List.of());
    }

    /** Validate against IDs already present in the host's catalogs; validation never mounts a provider. */
    public static List<String> validate(Manifest manifest, Set<String> existingIds) {
        Objects.requireNonNull(manifest, "manifest");
        Objects.requireNonNull(existingIds, "existingIds");
        List<String> errors = new ArrayList<>();
        Manifest baseline = empty();
        check(manifest.schemaVersion() == 1, "Unsupported schemaVersion", errors);
        check(IDENTITY.equals(manifest.identity()), "Realm identity must remain distinct deathhimself", errors);
        check(baseline.realmAttribution().equals(manifest.realmAttribution()), "Realm attribution is user asserted only", errors);
        check(!manifest.enabled() && !manifest.ready(), "Scaffold must remain disabled and not ready", errors);
        check(baseline.creative().equals(manifest.creative()), "Realm creative direction is awaiting creator input", errors);
        check(baseline.connection().equals(manifest.connection()), "Separate Labyrinth connection requires pending native adapter", errors);
        check(baseline.marketplace().equals(manifest.marketplace()), "Marketplace choices must remain unconfigured", errors);
        check(!existingIds.contains(REALM_ID) && !existingIds.contains("DEATHHIMSELF"), "Realm identity collision", errors);
        Set<String> ids = new HashSet<>(existingIds);
        Map<String, Entry> entries = new HashMap<>();
        for (Entry entry : manifest.entries()) {
            claim(entry.id(), ids, errors);
            entries.put(entry.id(), entry);
            check(entry.role() != null && entry.stage() != null && entry.saleIntent() != null, "Missing entry labels", errors);
            attribution(entry.creator(), errors);
            check(entry.role() == Role.ASSEMBLY || entry.componentIds().isEmpty(), "Only assemblies reference components", errors);
            check(entry.role() != Role.IDEA || entry.stage() == Stage.DRAFT, "Ideas remain draft briefs", errors);
            check(entry.role() != Role.IDEA || entry.originals().isEmpty(), "Attach art as a separately labelled content entry", errors);
            check(entry.role() != Role.IDEA || entry.saleIntent() != SaleIntent.REVIEW_REQUESTED, "Ideas are not sale candidates", errors);
            if (entry.stage() == Stage.FINAL) {
                check(!entry.originals().isEmpty(), "Final content requires original provenance", errors);
                check(entry.role() != Role.ASSEMBLY || !entry.componentIds().isEmpty(), "Final assembly requires members", errors);
            }
            Set<String> members = new HashSet<>();
            for (String member : entry.componentIds()) {
                check(members.add(member), "Duplicate assembly member", errors);
            }
            int version = 0;
            for (BriefRevision idea : entry.ideas()) {
                check(idea.version() == ++version && present(idea.text()), "Brief revisions must be nonempty and ordered", errors);
            }
            for (Original original : entry.originals()) {
                claim(original.id(), ids, errors);
                check(original.sha256() != null && original.sha256().matches("[0-9a-f]{64}"), "Original requires SHA-256", errors);
                check(Objects.equals(original.originalUri(), "urn:sha256:" + original.sha256()), "Original URI must pin its SHA-256", errors);
                check(present(original.provenance()), "Original requires submitted provenance", errors);
            }
        }
        for (Entry entry : manifest.entries()) {
            if (entry.supersedesId() != null) {
                Entry predecessor = entries.get(entry.supersedesId());
                check(predecessor != null && predecessor != entry && predecessor.role() == entry.role(),
                        "Preserve a distinct predecessor of the same role", errors);
                Set<String> lineage = new HashSet<>();
                Entry cursor = entry;
                while (cursor != null && lineage.add(cursor.id())) cursor = entries.get(cursor.supersedesId());
                check(cursor == null, "Creative lineage must not cycle", errors);
            }
            for (String member : entry.componentIds()) {
                Entry component = entries.get(member);
                check(component != null && (component.role() == Role.COMPONENT || component.role() == Role.ASSET),
                        "Assembly members must reference separate assets or components", errors);
                check(entry.stage() != Stage.FINAL || component != null && component.stage() == Stage.FINAL,
                        "Final assembly requires final members", errors);
            }
        }
        return List.copyOf(errors);
    }

    /** Refuse removal/replacement of originals or final entries when accepting the next saved intake. */
    public static List<String> validateUpdate(Manifest previous, Manifest next, Set<String> existingIds) {
        List<String> errors = new ArrayList<>(validate(next, existingIds));
        Map<String, Entry> entries = new HashMap<>();
        for (Entry entry : next.entries()) entries.put(entry.id(), entry);
        for (Entry before : previous.entries()) {
            Entry after = entries.get(before.id());
            if (after == null) {
                errors.add("Preserve previous entry: " + before.id());
            } else if (before.stage() == Stage.FINAL && !before.equals(after)) {
                errors.add("Final content requires a new ID: " + before.id());
            } else {
                check(prefix(before.originals(), after.originals()), "Preserve original revisions", errors);
                check(prefix(before.ideas(), after.ideas()), "Preserve brief revision history", errors);
                check(before.role() == after.role(), "Preserve entry role", errors);
            }
        }
        return List.copyOf(errors);
    }

    /** Append an editable brief revision; final content remains immutable and must receive a new item ID. */
    public static Entry appendIdea(Entry entry, String text) {
        if (entry.stage() != Stage.DRAFT || !present(text)) throw new IllegalArgumentException("A draft and nonempty brief are required");
        List<BriefRevision> ideas = new ArrayList<>(entry.ideas());
        ideas.add(new BriefRevision(ideas.size() + 1, text));
        return new Entry(entry.id(), entry.role(), entry.stage(), entry.supersedesId(), entry.name(), entry.description(),
                entry.previewUri(), entry.creator(), entry.saleIntent(), entry.componentIds(), entry.originals(), ideas);
    }

    public static SaleEligibility saleEligibility(Entry entry) {
        if (entry.role() == Role.IDEA || entry.saleIntent() == SaleIntent.NOT_FOR_SALE) return SaleEligibility.INELIGIBLE;
        return entry.saleIntent() == SaleIntent.REVIEW_REQUESTED ? SaleEligibility.REVIEW_REQUIRED : SaleEligibility.UNREVIEWED;
    }

    /** Every entry is labelled. Assembly membership never grants a component independent sale eligibility. */
    public static List<TokenAttribute> labels(Entry entry) {
        return List.of(TokenAttribute.of("Realm ID", REALM_ID), TokenAttribute.of("Content ID", entry.id()),
                TokenAttribute.of("Role", entry.role().name()), TokenAttribute.of("Content stage", entry.stage().name()),
                TokenAttribute.of("Creator handle", entry.creator().handle() == null ? "UNSET" : entry.creator().handle()),
                TokenAttribute.of("Attribution basis", entry.creator().basis() == null ? "UNSET" : entry.creator().basis().name()),
                TokenAttribute.of("Sale eligibility", saleEligibility(entry).name()));
    }

    /** Offline metadata draft using the existing marketplace DTO, not an island token or sale approval. */
    public static Optional<IslandTokenMetadata> metadataDraft(Manifest manifest, String entryId, Set<String> existingIds) {
        if (!validate(manifest, existingIds).isEmpty()) throw new IllegalArgumentException("Invalid creator intake");
        Entry entry = manifest.entries().stream().filter(item -> item.id().equals(entryId)).findFirst()
                .orElseThrow(() -> new IllegalArgumentException("Unknown content ID"));
        if (entry.stage() != Stage.FINAL || !present(entry.name()) || !present(entry.description())
                || entry.creator().handle() == null || !pinnedPreview(entry)) return Optional.empty();
        List<TokenAttribute> traits = new ArrayList<>(labels(entry));
        if (entry.supersedesId() != null) traits.add(TokenAttribute.of("Supersedes content ID", entry.supersedesId()));
        for (int index = 0; index < entry.componentIds().size(); index++) {
            traits.add(TokenAttribute.of("Component ID " + (index + 1), entry.componentIds().get(index)));
        }
        for (Original original : entry.originals()) {
            traits.add(TokenAttribute.of("Original URI " + original.id(), original.originalUri()));
            traits.add(TokenAttribute.of("Original SHA-256 " + original.id(), original.sha256()));
        }
        return Optional.of(new IslandTokenMetadata(entry.name(), entry.description(), entry.previewUri(), null, traits));
    }

    /** Even complete metadata has no sale authority: rights, production and marketplace review remain external. */
    public static boolean saleReady() { return false; }

    private static boolean pinnedPreview(Entry entry) {
        return entry.originals().stream().anyMatch(original -> original.originalUri().equals(entry.previewUri()));
    }

    private static void attribution(Attribution value, List<String> errors) {
        check(value != null, "Attribution slot is required", errors);
        if (value == null) return;
        check(value.legalIdentity() == null && value.accountId() == null, "No verified identity supplied", errors);
        check(value.handle() == null && value.basis() == null || present(value.handle()) && value.basis() != null,
                "Creator handle requires an explicit assertion basis", errors);
    }

    private static void claim(String id, Set<String> ids, List<String> errors) {
        check(id != null && id.length() <= 48 && id.matches("deathhimself_[a-z0-9_-]+"), "Invalid realm-scoped content ID", errors);
        check(ids.add(id), "Content/source ID collision: " + id, errors);
    }

    private static boolean present(String value) { return value != null && !value.isBlank(); }
    private static <T> List<T> copy(List<T> values) { return values == null ? List.of() : List.copyOf(values); }
    private static <T> boolean prefix(List<T> before, List<T> after) {
        return after.size() >= before.size() && after.subList(0, before.size()).equals(before);
    }
    private static void check(boolean condition, String message, List<String> errors) { if (!condition) errors.add(message); }
}
