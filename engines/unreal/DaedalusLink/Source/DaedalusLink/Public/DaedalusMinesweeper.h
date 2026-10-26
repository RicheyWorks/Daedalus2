// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "Engine/EngineBaseTypes.h"
#include "InputCoreTypes.h"

THIRD_PARTY_INCLUDES_START
#include "DaedalusMinesweeperCore.h"
THIRD_PARTY_INCLUDES_END

#include "DaedalusMinesweeper.generated.h"

class APlayerController;
class APlayerState;
class UGameViewportClient;
class ULocalPlayer;
class SDaedalusMinesweeper;
class SWidget;

UENUM(BlueprintType)
enum class EDaedalusMinesweeperOutcome : uint8
{
	Playing,
	Won,
	Lost
};

/** Canonical cell state. bMine is exposed for Blueprint diagnostics; the board UI hides covered mines. */
USTRUCT(BlueprintType)
struct DAEDALUSLINK_API FDaedalusMinesweeperCell
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Minesweeper") bool bValid = false;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Minesweeper") bool bMine = false;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Minesweeper") bool bRevealed = false;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Minesweeper") bool bFlagged = false;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Minesweeper") int32 Adjacent = 0;
};

USTRUCT(BlueprintType)
struct DAEDALUSLINK_API FDaedalusMinesweeperState
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Minesweeper") bool bInitialized = false;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Minesweeper") int32 Rows = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Minesweeper") int32 Columns = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Minesweeper") int32 Mines = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Minesweeper") int32 Flags = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Minesweeper") int32 Revealed = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Minesweeper") int32 Score = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Minesweeper") int32 Seed = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Minesweeper") int64 ElapsedMilliseconds = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Minesweeper") EDaedalusMinesweeperOutcome Outcome = EDaedalusMinesweeperOutcome::Playing;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FDaedalusMinesweeperBoardChanged);

/**
 * A local playable Minesweeper Pro cabinet on the existing nearest-usable Interact seam.
 * Rules and scoring live in the portable core. This pilot is fixed at 8x8 / 10 mines;
 * a seeded layout is generated upfront with the configured protected 3x3 neighborhood.
 * Place this actor in an island, then use E / X. No Hero edits or custom art are required.
 * The Slate overlay is standalone-only: it does not pause a network world or replicate scores.
 */
UCLASS(BlueprintType, Blueprintable)
class DAEDALUSLINK_API ADaedalusMinesweeper : public ADaedalusUsable
{
	GENERATED_BODY()

public:
	ADaedalusMinesweeper();
	virtual FString Prompt(const ADaedalusHero* Hero) const override;
	virtual bool Use(ADaedalusHero* Hero) override;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Minesweeper") int32 InitialSeed = 730;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Minesweeper", meta = (ClampMin = "0", ClampMax = "7")) int32 SafeRow = 4;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Minesweeper", meta = (ClampMin = "0", ClampMax = "7")) int32 SafeCol = 4;

	/** Generate immediately. Reset reuses this safety configuration (source desktop restart used origin safety). */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Minesweeper") bool StartRetro(int32 Seed);
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Minesweeper") bool RevealCell(int32 Row, int32 Column);
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Minesweeper") bool ToggleFlag(int32 Row, int32 Column);
	UFUNCTION(BlueprintPure, Category = "Daedalus|Minesweeper") FDaedalusMinesweeperCell GetCell(int32 Row, int32 Column) const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Minesweeper") FDaedalusMinesweeperState GetState() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Minesweeper") EDaedalusMinesweeperOutcome GetResult() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Minesweeper") int32 GetScore() const;
	/** Monotonic real time from board creation; pausing or closing the overlay does not stop a playing board's clock. */
	UFUNCTION(BlueprintPure, Category = "Daedalus|Minesweeper") int64 GetElapsedMilliseconds() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Minesweeper") bool IsBoardOpen() const;
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Minesweeper") void CloseBoard();

	/** Fired after a successful new game, reveal, or flag action; presentation does not own the rules. */
	UPROPERTY(BlueprintAssignable, Category = "Daedalus|Minesweeper") FDaedalusMinesweeperBoardChanged OnBoardChanged;

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	bool OtherHeroOverlayOpen() const;
	bool OtherOverlayOwnsInput() const;
	bool CanRestoreGameInput() const;
	void FinishAction(int64 ElapsedMilliseconds);

	daedalus::minesweeper::Board Board;
	bool bInitialized = false;
	int32 CurrentSeed = 0;
	double BoardCreatedSeconds = 0.0;
	int64 FinishedElapsedMilliseconds = 0;

	TSharedPtr<SDaedalusMinesweeper> BoardWidget;
	TSharedPtr<SWidget> BoardHost;
	TWeakObjectPtr<APlayerController> OpenController;
	TWeakObjectPtr<ADaedalusHero> OpenHero;
	TWeakObjectPtr<UGameViewportClient> OpenViewport;
	TWeakObjectPtr<ULocalPlayer> OpenLocalPlayer;
	TWeakObjectPtr<APlayerState> PauseOwner;
	int32 SlateUserIndex = INDEX_NONE;
	bool bOwnsPause = false;
	bool bPreviousMouseCursor = false;
	TEnumAsByte<EMouseCursor::Type> PreviousCursor = EMouseCursor::Default;
	EMouseCaptureMode PreviousCaptureMode = EMouseCaptureMode::CapturePermanently_IncludingInitialMouseDown;
	EMouseLockMode PreviousLockMode = EMouseLockMode::LockOnCapture;
};
