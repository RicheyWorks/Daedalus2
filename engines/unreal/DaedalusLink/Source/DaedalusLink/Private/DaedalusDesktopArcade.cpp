// SPDX-License-Identifier: MIT
#include "DaedalusDesktopArcade.h"

#include "DaedalusHero.h"
#include "SDaedalusDesktopArcade.h"
#include "Components/StaticMeshComponent.h"
#include "Containers/Ticker.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/GameModeBase.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerState.h"
#include "GameFramework/WorldSettings.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformTime.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Guid.h"
#include "Misc/Paths.h"
#include "UObject/ConstructorHelpers.h"
#include "Widgets/SViewport.h"

namespace DD = daedalus::desktop;

namespace DesktopArcadeStorage
{
	bool Number(const FString& Token, int64 Limit, int64& Value)
	{
		if (Token.IsEmpty() || Token.Len() > 13) return false;
		int64 Candidate = 0;
		for (TCHAR C : Token)
		{
			if (C < TEXT('0') || C > TEXT('9')) return false;
			const int64 Digit = C - TEXT('0');
			if (Candidate > (Limit - Digit) / 10 || Digit > Limit) return false;
			Candidate = Candidate * 10 + Digit;
		}
		Value = Candidate;
		return true;
	}
	void Rank(TArray<FDaedalusDesktopArcadeHighScore>& Records)
	{
		// Python's sort is stable for tied scores; keep existing entries ahead of newly appended ties.
		Records.StableSort([](const FDaedalusDesktopArcadeHighScore& A, const FDaedalusDesktopArcadeHighScore& B) { return A.Score > B.Score; });
		if (Records.Num() > 10) Records.SetNum(10);
	}
}

ADaedalusDesktopArcade::ADaedalusDesktopArcade()
{
	PrimaryActorTick.bCanEverTick = false;
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (Cube.Succeeded()) Body->SetStaticMesh(Cube.Object);
	Body->SetRelativeScale3D(FVector(0.8f, 0.5f, 1.1f));
	Tags.Add(TEXT("DaedalusDesktopArcade"));
}

void ADaedalusDesktopArcade::BeginPlay()
{
	Super::BeginPlay();
	if (!IsTemplate() && CabinetId.IsEmpty()) CabinetId = FGuid::NewGuid().ToString(EGuidFormats::Digits);
	EnsureScoresLoaded();
	if (Session.ActiveId().empty()) StartGame(InitialGameId, InitialSeed);
	RefreshSavedRun();
}

void ADaedalusDesktopArcade::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	if (!IsTemplate() && CabinetId.IsEmpty()) CabinetId = FGuid::NewGuid().ToString(EGuidFormats::Digits);
}

void ADaedalusDesktopArcade::PostDuplicate(EDuplicateMode::Type DuplicateMode)
{
	Super::PostDuplicate(DuplicateMode);
	// Editor duplication makes another cabinet; PIE duplication retains the saved instance identity.
	if (!IsTemplate() && DuplicateMode == EDuplicateMode::Normal) CabinetId = FGuid::NewGuid().ToString(EGuidFormats::Digits);
}

FString ADaedalusDesktopArcade::Prompt(const ADaedalusHero* Hero) const
{
	return TEXT("Play Desktop Arcade");
}

bool ADaedalusDesktopArcade::StartGame(const FString& Id, int32 Seed)
{
	if (Session.HasSaveRequest()) { RunSaveError = TEXT("A Star save is pending. Finish saving before replacing this run."); return false; }
	if (bClosing || Id.Len() > 64 || !Session.Select(TCHAR_TO_UTF8(*Id), static_cast<uint32>(Seed))) return false;
	CurrentSeed = Seed;
	bScoreSubmitted = false;
	RunSaveError.Reset();
	NextSaveAttemptSeconds = 0.0;
	EnsureScoresLoaded();
	RefreshSavedRun();
	ResetPresentationInput();
	return true;
}

void ADaedalusDesktopArcade::SetArcadeInput(const FDaedalusDesktopArcadeInput& Input)
{
	if (bClosing || bCloseScheduled) return;
	DD::Input Controls;
	Controls.Left = Input.Left; Controls.Right = Input.Right; Controls.Up = Input.Up; Controls.Down = Input.Down;
	Controls.PadLeft = Input.PadLeft; Controls.PadRight = Input.PadRight;
	Controls.PadUp = Input.PadUp; Controls.PadDown = Input.PadDown;
	Controls.AxisX = Input.AxisX; Controls.AxisY = Input.AxisY;
	Controls.Fire = Input.Fire; Controls.Jump = Input.Jump; Controls.Action = Input.Action; Controls.Dash = Input.Dash;
	Controls.FirePressed = Input.FirePressed; Controls.JumpPressed = Input.JumpPressed;
	Controls.ActionPressed = Input.ActionPressed; Controls.DashPressed = Input.DashPressed;
	Session.SetInput(Controls);
}

void ADaedalusDesktopArcade::ClearArcadeInput()
{
	Session.ClearInput();
}

void ADaedalusDesktopArcade::SubmitArcadeSourceKey(int32 Key)
{
	if (bClosing || bCloseScheduled || Key < 0 || Key > 9) return;
	Session.SourceKeyDown(Key);
}

bool ADaedalusDesktopArcade::SubmitArcadeSourceControllerButton(int32 Button)
{
	if (bClosing || bCloseScheduled || Button < 0 || Button > 1) return false;
	return Session.SourceControllerButton(Button);
}

void ADaedalusDesktopArcade::ResetPresentationInput()
{
	Session.ClearInput();
	if (ArcadeWidget.IsValid()) ArcadeWidget->ResetHeldInput();
}

int32 ADaedalusDesktopArcade::AdvanceGame(double DeltaSeconds)
{
	if (bClosing || bCloseScheduled) return 0;
	const int32 Count = Session.Advance(DeltaSeconds);
	// Do not stop merely because IsPaused is true: Star's source menu consumes fixed-step input.
	ProcessSourceRequests();
	return Count;
}

void ADaedalusDesktopArcade::RestartGame()
{
	if (Session.HasSaveRequest()) { RunSaveError = TEXT("A Star save is pending; restart is unavailable until it is saved."); return; }
	if (bClosing || bCloseScheduled) return;
	Session.Restart();
	bScoreSubmitted = false;
	RunSaveError.Reset();
	NextSaveAttemptSeconds = 0.0;
	ResetPresentationInput();
}

void ADaedalusDesktopArcade::PauseGame(bool bPaused)
{
	if (Session.HasSaveRequest()) return; // Save-and-quit owns a fixed pending snapshot until acknowledged.
	if (bClosing || bCloseScheduled) return;
	Session.SetPaused(bPaused);
	ResetPresentationInput();
}

bool ADaedalusDesktopArcade::SetGameOption(int32 Option)
{
	if (Session.HasSaveRequest()) { RunSaveError = TEXT("A Star save is pending; difficulty cannot replace it."); return false; }
	if (bClosing || bCloseScheduled || !Session.SetOption(Option)) return false;
	bScoreSubmitted = false;
	RunSaveError.Reset();
	ResetPresentationInput();
	return true;
}

int32 ADaedalusDesktopArcade::GetGameOption() const { return Session.GetOption(); }
FString ADaedalusDesktopArcade::GetSelectedGameId() const { return UTF8_TO_TCHAR(Session.ActiveId().c_str()); }

FDaedalusDesktopArcadeState ADaedalusDesktopArcade::GetState() const
{
	FDaedalusDesktopArcadeState Out;
	const DD::Status State = Session.GetStatus();
	Out.bInitialized = !Session.ActiveId().empty();
	Out.bOpen = ArcadeWidget.IsValid() && ArcadeHost.IsValid();
	Out.bPaused = Session.IsPaused(); Out.bOver = State.Over; Out.bWon = State.Won;
	Out.bSavePending = Session.HasSaveRequest(); Out.bHasSavedRun = bHasSavedRun;
	Out.Id = UTF8_TO_TCHAR(Session.ActiveId().c_str());
	for (const DD::Entry& E : DD::Catalog()) if (E.Id == Session.ActiveId()) { Out.Title = UTF8_TO_TCHAR(E.Title.c_str()); break; }
	Out.Note = UTF8_TO_TCHAR(State.Note.c_str());
	Out.PersistenceMessage = RunSaveError;
	if (!ScoresSaveError.IsEmpty()) Out.PersistenceMessage += (Out.PersistenceMessage.IsEmpty() ? TEXT("") : TEXT(" | ")) + ScoresSaveError;
	Out.Score = State.Score; Out.Lives = State.Lives; Out.Seed = CurrentSeed;
	Out.Steps = static_cast<int64>(FMath::Min<uint64>(Session.Ticks(), static_cast<uint64>(MAX_int64)));
	Out.Option = Session.GetOption();
	return Out;
}

TArray<FDaedalusDesktopArcadeEntry> ADaedalusDesktopArcade::GetAvailableGames() const
{
	TArray<FDaedalusDesktopArcadeEntry> Out;
	for (const DD::Entry& E : DD::Catalog())
	{
		FDaedalusDesktopArcadeEntry Entry;
		Entry.Id = UTF8_TO_TCHAR(E.Id.c_str()); Entry.Title = UTF8_TO_TCHAR(E.Title.c_str()); Entry.Controls = UTF8_TO_TCHAR(E.Controls.c_str());
		Out.Add(MoveTemp(Entry));
	}
	return Out;
}

FString ADaedalusDesktopArcade::SaveDirectory()
{
	return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("DaedalusDesktopGames"));
}
FString ADaedalusDesktopArcade::SavePath() { return FPaths::Combine(SaveDirectory(), TEXT("star_shooter.dgs")); }
FString ADaedalusDesktopArcade::MinesweeperSavePath() { return FPaths::Combine(SaveDirectory(), TEXT("minesweeper.dgs")); }
FString ADaedalusDesktopArcade::ScoresPath() { return FPaths::Combine(SaveDirectory(), TEXT("star_shooter.scores")); }

FString ADaedalusDesktopArcade::SelectedSavePath() const
{
	return Session.ActiveId() == "minesweeper" ? MinesweeperSavePath() : SavePath();
}

void ADaedalusDesktopArcade::RefreshSavedRun()
{
	const int64 Bytes = IFileManager::Get().FileSize(*SelectedSavePath());
	bHasSavedRun = Bytes > 0 && Bytes <= 4096;
}

bool ADaedalusDesktopArcade::WriteOwnedFile(const FString& Filename, const FString& Text) const
{
	// Only these private filenames can be written. Replace after a complete bounded temp write.
	if ((Filename != SavePath() && Filename != MinesweeperSavePath() && Filename != ScoresPath()) || Text.Len() > 4096) return false;
	IFileManager& Files = IFileManager::Get();
	if (!Files.MakeDirectory(*SaveDirectory(), true)) return false;
	const FString Temp = Filename + TEXT(".") + FGuid::NewGuid().ToString(EGuidFormats::Digits) + TEXT(".tmp");
	const bool bWritten = FFileHelper::SaveStringToFile(Text, *Temp, FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
	const bool bMoved = bWritten && Files.Move(*Filename, *Temp, true, false, false, true);
	if (!bMoved) Files.Delete(*Temp, false, false, true);
	return bMoved;
}

bool ADaedalusDesktopArcade::SaveGame()
{
	if (bClosing || bCloseScheduled || Session.ActiveId() != "minesweeper") return false;
	const std::string Payload = Session.CaptureSave();
	if (Payload.empty() || Payload.size() > 4096
		|| !WriteOwnedFile(MinesweeperSavePath(), FString(UTF8_TO_TCHAR(Payload.c_str()))))
	{
		RunSaveError = TEXT("Board could not be saved. Your current board and previous save were kept; try Save board again.");
		RefreshSavedRun();
		return false;
	}
	bHasSavedRun = true;
	RunSaveError = TEXT("Board saved on this installation. Continue saved board restores it after closing or restarting.");
	return true;
}

bool ADaedalusDesktopArcade::ResumeGame()
{
	if (Session.HasSaveRequest()) { RunSaveError = TEXT("A Star save is pending; Continue cannot replace it."); return false; }
	if (bClosing || bCloseScheduled) return false;
	const bool bMinesweeper = Session.ActiveId() == "minesweeper";
	const FString Filename = SelectedSavePath();
	RefreshSavedRun();
	const int64 Bytes = IFileManager::Get().FileSize(*Filename);
	FString Text;
	if (Bytes <= 0 || Bytes > 4096 || !FFileHelper::LoadFileToString(Text, *Filename))
	{
		RunSaveError = bMinesweeper ? TEXT("No readable saved board (maximum 4 KB). Your current board was kept.")
			: TEXT("No readable native Star save (maximum 4 KB).");
		return false;
	}
	DD::Driver Candidate;
	if (!Candidate.Select(bMinesweeper ? "minesweeper" : "star_shooter", static_cast<uint32>(CurrentSeed)) || !Candidate.RestoreSave(TCHAR_TO_UTF8(*Text)))
	{
		RunSaveError = bMinesweeper ? TEXT("The saved board could not be read. Your current board and the save file were kept.")
			: TEXT("Native Star save was refused; the current run was kept.");
		return false;
	}
	Session = std::move(Candidate);
	CurrentSeed = static_cast<int32>(Session.GetSeed());
	bHasSavedRun = true; bScoreSubmitted = false;
	RunSaveError = bMinesweeper ? TEXT("Saved board continued. Flags, revealed cells and active time were restored.") : FString();
	NextSaveAttemptSeconds = 0.0;
	ResetPresentationInput();
	return true;
}

void ADaedalusDesktopArcade::EnsureScoresLoaded()
{
	if (bScoresLoaded) return;
	if (ReadHighScoreRecords(HighScores)) bScoresLoaded = true;
	else ScoresSaveError = TEXT("The native leaderboard was refused or could not be read.");
}

bool ADaedalusDesktopArcade::ReadHighScoreRecords(TArray<FDaedalusDesktopArcadeHighScore>& Records) const
{
	const int64 Bytes = IFileManager::Get().FileSize(*ScoresPath());
	if (Bytes < 0) { Records.Reset(); return true; }
	FString Text;
	if (Bytes <= 0 || Bytes > 1024 || !FFileHelper::LoadFileToString(Text, *ScoresPath())) return false;
	TArray<FString> Tokens;
	Text.ParseIntoArrayWS(Tokens);
	if (Tokens.IsEmpty() || Tokens[0] != TEXT("DGL1") || Tokens.Num() > 31 || (Tokens.Num() - 1) % 3 != 0) return false;
	TArray<FDaedalusDesktopArcadeHighScore> Candidate;
	for (int32 N = 1; N < Tokens.Num(); N += 3)
	{
		int64 Score = 0, Wave = 0, Difficulty = 0;
		if (!DesktopArcadeStorage::Number(Tokens[N], 1000000000000LL, Score)
			|| !DesktopArcadeStorage::Number(Tokens[N + 1], 1000000, Wave) || Wave < 1
			|| !DesktopArcadeStorage::Number(Tokens[N + 2], 2, Difficulty)) return false;
		FDaedalusDesktopArcadeHighScore Entry;
		Entry.Score = Score; Entry.Wave = static_cast<int32>(Wave); Entry.Difficulty = static_cast<int32>(Difficulty);
		Candidate.Add(Entry);
	}
	DesktopArcadeStorage::Rank(Candidate);
	Records = MoveTemp(Candidate);
	return true;
}

TArray<int64> ADaedalusDesktopArcade::GetHighScores() const
{
	TArray<int64> Values;
	for (const FDaedalusDesktopArcadeHighScore& Entry : HighScores) Values.Add(Entry.Score);
	return Values;
}
TArray<FDaedalusDesktopArcadeHighScore> ADaedalusDesktopArcade::GetHighScoreRecords() const { return HighScores; }

void ADaedalusDesktopArcade::RecordScore()
{
	if (bScoreSubmitted || Session.ActiveId() != "star_shooter" || !Session.GetStatus().Over) return;
	EnsureScoresLoaded();
	const std::string Payload = Session.CaptureSave();
	TArray<FString> Fields;
	FString(UTF8_TO_TCHAR(Payload.c_str())).ParseIntoArrayWS(Fields);
	int64 Wave = 0, Difficulty = 0;
	if (Fields.Num() != 10 || Fields[0] != TEXT("DGS1")
		|| !DesktopArcadeStorage::Number(Fields[2], 1000000, Wave) || Wave < 1
		|| !DesktopArcadeStorage::Number(Fields[8], 2, Difficulty)) return;
	bScoreSubmitted = true;
	FDaedalusDesktopArcadeHighScore Entry;
	Entry.Score = FMath::Clamp<int64>(Session.GetStatus().Score, 0, 1000000000000LL);
	Entry.Wave = static_cast<int32>(Wave); Entry.Difficulty = static_cast<int32>(Difficulty);
	PendingScores.Add(Entry);
	DesktopArcadeStorage::Rank(PendingScores);
	bScoresNeedWrite = true;
	NextScoresAttemptSeconds = 0.0;
}

void ADaedalusDesktopArcade::ProcessSourceRequests()
{
	RecordScore();
	const double Now = FPlatformTime::Seconds();
	if (bScoresNeedWrite && Now >= NextScoresAttemptSeconds)
	{
		// Reload immediately before every write/retry. Another cabinet's newer records cannot be overwritten by a stale cache.
		TArray<FDaedalusDesktopArcadeHighScore> Latest;
		if (ReadHighScoreRecords(Latest))
		{
			Latest.Append(PendingScores);
			DesktopArcadeStorage::Rank(Latest);
			FString Text = TEXT("DGL1\n");
			for (const FDaedalusDesktopArcadeHighScore& Entry : Latest)
				Text += FString::Printf(TEXT("%lld %d %d\n"), Entry.Score, Entry.Wave, Entry.Difficulty);
			HighScores = Latest;
			if (WriteOwnedFile(ScoresPath(), Text))
			{
				PendingScores.Reset(); bScoresNeedWrite = false; ScoresSaveError.Reset();
			}
		}
		if (bScoresNeedWrite)
		{
			ScoresSaveError = TEXT("Native leaderboard could not be merged/saved; pending results are kept. Retrying in five seconds.");
			NextScoresAttemptSeconds = Now + 5.0;
		}
	}
	if (Session.HasSaveRequest())
	{
		if (Now < NextSaveAttemptSeconds) return;
		const std::string Payload = Session.CaptureSave();
		if (Session.ActiveId() != "star_shooter" || Payload.empty() || Payload.size() > 4096
			|| !WriteOwnedFile(SavePath(), FString(UTF8_TO_TCHAR(Payload.c_str()))))
		{
			RunSaveError = TEXT("Star save failed; the pending run is kept. Retrying in five seconds.");
			NextSaveAttemptSeconds = Now + 5.0;
			return; // Do not acknowledge or honor the source quit before a successful write.
		}
		Session.AcknowledgeSave();
		bHasSavedRun = true; RunSaveError.Reset();
	}
	if (Session.WantsExit()) CloseArcade();
}

bool ADaedalusDesktopArcade::OtherHeroOverlayOpen() const
{
	const APlayerController* PC = OpenController.Get();
	auto HasOverlay = [](const ADaedalusHero* Hero)
	{
		return Hero && (Hero->IsSettingsOpen() || Hero->IsFieldOpen() || Hero->IsRealmOpen());
	};
	return HasOverlay(OpenHero.Get()) || HasOverlay(PC ? Cast<ADaedalusHero>(PC->GetPawn()) : nullptr);
}

bool ADaedalusDesktopArcade::Use(ADaedalusHero* Hero)
{
	UWorld* World = GetWorld();
	APlayerController* PC = Hero ? Cast<APlayerController>(Hero->GetController()) : nullptr;
	UGameViewportClient* Viewport = World ? World->GetGameViewport() : nullptr;
	ULocalPlayer* LocalPlayer = PC ? PC->GetLocalPlayer() : nullptr;
	if (bClosing || bCloseScheduled || ArcadeHost.IsValid() || !World || !Hero || Hero->GetWorld() != World
		|| !PC || !PC->IsLocalController() || !LocalPlayer || !Viewport || !FSlateApplication::IsInitialized()
		|| GetNetMode() != NM_Standalone || UGameplayStatics::IsGamePaused(this) || PC->bShowMouseCursor
		|| Viewport->IgnoreInput() || Hero->IsSettingsOpen() || Hero->IsFieldOpen() || Hero->IsRealmOpen()) return false;
	if (Session.ActiveId().empty() && !StartGame(InitialGameId, InitialSeed)) return false;
	// A failed Save & Quit survives manual close/reopen. Never reset its pending snapshot.
	if (Session.WantsExit() && !Session.HasSaveRequest()) RestartGame();
	// Another cabinet may have saved since this instance began play.
	RefreshSavedRun();
	TArray<FDaedalusDesktopArcadeHighScore> LatestScores;
	if (ReadHighScoreRecords(LatestScores))
	{
		LatestScores.Append(PendingScores); DesktopArcadeStorage::Rank(LatestScores);
		HighScores = MoveTemp(LatestScores); bScoresLoaded = true;
	}
	if (!PC->SetPause(true)) return false;
	bOwnsPause = true;
	OpenController = PC; OpenHero = Hero; OpenViewport = Viewport; OpenLocalPlayer = LocalPlayer;
	PauseOwner = World->GetWorldSettings()->GetPauserPlayerState();
	bPreviousMouseCursor = PC->bShowMouseCursor; PreviousCursor = PC->CurrentMouseCursor;
	PreviousCaptureMode = Viewport->GetMouseCaptureMode(); PreviousLockMode = Viewport->GetMouseLockMode();
	SlateUserIndex = FSlateApplication::Get().GetUserIndexForController(LocalPlayer->GetControllerId());
	Session.ClearInput();
	ArcadeWidget = SNew(SDaedalusDesktopArcade).Game(this);
	// The engine's global viewport overlay paints above its per-player layer,
	// regardless of each layer's child Z. The host retains the player's rect/user.
	ArcadeHost = SDaedalusDesktopArcade::MakeForegroundHost(LocalPlayer, Viewport, ArcadeWidget.ToSharedRef());
	Viewport->AddViewportWidgetContent(ArcadeHost.ToSharedRef(), 100);
	FInputModeUIOnly Mode;
	Mode.SetWidgetToFocus(ArcadeWidget);
	Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
	PC->SetInputMode(Mode); PC->bShowMouseCursor = true; PC->CurrentMouseCursor = EMouseCursor::Default;
	if (SlateUserIndex != INDEX_NONE) FSlateApplication::Get().SetUserFocus(SlateUserIndex, ArcadeWidget, EFocusCause::SetDirectly);
	return true;
}

bool ADaedalusDesktopArcade::OtherOverlayOwnsInput() const
{
	if (OtherHeroOverlayOpen()) return true;
	if (!FSlateApplication::IsInitialized() || SlateUserIndex == INDEX_NONE) return false;
	return FSlateApplication::Get().GetUserFocusedWidget(SlateUserIndex).IsValid()
		&& !(ArcadeWidget.IsValid() && ArcadeWidget->OwnsUserFocus(SlateUserIndex));
}

bool ADaedalusDesktopArcade::CanRestoreGameInput() const
{
	const APlayerController* PC = OpenController.Get();
	return PC && PC->IsLocalController() && PC->GetWorld() == GetWorld() && !OtherOverlayOwnsInput();
}

bool ADaedalusDesktopArcade::MaintainOpenSession()
{
	if (!ArcadeHost.IsValid() || bClosing || bCloseScheduled) return false;
	const APlayerController* PC = OpenController.Get();
	const ADaedalusHero* Hero = OpenHero.Get();
	const TSharedPtr<SViewport> ViewportWidget = OpenViewport.IsValid() ? OpenViewport->GetGameViewportWidget() : nullptr;
	// Editor/window activation and the bare viewport are focus loss, not another
	// game's modal lease. Keep our host alive; Slate suspends and clears held input.
	const bool bOtherGameOverlay = OtherHeroOverlayOpen() || (OtherOverlayOwnsInput()
		&& ViewportWidget.IsValid() && ViewportWidget->HasUserFocusedDescendants(SlateUserIndex));
	if (!PC || !Hero || PC->GetWorld() != GetWorld() || PC->GetPawn() != Hero || Hero->GetController() != PC
		|| !OpenViewport.IsValid() || !OpenLocalPlayer.IsValid() || bOtherGameOverlay)
	{
		ResetPresentationInput();
		CloseArcade();
		return false;
	}
	// Initial focus can precede the foreground host's first arrangement. Retry
	// only after layout and only from our bare viewport, never editor/foreign UI.
	const FVector2D Size = ArcadeWidget.IsValid() ? ArcadeWidget->GetCachedGeometry().GetLocalSize() : FVector2D::ZeroVector;
	if (FSlateApplication::IsInitialized() && FSlateApplication::Get().IsActive() && SlateUserIndex != INDEX_NONE
		&& ViewportWidget.IsValid() && ViewportWidget->HasUserFocus(SlateUserIndex).IsSet()
		&& !Size.ContainsNaN() && Size.X > 0.0 && Size.Y > 0.0)
		FSlateApplication::Get().SetUserFocus(SlateUserIndex, ArcadeWidget, EFocusCause::SetDirectly);
	return true;
}

void ADaedalusDesktopArcade::CloseArcade()
{
	if (bClosing || bCloseScheduled || (!ArcadeHost.IsValid() && !bOwnsPause)) return;
	bCloseScheduled = true;
	ResetPresentationInput();
	TWeakObjectPtr<ADaedalusDesktopArcade> Self(this);
	FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateLambda([Self](float)
	{
		if (Self.IsValid()) Self->ReleaseOverlay();
		return false;
	}));
}

void ADaedalusDesktopArcade::ReleaseOverlay()
{
	if (bClosing) return;
	bClosing = true;
	const bool bOtherOverlay = OtherOverlayOwnsInput();
	const bool bRestore = CanRestoreGameInput();
	APlayerController* PC = OpenController.Get();
	UWorld* World = GetWorld();
	UGameViewportClient* Viewport = OpenViewport.Get();
	Session.ClearInput();
	if (ArcadeHost.IsValid() && Viewport)
		Viewport->RemoveViewportWidgetContent(ArcadeHost.ToSharedRef());
	ArcadeHost.Reset(); ArcadeWidget.Reset();
	if (bRestore && PC)
	{
		PC->SetInputMode(FInputModeGameOnly()); PC->bShowMouseCursor = bPreviousMouseCursor; PC->CurrentMouseCursor = PreviousCursor;
	}
	if (!bOtherOverlay && Viewport)
	{
		Viewport->SetIgnoreInput(false);
		Viewport->SetMouseCaptureMode(PreviousCaptureMode); Viewport->SetMouseLockMode(PreviousLockMode);
		if (FSlateApplication::IsInitialized() && SlateUserIndex != INDEX_NONE)
			FSlateApplication::Get().SetUserFocusToGameViewport(SlateUserIndex, EFocusCause::SetDirectly);
	}
	AWorldSettings* Settings = World ? World->GetWorldSettings() : nullptr;
	if (bOwnsPause && !bOtherOverlay && Settings
		&& PauseOwner.HasSameIndexAndSerialNumber(TWeakObjectPtr<APlayerState>(Settings->GetPauserPlayerState())))
	{
		if (PC && PC->GetWorld() == World) PC->SetPause(false);
		else if (AGameModeBase* Mode = World->GetAuthGameMode()) Mode->ClearPause();
	}
	bOwnsPause = false; bCloseScheduled = false; SlateUserIndex = INDEX_NONE;
	OpenController.Reset(); OpenHero.Reset(); OpenViewport.Reset(); OpenLocalPlayer.Reset(); PauseOwner.Reset();
	bClosing = false;
}

void ADaedalusDesktopArcade::EndPlay(const EEndPlayReason::Type Reason)
{
	ReleaseOverlay();
	Super::EndPlay(Reason);
}
