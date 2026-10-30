// SPDX-License-Identifier: MIT
package com.daedalus.server.realm;

import static com.daedalus.server.realm.CreatorRealmScaffold.*;
import static org.assertj.core.api.Assertions.*;

import com.daedalus.world.WorldStyle;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

class CreatorRealmScaffoldTest {
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final String HASH = "0".repeat(64);
    private static final String PIN = "urn:sha256:" + HASH;
    private static final Attribution SYNTHETIC = new Attribution("synthetic-fixture", Basis.SYNTHETIC, null, null);

    private static Original original(String id) { return new Original(id, PIN, HASH, "Synthetic fixture; no creator art"); }
    private static Entry content(String suffix, Role role, Stage stage, SaleIntent intent, String... members) {
        String id = "deathhimself_" + suffix;
        return new Entry(id, role, stage, null, "Synthetic fixture", "No creator art or ideas", PIN, SYNTHETIC,
                intent, List.of(members), stage == Stage.FINAL ? List.of(original(id + "_source")) : List.of(), List.of());
    }
    private static Entry revise(Entry e, String predecessor, Attribution creator, String preview,
                                List<Original> originals, List<BriefRevision> ideas) {
        return new Entry(e.id(), e.role(), e.stage(), predecessor, e.name(), e.description(), preview, creator,
                e.saleIntent(), e.componentIds(), originals, ideas);
    }
    private static Manifest manifest(Entry... entries) {
        Manifest m = empty();
        return new Manifest(m.schemaVersion(), m.identity(), m.realmAttribution(), m.enabled(), m.ready(),
                m.creative(), m.connection(), m.marketplace(), List.of(entries));
    }

    @Test void emptyScaffoldKeepsTwoDistinctRealmsAndUnconfiguredChoices() throws Exception {
        Manifest m = empty();
        assertThat(validate(m, Set.of("labyrinth", "LABYRINTH"))).isEmpty();
        assertThat(m.identity()).isEqualTo(new Identity("deathhimself", "deathhimself", "DEATHHIMSELF", "deathhimself"));
        assertThat(m.connection().from()).isEqualTo(new Endpoint("labyrinth", "LABYRINTH", "labyrinth"));
        assertThat(m.connection().to()).isEqualTo(DESTINATION).isNotEqualTo(m.connection().from());
        assertThat(m.connection().relationship()).isEqualTo("CONNECTED_SEPARATE");
        assertThat(m.connection().nativeAdapter()).isEqualTo("PENDING");
        assertThat(m.enabled() || m.ready() || m.connection().enabled() || WorldStyle.LABYRINTH.ready() || saleReady()).isFalse();
        assertThat(m.entries()).isEmpty();
        assertThat(m.realmAttribution()).isEqualTo(new Attribution("deathhimself", Basis.USER_ASSERTED, null, null));
        JSON.valueToTree(m.creative()).forEach(value -> assertThat(value.isNull()).isTrue());
        JSON.valueToTree(m.marketplace()).forEach(value -> assertThat(value.isNull()).isTrue());
        assertThat(JSON.readValue(JSON.writeValueAsBytes(m), Manifest.class)).isEqualTo(m);
    }

    @Test void checkedInManifestsLoadRoundTripAndKeepAllContentSynthetic() throws Exception {
        Path directory = Path.of("config/realms/deathhimself");
        if (!Files.isDirectory(directory)) directory = Path.of("../config/realms/deathhimself");
        for (String file : List.of("scaffold-v1.json", "intake-example-v1.json")) {
            Manifest m = JSON.readValue(directory.resolve(file).toFile(), Manifest.class);
            assertThat(validate(m, Set.of())).as(file).isEmpty();
            assertThat(JSON.readValue(JSON.writeValueAsBytes(m), Manifest.class)).isEqualTo(m);
            assertThat(m.entries()).allSatisfy(e -> assertThat(e.creator().basis()).isEqualTo(Basis.SYNTHETIC));
        }
    }

    @Test void refusesDuplicateAndForeignCatalogIdsWithoutChangingInput() {
        Entry asset = content("asset", Role.ASSET, Stage.DRAFT, SaleIntent.UNSET);
        assertThat(validate(manifest(asset, asset), Set.of())).anyMatch(e -> e.contains("collision"));
        assertThat(validate(manifest(asset), Set.of(asset.id()))).anyMatch(e -> e.contains("collision"));
        assertThat(validate(empty(), Set.of("DEATHHIMSELF"))).contains("Realm identity collision");
        Entry foreign = new Entry("Mob_Lab_Existing", Role.ASSET, Stage.DRAFT, null, null, null, null,
                SYNTHETIC, SaleIntent.UNSET, List.of(), List.of(), List.of());
        assertThat(validate(manifest(foreign), Set.of())).contains("Invalid realm-scoped content ID");
    }

    @Test void rejectsInventedReadinessDirectionsFinancialChoicesAndVerifiedIdentity() {
        Manifest m = empty();
        Manifest invented = new Manifest(2, new Identity("labyrinth", "deathhimself", "LABYRINTH", "labyrinth"),
                new Attribution("deathhimself", Basis.USER_ASSERTED, "Unverified person", "Unverified account"), true, true,
                new Creative("Invented theme", null, null, null, null),
                new Connection(LABYRINTH, LABYRINTH, "CONNECTED_SEPARATE", true, "READY"),
                new Marketplace(null, null, "Invented token", null, null, null, null, null), m.entries());
        assertThat(validate(invented, Set.of())).contains("Unsupported schemaVersion",
                "Realm identity must remain distinct deathhimself", "Realm attribution is user asserted only",
                "Scaffold must remain disabled and not ready", "Realm creative direction is awaiting creator input",
                "Separate Labyrinth connection requires pending native adapter", "Marketplace choices must remain unconfigured");
        Entry asset = content("asset", Role.ASSET, Stage.DRAFT, SaleIntent.UNSET);
        assertThat(validate(manifest(revise(asset, null,
                new Attribution("creator", null, "Unverified person", null), PIN, List.of(), List.of())), Set.of()))
                .contains("No verified identity supplied", "Creator handle requires an explicit assertion basis");
    }

    @Test void originalsRequireChecksumPinnedUrisAndDistinctSourceIds() {
        Entry asset = content("asset", Role.ASSET, Stage.FINAL, SaleIntent.UNSET);
        Original bad = new Original(asset.id(), "https://example.invalid/mutable", "bad", " ");
        assertThat(validate(manifest(revise(asset, null, SYNTHETIC, PIN, List.of(bad), List.of())), Set.of()))
                .contains("Original requires SHA-256", "Original URI must pin its SHA-256", "Original requires submitted provenance")
                .anyMatch(e -> e.contains("collision"));
        assertThat(validate(manifest(revise(asset, null, SYNTHETIC, PIN, List.of(), List.of())), Set.of()))
                .contains("Final content requires original provenance");
    }

    @Test void labelsEveryRoleWithoutPromotingComponentsOrIdeasForSale() {
        Entry component = content("component", Role.COMPONENT, Stage.FINAL, SaleIntent.UNSET);
        Entry assembly = content("assembly", Role.ASSEMBLY, Stage.FINAL, SaleIntent.REVIEW_REQUESTED, component.id());
        Entry asset = content("asset", Role.ASSET, Stage.FINAL, SaleIntent.NOT_FOR_SALE);
        Entry idea = content("idea", Role.IDEA, Stage.DRAFT, SaleIntent.UNSET);
        assertThat(validate(manifest(component, assembly, asset, idea), Set.of())).isEmpty();
        assertThat(saleEligibility(assembly)).isEqualTo(SaleEligibility.REVIEW_REQUIRED);
        assertThat(saleEligibility(component)).isEqualTo(SaleEligibility.UNREVIEWED);
        assertThat(saleEligibility(asset)).isEqualTo(SaleEligibility.INELIGIBLE);
        assertThat(saleEligibility(idea)).isEqualTo(SaleEligibility.INELIGIBLE);
        for (Entry e : List.of(component, assembly, asset, idea)) {
            assertThat(labels(e)).anySatisfy(label -> {
                assertThat(label.traitType()).isEqualTo("Role"); assertThat(label.value()).isEqualTo(e.role().name());
            });
        }
        assertThat(validate(manifest(content("bad", Role.IDEA, Stage.FINAL, SaleIntent.REVIEW_REQUESTED)), Set.of()))
                .contains("Ideas remain draft briefs", "Ideas are not sale candidates", "Attach art as a separately labelled content entry");
        assertThat(validate(manifest(content("bad", Role.ASSET, Stage.DRAFT, SaleIntent.UNSET, component.id())), Set.of()))
                .contains("Only assemblies reference components");
        assertThat(validate(manifest(content("bad", Role.ASSEMBLY, Stage.DRAFT, SaleIntent.UNSET, "deathhimself_missing")), Set.of()))
                .contains("Assembly members must reference separate assets or components");
    }

    @Test void keepsOriginalsFinalContentAndBriefHistoryAcrossUpdates() {
        Entry old = content("first", Role.ASSET, Stage.FINAL, SaleIntent.UNSET);
        Entry next = content("second", Role.ASSET, Stage.FINAL, SaleIntent.UNSET);
        next = revise(next, old.id(), SYNTHETIC, PIN, next.originals(), List.of());
        assertThat(validateUpdate(manifest(old), manifest(old, next), Set.of())).isEmpty();
        assertThat(validateUpdate(manifest(old), manifest(next), Set.of())).anyMatch(e -> e.startsWith("Preserve previous entry:"));
        assertThat(validateUpdate(manifest(old), manifest(revise(old, null, SYNTHETIC, null, old.originals(), List.of())), Set.of()))
                .anyMatch(e -> e.startsWith("Final content requires a new ID:"));
        Entry draft = content("brief", Role.IDEA, Stage.DRAFT, SaleIntent.UNSET);
        Entry edited = appendIdea(appendIdea(draft, "Synthetic first brief"), "Synthetic revised brief");
        assertThat(draft.ideas()).isEmpty();
        assertThat(edited.ideas()).extracting(BriefRevision::version).containsExactly(1, 2);
        assertThat(validateUpdate(manifest(draft), manifest(edited), Set.of())).isEmpty();
        assertThat(validateUpdate(manifest(edited), manifest(draft), Set.of())).contains("Preserve brief revision history");
        assertThatThrownBy(() -> appendIdea(old, "change")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> appendIdea(draft, " ")).isInstanceOf(IllegalArgumentException.class);
    }

    @Test void finalAssembliesRequireMembersAndEveryAssetOrComponentMustBeFinal() {
        Entry emptyFinal = content("empty_final", Role.ASSEMBLY, Stage.FINAL, SaleIntent.UNSET);
        assertThat(validate(manifest(emptyFinal), Set.of())).contains("Final assembly requires members");
        assertThat(validate(manifest(content("empty_draft", Role.ASSEMBLY, Stage.DRAFT, SaleIntent.UNSET)), Set.of())).isEmpty();
        for (Role role : List.of(Role.ASSET, Role.COMPONENT)) {
            Entry member = content("member", role, Stage.DRAFT, SaleIntent.UNSET);
            Entry assembly = content("assembly", Role.ASSEMBLY, Stage.FINAL, SaleIntent.REVIEW_REQUESTED, member.id());
            assertThat(validate(manifest(member, assembly), Set.of())).contains("Final assembly requires final members");
            Entry finalMember = content("member", role, Stage.FINAL, SaleIntent.UNSET);
            assertThat(validate(manifest(finalMember, assembly), Set.of())).isEmpty();
        }
    }

    @Test void metadataPreservesPredecessorAndNumberedAssemblyMembershipWithoutPromotingMembers() {
        Entry first = content("first_component", Role.COMPONENT, Stage.FINAL, SaleIntent.UNSET);
        Entry second = content("second_asset", Role.ASSET, Stage.FINAL, SaleIntent.NOT_FOR_SALE);
        Entry previous = content("previous_assembly", Role.ASSEMBLY, Stage.FINAL, SaleIntent.REVIEW_REQUESTED, first.id());
        Entry next = content("next_assembly", Role.ASSEMBLY, Stage.FINAL, SaleIntent.REVIEW_REQUESTED, first.id(), second.id());
        next = revise(next, previous.id(), SYNTHETIC, PIN, next.originals(), List.of());
        Manifest intake = manifest(first, second, previous, next);
        var traits = metadataDraft(intake, next.id(), Set.of()).orElseThrow().attributes();
        assertThat(traits).anySatisfy(trait -> {
            assertThat(trait.traitType()).isEqualTo("Supersedes content ID");
            assertThat(trait.value()).isEqualTo(previous.id());
        });
        assertThat(traits).anySatisfy(trait -> {
            assertThat(trait.traitType()).isEqualTo("Component ID 1"); assertThat(trait.value()).isEqualTo(first.id());
        });
        assertThat(traits).anySatisfy(trait -> {
            assertThat(trait.traitType()).isEqualTo("Component ID 2"); assertThat(trait.value()).isEqualTo(second.id());
        });
        assertThat(saleEligibility(first)).isEqualTo(SaleEligibility.UNREVIEWED);
        assertThat(saleEligibility(second)).isEqualTo(SaleEligibility.INELIGIBLE);
        assertThat(saleReady()).isFalse();
    }

    @Test void rejectsCyclesMissingPredecessorsAndReplacedDraftOriginals() {
        Entry a = content("a", Role.ASSET, Stage.DRAFT, SaleIntent.UNSET);
        Entry b = content("b", Role.ASSET, Stage.DRAFT, SaleIntent.UNSET);
        Entry cyclicA = revise(a, b.id(), SYNTHETIC, PIN, List.of(), List.of());
        Entry cyclicB = revise(b, a.id(), SYNTHETIC, PIN, List.of(), List.of());
        assertThat(validate(manifest(cyclicA, cyclicB), Set.of())).contains("Creative lineage must not cycle");
        assertThat(validate(manifest(cyclicA), Set.of())).contains("Preserve a distinct predecessor of the same role");
        Entry withOriginal = revise(a, null, SYNTHETIC, PIN, List.of(original("deathhimself_source")), List.of());
        assertThat(validateUpdate(manifest(withOriginal), manifest(a), Set.of())).contains("Preserve original revisions");
    }

    @Test void metadataDraftUsesExistingSerializedContractAndRequiresFinalAttributedPinnedPreview() throws Exception {
        Entry asset = content("asset", Role.ASSET, Stage.FINAL, SaleIntent.UNSET);
        var metadata = metadataDraft(manifest(asset), asset.id(), Set.of()).orElseThrow();
        var json = JSON.valueToTree(metadata);
        assertThat(json.has("external_url")).isTrue();
        assertThat(json.has("externalUrl")).isFalse();
        assertThat(json.get("image").asText()).isEqualTo(PIN);
        assertThat(json.get("attributes").get(0).has("trait_type")).isTrue();
        assertThat(metadata.attributes()).anyMatch(a -> a.value().equals("UNREVIEWED"));
        assertThatThrownBy(() -> metadata.attributes().clear()).isInstanceOf(UnsupportedOperationException.class);
        Entry unattributed = revise(asset, null, new Attribution(null, null, null, null), PIN, asset.originals(), List.of());
        Entry noPreview = revise(asset, null, SYNTHETIC, null, asset.originals(), List.of());
        assertThat(metadataDraft(manifest(unattributed), asset.id(), Set.of())).isEmpty();
        assertThat(metadataDraft(manifest(noPreview), asset.id(), Set.of())).isEmpty();
        Entry draft = content("draft", Role.ASSET, Stage.DRAFT, SaleIntent.REVIEW_REQUESTED);
        assertThat(metadataDraft(manifest(draft), draft.id(), Set.of())).isEmpty();
        assertThatThrownBy(() -> metadataDraft(manifest(asset), asset.id(), Set.of(asset.id())))
                .isInstanceOf(IllegalArgumentException.class);
        assertThat(saleReady()).isFalse();
    }

    @Test void defensiveCopiesKeepIntakeAndValidationResultsImmutable() {
        List<Original> originals = new ArrayList<>(List.of(original("deathhimself_source")));
        Entry e = content("draft", Role.ASSET, Stage.DRAFT, SaleIntent.UNSET);
        e = revise(e, null, SYNTHETIC, PIN, originals, List.of());
        originals.clear();
        assertThat(e.originals()).hasSize(1);
        Entry copied = e;
        assertThatThrownBy(() -> copied.originals().clear()).isInstanceOf(UnsupportedOperationException.class);
        assertThatThrownBy(() -> copied.componentIds().add("deathhimself_other")).isInstanceOf(UnsupportedOperationException.class);
        assertThatThrownBy(() -> copied.ideas().clear()).isInstanceOf(UnsupportedOperationException.class);
        Manifest m = manifest(e);
        assertThatThrownBy(() -> m.entries().clear()).isInstanceOf(UnsupportedOperationException.class);
        assertThatThrownBy(() -> validate(m, Set.of()).clear()).isInstanceOf(UnsupportedOperationException.class);
    }
}
