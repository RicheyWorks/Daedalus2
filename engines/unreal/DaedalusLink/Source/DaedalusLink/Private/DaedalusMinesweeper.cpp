// SPDX-License-Identifier: MIT

#include "DaedalusMinesweeper.h"

#include "DaedalusHero.h"
#include "SDaedalusMinesweeper.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerState.h"
#include "GameFramework/WorldSettings.h"
#include "HAL/PlatformTime.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/ConstructorHelpers.h"
#include "Widgets/SWeakWidget.h"

ADaedalusMinesweeper::ADaedalusMinesweeper()
{
	PrimaryActorTick.bCanEverTick = false;
	// Engine content only: a visible placement placeholder, replaceable by a Blueprint's Body mesh.
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (Cube.Succeeded()) Body->SetStaticMesh(Cube.Object);
	Body->SetRelativeScale3D(FVector(0.75f, 0.45f, 0.9f));
	Tags.Add(TEXT("DaedalusMinesweeper"));
}

void ADaedalusMinesweeper::BeginPlay()
{
	Super::BeginPlay();
	if (!bInitialized) StartRetro(InitialSeed);
}

FString ADaedalusMinesweeper::Prompt(const ADaedalusHero* Hero) const
{
	return TEXT("Play Minesweeper Pro");
}

bool ADaedalusMinesweeper::StartRetro(int32 Seed)
{
	if (!Board.Generate(8, 8, 10, static_cast<uint32>(Seed), SafeRow, SafeCol)) return false;
	bInitialized = true;
	CurrentSeed = Seed;
	BoardCreatedSeconds = FPlatformTime::Seconds();
	FinishedElapsedMilliseconds = 0;
	OnBoardChanged.Broadcast();
	return true;
}

bool ADaedalusMinesweeper::RevealCell(int32 Row, int32 Column)
{
	if (!bInitialized) return false;
	const int64 Elapsed = GetElapsedMilliseconds();
	if (!Board.Reveal(Row, Column, Elapsed)) return false;
	FinishAction(Elapsed);
	return true;
}

bool ADaedalusMinesweeper::ToggleFlag(int32 Row, int32 Column)
{
	if (!bInitialized) return false;
	const int64 Elapsed = GetElapsedMilliseconds();
	if (!Board.ToggleFlag(Row, Column, Elapsed)) return false;
	FinishAction(Elapsed);
	return true;
}

void ADaedalusMinesweeper::FinishAction(int64 ElapsedMilliseconds)
{
	if (Board.Result() != daedalus::minesweeper::Outcome::Playing) FinishedElapsedMilliseconds = ElapsedMilliseconds;
	OnBoardChanged.Broadcast();
}

FDaedalusMinesweeperCell ADaedalusMinesweeper::GetCell(int32 Row, int32 Column) const
{
	FDaedalusMinesweeperCell Out;
	if (const daedalus::minesweeper::Cell* Cell = Board.At(Row, Column))
	{
		Out.bValid = true;
		Out.bMine = Cell->Mine;
		Out.bRevealed = Cell->Revealed;
		Out.bFlagged = Cell->Flagged;
		Out.Adjacent = Cell->Adjacent;
	}
	return Out;
}

FDaedalusMinesweeperState ADaedalusMinesweeper::GetState() const
{
	FDaedalusMinesweeperState Out;
	Out.bInitialized = bInitialized;
	Out.Rows = Board.Rows();
	Out.Columns = Board.Cols();
	Out.Mines = Board.MineCount();
	Out.Flags = Board.FlagCount();
	Out.Revealed = Board.RevealedCount();
	Out.Score = Board.Score();
	Out.Seed = CurrentSeed;
	Out.ElapsedMilliseconds = GetElapsedMilliseconds();
	Out.Outcome = GetResult();
	return Out;
}

EDaedalusMinesweeperOutcome ADaedalusMinesweeper::GetResult() const
{
	switch (Board.Result())
	{
	case daedalus::minesweeper::Outcome::Won: return EDaedalusMinesweeperOutcome::Won;
	case daedalus::minesweeper::Outcome::Lost: return EDaedalusMinesweeperOutcome::Lost;
	default: return EDaedalusMinesweeperOutcome::Playing;
	}
}

int32 ADaedalusMinesweeper::GetScore() const
{
	return Board.Score();
}

int64 ADaedalusMinesweeper::GetElapsedMilliseconds() const
{
	if (!bInitialized) return 0;
	if (Board.Result() != daedalus::minesweeper::Outcome::Playing) return FinishedElapsedMilliseconds;
	return static_cast<int64>(FMath::Max(0.0, FPlatformTime::Seconds() - BoardCreatedSeconds) * 1000.0);
}

bool ADaedalusMinesweeper::IsBoardOpen() const
{
	return BoardWidget.IsValid() && BoardHost.IsValid();
}

bool ADaedalusMinesweeper::OtherHeroOverlayOpen() const
{
	const ADaedalusHero* Hero = OpenHero.Get();
	const APlayerController* PC = OpenController.Get();
	const ADaedalusHero* CurrentHero = PC ? Cast<ADaedalusHero>(PC->GetPawn()) : nullptr;
	auto HasOverlay = [](const ADaedalusHero* H)
	{
		return H && (H->IsSettingsOpen() || H->IsFieldOpen() || H->IsRealmOpen());
	};
	return HasOverlay(Hero) || HasOverlay(CurrentHero);
}

bool ADaedalusMinesweeper::Use(ADaedalusHero* Hero)
{
	UWorld* World = GetWorld();
	APlayerController* PC = Hero ? Cast<APlayerController>(Hero->GetController()) : nullptr;
	UGameViewportClient* Viewport = World ? World->GetGameViewport() : nullptr;
	ULocalPlayer* LocalPlayer = PC ? PC->GetLocalPlayer() : nullptr;
	if (IsBoardOpen() || !World || !Hero || Hero->GetWorld() != World || !PC || !PC->IsLocalController()
		|| !LocalPlayer || !Viewport || !FSlateApplication::IsInitialized() || GetNetMode() != NM_Standalone
		|| UGameplayStatics::IsGamePaused(this) || PC->bShowMouseCursor || Viewport->IgnoreInput()
		|| Hero->IsSettingsOpen() || Hero->IsFieldOpen() || Hero->IsRealmOpen()) return false;
	if (!bInitialized && !StartRetro(InitialSeed)) return false;

	// Only acquire input after acquiring our own pause. An existing pause/menu is never displaced.
	if (!PC->SetPause(true)) return false;
	bOwnsPause = true;
	OpenController = PC;
	OpenHero = Hero;
	OpenViewport = Viewport;
	OpenLocalPlayer = LocalPlayer;
	PauseOwner = World->GetWorldSettings()->GetPauserPlayerState();
	bPreviousMouseCursor = PC->bShowMouseCursor;
	PreviousCursor = PC->CurrentMouseCursor;
	PreviousCaptureMode = Viewport->GetMouseCaptureMode();
	PreviousLockMode = Viewport->GetMouseLockMode();
	SlateUserIndex = FSlateApplication::Get().GetUserIndexForController(LocalPlayer->GetControllerId());

	BoardWidget = SNew(SDaedalusMinesweeper)
		.Game(this)
		.OnClose(FSimpleDelegate::CreateUObject(this, &ADaedalusMinesweeper::CloseBoard));
	BoardHost = SNew(SWeakWidget).PossiblyNullContent(BoardWidget.ToSharedRef());
	Viewport->AddViewportWidgetForPlayer(LocalPlayer, BoardHost.ToSharedRef(), 100);
	FInputModeUIOnly Mode;
	Mode.SetWidgetToFocus(BoardWidget);
	Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
	PC->SetInputMode(Mode);
	PC->bShowMouseCursor = true;
	PC->CurrentMouseCursor = EMouseCursor::Default;
	if (SlateUserIndex != INDEX_NONE)
		FSlateApplication::Get().SetUserFocus(SlateUserIndex, BoardWidget, EFocusCause::SetDirectly);
	return true;
}

bool ADaedalusMinesweeper::OtherOverlayOwnsInput() const
{
	if (OtherHeroOverlayOpen()) return true;
	if (!FSlateApplication::IsInitialized() || SlateUserIndex == INDEX_NONE) return false;
	// A newly focused unrelated overlay owns input now. Do not dismiss or unpause it.
	return FSlateApplication::Get().GetUserFocusedWidget(SlateUserIndex).IsValid()
		&& !(BoardWidget.IsValid() && (BoardWidget->HasUserFocus(SlateUserIndex).IsSet()
			|| BoardWidget->HasUserFocusedDescendants(SlateUserIndex)));
}

bool ADaedalusMinesweeper::CanRestoreGameInput() const
{
	const APlayerController* PC = OpenController.Get();
	// Pawn replacement/destruction does not invalidate the recorded local controller's input lease.
	return PC && PC->IsLocalController() && PC->GetWorld() == GetWorld() && !OtherOverlayOwnsInput();
}

void ADaedalusMinesweeper::CloseBoard()
{
	if (!BoardHost.IsValid() && !bOwnsPause) return;
	const bool bOtherOverlay = OtherOverlayOwnsInput();
	const bool bRestore = CanRestoreGameInput();
	APlayerController* PC = OpenController.Get();
	UWorld* World = GetWorld();
	UGameViewportClient* Viewport = OpenViewport.Get();
	if (BoardHost.IsValid())
	{
		if (Viewport)
		{
			if (ULocalPlayer* LocalPlayer = OpenLocalPlayer.Get())
				Viewport->RemoveViewportWidgetForPlayer(LocalPlayer, BoardHost.ToSharedRef());
			else
				// UE supports null here: search player layers for this exact widget, without clearing other UI.
				Viewport->RemoveViewportWidgetForPlayer(nullptr, BoardHost.ToSharedRef());
		}
	}
	BoardHost.Reset();
	BoardWidget.Reset();
	if (bRestore && PC)
	{
		PC->SetInputMode(FInputModeGameOnly());
		PC->bShowMouseCursor = bPreviousMouseCursor;
		PC->CurrentMouseCursor = PreviousCursor;
	}
	if (!bOtherOverlay && Viewport)
	{
		// Undo UIOnly's viewport suppression even if the controller was removed before EndPlay.
		Viewport->SetIgnoreInput(false);
		Viewport->SetMouseCaptureMode(PreviousCaptureMode);
		Viewport->SetMouseLockMode(PreviousLockMode);
		if (FSlateApplication::IsInitialized() && SlateUserIndex != INDEX_NONE)
			FSlateApplication::Get().SetUserFocusToGameViewport(SlateUserIndex, EFocusCause::SetDirectly);
	}
	// Pause cleanup is independent of pawn/controller lifetime. Weak identity remains comparable when
	// the original PlayerState is pending destruction. An unrelated overlay keeps its pause and input.
	AWorldSettings* Settings = World ? World->GetWorldSettings() : nullptr;
	if (bOwnsPause && !bOtherOverlay && Settings
		&& PauseOwner.HasSameIndexAndSerialNumber(TWeakObjectPtr<APlayerState>(Settings->GetPauserPlayerState())))
	{
		if (PC && PC->GetWorld() == World) PC->SetPause(false);
		else if (AGameModeBase* GameMode = World->GetAuthGameMode()) GameMode->ClearPause();
	}
	bOwnsPause = false;
	SlateUserIndex = INDEX_NONE;
	OpenController.Reset();
	OpenHero.Reset();
	OpenViewport.Reset();
	OpenLocalPlayer.Reset();
	PauseOwner.Reset();
}

void ADaedalusMinesweeper::EndPlay(const EEndPlayReason::Type Reason)
{
	CloseBoard();
	Super::EndPlay(Reason);
}
