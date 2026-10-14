// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DaedalusRealmPortal.generated.h"

class UBoxComponent;
class UTextRenderComponent;

/**
 * A realm crossing you can walk into (BASE-LAYER.md row 10): stands at a realm's Gate_/Dock_/SubDock_ marker
 * (daedalus_realm_ground lays one per marker). Walking a hero into the box calls ADaedalusHero::SwitchRealm with
 * this portal's Target/Via/Detail; the session core refuses what the rules forbid (DaedalusRealmSessionCore), the
 * hero lands at the destination's marker (LandAt), and the world actor follows through the directory. A cooldown
 * stops the landing marker's own portal from bouncing the hero straight back.
 */
UCLASS()
class DAEDALUSLINK_API ADaedalusRealmPortal : public AActor
{
	GENERATED_BODY()

public:
	ADaedalusRealmPortal();

	/** Session realm id to go to: WORLD-ZERO, GALLERY-CITY, ..., OCEAN. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Portal") FString Target = TEXT("WORLD-ZERO");
	/** gate | dock | shore | portal. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Portal") FString Via = TEXT("gate");
	/** For a dock: "boat:<dockId>" or "sub:<dockId>". */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Portal") FString Detail;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Portal") float CooldownSeconds = 3.f;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Portal") int32 Crossings = 0;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Portal") FString LastResult;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Portal") TObjectPtr<UBoxComponent> Box;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Portal") TObjectPtr<UTextRenderComponent> Sign;

	/** Walk-in behaviour for the harness: the same as the overlap. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Portal") FString Cross(class ADaedalusHero* Hero);
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Portal") FString PortalState() const;

protected:
	virtual void BeginPlay() override;
	UFUNCTION() void OnOverlap(UPrimitiveComponent* Overlapped, AActor* Other, UPrimitiveComponent* OtherComp, int32 BodyIndex, bool bFromSweep, const FHitResult& Sweep);

private:
	double ReadyAt = 0.0;
};
