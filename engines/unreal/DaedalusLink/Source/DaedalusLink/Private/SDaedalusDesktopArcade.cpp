// SPDX-License-Identifier: MIT
#include "SDaedalusDesktopArcade.h"

#include "Framework/Application/SlateApplication.h"
#include "InputCoreTypes.h"
#include "Layout/WidgetPath.h"
#include "Rendering/DrawElements.h"
#include "Rendering/SlateRenderer.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SLeafWidget.h"
#include "Widgets/Text/STextBlock.h"

namespace DesktopArcadeUI
{
	const FSlateBrush* WhiteBrush() { return FCoreStyle::Get().GetBrush("GenericWhiteBox"); }
	FSlateFontInfo Font(int32 Size, bool bBold = false) { return FCoreStyle::GetDefaultFontStyle(bBold ? "Bold" : "Regular", Size); }
	FLinearColor Tint(daedalus::desktop::Color C) { return FLinearColor::FromSRGBColor(FColor(C.R, C.G, C.B, C.A)); }
	bool ValidPoint(daedalus::desktop::Vec P)
	{
		return FMath::IsFinite(P.X) && FMath::IsFinite(P.Y) && FMath::Abs(P.X) < 1000000.0 && FMath::Abs(P.Y) < 1000000.0;
	}

	/** Commands remain in std::vector. Only trivial Slate vertices/indices use TArray. */
	class SGameCanvas : public SLeafWidget
	{
	public:
		SLATE_BEGIN_ARGS(SGameCanvas) {}
			SLATE_ARGUMENT(TWeakObjectPtr<ADaedalusDesktopArcade>, Game)
		SLATE_END_ARGS()
		void Construct(const FArguments& Args) { Game = Args._Game; SetCanTick(false); }
		virtual FVector2D ComputeDesiredSize(float LayoutScaleMultiplier) const override { return FVector2D(800.f, 600.f); }
		virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& Geometry, const FSlateRect& CullRect,
			FSlateWindowElementList& Elements, int32 LayerId, const FWidgetStyle& Style, bool bParentEnabled) const override
		{
			const ADaedalusDesktopArcade* Actor = Game.Get();
			if (!Actor) return LayerId;
			const daedalus::desktop::Frame& Picture = Actor->GetArcadeFrame();
			if (!FMath::IsFinite(Picture.Width) || !FMath::IsFinite(Picture.Height)
				|| Picture.Width <= 0.0 || Picture.Height <= 0.0 || Picture.Width > 10000.0 || Picture.Height > 10000.0) return LayerId;
			const FVector2f LocalSize = Geometry.GetLocalSize();
			const FVector2f LogicalSize(static_cast<float>(Picture.Width), static_cast<float>(Picture.Height));
			const float Scale = FMath::Min(LocalSize.X / LogicalSize.X, LocalSize.Y / LogicalSize.Y);
			if (!FMath::IsFinite(Scale) || Scale <= 0.f) return LayerId;
			const FVector2f Offset = (LocalSize - LogicalSize * Scale) * 0.5f;
			const FGeometry Screen = Geometry.MakeChild(LogicalSize, FSlateLayoutTransform(Scale, Offset));
			const FLinearColor StyleTint = Style.GetColorAndOpacityTint();
			FSlateDrawElement::MakeBox(Elements, LayerId, Geometry.ToPaintGeometry(), WhiteBrush(), ESlateDrawEffect::None, FLinearColor::Black * StyleTint);
			Elements.PushClip(FSlateClippingZone(Screen));
			FSlateDrawElement::MakeBox(Elements, ++LayerId, Screen.ToPaintGeometry(), WhiteBrush(), ESlateDrawEffect::None, Tint(Picture.Background) * StyleTint);
			const FSlateResourceHandle Resource = FSlateApplication::Get().GetRenderer()->GetResourceHandle(*WhiteBrush());
			TArray<FSlateVertex> Vertices;
			TArray<SlateIndex> Indices;
			Vertices.Reserve(26); Indices.Reserve(72);
			auto Vertex = [&Screen](FVector2f Point, FColor Color)
			{
				return FSlateVertex::Make<ESlateVertexRounding::Disabled>(Screen.GetAccumulatedRenderTransform(), Point, FVector2f(0.5f, 0.5f), Color);
			};
			std::size_t Seen = 0;
			for (const daedalus::desktop::DrawCommand& Command : Picture.Commands)
			{
				if (++Seen > daedalus::desktop::Frame::MaxCommands) break;
				if (!ValidPoint(Command.A) || !ValidPoint(Command.B) || !ValidPoint(Command.C)
					|| !FMath::IsFinite(Command.Size) || Command.Size < 0.0 || Command.Size > 10000.0) continue;
				const FVector2f A(static_cast<float>(Command.A.X), static_cast<float>(Command.A.Y));
				const FVector2f B(static_cast<float>(Command.B.X), static_cast<float>(Command.B.Y));
				const FLinearColor Color = Tint(Command.Tint) * StyleTint;
				const FColor VertexColor = Color.ToFColor(true);
				++LayerId;
				switch (Command.Kind)
				{
				case daedalus::desktop::Shape::Rectangle:
					if (B.X > 0.f && B.Y > 0.f)
						FSlateDrawElement::MakeBox(Elements, LayerId, Screen.ToPaintGeometry(B, FSlateLayoutTransform(A)), WhiteBrush(), ESlateDrawEffect::None, Color);
					break;
				case daedalus::desktop::Shape::Line:
					{
						TArray<FVector2f> Points{A, B};
						FSlateDrawElement::MakeLines(Elements, LayerId, Screen.ToPaintGeometry(), MoveTemp(Points), ESlateDrawEffect::None, Color, false, FMath::Max(0.5f, static_cast<float>(Command.Size)));
					}
					break;
				case daedalus::desktop::Shape::Triangle:
					Vertices.Reset(); Indices.Reset();
					Vertices.Add(Vertex(A, VertexColor)); Vertices.Add(Vertex(B, VertexColor));
					Vertices.Add(Vertex(FVector2f(static_cast<float>(Command.C.X), static_cast<float>(Command.C.Y)), VertexColor));
					Indices.Append({0, 1, 2});
					FSlateDrawElement::MakeCustomVerts(Elements, LayerId, Resource, Vertices, Indices, nullptr, 0, 0);
					break;
				case daedalus::desktop::Shape::Circle:
					Vertices.Reset(); Indices.Reset();
					Vertices.Add(Vertex(A, VertexColor));
					for (int32 N = 0; N <= 24; ++N)
					{
						const float Angle = static_cast<float>(N) * 2.f * PI / 24.f;
						const float Radius = static_cast<float>(Command.Size);
						Vertices.Add(Vertex(A + FVector2f(FMath::Cos(Angle), FMath::Sin(Angle)) * Radius, VertexColor));
						if (N < 24) { Indices.Add(0); Indices.Add(static_cast<SlateIndex>(N + 1)); Indices.Add(static_cast<SlateIndex>(N + 2)); }
					}
					FSlateDrawElement::MakeCustomVerts(Elements, LayerId, Resource, Vertices, Indices, nullptr, 0, 0);
					break;
				case daedalus::desktop::Shape::Text:
					FSlateDrawElement::MakeText(Elements, LayerId, Screen.ToPaintGeometry(LogicalSize, FSlateLayoutTransform(A)),
						FString(UTF8_TO_TCHAR(Command.Label.c_str())).Left(256), Font(FMath::Clamp(FMath::RoundToInt(Command.Size), 6, 96)), ESlateDrawEffect::None, Color);
					break;
				}
			}
			const FDaedalusDesktopArcadeState State = Actor->GetState();
			if (State.bPaused && State.Id != TEXT("star_shooter"))
			{
				FSlateDrawElement::MakeBox(Elements, ++LayerId, Screen.ToPaintGeometry(), WhiteBrush(), ESlateDrawEffect::None, FLinearColor(0.f, 0.f, 0.f, 0.65f));
				FSlateDrawElement::MakeText(Elements, ++LayerId, Screen.ToPaintGeometry(LogicalSize, FSlateLayoutTransform(FVector2f(30.f, LogicalSize.Y * 0.45f))),
					TEXT("PAUSED - P / Start or Resume to continue"), Font(24, true), ESlateDrawEffect::None, FLinearColor::White);
			}
			Elements.PopClip();
			return LayerId;
		}
	private:
		TWeakObjectPtr<ADaedalusDesktopArcade> Game;
	};
}

namespace DAUI = DesktopArcadeUI;

void SDaedalusDesktopArcade::Construct(const FArguments& InArgs)
{
	Game = InArgs._Game;
	if (const ADaedalusDesktopArcade* Actor = Game.Get())
		for (const FDaedalusDesktopArcadeEntry& Entry : Actor->GetAvailableGames()) GameItems.Add(MakeShared<FString>(Entry.Id));
	ChildSlot
	[
		SNew(SBorder).BorderImage(DAUI::WhiteBrush()).BorderBackgroundColor(FLinearColor(0.02f, 0.025f, 0.04f, 1.f)).Padding(12.f)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().FillWidth(1.f).Padding(0.f, 0.f, 8.f, 0.f)
				[
					SAssignNew(CatalogSelector, SComboBox<TSharedPtr<FString>>).OptionsSource(&GameItems).IsFocusable(false)
					.IsEnabled_Lambda([this]() { const ADaedalusDesktopArcade* Actor = Game.Get(); return Actor && !Actor->GetState().bSavePending; })
					.OnGenerateWidget(this, &SDaedalusDesktopArcade::MakeGameRow)
					.OnSelectionChanged(this, &SDaedalusDesktopArcade::SelectGame)
					.OnComboBoxOpening_Lambda([this]() { SuspendForFocusLoss(); })
					[SNew(STextBlock).Text(this, &SDaedalusDesktopArcade::CurrentTitle).Font(DAUI::Font(18, true))]
				]
				+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)
				[
					SNew(SButton).IsFocusable(false).ContentPadding(FMargin(12.f, 6.f))
					.IsEnabled_Lambda([this]() { const ADaedalusDesktopArcade* Actor = Game.Get(); return Actor && !Actor->GetState().bSavePending; })
					.OnClicked_Lambda([this]() { if (ADaedalusDesktopArcade* Actor = Game.Get()) Actor->PauseGame(!Actor->GetState().bPaused); return FocusReply(); })
					[SNew(STextBlock).Text_Lambda([this]() { const ADaedalusDesktopArcade* Actor = Game.Get(); return FText::FromString(Actor && Actor->GetState().bPaused ? TEXT("Resume") : TEXT("Pause")); })]
				]
				+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)
				[MakeAction(TEXT("Restart"), FSimpleDelegate::CreateLambda([this]() { if (ADaedalusDesktopArcade* Actor = Game.Get()) Actor->RestartGame(); }), true)]
				+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)
				[MakeAction(TEXT("Close"), FSimpleDelegate::CreateLambda([this]() { if (ADaedalusDesktopArcade* Actor = Game.Get()) Actor->CloseArcade(); }))]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 6.f)
			[SNew(STextBlock).Text(this, &SDaedalusDesktopArcade::StatusText).Font(DAUI::Font(13)).AutoWrapText(true).ColorAndOpacity(FLinearColor(0.7f, 0.85f, 1.f))]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 6.f)
			[
				SNew(SHorizontalBox).Visibility(this, &SDaedalusDesktopArcade::StarVisibility)
				+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)
				[
					SNew(SButton).IsFocusable(false).ContentPadding(FMargin(10.f, 4.f))
					.IsEnabled_Lambda([this]() { const ADaedalusDesktopArcade* Actor = Game.Get(); return Actor && Actor->GetState().bHasSavedRun && !Actor->GetState().bSavePending; })
					.OnClicked_Lambda([this]() { if (ADaedalusDesktopArcade* Actor = Game.Get()) Actor->ResumeGame(); SyncSelection(); return FocusReply(); })
					[SNew(STextBlock).Text(FText::FromString(TEXT("Continue saved Star run")))]
				]
				+ SHorizontalBox::Slot().AutoWidth().Padding(6.f, 2.f)
				[SNew(STextBlock).Text(FText::FromString(TEXT("New run:"))).Font(DAUI::Font(13))]
				+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)
				[MakeAction(TEXT("Easy"), FSimpleDelegate::CreateLambda([this]() { if (ADaedalusDesktopArcade* Actor = Game.Get()) Actor->SetGameOption(0); }), true)]
				+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)
				[MakeAction(TEXT("Medium"), FSimpleDelegate::CreateLambda([this]() { if (ADaedalusDesktopArcade* Actor = Game.Get()) Actor->SetGameOption(1); }), true)]
				+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)
				[MakeAction(TEXT("Hard"), FSimpleDelegate::CreateLambda([this]() { if (ADaedalusDesktopArcade* Actor = Game.Get()) Actor->SetGameOption(2); }), true)]
			]
			+ SVerticalBox::Slot().FillHeight(1.f)
			[SNew(DAUI::SGameCanvas).Game(Game)]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 6.f, 0.f, 0.f)
			[SNew(STextBlock).Text(this, &SDaedalusDesktopArcade::LeaderboardText).Visibility(this, &SDaedalusDesktopArcade::LeaderboardVisibility)
				.Font(DAUI::Font(13)).AutoWrapText(true).ColorAndOpacity(FLinearColor(1.f, 0.85f, 0.45f))]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 6.f, 0.f, 0.f)
			[SNew(STextBlock).Text(this, &SDaedalusDesktopArcade::ControlText).Font(DAUI::Font(12)).AutoWrapText(true).ColorAndOpacity(FLinearColor(0.7f, 0.75f, 0.8f))]
		]
	];
	SyncSelection();
	CoreTickHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateSP(this, &SDaedalusDesktopArcade::CoreTick));
}

SDaedalusDesktopArcade::~SDaedalusDesktopArcade()
{
	FTSTicker::GetCoreTicker().RemoveTicker(CoreTickHandle);
}

TSharedRef<SWidget> SDaedalusDesktopArcade::MakeAction(const TCHAR* Label, FSimpleDelegate Action, bool bReplacesRun)
{
	return SNew(SButton).IsFocusable(false).ContentPadding(FMargin(12.f, 6.f))
		.IsEnabled_Lambda([this, bReplacesRun]() { const ADaedalusDesktopArcade* Actor = Game.Get(); return Actor && (!bReplacesRun || !Actor->GetState().bSavePending); })
		.OnClicked_Lambda([this, Action]() { Action.ExecuteIfBound(); return FocusReply(); })
		[SNew(STextBlock).Text(FText::FromString(Label))];
}

TSharedRef<SWidget> SDaedalusDesktopArcade::MakeGameRow(TSharedPtr<FString> Item) const
{
	FString Label = Item.IsValid() ? *Item : FString();
	if (const ADaedalusDesktopArcade* Actor = Game.Get())
		for (const FDaedalusDesktopArcadeEntry& Entry : Actor->GetAvailableGames()) if (Entry.Id == Label) { Label = Entry.Title; break; }
	return SNew(STextBlock).Text(FText::FromString(Label)).Font(DAUI::Font(15));
}

void SDaedalusDesktopArcade::SelectGame(TSharedPtr<FString> Item, ESelectInfo::Type Selection)
{
	if (Selection == ESelectInfo::Direct || !Item.IsValid()) return;
	if (ADaedalusDesktopArcade* Actor = Game.Get()) Actor->StartGame(*Item, Actor->GetState().Seed);
	SyncSelection(); FocusGame();
}

void SDaedalusDesktopArcade::SyncSelection()
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	if (!Actor || !CatalogSelector.IsValid()) return;
	const FString Id = Actor->GetSelectedGameId();
	if (Id == LastGameId) return;
	LastGameId = Id;
	ResetHeldInput();
	for (const TSharedPtr<FString>& Item : GameItems) if (Item.IsValid() && *Item == Id) { CatalogSelector->SetSelectedItem(Item); break; }
}

FText SDaedalusDesktopArcade::CurrentTitle() const
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	return FText::FromString(Actor ? Actor->GetState().Title : TEXT("Desktop Arcade unavailable"));
}

FText SDaedalusDesktopArcade::StatusText() const
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	if (!Actor) return FText::FromString(TEXT("Arcade unavailable."));
	const FDaedalusDesktopArcadeState State = Actor->GetState();
	FString Text = FString::Printf(TEXT("Score %lld   Lives / health %d   Seed %d   %s"), State.Score, State.Lives, State.Seed, *State.Note);
	if (State.bWon) Text += TEXT("   Won");
	else if (State.bOver) Text += TEXT("   Result / next round");
	if (!State.PersistenceMessage.IsEmpty()) Text += TEXT("\n") + State.PersistenceMessage;
	return FText::FromString(Text);
}

EVisibility SDaedalusDesktopArcade::StarVisibility() const
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	return Actor && Actor->GetSelectedGameId() == TEXT("star_shooter") ? EVisibility::Visible : EVisibility::Collapsed;
}

EVisibility SDaedalusDesktopArcade::LeaderboardVisibility() const
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	if (!Actor) return EVisibility::Collapsed;
	const FDaedalusDesktopArcadeState State = Actor->GetState();
	return State.Id == TEXT("star_shooter") && (State.bPaused || State.bOver) ? EVisibility::Visible : EVisibility::Collapsed;
}

FText SDaedalusDesktopArcade::LeaderboardText() const
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	if (!Actor) return FText::GetEmpty();
	const TArray<FDaedalusDesktopArcadeHighScore> Scores = Actor->GetHighScoreRecords();
	FString Text = TEXT("STAR TOP TEN (this installation)");
	if (Scores.IsEmpty()) Text += TEXT(" — Finish a run to record a score.");
	for (int32 N = 0; N < Scores.Num(); ++N)
	{
		const FDaedalusDesktopArcadeHighScore& Entry = Scores[N];
		const TCHAR* Difficulty = Entry.Difficulty == 0 ? TEXT("Easy") : (Entry.Difficulty == 1 ? TEXT("Medium") : TEXT("Hard"));
		Text += FString::Printf(TEXT("   #%d %lld / Wave %d / %s"), N + 1, Entry.Score, Entry.Wave, Difficulty);
	}
	return FText::FromString(Text);
}

FText SDaedalusDesktopArcade::ControlText() const
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	const FString Id = Actor ? Actor->GetSelectedGameId() : FString();
	FString Text = TEXT("Move: WASD / arrows, D-pad or left stick. P / Start: pause. R: restart. Esc / Back: close. ");
	if (Id == TEXT("dodge_ball")) Text += TEXT("Space/Z/J or pad A: throw/catch; pad X/RB: throw press only; Shift/pad B: jump; Up: charge; K/Enter: confirm.");
	else if (Id == TEXT("shadow_ninja")) Text += TEXT("Space/A: jump; J/Z/X or pad B/X: sword; K/C or pad Y/RB: star; Shift/V or LB: spin; Up/Down: climb.");
	else if (Id == TEXT("contra")) Text += TEXT("Enter/Space or pad A: title start; literal arrow keys then B,A: source code. Space/W or pad A: jump; J/Z/Ctrl/X/RT: shoot; Down: crouch. Enter/R or pad A/Start: terminal retry.");
	else if (Id == TEXT("star_shooter")) Text += TEXT("Space/J/Z/X/RT: shoot; source pause menu Up/Down: select, J/X or Space/A: confirm, Shift/Y: resume. Difficulty buttons start a new run.");
	else if (Id == TEXT("asteroids") || Id == TEXT("sega_shooter")) Text += TEXT("Space/J/Z or pad face/bumper: shoot. Asteroids Left/Right: turn, Up: thrust.");
	else if (Id == TEXT("football")) Text += TEXT("Space/J/Z or A/X: kick.");
	else Text += TEXT("J/Z/X: fire/sword, Space/A: jump/confirm, K/B/Enter: action. Source title screens use the cabinet launcher.");
	return FText::FromString(Text);
}

void SDaedalusDesktopArcade::ResetHeldInput()
{
	HeldKeys.Reset(); PreviousInput = {}; StickX = 0.f; StickY = 0.f; RightTrigger = 0.f;
	if (ADaedalusDesktopArcade* Actor = Game.Get()) Actor->ClearArcadeInput();
}

bool SDaedalusDesktopArcade::OwnsUserFocus(int32 UserIndex) const
{
	return HasUserFocus(UserIndex).IsSet() || HasUserFocusedDescendants(UserIndex)
		|| (CatalogSelector.IsValid() && CatalogSelector->IsOpen());
}

void SDaedalusDesktopArcade::SuspendForFocusLoss()
{
	ResetHeldInput();
	if (ADaedalusDesktopArcade* Actor = Game.Get()) if (!Actor->GetState().bPaused) Actor->PauseGame(true);
	bHadFocus = false;
}

void SDaedalusDesktopArcade::FocusGame()
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	if (Actor && FSlateApplication::IsInitialized() && Actor->GetArcadeSlateUserIndex() != INDEX_NONE)
		FSlateApplication::Get().SetUserFocus(Actor->GetArcadeSlateUserIndex(), AsShared(), EFocusCause::SetDirectly);
}

FReply SDaedalusDesktopArcade::FocusReply() { return FReply::Handled().SetUserFocus(AsShared(), EFocusCause::SetDirectly); }

bool SDaedalusDesktopArcade::CoreTick(float DeltaSeconds)
{
	ADaedalusDesktopArcade* Actor = Game.Get();
	if (!Actor || !Actor->MaintainOpenSession()) return false;
	SyncSelection();
	const int32 UserIndex = Actor->GetArcadeSlateUserIndex();
	const bool bFocused = FSlateApplication::IsInitialized() && FSlateApplication::Get().IsActive()
		&& UserIndex != INDEX_NONE && OwnsUserFocus(UserIndex) && !(CatalogSelector.IsValid() && CatalogSelector->IsOpen());
	if (!bFocused && bHadFocus) SuspendForFocusLoss();
	bHadFocus = bFocused;
	if (Actor->bAutoAdvance) Actor->AdvanceGame(DeltaSeconds);
	Invalidate(EInvalidateWidgetReason::Paint);
	return true;
}

void SDaedalusDesktopArcade::PushInput(const FKey& PressedKey)
{
	ADaedalusDesktopArcade* Actor = Game.Get();
	if (!Actor) return;
	const FString Id = Actor->GetSelectedGameId();
	auto Held = [this](const FKey& Key) { return HeldKeys.Contains(Key); };
	FDaedalusDesktopArcadeInput Input;
	Input.Left = Held(EKeys::Left) || Held(EKeys::A); Input.Right = Held(EKeys::Right) || Held(EKeys::D);
	Input.Up = Held(EKeys::Up) || Held(EKeys::W); Input.Down = Held(EKeys::Down) || Held(EKeys::S);
	Input.PadLeft = Held(EKeys::Gamepad_DPad_Left); Input.PadRight = Held(EKeys::Gamepad_DPad_Right);
	Input.PadUp = Held(EKeys::Gamepad_DPad_Up); Input.PadDown = Held(EKeys::Gamepad_DPad_Down);
	Input.AxisX = StickX; Input.AxisY = StickY;
	auto CommonFire = [](const FKey& Key) { return Key == EKeys::J || Key == EKeys::Z || Key == EKeys::X || Key == EKeys::LeftControl || Key == EKeys::Gamepad_FaceButton_Left || Key == EKeys::Gamepad_RightShoulder; };
	auto CommonJump = [](const FKey& Key) { return Key == EKeys::SpaceBar || Key == EKeys::Gamepad_FaceButton_Bottom; };
	auto CommonAction = [](const FKey& Key) { return Key == EKeys::K || Key == EKeys::C || Key == EKeys::Enter || Key == EKeys::Gamepad_FaceButton_Right; };
	auto CommonDash = [](const FKey& Key) { return Key == EKeys::LeftShift || Key == EKeys::RightShift || Key == EKeys::V || Key == EKeys::Gamepad_FaceButton_Top || Key == EKeys::Gamepad_LeftShoulder; };
	bool bFireEdge = CommonFire(PressedKey), bJumpEdge = CommonJump(PressedKey);
	bool bActionEdge = CommonAction(PressedKey), bDashEdge = CommonDash(PressedKey);
	for (const FKey& Key : HeldKeys)
	{
		Input.Fire |= CommonFire(Key); Input.Jump |= CommonJump(Key);
		Input.Action |= CommonAction(Key); Input.Dash |= CommonDash(Key);
	}
	Input.Fire |= RightTrigger > 0.5f;
	if (Id == TEXT("dodge_ball"))
	{
		auto FireHeld = [](const FKey& Key) { return Key == EKeys::SpaceBar || Key == EKeys::Z || Key == EKeys::J || Key == EKeys::Gamepad_FaceButton_Bottom; };
		auto FireEdge = [&FireHeld](const FKey& Key) { return FireHeld(Key) || Key == EKeys::Gamepad_FaceButton_Left || Key == EKeys::Gamepad_RightShoulder; };
		auto Jump = [](const FKey& Key) { return Key == EKeys::LeftShift || Key == EKeys::RightShift || Key == EKeys::Gamepad_FaceButton_Right; };
		auto Action = [](const FKey& Key) { return Key == EKeys::K || Key == EKeys::C || Key == EKeys::Enter; };
		Input.Fire = Input.Jump = Input.Action = Input.Dash = false;
		for (const FKey& Key : HeldKeys) { Input.Fire |= FireHeld(Key); Input.Jump |= Jump(Key); Input.Action |= Action(Key); }
		bFireEdge = FireEdge(PressedKey); bJumpEdge = Jump(PressedKey); bActionEdge = Action(PressedKey); bDashEdge = false;
		// Preserve independent hat fields and the real stick; the core handles hat movement precedence.
		// The core reads PadUp/PadDown for country selection. Never turn hat-up into keyboard Up: that would wrongly charge throws.
	}
	else if (Id == TEXT("shadow_ninja"))
	{
		auto Sword = [](const FKey& Key) { return Key == EKeys::J || Key == EKeys::Z || Key == EKeys::X || Key == EKeys::Gamepad_FaceButton_Right || Key == EKeys::Gamepad_FaceButton_Left; };
		Input.Fire = false;
		for (const FKey& Key : HeldKeys) Input.Fire |= Sword(Key);
		Input.Action = Held(EKeys::K) || Held(EKeys::C) || Held(EKeys::Gamepad_FaceButton_Top) || Held(EKeys::Gamepad_RightShoulder);
		Input.Dash = Held(EKeys::LeftShift) || Held(EKeys::RightShift) || Held(EKeys::V) || Held(EKeys::Gamepad_LeftShoulder);
		bFireEdge = Sword(PressedKey);
		bActionEdge = PressedKey == EKeys::K || PressedKey == EKeys::C || PressedKey == EKeys::Gamepad_FaceButton_Top || PressedKey == EKeys::Gamepad_RightShoulder;
		bDashEdge = PressedKey == EKeys::LeftShift || PressedKey == EKeys::RightShift || PressedKey == EKeys::V || PressedKey == EKeys::Gamepad_LeftShoulder;
		// The core passes these separate hats to NinjaPlayer::Update; preserve opposing keyboard/hat priority there.
	}
	else if (Id == TEXT("contra"))
	{
		Input.Jump |= Held(EKeys::W); bJumpEdge |= PressedKey == EKeys::W;
		Input.Action |= Held(EKeys::B); bActionEdge |= PressedKey == EKeys::B;
	}
	else if (Id == TEXT("asteroids") || Id == TEXT("sega_shooter"))
	{
		auto ExtraFire = [](const FKey& Key) { return Key == EKeys::SpaceBar || Key == EKeys::Gamepad_FaceButton_Bottom || Key == EKeys::Gamepad_FaceButton_Right || Key == EKeys::Gamepad_FaceButton_Top || Key == EKeys::Gamepad_LeftShoulder; };
		for (const FKey& Key : HeldKeys) Input.Fire |= ExtraFire(Key);
		bFireEdge |= ExtraFire(PressedKey);
	}
	else if (Id == TEXT("football") || Id == TEXT("star_shooter"))
	{
		Input.Fire |= Held(EKeys::SpaceBar); bFireEdge |= PressedKey == EKeys::SpaceBar;
		if (Id == TEXT("football")) { Input.Fire |= Held(EKeys::Gamepad_FaceButton_Bottom); bFireEdge |= PressedKey == EKeys::Gamepad_FaceButton_Bottom; }
		else
		{
			Input.Action = Held(EKeys::K) || Held(EKeys::C) || Held(EKeys::Gamepad_FaceButton_Right);
			bActionEdge = PressedKey == EKeys::K || PressedKey == EKeys::C || PressedKey == EKeys::Gamepad_FaceButton_Right;
			bFireEdge |= PressedKey == EKeys::Enter; // Source pause confirmation; does not toggle pause as a generic Action.
		}
	}
	// These cores use merged digital directions. Asteroids and Dodge preserve independent keyboard/hat behavior.
	if (Id != TEXT("asteroids") && Id != TEXT("dodge_ball") && Id != TEXT("shadow_ninja"))
	{
		Input.Left |= Input.PadLeft; Input.Right |= Input.PadRight;
		Input.Up |= Input.PadUp; Input.Down |= Input.PadDown;
	}
	Input.FirePressed = bFireEdge || (Input.Fire && !PreviousInput.Fire);
	Input.JumpPressed = bJumpEdge || (Input.Jump && !PreviousInput.Jump);
	Input.ActionPressed = bActionEdge || (Input.Action && !PreviousInput.Action);
	Input.DashPressed = bDashEdge || (Input.Dash && !PreviousInput.Dash);
	PreviousInput = Input;
	PreviousInput.FirePressed = PreviousInput.JumpPressed = PreviousInput.ActionPressed = PreviousInput.DashPressed = false;
	Actor->SetArcadeInput(Input);
}

FReply SDaedalusDesktopArcade::OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
	const FKey Key = Event.GetKey();
	if (!Event.IsRepeat())
	{
		if (ADaedalusDesktopArcade* Actor = Game.Get())
		{
			// Preserve every keyboard keydown in event order before held mapping.
			// Controllers use a separate seam and never enter/reset the keyboard code.
			if (!Key.IsGamepadKey())
			{
				const int32 SourceKey = Key == EKeys::Up ? 0 : Key == EKeys::Down ? 1 : Key == EKeys::Left ? 2 : Key == EKeys::Right ? 3
					: Key == EKeys::B ? 4 : Key == EKeys::A ? 5 : Key == EKeys::Enter ? 6 : Key == EKeys::SpaceBar ? 7 : Key == EKeys::R ? 8 : 9;
				Actor->SubmitArcadeSourceKey(SourceKey);
			}
			else if (Key == EKeys::Gamepad_FaceButton_Bottom || Key == EKeys::Gamepad_Special_Right)
			{
				const bool bConsumed = Actor->SubmitArcadeSourceControllerButton(Key == EKeys::Gamepad_FaceButton_Bottom ? 0 : 1);
				if (bConsumed && Key == EKeys::Gamepad_Special_Right) { PushInput(); return FReply::Handled(); }
				// A still enters held jump mapping after its immediate source start.
			}
			if (Key == EKeys::Escape || Key == EKeys::Gamepad_Special_Left) { Actor->CloseArcade(); return FReply::Handled(); }
			if (Key == EKeys::P || Key == EKeys::Gamepad_Special_Right) { Actor->PauseGame(!Actor->GetState().bPaused); return FReply::Handled(); }
			if (Key == EKeys::R) { Actor->RestartGame(); return FReply::Handled(); }
		}
		HeldKeys.Add(Key); PushInput(Key);
	}
	return FReply::Handled();
}

FReply SDaedalusDesktopArcade::OnKeyUp(const FGeometry& Geometry, const FKeyEvent& Event)
{
	HeldKeys.Remove(Event.GetKey()); PushInput();
	return FReply::Handled();
}

FReply SDaedalusDesktopArcade::OnAnalogValueChanged(const FGeometry& Geometry, const FAnalogInputEvent& Event)
{
	const float Value = FMath::IsFinite(Event.GetAnalogValue()) ? FMath::Clamp(Event.GetAnalogValue(), -1.f, 1.f) : 0.f;
	if (Event.GetKey() == EKeys::Gamepad_LeftX) StickX = Value;
	else if (Event.GetKey() == EKeys::Gamepad_LeftY) StickY = -Value;
	else if (Event.GetKey() == EKeys::Gamepad_RightTriggerAxis) RightTrigger = FMath::Max(0.f, Value);
	else return FReply::Handled();
	PushInput();
	return FReply::Handled();
}

FReply SDaedalusDesktopArcade::OnMouseButtonDown(const FGeometry& Geometry, const FPointerEvent& Event) { return FocusReply(); }
FNavigationReply SDaedalusDesktopArcade::OnNavigation(const FGeometry& Geometry, const FNavigationEvent& Event) { return FNavigationReply::Stop(); }

void SDaedalusDesktopArcade::OnFocusLost(const FFocusEvent& Event)
{
	SCompoundWidget::OnFocusLost(Event);
	SuspendForFocusLoss();
}

void SDaedalusDesktopArcade::OnFocusChanging(const FWeakWidgetPath& Previous, const FWidgetPath& Next, const FFocusEvent& Event)
{
	SCompoundWidget::OnFocusChanging(Previous, Next, Event);
	if (!Next.ContainsWidget(this) && !(CatalogSelector.IsValid() && CatalogSelector->IsOpen())) SuspendForFocusLoss();
}
