// SPDX-License-Identifier: MIT
// G04 LAB07 Twin Doors actor (contract docs/contracts/twin-doors-v1, Java com.daedalus.world.labyrinth.TwinDoors,
// prometheus core-test/twin_doors). Two bell guards stand by two doors; one always tells the truth, one always lies.
// Interact to talk to the guards, ask your one question (default: the embedded question, which always solves), and
// deliberately choose a door. The safe door swings open (A -90, B +90 yaw, blender-team hinge sidecar); the wrong one resets the
// riddle with the next seed. All rules live in DaedalusTwinDoorsCore.h (exception-free, core-test/twin_doors_plugin).
// Meshes are engine shapes until the Bld_Lab_TwinDoors / _DoorA / _DoorB / Prop_Lab_GateRiddler art is READY.
#pragma once

#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusTwinDoorsCore.h"
#include "DaedalusTwinDoorsGuide.h"
#include "DaedalusTwinDoors.generated.h"

UENUM(BlueprintType)
enum class EDaedalusTwinQuestion : uint8
{
	Direct UMETA(DisplayName = "Is door d safe?"),
	OtherGuard UMETA(DisplayName = "Would the other guard say door d is safe?"),
	Embedded UMETA(DisplayName = "If I asked whether door d is safe, would you ring the low bell?"),
	Self UMETA(DisplayName = "Are you the truth guard?")
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FDaedalusTwinBell, int32, Guard, bool, bLowBell, float, Hz);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FDaedalusTwinDoorPicked, int32, Door, bool, bOpened);

UCLASS(Blueprintable)
class DAEDALUSLINK_API ADaedalusTwinDoors : public ADaedalusUsable
{
	GENERATED_BODY()
public:
	ADaedalusTwinDoors();
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual FString Prompt(const ADaedalusHero* Hero) const override;
	virtual bool Use(ADaedalusHero* Hero) override;

	/** Riddle seed (contract RNG: SplitMix64 of seed ^ 0x54574431). A wrong door moves it to Seed + 1. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|TwinDoors") int64 Seed = 1;
	/** 0: the low bell means yes. 1: the bell meaning is hidden too. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|TwinDoors", meta = (ClampMin = "0", ClampMax = "1")) int32 Difficulty = 0;
	/** The question the player can ask through the guard dialogue (guard AskGuard, about door AskDoor). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|TwinDoors") EDaedalusTwinQuestion AskQuestion = EDaedalusTwinQuestion::Embedded;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|TwinDoors", meta = (ClampMin = "0", ClampMax = "1")) int32 AskGuard = 0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|TwinDoors", meta = (ClampMin = "0", ClampMax = "1")) int32 AskDoor = 0;
	/** Open yaw per door in degrees (blender-team sidecar hinges: A -90, B +90) and the swing time. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|TwinDoors") float OpenYawA = -90.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|TwinDoors") float OpenYawB = 90.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|TwinDoors") float SwingSeconds = 1.5f;

	/** Body (the root) stays unscaled and empty; the lintel is Frame. Each door hangs from a hinge at its outer edge. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|TwinDoors") TObjectPtr<UStaticMeshComponent> Frame;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|TwinDoors") TObjectPtr<USceneComponent> HingeA;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|TwinDoors") TObjectPtr<USceneComponent> HingeB;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|TwinDoors") TObjectPtr<UStaticMeshComponent> DoorA;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|TwinDoors") TObjectPtr<UStaticMeshComponent> DoorB;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|TwinDoors") TObjectPtr<UStaticMeshComponent> GuardA;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|TwinDoors") TObjectPtr<UStaticMeshComponent> GuardB;

	/** Ask the one question. False (see LastLine) if already asked or a side is not 0/1. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|TwinDoors") bool Ask(int32 Guard, EDaedalusTwinQuestion Question, int32 Door);
	/** Open a door after asking. True if it was the safe door; a wrong door resets the riddle with Seed + 1. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|TwinDoors") bool Choose(int32 Door);
	/** New session on the current Seed and Difficulty (doors close). */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|TwinDoors") void ResetRiddle();

	UFUNCTION(BlueprintPure, Category = "Daedalus|TwinDoors") bool HasAsked() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|TwinDoors") bool IsSolved() const { return bSolved; }
	/** What a careful player can prove from the answer heard: 0, 1, or -1. */
	UFUNCTION(BlueprintPure, Category = "Daedalus|TwinDoors") int32 Deduced() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|TwinDoors") FString LastLine() const { return Line; }
	/** TWD 1 text of the current riddle (debug; it reveals the answer). */
	UFUNCTION(BlueprintPure, Category = "Daedalus|TwinDoors") FString Wire() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|TwinDoors") FString Status() const;

	UPROPERTY(BlueprintAssignable, Category = "Daedalus|TwinDoors") FDaedalusTwinBell OnBell;
	UPROPERTY(BlueprintAssignable, Category = "Daedalus|TwinDoors") FDaedalusTwinDoorPicked OnDoorPicked;

private:
	void Tell(const FString& Text);
	void ShowGuide(daedalus::twindoors::GuidePage Page);
	void OnGuideChoice(const FString& Speaker, int32 Choice);
	void StopGuide();
	bool IsGuideCurrent() const;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

	TWeakObjectPtr<ADaedalusHero> ListeningHero;
	FDelegateHandle GuideHandle;
	daedalus::twindoors::GuidePage CurrentGuidePage = daedalus::twindoors::GuidePage::Welcome;
	EDaedalusTwinQuestion PresentedQuestion = EDaedalusTwinQuestion::Embedded;
	int32 PresentedGuard = 0, PresentedDoor = 0;
	FString GuideRealm;
	uint64 RiddleRevision = 0, GuideRevision = 0;
	bool bEndingPlay = false;

	TUniquePtr<daedalus::twindoors::Riddle> Riddle;
	TUniquePtr<daedalus::twindoors::Session> Run;
	int32 HeardGuard = 0, HeardDoor = 0;
	daedalus::twindoors::Question HeardQuestion = daedalus::twindoors::Question::Embedded;
	bool bSolved = false;
	int32 OpenDoor = -1;
	float SwingT = 0.f;
	FString Line;
};
