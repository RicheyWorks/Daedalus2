// SPDX-License-Identifier: MIT
package com.daedalus.world.gallery;

import com.daedalus.world.activity.ActivityMode;
import com.daedalus.world.activity.ActivityOutcome;
import com.daedalus.world.activity.ActivityParticipant;
import com.daedalus.world.activity.ActivityResultAdapter;
import com.daedalus.world.activity.ActivityResultReceipt;
import com.daedalus.world.activity.AwardPolicy;
import com.daedalus.world.activity.ProgressionLedger;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class ColourKnowledgeTest {

    @Test
    void chemistryGrindsPrimariesAndKnownSecondaries() {
        assertThat(Pigment.fromIngredient("beet")).contains(Pigment.RED);
        assertThat(Pigment.fromIngredient("cherry")).contains(Pigment.RED);
        assertThat(Pigment.fromIngredient("cobalt")).contains(Pigment.BLUE);
        assertThat(Pigment.fromIngredient("dawnleaf")).contains(Pigment.YELLOW);
        assertThat(Pigment.fromIngredient("copper")).contains(Pigment.GREEN);
        assertThat(Pigment.fromIngredient("glass")).isEmpty();
        PigmentPalette pal = new PigmentPalette();
        assertThat(pal.grind("glass")).isEqualTo(PigmentPalette.Result.UNKNOWN_INGREDIENT);
        assertThat(pal.grind("beet")).isEqualTo(PigmentPalette.Result.OK);
        assertThat(pal.grind("cobalt")).isEqualTo(PigmentPalette.Result.OK);
        ColourKnowledge k = new ColourKnowledge();
        assertThat(pal.mix(Pigment.VIOLET, k)).isEqualTo(PigmentPalette.Result.NOT_KNOWN);
        for (int i = 0; i < ColourKnowledge.KNOW_AT; i++) { k.learn(Pigment.RED); k.learn(Pigment.BLUE); }
        assertThat(pal.mix(Pigment.VIOLET, k)).isEqualTo(PigmentPalette.Result.OK);
        assertThat(pal.count(Pigment.VIOLET)).isEqualTo(1);
        assertThat(pal.count(Pigment.RED)).isZero();
        assertThat(pal.mix(Pigment.VIOLET, k)).isEqualTo(PigmentPalette.Result.MISSING_PRIMARY);
        assertThat(pal.mix(Pigment.RED, k)).isEqualTo(PigmentPalette.Result.NOT_KNOWN);
    }

    @Test
    void knowledgeUnlocksAbilitiesAndPrismSightNeedsAllPrimaries() {
        ColourKnowledge k = new ColourKnowledge();
        assertThat(k.abilities()).isEmpty();
        for (int i = 0; i < ColourKnowledge.KNOW_AT - 1; i++) k.learn(Pigment.RED);
        assertThat(k.knows(Pigment.RED)).isFalse();
        k.learn(Pigment.RED);
        assertThat(k.abilities()).containsExactly(ColourKnowledge.Ability.EMBER_LANTERN);
        for (int i = 0; i < ColourKnowledge.KNOW_AT; i++) { k.learn(Pigment.YELLOW); k.learn(Pigment.BLUE); }
        assertThat(k.abilities()).contains(ColourKnowledge.Ability.PRISM_SIGHT, ColourKnowledge.Ability.CANAL_TINT,
                ColourKnowledge.Ability.SUNWASH).doesNotContain(ColourKnowledge.Ability.TRELLIS_VINE);
        assertThat(k.canMix(Pigment.GREEN)).isTrue();
        assertThat(k.snapshot()).containsEntry(Pigment.RED, ColourKnowledge.KNOW_AT);
    }

    @Test
    void restorationSessionCreditsCompanionsOnceThroughG12Receipts() {
        LivingPainting m = new LivingPainting(31_337, 2, 2);
        ColourKnowledge k = LivingPaintingTest.primed();
        PigmentPalette pal = new PigmentPalette();
        for (int y = 0; y < 2; y++) for (int x = 0; x < 2; x++) {
            Pigment need = m.reveal(x, y, k);
            LivingPaintingTest.stock(pal, need, k);
            m.paint(x, y, need, pal, k);
        }
        MuralRestorationAdapter adapter = new MuralRestorationAdapter(ActivityMode.AUTHORITATIVE);
        ActivityParticipant finch = new ActivityParticipant("life:prism-finch-3", ActivityParticipant.Kind.LIFE, "bird", "carrying");
        ActivityResultAdapter.Session s = new ActivityResultAdapter.Session("sess-gal-1", "res-gal-1", "gallery-host",
                "verify:gal-1", List.of(finch), List.of("evt:mural-31337"), 1_760_864_000_000L);
        ActivityResultReceipt r = adapter.toReceipt(s, MuralRestorationAdapter.Session.of(m, 0, 0, false));
        assertThat(r.outcome()).isEqualTo(ActivityOutcome.COMPLETED);
        assertThat(r.measures()).containsEntry("cells_restored", 4L).containsEntry("mural_living", 1L)
                .containsEntry("smudges", 0L);
        ProgressionLedger ledger = new ProgressionLedger();
        AwardPolicy policy = new AwardPolicy(MuralRestorationAdapter.ACTIVITY_ID, 1, "mastery.restoration",
                Map.of("cells_restored", 1L, "mural_living", 5L), 100);
        ledger.credit(r, policy);
        ledger.credit(adapter.toReceipt(s, MuralRestorationAdapter.Session.of(m, 0, 0, false)), policy);
        assertThat(ledger.total("life:prism-finch-3", "mastery.restoration")).isEqualTo(9);
        ActivityResultReceipt partial = adapter.toReceipt(new ActivityResultAdapter.Session("sess-gal-2", "res-gal-2",
                "gallery-host", "verify:gal-2", List.of(finch), List.of(), 1L), new MuralRestorationAdapter.Session(1, 2, 3, false, true));
        assertThat(partial.outcome()).isEqualTo(ActivityOutcome.ABANDONED);
        assertThat(policy.points(partial)).isZero();
    }
}
