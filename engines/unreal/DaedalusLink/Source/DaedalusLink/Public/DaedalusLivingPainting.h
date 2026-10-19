// SPDX-License-Identifier: MIT
// G13 GAL01 living painting (docs/mechanics/GAL01-LIVING-PAINTINGS.md, owner 2hot2trot; Java com.daedalus.world.gallery).
// A Gallery City mural drained grey by the Grey Wash. Each cell remembers its colour (from the frame seed, so every client
// paints the same mural). Paint a cell with the right pigment to restore it and learn the colour; the wrong pigment
// smudges it and needs a turpentine wash. When every cell is restored the mural wakes and its subject steps out.
// Rules live in DaedalusLivingPaintingCore.h (C++ = Java, core-test/living_painting_parity.txt). Prototype: the actor
// owns its own palette and colour knowledge until the host inventory is wired; cells are engine planes with a
// dynamic colour until the grey Prop_Gallery_MuralPanel variant ships.
#pragma once

#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusLivingPaintingCore.h"
#include "DaedalusLivingPainting.generated.h"

class UMaterialInstanceDynamic;

UENUM(BlueprintType)
enum class EDaedalusPigment : uint8 { Red, Yellow, Blue, Orange, Green, Violet };

DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FDaedalusMuralStroke, int32, X, int32, Y, const FString&, Result);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusMuralAwake, const FString&, Subject);

UCLASS(Blueprintable)
class DAEDALUSLINK_API ADaedalusLivingPainting : public ADaedalusUsable
{
	GENERATED_BODY()
public:
	ADaedalusLivingPainting();
	virtual void BeginPlay() override;
	virtual FString Prompt(const ADaedalusHero* Hero) const override;
	virtual bool Use(ADaedalusHero* Hero) override;

	/** The frame seed (GalleryOps.Frame.seed, 0..999999999) and the mural size in cells (1..12 each). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Gallery") int64 Seed = 1;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Gallery", meta = (ClampMin = "1", ClampMax = "12")) int32 Width = 4;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Gallery", meta = (ClampMin = "1", ClampMax = "12")) int32 Height = 4;
	/** Cell edge in cm and the pigment Interact paints with. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Gallery") float CellSize = 40.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Gallery") EDaedalusPigment SelectedPigment = EDaedalusPigment::Red;
	/** Starting units of each primary in this mural's palette (prototype stand-in for the player's inventory). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Gallery", meta = (ClampMin = "0", ClampMax = "999")) int32 StartingPrimaries = 6;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Gallery") TObjectPtr<UStaticMeshComponent> Panel;

	/** Mural from a GalleryOps frame: 2x2 cells per wall cube, capped at 12. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Gallery") void SetFromFrame(int64 FrameSeed, int32 FrameW, int32 FrameH);
	/** Rebuild the mural grey from Seed/Width/Height. Palette and knowledge are kept. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Gallery") bool Rebuild();
	/** Grind one ingredient (beet, cherry, dawnleaf, cobalt, orange, copper). Returns the PigmentPalette result name. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Gallery") FString Grind(const FString& Ingredient);
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Gallery") FString Mix(EDaedalusPigment Secondary);
	/** Paint one cell; returns the LivingPainting result name (RESTORED, SMUDGED, NEEDS_WASH, NO_PIGMENT, ..., BAD_CELL). */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Gallery") FString Paint(int32 X, int32 Y, EDaedalusPigment Pigment);
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Gallery") FString Wash(int32 X, int32 Y);
	/** PRISM_SIGHT hint for a cell; false without the ability. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Gallery") bool Reveal(int32 X, int32 Y, EDaedalusPigment& Pigment) const;

	UFUNCTION(BlueprintPure, Category = "Daedalus|Gallery") FString MuralState() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Gallery") int32 ProgressPm() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Gallery") int32 Units(EDaedalusPigment Pigment) const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Gallery") bool Knows(EDaedalusPigment Pigment) const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Gallery") TArray<FString> Abilities() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Gallery") FString Subject() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Gallery") FString Status() const;

	UPROPERTY(BlueprintAssignable, Category = "Daedalus|Gallery") FDaedalusMuralStroke OnStroke;
	UPROPERTY(BlueprintAssignable, Category = "Daedalus|Gallery") FDaedalusMuralAwake OnAwake;

private:
	void Tell(const FString& Text) const;
	void Recolour(int32 X, int32 Y);
	bool NextCell(int32& X, int32& Y) const;

	TUniquePtr<daedalus::gallery::Painting> Mural;
	daedalus::gallery::Palette Pal;
	daedalus::gallery::Knowledge Know;
	TArray<int32> PaintedWith;
	UPROPERTY(Transient) TArray<TObjectPtr<UStaticMeshComponent>> CellParts;
	UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> CellMats;
	bool bAwake = false;
};