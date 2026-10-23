// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "Engine/EngineBaseTypes.h"
#include "GenericPlatform/ICursor.h"
#include "InputCoreTypes.h"

THIRD_PARTY_INCLUDES_START
#include "DesktopGames/DaedalusDesktopGameRegistry.h"
THIRD_PARTY_INCLUDES_END

#include "DaedalusDesktopArcade.generated.h"

class APlayerController;
class APlayerState;
class UGameViewportClient;
class ULocalPlayer;
class SDaedalusDesktopArcade;
class SWidget;

/** Complete portable input contract. Axes are screen coordinates: positive Y is down.
 * Pressed fields are consumed once, even when AdvanceGame catches up several fixed steps. */
USTRUCT(BlueprintType)
struct DAEDALUSLINK_API FDaedalusDesktopArcadeInput
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") bool Left = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") bool Right = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") bool Up = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") bool Down = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") bool PadLeft = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") bool PadRight = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") bool PadUp = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") bool PadDown = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") double AxisX = 0.0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") double AxisY = 0.0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") bool Fire = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") bool Jump = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") bool Action = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") bool Dash = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") bool FirePressed = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") bool JumpPressed = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") bool ActionPressed = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") bool DashPressed = false;
};

USTRUCT(BlueprintType)
struct DAEDALUSLINK_API FDaedalusDesktopArcadeEntry
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") FString Id;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") FString Title;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") FString Controls;
};

USTRUCT(BlueprintType)
struct DAEDALUSLINK_API FDaedalusDesktopArcadeHighScore
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") int64 Score = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") int32 Wave = 1;
	/** Source difficulty: 0 Easy, 1 Medium, 2 Hard. */
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") int32 Difficulty = 1;
};

USTRUCT(BlueprintType)
struct DAEDALUSLINK_API FDaedalusDesktopArcadeState
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") bool bInitialized = false;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") bool bOpen = false;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") bool bPaused = false;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") bool bOver = false;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") bool bWon = false;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") bool bSavePending = false;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") bool bHasSavedRun = false;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") FString Id;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") FString Title;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") FString Note;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") FString PersistenceMessage;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") int64 Score = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") int32 Lives = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") int32 Seed = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") int64 Steps = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Daedalus|Desktop Arcade") int32 Option = -1;
};

/** Local cabinet for the user's eleven Desktop Python game families. Interact/HUD discovery
 * uses ADaedalusUsable unchanged. The portable Driver owns rules; this host owns UI and files.
 * The overlay is standalone-only and never acquires pause/input in a network world. */
UCLASS(BlueprintType, Blueprintable)
class DAEDALUSLINK_API ADaedalusDesktopArcade : public ADaedalusUsable
{
	GENERATED_BODY()
public:
	ADaedalusDesktopArcade();
	virtual FString Prompt(const ADaedalusHero* Hero) const override;
	virtual bool Use(ADaedalusHero* Hero) override;
	virtual void OnConstruction(const FTransform& Transform) override;
	virtual void PostDuplicate(EDuplicateMode::Type DuplicateMode) override;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") FString InitialGameId = TEXT("pong");
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") int32 InitialSeed = 730;
	/** Saved per placed instance. Identity is independent of selected gameplay and future entitlement providers. */
	UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") FString CabinetId;
	/** Disable for a harness/Blueprint that drives AdvanceGame itself, avoiding a second simulation clock. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Desktop Arcade") bool bAutoAdvance = true;

	UFUNCTION(BlueprintCallable, Category = "Daedalus|Desktop Arcade") bool StartGame(const FString& Id, int32 Seed);
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Desktop Arcade") void SetArcadeInput(const FDaedalusDesktopArcadeInput& Input);
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Desktop Arcade") void ClearArcadeInput();
	/** Ordered non-repeat keyboard dispatch; 0..9 follow Game::SourceKeyDown. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Desktop Arcade") void SubmitArcadeSourceKey(int32 Key);
	/** Source controller A=0 / Start=1; true consumes the source action before generic pause. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Desktop Arcade") bool SubmitArcadeSourceControllerButton(int32 Button);
	/** At most eight 1/60-second steps. Invalid/negative delta is ignored; stalled wall time is dropped. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Desktop Arcade") int32 AdvanceGame(double DeltaSeconds);
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Desktop Arcade") void RestartGame();
	/** Star keeps advancing its own pause-menu input; generic games stop within Driver::Advance. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Desktop Arcade") void PauseGame(bool bPaused);
	UFUNCTION(BlueprintPure, Category = "Daedalus|Desktop Arcade") FDaedalusDesktopArcadeState GetState() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Desktop Arcade") TArray<FDaedalusDesktopArcadeEntry> GetAvailableGames() const;
	/** Star: 0 Easy, 1 Medium, 2 Hard. Minesweeper: 0 Beginner, 1 Intermediate, 2 Expert. Changes start a new run. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Desktop Arcade") bool SetGameOption(int32 Option);
	UFUNCTION(BlueprintPure, Category = "Daedalus|Desktop Arcade") int32 GetGameOption() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Desktop Arcade") FString GetCabinetId() const { return CabinetId; }
	UFUNCTION(BlueprintPure, Category = "Daedalus|Desktop Arcade") FString GetSelectedGameId() const;
	/** Save the current Minesweeper board to its separate local slot. Failed writes preserve the previous save. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Desktop Arcade") bool SaveGame();
	/** Continue Minesweeper when selected, otherwise the native Star run. Invalid files preserve the current session. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Desktop Arcade") bool ResumeGame();
	UFUNCTION(BlueprintPure, Category = "Daedalus|Desktop Arcade") TArray<int64> GetHighScores() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|Desktop Arcade") TArray<FDaedalusDesktopArcadeHighScore> GetHighScoreRecords() const;
	/** Deferred cleanup so calls made by a widget event or its ticker never destroy it mid-callback. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Desktop Arcade") void CloseArcade();

	const daedalus::desktop::Frame& GetArcadeFrame() const { return Session.GetFrame(); }
	bool MaintainOpenSession();
	int32 GetArcadeSlateUserIndex() const { return SlateUserIndex; }

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	bool OtherHeroOverlayOpen() const;
	bool OtherOverlayOwnsInput() const;
	bool CanRestoreGameInput() const;
	void ReleaseOverlay();
	void ResetPresentationInput();
	void ProcessSourceRequests();
	void EnsureScoresLoaded();
	void RecordScore();
	bool ReadHighScoreRecords(TArray<FDaedalusDesktopArcadeHighScore>& Records) const;
	bool WriteOwnedFile(const FString& Filename, const FString& Text) const;
	void RefreshSavedRun();
	FString SelectedSavePath() const;
	static FString SaveDirectory();
	static FString SavePath();
	static FString MinesweeperSavePath();
	static FString ScoresPath();

	daedalus::desktop::Driver Session;
	int32 CurrentSeed = 730;
	TArray<FDaedalusDesktopArcadeHighScore> HighScores;
	TArray<FDaedalusDesktopArcadeHighScore> PendingScores;
	bool bScoresLoaded = false;
	bool bScoreSubmitted = false;
	bool bScoresNeedWrite = false;
	bool bHasSavedRun = false;
	double NextSaveAttemptSeconds = 0.0;
	double NextScoresAttemptSeconds = 0.0;
	FString RunSaveError;
	FString ScoresSaveError;

	TSharedPtr<SDaedalusDesktopArcade> ArcadeWidget;
	TSharedPtr<SWidget> ArcadeHost;
	TWeakObjectPtr<APlayerController> OpenController;
	TWeakObjectPtr<ADaedalusHero> OpenHero;
	TWeakObjectPtr<UGameViewportClient> OpenViewport;
	TWeakObjectPtr<ULocalPlayer> OpenLocalPlayer;
	TWeakObjectPtr<APlayerState> PauseOwner;
	int32 SlateUserIndex = INDEX_NONE;
	bool bOwnsPause = false;
	bool bCloseScheduled = false;
	bool bClosing = false;
	bool bPreviousMouseCursor = false;
	TEnumAsByte<EMouseCursor::Type> PreviousCursor = EMouseCursor::Default;
	EMouseCaptureMode PreviousCaptureMode = EMouseCaptureMode::CapturePermanently_IncludingInitialMouseDown;
	EMouseLockMode PreviousLockMode = EMouseLockMode::LockOnCapture;
};
