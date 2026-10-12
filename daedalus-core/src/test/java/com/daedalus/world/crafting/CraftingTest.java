// SPDX-License-Identifier: MIT

package com.daedalus.world.crafting;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

/**
 * Economy v0 quantities are an atomic inventory exchange: every input is available before any is
 * consumed, outputs fit before anything changes, and callers retain immutable result snapshots.
 */
class CraftingTest {

    // Exact fixtures from shared main's data/economy/recipes.json; recipe IDs need not be output item IDs.
    private static final Recipe COPPER = new Recipe("copper_ingot", "bloomery", 20,
            List.of(component("copper_ore", 2), component("charcoal", 1)), List.of(component("copper", 1)));
    private static final Recipe BRONZE = new Recipe("bronze_ingot", "smelter", 20,
            List.of(component("copper", 3), component("tin", 1)), List.of(component("bronze", 4)));
    private static final Recipe HARNESS = new Recipe("pet_harness", "workbench", 20,
            List.of(component("leather", 2), component("rope", 1), component("bronze", 1)), List.of(component("pet_harness", 1)));

    @Test
    void copperUsesTheCanonicalStationAndProducesTheItemRatherThanTheRecipeId() {
        Map<String, Integer> stock = new HashMap<>(Map.of("copper_ore", 4, "charcoal", 1, "hardwood", 8));

        CraftResult result = Crafting.craft(COPPER, stock, "bloomery");

        assertThat(result.status()).isEqualTo(CraftResult.Status.CRAFTED);
        assertThat(result.success()).isTrue();
        assertThat(result.recipeId()).isEqualTo("copper_ingot");
        assertThat(result.batches()).isEqualTo(1);
        assertThat(result.inventory()).isEqualTo(Map.of("copper_ore", 2, "copper", 1, "hardwood", 8));
        assertThat(result.inventory()).doesNotContainKeys("charcoal", "copper_ingot");
        assertThat(result.missing()).isEmpty();
        assertThat(stock).isEqualTo(Map.of("copper_ore", 4, "charcoal", 1, "hardwood", 8));
        assertThat(COPPER.seconds()).as("duration is recipe metadata").isEqualTo(20);
    }

    @Test
    void twoBronzeBatchesScaleEveryQuantityAndAddToExistingOutputStock() {
        Map<String, Integer> stock = Map.of("copper", 6, "tin", 2, "bronze", 5, "water", 0);

        CraftResult result = Crafting.craft(BRONZE, stock, "smelter", 2);

        assertThat(result.status()).isEqualTo(CraftResult.Status.CRAFTED);
        assertThat(result.batches()).isEqualTo(2);
        assertThat(result.inventory()).isEqualTo(Map.of("bronze", 13, "water", 0));
        assertThat(result.missing()).isEmpty();
        assertThat(stock).isEqualTo(Map.of("copper", 6, "tin", 2, "bronze", 5, "water", 0));
    }

    @Test
    void theHarnessConsumesAllThreeInputsAndPreservesUnrelatedZeroEntries() {
        CraftResult result = Crafting.craft(HARNESS,
                Map.of("leather", 2, "rope", 1, "bronze", 1, "copper", 0), "workbench", 1);

        assertThat(result.success()).isTrue();
        assertThat(result.inventory()).isEqualTo(Map.of("pet_harness", 1, "copper", 0));
        assertThat(result.inventory()).doesNotContainKeys("leather", "rope", "bronze");
    }

    @Test
    void aWrongStationReturnsAnUnchangedSnapshotWithoutReportingIngredientShortages() {
        Map<String, Integer> stock = new HashMap<>(Map.of("copper_ore", 1, "water", 0));
        Map<String, Integer> before = Map.copyOf(stock);

        CraftResult result = Crafting.craft(COPPER, stock, "Bloomery", 3);

        assertThat(result.status()).isEqualTo(CraftResult.Status.WRONG_STATION);
        assertThat(result.success()).isFalse();
        assertThat(result.recipeId()).isEqualTo(COPPER.id());
        assertThat(result.batches()).isEqualTo(3);
        assertThat(result.inventory()).isEqualTo(before);
        assertThat(result.missing()).isEmpty();
        assertThat(stock).isEqualTo(before);
        stock.put("copper_ore", 99);
        assertThat(result.inventory()).isEqualTo(before);
    }

    @Test
    void aMissingLaterIngredientDoesNotConsumeAnEarlierAvailableIngredient() {
        Map<String, Integer> stock = new HashMap<>(Map.of("copper", 3, "tin", 0, "bronze", 2));
        Map<String, Integer> before = Map.copyOf(stock);

        CraftResult result = Crafting.craft(BRONZE, stock, "smelter", 1);

        assertThat(result.status()).isEqualTo(CraftResult.Status.INSUFFICIENT_INGREDIENTS);
        assertThat(result.success()).isFalse();
        assertThat(result.inventory()).isEqualTo(before);
        assertThat(result.missing()).isEqualTo(Map.of("tin", 1));
        assertThat(stock).isEqualTo(before);
    }

    @Test
    void everyMissingIngredientReportsRequiredMinusAvailableAcrossBatches() {
        Map<String, Integer> stock = Map.of("leather", 1, "rope", 0, "hardwood", 50);

        CraftResult result = Crafting.craft(HARNESS, stock, "workbench", 2);

        assertThat(result.status()).isEqualTo(CraftResult.Status.INSUFFICIENT_INGREDIENTS);
        assertThat(result.missing()).isEqualTo(Map.of("leather", 3, "rope", 2, "bronze", 2));
        assertThat(result.inventory()).isEqualTo(stock);
    }

    @Test
    void anEmptyInventoryReportsAllInputsAndCannotBeFilledByARecipe() {
        CraftResult result = Crafting.craft(COPPER, Map.of(), "bloomery", 1);

        assertThat(result.status()).isEqualTo(CraftResult.Status.INSUFFICIENT_INGREDIENTS);
        assertThat(result.inventory()).isEmpty();
        assertThat(result.missing()).isEqualTo(Map.of("copper_ore", 2, "charcoal", 1));
    }

    @Test
    void duplicateInputAndOutputRowsAreAggregatedBeforeCheckingAndCrafting() {
        Recipe recipe = new Recipe("alloy", "smelter", 0,
                List.of(component("copper", 2), component("tin", 1), component("copper", 1)),
                List.of(component("bronze", 1), component("bronze", 3)));

        assertThat(recipe.inputs()).containsExactlyInAnyOrder(component("copper", 3), component("tin", 1));
        assertThat(recipe.outputs()).containsExactly(component("bronze", 4));
        CraftResult shortResult = Crafting.craft(recipe, Map.of("copper", 2, "tin", 1), "smelter", 1);
        assertThat(shortResult.status()).isEqualTo(CraftResult.Status.INSUFFICIENT_INGREDIENTS);
        assertThat(shortResult.missing()).isEqualTo(Map.of("copper", 1));
        assertThat(shortResult.inventory()).isEqualTo(Map.of("copper", 2, "tin", 1));

        CraftResult result = Crafting.craft(recipe, Map.of("copper", 6, "tin", 2), "smelter", 2);
        assertThat(result.inventory()).isEqualTo(Map.of("bronze", 8));
        assertThat(result.success()).isTrue();
        assertThat(recipe.seconds()).as("zero duration is allowed metadata").isZero();
    }

    @Test
    void duplicateQuantityOverflowIsRejectedOnEitherSideOfARecipe() {
        List<Recipe.Component> overflow = List.of(component("copper", Integer.MAX_VALUE), component("copper", 1));
        List<Recipe.Component> valid = List.of(component("tin", 1));

        assertThatThrownBy(() -> new Recipe("overflow", "smelter", 20, overflow, valid))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Recipe("overflow", "smelter", 20, valid, overflow))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void overflowingAnExistingOutputRollsBackEveryInputAndEarlierOutput() {
        Recipe recipe = new Recipe("two_outputs", "workbench", 20, List.of(component("hardwood", 1)),
                List.of(component("rope", 1), component("bronze", 1)));
        Map<String, Integer> stock = new HashMap<>(Map.of("hardwood", 1, "bronze", Integer.MAX_VALUE, "water", 0));
        Map<String, Integer> before = Map.copyOf(stock);

        CraftResult result = Crafting.craft(recipe, stock, "workbench", 1);

        assertThat(result.status()).isEqualTo(CraftResult.Status.OVERFLOW);
        assertThat(result.success()).isFalse();
        assertThat(result.inventory()).isEqualTo(before);
        assertThat(result.missing()).isEmpty();
        assertThat(stock).isEqualTo(before);
    }

    @Test
    void multiplyingEitherInputsOrOutputsByBatchesCannotWrap() {
        Recipe inputOverflow = new Recipe("large_input", "workbench", 0,
                List.of(component("hardwood", Integer.MAX_VALUE)), List.of(component("rope", 1)));
        Map<String, Integer> largeStock = Map.of("hardwood", Integer.MAX_VALUE);
        CraftResult inputResult = Crafting.craft(inputOverflow, largeStock, "workbench", 2);
        assertThat(inputResult.status()).isEqualTo(CraftResult.Status.OVERFLOW);
        assertThat(inputResult.inventory()).isEqualTo(largeStock);
        assertThat(inputResult.missing()).isEmpty();

        Recipe outputOverflow = new Recipe("large_output", "workbench", 0,
                List.of(component("hardwood", 1)), List.of(component("rope", Integer.MAX_VALUE)));
        Map<String, Integer> stock = Map.of("hardwood", 2);
        CraftResult outputResult = Crafting.craft(outputOverflow, stock, "workbench", 2);
        assertThat(outputResult.status()).isEqualTo(CraftResult.Status.OVERFLOW);
        assertThat(outputResult.inventory()).isEqualTo(stock);
        assertThat(outputResult.missing()).isEmpty();
    }

    @Test
    void balancedInputsAndOutputsAtTheIntegerCeilingUseTheNetChange() {
        Recipe recipe = new Recipe("rework", "workbench", 0,
                List.of(component("copper", 1)), List.of(component("copper", 1)));
        Map<String, Integer> stock = Map.of("copper", Integer.MAX_VALUE, "water", 0);

        CraftResult result = Crafting.craft(recipe, stock, "workbench", Integer.MAX_VALUE);

        assertThat(result.status()).isEqualTo(CraftResult.Status.CRAFTED);
        assertThat(result.inventory()).isEqualTo(stock);
        assertThat(result.missing()).isEmpty();
    }

    @Test
    void overlappingInputsAndOutputsCanReduceCeilingStockButCannotGrowPastIt() {
        Recipe shrinking = new Recipe("shrink", "workbench", 0,
                List.of(component("copper", 2)), List.of(component("copper", 1)));
        Map<String, Integer> stock = Map.of("copper", Integer.MAX_VALUE);
        CraftResult smaller = Crafting.craft(shrinking, stock, "workbench", 1);
        assertThat(smaller.success()).isTrue();
        assertThat(smaller.inventory()).isEqualTo(Map.of("copper", Integer.MAX_VALUE - 1));

        Recipe growing = new Recipe("grow", "workbench", 0,
                List.of(component("copper", 1)), List.of(component("copper", 2)));
        CraftResult overflow = Crafting.craft(growing, stock, "workbench", 1);
        assertThat(overflow.status()).isEqualTo(CraftResult.Status.OVERFLOW);
        assertThat(overflow.inventory()).isEqualTo(stock);
    }

    @Test
    void anOutputOfTheSameItemCannotSupplyItsOwnMissingInput() {
        Recipe recipe = new Recipe("rework", "workbench", 0,
                List.of(component("copper", 2)), List.of(component("copper", 2)));

        CraftResult result = Crafting.craft(recipe, Map.of("copper", 1), "workbench", 1);

        assertThat(result.status()).isEqualTo(CraftResult.Status.INSUFFICIENT_INGREDIENTS);
        assertThat(result.inventory()).isEqualTo(Map.of("copper", 1));
        assertThat(result.missing()).isEqualTo(Map.of("copper", 1));
    }

    @Test
    void recipesDefensivelyCopyAndExposeImmutableAggregatedLists() {
        List<Recipe.Component> inputs = new ArrayList<>(List.of(component("hardwood", 1), component("hardwood", 2)));
        List<Recipe.Component> outputs = new ArrayList<>(List.of(component("rope", 1)));
        Recipe recipe = new Recipe("rope", "workbench", 20, inputs, outputs);
        inputs.clear();
        outputs.set(0, component("bronze", 99));

        assertThat(recipe.inputs()).containsExactly(component("hardwood", 3));
        assertThat(recipe.outputs()).containsExactly(component("rope", 1));
        assertThatThrownBy(() -> recipe.inputs().add(component("tin", 1))).isInstanceOf(UnsupportedOperationException.class);
        assertThatThrownBy(() -> recipe.outputs().clear()).isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void aRecipeCanBeReusedWithoutChangingItOrPreviousResults() {
        Map<String, Integer> stock = new HashMap<>(Map.of("copper_ore", 4, "charcoal", 2));
        Map<String, Integer> before = Map.copyOf(stock);

        CraftResult first = Crafting.craft(COPPER, stock, "bloomery", 1);
        CraftResult repeated = Crafting.craft(COPPER, stock, "bloomery", 1);
        CraftResult second = Crafting.craft(COPPER, first.inventory(), "bloomery", 1);
        stock.clear();

        assertThat(first).isEqualTo(repeated);
        assertThat(first.inventory()).isEqualTo(Map.of("copper_ore", 2, "charcoal", 1, "copper", 1));
        assertThat(second.inventory()).isEqualTo(Map.of("copper", 2));
        assertThat(before).isEqualTo(Map.of("copper_ore", 4, "charcoal", 2));
        assertThat(COPPER.inputs()).containsExactlyInAnyOrder(component("copper_ore", 2), component("charcoal", 1));
        assertThat(COPPER.outputs()).containsExactly(component("copper", 1));
    }

    @Test
    void successAndFailureMapsAreImmutableAndDetachedFromCallerStock() {
        Map<String, Integer> stock = new HashMap<>(Map.of("copper_ore", 2, "charcoal", 1));
        CraftResult success = Crafting.craft(COPPER, stock, "bloomery", 1);
        assertThatThrownBy(() -> success.inventory().put("copper", 99)).isInstanceOf(UnsupportedOperationException.class);
        assertThatThrownBy(() -> success.missing().put("tin", 1)).isInstanceOf(UnsupportedOperationException.class);
        stock.clear();
        assertThat(success.inventory()).isEqualTo(Map.of("copper", 1));

        stock.put("copper", 3);
        CraftResult failure = Crafting.craft(BRONZE, stock, "smelter", 1);
        assertThatThrownBy(() -> failure.inventory().put("tin", 1)).isInstanceOf(UnsupportedOperationException.class);
        assertThatThrownBy(() -> failure.missing().put("tin", 99)).isInstanceOf(UnsupportedOperationException.class);
        stock.put("tin", 1);
        assertThat(failure.inventory()).isEqualTo(Map.of("copper", 3));
        assertThat(failure.missing()).isEqualTo(Map.of("tin", 1));
    }

    @Test
    void componentIdsAndQuantitiesRejectNullBlankAndNonpositiveValues() {
        for (String item : new String[] {null, "", " ", "\t\n"}) {
            assertThatThrownBy(() -> component(item, 1)).isInstanceOf(IllegalArgumentException.class);
        }
        for (int quantity : new int[] {0, -1, Integer.MIN_VALUE}) {
            assertThatThrownBy(() -> component("copper", quantity)).isInstanceOf(IllegalArgumentException.class);
        }
    }

    @Test
    void recipeMetadataAndBothComponentListsRejectMalformedValues() {
        List<Recipe.Component> valid = List.of(component("copper", 1));
        for (String id : new String[] {null, "", " \t"}) {
            assertThatThrownBy(() -> new Recipe(id, "smelter", 0, valid, valid)).isInstanceOf(IllegalArgumentException.class);
            assertThatThrownBy(() -> new Recipe("alloy", id, 0, valid, valid)).isInstanceOf(IllegalArgumentException.class);
        }
        assertThatThrownBy(() -> new Recipe("alloy", "smelter", -1, valid, valid)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Recipe("alloy", "smelter", 0, null, valid)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Recipe("alloy", "smelter", 0, valid, null)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Recipe("alloy", "smelter", 0, List.of(), valid)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Recipe("alloy", "smelter", 0, valid, List.of())).isInstanceOf(IllegalArgumentException.class);
        List<Recipe.Component> nullEntry = Arrays.asList(component("copper", 1), null);
        assertThatThrownBy(() -> new Recipe("alloy", "smelter", 0, nullEntry, valid)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Recipe("alloy", "smelter", 0, valid, nullEntry)).isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void craftRejectsNullArgumentsBlankStationsAndNonpositiveBatches() {
        Map<String, Integer> stock = Map.of("copper_ore", 2, "charcoal", 1);
        assertThatThrownBy(() -> Crafting.craft(null, stock, "bloomery", 1)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> Crafting.craft(COPPER, null, "bloomery", 1)).isInstanceOf(IllegalArgumentException.class);
        for (String station : new String[] {null, "", " \t\n"}) {
            assertThatThrownBy(() -> Crafting.craft(COPPER, stock, station, 1)).isInstanceOf(IllegalArgumentException.class);
        }
        for (int batches : new int[] {0, -1, Integer.MIN_VALUE}) {
            assertThatThrownBy(() -> Crafting.craft(COPPER, stock, "bloomery", batches)).isInstanceOf(IllegalArgumentException.class);
        }
        assertThat(stock).isEqualTo(Map.of("copper_ore", 2, "charcoal", 1));
    }

    @Test
    void everyInventoryEntryIsValidatedEvenAtTheWrongStation() {
        for (String key : new String[] {null, "", " \t\n"}) {
            Map<String, Integer> malformed = new HashMap<>();
            malformed.put(key, 1);
            assertThatThrownBy(() -> Crafting.craft(COPPER, malformed, "anvil", 1)).isInstanceOf(IllegalArgumentException.class);
            assertThat(malformed).hasSize(1);
        }
        Map<String, Integer> nullCount = new HashMap<>();
        nullCount.put("unrelated", null);
        assertThatThrownBy(() -> Crafting.craft(COPPER, nullCount, "anvil", 1)).isInstanceOf(IllegalArgumentException.class);
        assertThat(nullCount).containsEntry("unrelated", null);
        Map<String, Integer> negativeCount = new HashMap<>(Map.of("copper_ore", 2, "charcoal", 1, "unrelated", -1));
        assertThatThrownBy(() -> Crafting.craft(COPPER, negativeCount, "bloomery", 1)).isInstanceOf(IllegalArgumentException.class);
        assertThat(negativeCount).isEqualTo(Map.of("copper_ore", 2, "charcoal", 1, "unrelated", -1));
    }

    @Test
    void directlyConstructedResultsDefensivelyCopyBothMaps() {
        Map<String, Integer> stock = new HashMap<>(Map.of("copper", 3, "water", 0));
        Map<String, Integer> missing = new HashMap<>(Map.of("tin", 1));
        CraftResult result = new CraftResult(CraftResult.Status.INSUFFICIENT_INGREDIENTS, "bronze_ingot", 1, stock, missing);
        stock.clear();
        missing.put("tin", 99);

        assertThat(result.success()).isFalse();
        assertThat(result.inventory()).isEqualTo(Map.of("copper", 3, "water", 0));
        assertThat(result.missing()).isEqualTo(Map.of("tin", 1));
        assertThatThrownBy(() -> result.inventory().clear()).isInstanceOf(UnsupportedOperationException.class);
        assertThatThrownBy(() -> result.missing().clear()).isInstanceOf(UnsupportedOperationException.class);
    }

    @Test
    void resultMetadataRejectsNullStatusBlankRecipeIdsAndNonpositiveBatches() {
        assertThatThrownBy(() -> new CraftResult(null, "copper_ingot", 1, Map.of(), Map.of()))
                .isInstanceOf(IllegalArgumentException.class);
        for (String id : new String[] {null, "", " \t"}) {
            assertThatThrownBy(() -> new CraftResult(CraftResult.Status.CRAFTED, id, 1, Map.of(), Map.of()))
                    .isInstanceOf(IllegalArgumentException.class);
        }
        for (int batches : new int[] {0, -1, Integer.MIN_VALUE}) {
            assertThatThrownBy(() -> new CraftResult(CraftResult.Status.CRAFTED, "copper_ingot", batches, Map.of(), Map.of()))
                    .isInstanceOf(IllegalArgumentException.class);
        }
    }

    @Test
    void onlyInsufficientResultsCarryPositiveMissingCounts() {
        assertThatThrownBy(() -> new CraftResult(CraftResult.Status.INSUFFICIENT_INGREDIENTS, "copper_ingot", 1, Map.of(), Map.of()))
                .isInstanceOf(IllegalArgumentException.class);
        for (CraftResult.Status status : List.of(CraftResult.Status.CRAFTED, CraftResult.Status.WRONG_STATION, CraftResult.Status.OVERFLOW)) {
            assertThatThrownBy(() -> new CraftResult(status, "copper_ingot", 1, Map.of(), Map.of("tin", 1)))
                    .isInstanceOf(IllegalArgumentException.class);
        }
        for (int missingCount : new int[] {0, -1}) {
            assertThatThrownBy(() -> new CraftResult(CraftResult.Status.INSUFFICIENT_INGREDIENTS, "copper_ingot", 1,
                    Map.of(), Map.of("tin", missingCount))).isInstanceOf(IllegalArgumentException.class);
        }
        assertThatThrownBy(() -> new CraftResult(CraftResult.Status.CRAFTED, "copper_ingot", 1, null, Map.of()))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CraftResult(CraftResult.Status.CRAFTED, "copper_ingot", 1, Map.of(), null))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new CraftResult(CraftResult.Status.CRAFTED, "copper_ingot", 1, Map.of("tin", -1), Map.of()))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    @SuppressWarnings("unchecked")
    void erasedGenericEntriesFailValidationRatherThanLeakingClassCastErrors() {
        List<Recipe.Component> invalidComponents = (List<Recipe.Component>) (List<?>) List.of("copper");
        List<Recipe.Component> valid = List.of(component("tin", 1));
        assertThatThrownBy(() -> new Recipe("alloy", "smelter", 0, invalidComponents, valid))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Recipe("alloy", "smelter", 0, valid, invalidComponents))
                .isInstanceOf(IllegalArgumentException.class);

        List<Map<?, ?>> malformedInventories = List.of(Map.of(1, 1), Map.of("copper", 1L), Map.of("copper", "1"));
        for (Map<?, ?> malformed : malformedInventories) {
            Map<String, Integer> stock = (Map<String, Integer>) malformed;
            assertThatThrownBy(() -> Crafting.craft(COPPER, stock, "bloomery", 1)).isInstanceOf(IllegalArgumentException.class);
        }
    }

    private static Recipe.Component component(String item, int quantity) {
        return new Recipe.Component(item, quantity);
    }
}
