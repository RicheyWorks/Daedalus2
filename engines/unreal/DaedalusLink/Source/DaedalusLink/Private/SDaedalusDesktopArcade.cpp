// SPDX-License-Identifier: MIT
#include "SDaedalusDesktopArcade.h"

#include "DesktopGames/DaedalusDesktopMazeCore.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Framework/Application/SlateApplication.h"
#include "HAL/IConsoleManager.h"
#include "Input/HittestGrid.h"
#include "InputCoreTypes.h"
#include "Layout/ArrangedChildren.h"
#include "Layout/WidgetPath.h"
#include "Rendering/DrawElements.h"
#include "Rendering/SlateRenderer.h"
#include "Slate/SGameLayerManager.h"
#include "Styling/CoreStyle.h"
#include "Types/NavigationMetaData.h"
#include "Types/PaintArgs.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SCheckBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SLeafWidget.h"
#include "Widgets/SWeakWidget.h"
#include "Widgets/Text/STextBlock.h"

namespace DesktopArcadeUI
{
	/** Above the global HUD while retaining the engine's local-player view rectangle. */
	class SForegroundPlayerHost : public SCompoundWidget
	{
	public:
		SLATE_BEGIN_ARGS(SForegroundPlayerHost) {}
			SLATE_ARGUMENT(TWeakObjectPtr<ULocalPlayer>, Player)
			SLATE_ARGUMENT(TWeakObjectPtr<UGameViewportClient>, Viewport)
			SLATE_DEFAULT_SLOT(FArguments, Content)
		SLATE_END_ARGS()
		void Construct(const FArguments& Args)
		{
			Player = Args._Player; Viewport = Args._Viewport;
			SetVisibility(EVisibility::SelfHitTestInvisible);
			ChildSlot
			[
				SNew(SWeakWidget).PossiblyNullContent(Args._Content.Widget)
				.Clipping(EWidgetClipping::ClipToBoundsAlways)
			];
		}
		virtual void OnArrangeChildren(const FGeometry& Geometry, FArrangedChildren& Children) const override
		{
			UGameViewportClient* Client = Viewport.Get();
			ULocalPlayer* LocalPlayer = Player.Get();
			const TSharedPtr<IGameLayerManager> Layers = Client ? Client->GetGameLayerManager() : nullptr;
			if (!Layers.IsValid() || !LocalPlayer) return;
			const FGeometry PlayerGeometry = Layers->GetPlayerWidgetHostGeometry(LocalPlayer);
			const FVector2D Origin = Geometry.AbsoluteToLocal(PlayerGeometry.LocalToAbsolute(FVector2D::ZeroVector));
			const FVector2D Extent = Geometry.AbsoluteToLocal(PlayerGeometry.LocalToAbsolute(PlayerGeometry.GetLocalSize())) - Origin;
			if (Origin.ContainsNaN() || Extent.ContainsNaN() || Extent.X <= 0.0 || Extent.Y <= 0.0) return;
			// Zero/unknown geometry stays empty until the engine supplies a valid player rect.
			Children.AddWidget(Geometry.MakeChild(ChildSlot.GetWidget(), Extent, FSlateLayoutTransform(Origin)));
		}
		virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& Geometry, const FSlateRect& CullRect,
			FSlateWindowElementList& Elements, int32 LayerId, const FWidgetStyle& Style, bool bParentEnabled) const override
		{
			const ULocalPlayer* LocalPlayer = Player.Get();
			if (!LocalPlayer || !FSlateApplication::IsInitialized()) return LayerId;
			FHittestGrid& Grid = Args.GetHittestGrid();
			const int32 PreviousUser = Grid.GetUserIndex();
			static const IConsoleVariable* PerUserHits = IConsoleManager::Get().FindConsoleVariable(TEXT("Slate.AllowPerUserHitTesting"));
			const bool bPerUserHits = !PerUserHits || PerUserHits->GetBool();
			Grid.SetUserIndex(bPerUserHits ? FSlateApplication::Get().GetUserIndexForController(LocalPlayer->GetControllerId()) : INDEX_NONE);
			const int32 Result = SCompoundWidget::OnPaint(Args, Geometry, CullRect, Elements, LayerId, Style, bParentEnabled);
			Grid.SetUserIndex(PreviousUser);
			return Result;
		}
	private:
		TWeakObjectPtr<ULocalPlayer> Player;
		TWeakObjectPtr<UGameViewportClient> Viewport;
	};

	const FSlateBrush* WhiteBrush() { return FCoreStyle::Get().GetBrush("GenericWhiteBox"); }
	FSlateFontInfo Font(int32 Size, bool bBold = false) { return FCoreStyle::GetDefaultFontStyle(bBold ? "Bold" : "Regular", Size); }
	FLinearColor Tint(daedalus::desktop::Color C) { return FLinearColor::FromSRGBColor(FColor(C.R, C.G, C.B, C.A)); }
	bool ValidPoint(daedalus::desktop::Vec P)
	{
		return FMath::IsFinite(P.X) && FMath::IsFinite(P.Y) && FMath::Abs(P.X) < 1000000.0 && FMath::Abs(P.Y) < 1000000.0;
	}
	bool CanvasTransform(const FGeometry& Geometry, const daedalus::desktop::Frame& Picture, FVector2f& LogicalSize, float& Scale, FVector2f& Offset)
	{
		if (!FMath::IsFinite(Picture.Width) || !FMath::IsFinite(Picture.Height) || Picture.Width <= 0 || Picture.Height <= 0
			|| Picture.Width > 10000 || Picture.Height > 10000) return false;
		const FVector2f LocalSize = Geometry.GetLocalSize();
		if (!FMath::IsFinite(LocalSize.X) || !FMath::IsFinite(LocalSize.Y) || LocalSize.X <= 0 || LocalSize.Y <= 0) return false;
		LogicalSize = FVector2f(static_cast<float>(Picture.Width), static_cast<float>(Picture.Height));
		Scale = FMath::Min(LocalSize.X / LogicalSize.X, LocalSize.Y / LogicalSize.Y);
		if (!FMath::IsFinite(Scale) || Scale <= 0.f) return false;
		Offset = (LocalSize - LogicalSize * Scale) * 0.5f;
		return true;
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
		virtual FReply OnMouseButtonDown(const FGeometry& Geometry, const FPointerEvent& Event) override
		{
			ADaedalusDesktopArcade* Actor = Game.Get();
			if (!Actor) return FReply::Unhandled();
			const FKey Key = Event.GetEffectingButton();
			const int32 Button = Key == EKeys::LeftMouseButton ? 0 : Key == EKeys::RightMouseButton ? 1 : Key == EKeys::MiddleMouseButton ? 2 : -1;
			if (Button < 0) return FReply::Unhandled();
			const auto& Picture = Actor->GetArcadeFrame();
			FVector2f LogicalSize, Offset; float Scale;
			if (!CanvasTransform(Geometry, Picture, LogicalSize, Scale, Offset)) return FReply::Unhandled();
			const FVector2D Local = Geometry.AbsoluteToLocal(Event.GetScreenSpacePosition());
			const double X = (Local.X - Offset.X) / Scale, Y = (Local.Y - Offset.Y) / Scale;
			if (X >= 0 && X < LogicalSize.X && Y >= 0 && Y < LogicalSize.Y) Actor->SubmitArcadeSourcePointerButton(X, Y, Button);
			// Bubble to the cabinet's existing focus handler; the canvas never traps keyboard focus.
			return FReply::Unhandled();
		}
		virtual FReply OnMouseButtonDoubleClick(const FGeometry& Geometry, const FPointerEvent& Event) override { return OnMouseButtonDown(Geometry, Event); }
		virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& Geometry, const FSlateRect& CullRect,
			FSlateWindowElementList& Elements, int32 LayerId, const FWidgetStyle& Style, bool bParentEnabled) const override
		{
			const ADaedalusDesktopArcade* Actor = Game.Get();
			if (!Actor) return LayerId;
			const daedalus::desktop::Frame& Picture = Actor->GetArcadeFrame();
			FVector2f LogicalSize, Offset; float Scale;
			if (!CanvasTransform(Geometry, Picture, LogicalSize, Scale, Offset)) return LayerId;
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
					State.Id == TEXT("minesweeper")
						? TEXT("PAUSED - P / Start: resume\nF5 / pad X: save board\nF9 / pad Y: continue saved board")
						: TEXT("PAUSED - P / Start or Resume to continue"), Font(24, true), ESlateDrawEffect::None, FLinearColor::White);
			}
			Elements.PopClip();
			return LayerId;
		}
	private:
		TWeakObjectPtr<ADaedalusDesktopArcade> Game;
	};
}

namespace DAUI = DesktopArcadeUI;

TSharedRef<SWidget> SDaedalusDesktopArcade::MakeForegroundHost(ULocalPlayer* Player, UGameViewportClient* Viewport, const TSharedRef<SWidget>& Content)
{
	TSharedRef<FNavigationMetaData> Boundary = MakeShared<FNavigationMetaData>();
	for (EUINavigation Direction : {EUINavigation::Up, EUINavigation::Down, EUINavigation::Left, EUINavigation::Right, EUINavigation::Next, EUINavigation::Previous})
		Boundary->SetNavigationStop(Direction);
	return SNew(DAUI::SForegroundPlayerHost).Player(Player).Viewport(Viewport).AddMetaData(Boundary)[Content];
}

void SDaedalusDesktopArcade::Construct(const FArguments& InArgs)
{
	Game = InArgs._Game;
	if (const ADaedalusDesktopArcade* Actor = Game.Get())
		for (const FDaedalusDesktopArcadeEntry& Entry : Actor->GetAvailableGames()) GameItems.Add(MakeShared<FString>(Entry.Id));
	ChildSlot
	[
		SNew(SOverlay)
		+ SOverlay::Slot()
		[
		SNew(SBorder).BorderImage(DAUI::WhiteBrush()).BorderBackgroundColor(FLinearColor(0.02f, 0.025f, 0.04f, 1.f)).Padding(12.f)
		.IsEnabled_Lambda([this]() { return !bGameHelpOpen; })
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().FillWidth(1.f).Padding(0.f, 0.f, 8.f, 0.f)
				[
					SAssignNew(CatalogSelector, SComboBox<TSharedPtr<FString>>).OptionsSource(&GameItems).IsFocusable(true)
					.EnableGamepadNavigationMode(true).MaxListHeight(300.f)
					.IsEnabled_Lambda([this]() { const ADaedalusDesktopArcade* Actor = Game.Get(); return Actor && !Actor->GetState().bSavePending; })
					.OnGenerateWidget(this, &SDaedalusDesktopArcade::MakeGameRow)
					.OnSelectionChanged(this, &SDaedalusDesktopArcade::SelectCatalogChoice)
					.OnComboBoxOpening_Lambda([this]() { SuspendForFocusLoss(); })
					[SNew(STextBlock).Text(this, &SDaedalusDesktopArcade::CatalogTitle).Font(DAUI::Font(18, true))]
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
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)
				[SNew(SButton).ContentPadding(FMargin(12.f, 6.f)).Text(FText::FromString(TEXT("Switch game")))
					.ToolTipText(FText::FromString(TEXT("Start a fresh run in the selected game. Existing saved runs are kept.")))
					.IsEnabled_Lambda([this]() { return CanSwitchGame(); }).OnClicked(this, &SDaedalusDesktopArcade::SwitchGame)]
				+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)
				[SNew(SButton).ContentPadding(FMargin(12.f, 6.f)).Text(FText::FromString(TEXT("Keep playing")))
					.IsEnabled_Lambda([this]() { const ADaedalusDesktopArcade* Actor = Game.Get(); return Actor && !Actor->GetState().bSavePending; })
					.OnClicked(this, &SDaedalusDesktopArcade::KeepPlaying)]
				+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)
				[SNew(SButton).Text(FText::FromString(TEXT("How to play"))).ContentPadding(FMargin(12.f, 6.f))
					.Visibility(this, &SDaedalusDesktopArcade::GameHelpVisibility)
					.OnClicked(this, &SDaedalusDesktopArcade::ShowGameHelp)]
				+ SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center).Padding(8.f, 0.f)
				[SNew(STextBlock).Text(this, &SDaedalusDesktopArcade::CurrentTitle).Font(DAUI::Font(14, true)).AutoWrapText(true)]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 6.f)
			[SNew(STextBlock).Text(this, &SDaedalusDesktopArcade::CatalogNoticeText).AutoWrapText(true)
				.Visibility_Lambda([this]() { const ADaedalusDesktopArcade* Actor = Game.Get(); return !CatalogError.IsEmpty() || (Actor && CatalogChoiceId != Actor->GetSelectedGameId()) ? EVisibility::Visible : EVisibility::Collapsed; })]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 6.f)
			[SNew(STextBlock).Text(this, &SDaedalusDesktopArcade::StatusText).Font(DAUI::Font(13)).AutoWrapText(true).ColorAndOpacity(FLinearColor(0.7f, 0.85f, 1.f))]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 6.f)
			[
				SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(8.f, 4.f)).Visibility(this, &SDaedalusDesktopArcade::PongVisibility)
				+ SWrapBox::Slot()[MakeMode(TEXT("pong"), TEXT("Match"), 0, TEXT("Changing mode starts over. Session best lasts until Restart or a mode change."))]
				+ SWrapBox::Slot()[MakeMode(TEXT("pong"), TEXT("Rally practice"), 1, TEXT("Changing mode starts over. Session best lasts until Restart or a mode change."))]
				+ SWrapBox::Slot()[MakeMode(TEXT("pong"), TEXT("First to 5"), 2, TEXT("Changing mode starts over. First to five points wins this short match."))]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 6.f)
			[
				SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(8.f, 4.f)).Visibility(this, &SDaedalusDesktopArcade::FootballVisibility)
				+ SWrapBox::Slot()[MakeMode(TEXT("football"), TEXT("Match"), 0, TEXT("Changing mode starts over. Target progress lasts until Restart or a mode change."))]
				+ SWrapBox::Slot()[MakeMode(TEXT("football"), TEXT("Target practice"), 1, TEXT("Changing mode starts over. Target progress lasts until Restart or a mode change."))]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 6.f)
			[
				SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(8.f, 4.f)).Visibility(this, &SDaedalusDesktopArcade::AsteroidsVisibility)
				+ SWrapBox::Slot()[MakeMode(TEXT("asteroids"), TEXT("Endless"), 0, TEXT("Changing mode starts over. Endless keeps the original wave progression."))]
				+ SWrapBox::Slot()[MakeMode(TEXT("asteroids"), TEXT("Three waves"), 1, TEXT("Changing mode starts over. Clear all rocks in the first three waves to finish the voyage."))]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 6.f)
			[
				SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(8.f, 4.f)).Visibility(this, &SDaedalusDesktopArcade::SegaVisibility)
				+ SWrapBox::Slot()[MakeMode(TEXT("sega_shooter"), TEXT("Full run"), 0, TEXT("Changing mode starts over. Full run reaches the boss at 1500 points."))]
				+ SWrapBox::Slot()[MakeMode(TEXT("sega_shooter"), TEXT("Boss rehearsal"), 1, TEXT("Changing mode starts over. Rehearsal starts the same boss immediately; regular enemies still arrive."))]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 6.f)
			[
				SNew(SHorizontalBox).Visibility(this, &SDaedalusDesktopArcade::DungeonVisibility)
				+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)
				[
					SNew(SButton).IsFocusable(true).ContentPadding(FMargin(10.f, 4.f))
					.Text(FText::FromString(TEXT("Next circuit")))
					.ToolTipText(FText::FromString(TEXT("Start the next lantern order, clearing this circuit's progress. Restart replays the current order.")))
					.IsEnabled_Lambda([this]() { const ADaedalusDesktopArcade* Actor = Game.Get(); return Actor && Actor->GetSelectedGameId() == TEXT("dungeon") && !Actor->GetState().bSavePending; })
					.OnClicked(this, &SDaedalusDesktopArcade::NextCircuit)
				]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 6.f)
			[
				SNew(SHorizontalBox).Visibility(this, &SDaedalusDesktopArcade::StarVisibility)
				+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)
				[
					SNew(SButton).IsFocusable(true).ContentPadding(FMargin(10.f, 4.f))
					.IsEnabled_Lambda([this]() { const ADaedalusDesktopArcade* Actor = Game.Get(); return Actor && Actor->GetState().bHasSavedRun && !Actor->GetState().bSavePending; })
					.OnClicked_Lambda([this]() { if (ADaedalusDesktopArcade* Actor = Game.Get()) Actor->ResumeGame(); SyncSelection(); return FocusReply(); })
					[SNew(STextBlock).Text(FText::FromString(TEXT("Continue saved Star run")))]
				]
				+ SHorizontalBox::Slot().AutoWidth().Padding(6.f, 2.f)
				[SNew(STextBlock).Text(FText::FromString(TEXT("New run:"))).Font(DAUI::Font(13))]
				+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)
				[MakeAction(TEXT("Easy"), FSimpleDelegate::CreateLambda([this]() { if (ADaedalusDesktopArcade* Actor = Game.Get()) Actor->SetGameOption(0); }), true, true)]
				+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)
				[MakeAction(TEXT("Medium"), FSimpleDelegate::CreateLambda([this]() { if (ADaedalusDesktopArcade* Actor = Game.Get()) Actor->SetGameOption(1); }), true, true)]
				+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)
				[MakeAction(TEXT("Hard"), FSimpleDelegate::CreateLambda([this]() { if (ADaedalusDesktopArcade* Actor = Game.Get()) Actor->SetGameOption(2); }), true, true)]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 6.f)
			[
				SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(4.f, 4.f)).Visibility(this, &SDaedalusDesktopArcade::MinesweeperVisibility)
				+ SWrapBox::Slot()
				[MakeAction(TEXT("Save board"), FSimpleDelegate::CreateLambda([this]() { if (ADaedalusDesktopArcade* Actor = Game.Get()) Actor->SaveGame(); }), false, true)]
				+ SWrapBox::Slot()
				[
					SNew(SButton).IsFocusable(true).ContentPadding(FMargin(12.f, 6.f))
					.ToolTipText(FText::FromString(TEXT("Replace the current board with the last saved Minesweeper board.")))
					.IsEnabled_Lambda([this]() { const ADaedalusDesktopArcade* Actor = Game.Get(); return Actor && Actor->GetState().bHasSavedRun; })
					.OnClicked_Lambda([this]() { if (ADaedalusDesktopArcade* Actor = Game.Get()) Actor->ResumeGame(); return FocusReply(); })
					[SNew(STextBlock).Text(FText::FromString(TEXT("Continue saved board")))]
				]
				+ SWrapBox::Slot()
				[MakeAction(TEXT("Save & Close"), FSimpleDelegate::CreateLambda([this]()
				{
					if (ADaedalusDesktopArcade* Actor = Game.Get()) if (Actor->SaveGame()) Actor->CloseArcade();
				}), false, true)]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 6.f)
			[
				SNew(SVerticalBox).Visibility(this, &SDaedalusDesktopArcade::MinesweeperVisibility)
				+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 4.f)
				[SNew(STextBlock).Text(this, &SDaedalusDesktopArcade::MinesweeperDifficultyText).AutoWrapText(true)]
				+ SVerticalBox::Slot().AutoHeight()
				[
					SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(4.f, 4.f))
					+ SWrapBox::Slot()
					[MakeAction(TEXT("New puzzle"), FSimpleDelegate::CreateLambda([this]()
					{ if (ADaedalusDesktopArcade* Actor = Game.Get()) Actor->NewMinesweeperPuzzle(); }), true, true)]
					+ SWrapBox::Slot()
					[MakeAction(TEXT("9 x 9 / 10 mines"), FSimpleDelegate::CreateLambda([this]()
					{ if (ADaedalusDesktopArcade* Actor = Game.Get()) if (Actor->GetSelectedGameId() == TEXT("minesweeper")) Actor->SetGameOption(0); }), true, true)]
					+ SWrapBox::Slot()
					[MakeAction(TEXT("16 x 16 / 40 mines"), FSimpleDelegate::CreateLambda([this]()
					{ if (ADaedalusDesktopArcade* Actor = Game.Get()) if (Actor->GetSelectedGameId() == TEXT("minesweeper")) Actor->SetGameOption(1); }), true, true)]
					+ SWrapBox::Slot()
					[MakeAction(TEXT("30 x 16 / 99 mines"), FSimpleDelegate::CreateLambda([this]()
					{ if (ADaedalusDesktopArcade* Actor = Game.Get()) if (Actor->GetSelectedGameId() == TEXT("minesweeper")) Actor->SetGameOption(2); }), true, true)]
				]
				+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f, 0.f, 0.f)
				[SNew(STextBlock).Text(FText::FromString(TEXT("New puzzle and size changes replace this board. Save first to keep progress. The saved board stays unchanged."))).AutoWrapText(true)]
			]
			+ SVerticalBox::Slot().FillHeight(1.f)
			[SNew(DAUI::SGameCanvas).Game(Game)]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 6.f, 0.f, 0.f)
			[SNew(STextBlock).Text(this, &SDaedalusDesktopArcade::LeaderboardText).Visibility(this, &SDaedalusDesktopArcade::LeaderboardVisibility)
				.Font(DAUI::Font(13)).AutoWrapText(true).ColorAndOpacity(FLinearColor(1.f, 0.85f, 0.45f))]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 6.f, 0.f, 0.f)
			[SNew(STextBlock).Text(this, &SDaedalusDesktopArcade::ControlText).Font(DAUI::Font(12)).AutoWrapText(true).ColorAndOpacity(FLinearColor(0.7f, 0.75f, 0.8f))]
		]
		]
		+ SOverlay::Slot()[GameHelpPanel()]
	];
	SyncSelection();
	CoreTickHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateSP(this, &SDaedalusDesktopArcade::CoreTick));
}

SDaedalusDesktopArcade::~SDaedalusDesktopArcade()
{
	FTSTicker::GetCoreTicker().RemoveTicker(CoreTickHandle);
}

TSharedRef<SWidget> SDaedalusDesktopArcade::GameHelpPanel()
{
	return SNew(SBorder).Padding(20.f).BorderImage(DAUI::WhiteBrush())
		.BorderBackgroundColor(FLinearColor(0.025f, 0.04f, 0.08f, 1.f))
		.Visibility_Lambda([this]() { return bGameHelpOpen ? EVisibility::Visible : EVisibility::Collapsed; })
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
			[SNew(STextBlock).Text(this, &SDaedalusDesktopArcade::GameHelpTitle).Font(DAUI::Font(26, true)).AutoWrapText(true)]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
			[SNew(STextBlock).Text(this, &SDaedalusDesktopArcade::GameHelpNotice).Font(DAUI::Font(16)).AutoWrapText(true)
				.ColorAndOpacity(FLinearColor(1.f, 0.85f, 0.45f))
				.Visibility_Lambda([this]() { return GameHelpNotice().IsEmpty() ? EVisibility::Collapsed : EVisibility::Visible; })]
			+ SVerticalBox::Slot().FillHeight(1.f)
			[
				SAssignNew(GameHelpScroll, SScrollBox)
				+ SScrollBox::Slot()
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 14.f)
					[SNew(STextBlock).Font(DAUI::Font(18)).AutoWrapText(true).Text(this, &SDaedalusDesktopArcade::GameHelpIntro)]
					+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 14.f)
					[SNew(STextBlock).Text(this, &SDaedalusDesktopArcade::ControlText).Font(DAUI::Font(18)).AutoWrapText(true)]
					+ SVerticalBox::Slot().AutoHeight()
					[SNew(STextBlock).Font(DAUI::Font(18)).AutoWrapText(true).Text(this, &SDaedalusDesktopArcade::GameHelpProgress)]
				]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 10.f, 0.f, 6.f)
			[
				SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(8.f, 6.f))
				+ SWrapBox::Slot()
				[SAssignNew(GameHelpResume, SButton).Text(FText::FromString(TEXT("Resume game"))).ContentPadding(FMargin(16.f, 8.f))
					.IsEnabled(this, &SDaedalusDesktopArcade::CanResumeGameHelp)
					.OnClicked_Lambda([this]() { return DismissGameHelp(true); })]
				+ SWrapBox::Slot()
				[SAssignNew(GameHelpReturn, SButton).Text(FText::FromString(TEXT("Return paused"))).ContentPadding(FMargin(16.f, 8.f))
					.OnClicked_Lambda([this]() { return DismissGameHelp(false); })]
			]
			+ SVerticalBox::Slot().AutoHeight()
			[SNew(STextBlock).Font(DAUI::Font(14)).AutoWrapText(true).Text(FText::FromString(TEXT(
				"Help keeps this run paused. Page Up/Down or LB/RB: scroll. F1 / left-stick click, Esc / Back or pad B: return paused.")))]
		];
}

FReply SDaedalusDesktopArcade::FocusGameHelp()
{
	const auto Target = GameHelpResume.IsValid() && GameHelpResume->IsEnabled() ? GameHelpResume : GameHelpReturn;
	return Target.IsValid() ? FReply::Handled().SetUserFocus(Target.ToSharedRef(), EFocusCause::SetDirectly) : FReply::Handled();
}

FReply SDaedalusDesktopArcade::ShowGameHelp()
{
	ADaedalusDesktopArcade* Actor = Game.Get();
	if (!Actor || !HasGameHelp()) return FReply::Handled();
	HelpGameId = Actor->GetSelectedGameId();
	SuspendForFocusLoss();
	if (CatalogSelector.IsValid()) CatalogSelector->SetIsOpen(false, false, Actor->GetArcadeSlateUserIndex());
	bGameHelpOpen = true;
	if (GameHelpScroll.IsValid()) GameHelpScroll->ScrollToStart();
	return FocusGameHelp();
}

bool SDaedalusDesktopArcade::CanResumeGameHelp() const
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	if (!bGameHelpOpen || !Actor) return false;
	const auto State = Actor->GetState();
	// Dodge results continue between rounds; resume the retained scorecard, without confirming it.
	return State.Id == HelpGameId && !State.bSavePending && (!State.bOver || State.Id == TEXT("dodge_ball"));
}

FReply SDaedalusDesktopArcade::DismissGameHelp(bool bResume)
{
	if (bResume && !CanResumeGameHelp()) return FReply::Handled();
	SuspendForFocusLoss();
	bGameHelpOpen = false;
	HelpGameId.Empty();
	if (bResume) if (ADaedalusDesktopArcade* Actor = Game.Get()) Actor->PauseGame(false);
	return FocusReply();
}

FReply SDaedalusDesktopArcade::ScrollGameHelp(float Delta)
{
	if (GameHelpScroll.IsValid()) GameHelpScroll->SetScrollOffset(FMath::Clamp(
		GameHelpScroll->GetScrollOffset() + Delta, 0.f, FMath::Max(0.f, GameHelpScroll->GetScrollOffsetOfEnd())));
	return FReply::Handled();
}

bool SDaedalusDesktopArcade::HasGameHelp() const
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	if (!Actor) return false;
	const FString Id = Actor->GetSelectedGameId();
	return Id == TEXT("minesweeper") || Id == TEXT("star_shooter") || Id == TEXT("dodge_ball");
}

EVisibility SDaedalusDesktopArcade::GameHelpVisibility() const { return HasGameHelp() ? EVisibility::Visible : EVisibility::Collapsed; }

FText SDaedalusDesktopArcade::GameHelpTitle() const
{
	if (HelpGameId == TEXT("dodge_ball")) return FText::FromString(TEXT("Courtyard Clash — How to play"));
	return FText::FromString(HelpGameId == TEXT("minesweeper") ? TEXT("Minesweeper — How to play") : TEXT("Star Shooter — How to play"));
}

FText SDaedalusDesktopArcade::GameHelpIntro() const
{
	if (HelpGameId == TEXT("minesweeper")) return FText::FromString(TEXT(
		"YOUR GOAL\nReveal every cell that has no mine. Flags are optional reminders; marking all mines alone does not finish the board.\n\n"
		"A SAFE START\nChoose any covered cell and reveal it. Your first reveal and its neighbours are mine-free. An empty cell opens the connected empty area and its safe numbered border; flags block that reveal.\n\n"
		"READ THE NUMBERS\nA number counts mines in the cells touching it, including diagonals: up to eight neighbours. Use nearby numbers together to decide which covered cells are safe.\n\n"
		"FLAGS AND CHORDING\nFlag a suspected mine; right-click again to remove a flag. A wrongly flagged safe cell must be unflagged and revealed to finish. Mines remaining is the total mine count minus your flags, so it can be negative and does not confirm that your flags are correct.\n\n"
		"On an open number, a chord reveals the unflagged neighbours when the neighbouring flag count matches that number. A wrong flag can make this hit a mine. You can reveal cells individually instead.\n\n"
		"CONTROLS IN THE GAME"));
	if (HelpGameId == TEXT("dodge_ball")) return FText::FromString(TEXT(
		"YOUR TEAM\nMove and jump all three living teammates together. Approach a loose ball to pick it up. A throw aims at the nearest living opponent; the small brackets and C1/C2/C3 cue show the current target.\n\n"
		"THROW AND CATCH\nSpace/Z/J or pad A throws. Holding it also catches a nearby incoming ball and can immediately rethrow when ready. Pad X/RB throws only on a fresh press. Shift / pad B jumps; an airborne teammate catches automatically when a ball comes close.\n\n"
		"CHARGE A SUPER\nWhile carrying the ball, hold W/Up or push the left stick up to build charge, then throw. Charge past halfway for your country's super throw. These inputs also move the team. D-pad Up moves without charging; it can be combined with stick Up to charge. Country supers can change the throw angle.\n\n"
		"WATCH YOUR TEAM\nFriendly hits are possible. Normal hits cost one health; super hits cost two. A teammate with no health sits out for the rest of the match.\n\n"
		"CONTROLS IN THE GAME"));
	return FText::FromString(TEXT(
		"YOUR GOAL\nSurvive successive waves and build your score. Keep moving to avoid enemy fire. Bosses arrive on every fifth wave; the run ends when your lives run out.\n\n"
		"UPGRADES\nCollect Triple, Shield and Speed pickups. A shield absorbs one hit. Triple shot and speed last until a boss is defeated or a new run starts.\n\n"
		"CONTROLS IN THE GAME"));
}

FText SDaedalusDesktopArcade::GameHelpProgress() const
{
	if (HelpGameId == TEXT("minesweeper")) return FText::FromString(TEXT(
		"KEEP YOUR BOARD\nSave board / F5 keeps one local saved board. Continue saved board / F9 replaces the current board with that save, including its flags, selected cell, size, active timer and seed. Continue adds no time spent away. While paused, pad X saves and pad Y continues.\n\n"
		"Save & Close leaves the cabinet open if writing fails. New puzzle chooses a fresh seed at the current size. Restart keeps the current size and seed; choosing a different first cell can change the mine layout. Close, Restart, New puzzle and size changes keep the saved board unchanged. Save first before starting another board if you want to keep this progress.\n\n"
		"To reach cabinet buttons, return paused, press F2 / right-stick click, then close the catalog list and navigate the controls.\n\n"
		"AFTER A RESULT\nA mine hit ends the board; revealing every safe cell wins. Return paused keeps the result paused. Then R / Restart retries at the current size and seed. For pad A replay, use P / Start to show the result first, then press pad A freshly. To save the finished board before retrying, return paused and use F5 / pad X."));
	if (HelpGameId == TEXT("dodge_ball")) return FText::FromString(TEXT(
		"FOUR ROUNDS\nChoose a country with keys, D-pad or stick flicks, then confirm. Knock out the other team to win a match. All four matches count toward the tournament result; random opponents can repeat.\n\n"
		"BETWEEN MATCHES\nA fresh throw, confirm or jump press starts the next round. After round four, the scorecard shows the overall win, loss or draw. Continue returns to the title; confirming a country starts a fresh tournament. R / Restart clears the tournament.\n\n"
		"RETURN TO PLAY\nHelp pauses this match or result. Resume game returns to the same screen; a result still needs a fresh continuation press. Return paused keeps it paused. F1 / left-stick click opens this guide again."));
	return FText::FromString(TEXT(
		"KEEP YOUR RUN\nIn the game, P / Start opens the pause menu. Select Save & Quit with Up/Down, then confirm with Space / pad A or J / pad X. Save warnings appear here too; a pending save keeps Resume unavailable.\n\n"
		"Continue saved Star run restores your saved score, wave, lives and upgrades. The arena, position and timers start fresh. To reach cabinet buttons, return paused, press F2 / right-stick click, then close the catalog list and navigate the controls. Restart and difficulty buttons start a new run while keeping the previous saved run.\n\n"
		"AFTER GAME OVER\nReturn to the result, then use a fresh pad A / Start or R / Restart to retry at the current difficulty."));
}

FText SDaedalusDesktopArcade::GameHelpNotice() const
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	if (!Actor) return FText::GetEmpty();
	const auto State = Actor->GetState();
	const FString Pending = State.bSavePending ? TEXT("A save is pending. Resume is unavailable while it is pending.\n") : TEXT("");
	return FText::FromString(Pending + State.PersistenceMessage);
}

TSharedRef<SWidget> SDaedalusDesktopArcade::MakeAction(const TCHAR* Label, FSimpleDelegate Action, bool bReplacesRun, bool bFocusable)
{
	return SNew(SButton).IsFocusable(bFocusable).ContentPadding(FMargin(12.f, 6.f))
		.IsEnabled_Lambda([this, bReplacesRun]() { const ADaedalusDesktopArcade* Actor = Game.Get(); return Actor && (!bReplacesRun || !Actor->GetState().bSavePending); })
		.OnClicked_Lambda([this, Action]() { Action.ExecuteIfBound(); return FocusReply(); })
		[SNew(STextBlock).Text(FText::FromString(Label))];
}

TSharedRef<SWidget> SDaedalusDesktopArcade::MakeMode(const TCHAR* GameId, const TCHAR* Label, int32 Option, const TCHAR* Warning)
{
	const FString Id(GameId);
	return SNew(SCheckBox).IsFocusable(true)
		.Style(&FCoreStyle::Get().GetWidgetStyle<FCheckBoxStyle>("ToggleButtonCheckbox"))
		.ToolTipText(FText::FromString(Warning))
		.IsEnabled_Lambda([this]() { const ADaedalusDesktopArcade* Actor = Game.Get(); return Actor && !Actor->GetState().bSavePending; })
		.IsChecked_Lambda([this, Id, Option]() { const ADaedalusDesktopArcade* Actor = Game.Get();
			return Actor && Actor->GetSelectedGameId() == Id && Actor->GetGameOption() == Option ? ECheckBoxState::Checked : ECheckBoxState::Unchecked; })
		.OnCheckStateChanged_Lambda([this, Id, Option](ECheckBoxState State)
		{
			if (State != ECheckBoxState::Checked) return;
			if (ADaedalusDesktopArcade* Actor = Game.Get())
				if (Actor->GetSelectedGameId() == Id && Actor->GetGameOption() != Option && Actor->SetGameOption(Option)) FocusGame();
		})
		[SNew(STextBlock).Text(FText::FromString(Label)).Font(DAUI::Font(18))];
}

TSharedRef<SWidget> SDaedalusDesktopArcade::MakeGameRow(TSharedPtr<FString> Item) const
{
	FString Label = Item.IsValid() ? *Item : FString();
	if (const ADaedalusDesktopArcade* Actor = Game.Get())
		for (const FDaedalusDesktopArcadeEntry& Entry : Actor->GetAvailableGames()) if (Entry.Id == Label) { Label = Entry.Title; break; }
	return SNew(STextBlock).Text(FText::FromString(Label)).Font(DAUI::Font(15));
}

void SDaedalusDesktopArcade::SelectCatalogChoice(TSharedPtr<FString> Item, ESelectInfo::Type Selection)
{
	if (Selection == ESelectInfo::Direct || !Item.IsValid()) return;
	if (!GameItems.Contains(Item)) return;
	// Highlighting or accepting a catalog row only drafts a choice; it never replaces the run.
	SuspendForFocusLoss();
	CatalogChoiceId = *Item;
	CatalogError.Reset();
}

bool SDaedalusDesktopArcade::CanSwitchGame() const
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	return Actor && !Actor->GetState().bSavePending && CatalogChoiceId != Actor->GetSelectedGameId()
		&& GameItems.ContainsByPredicate([this](const TSharedPtr<FString>& Item) { return Item.IsValid() && *Item == CatalogChoiceId; });
}

FReply SDaedalusDesktopArcade::BrowseCatalog()
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	if (Actor && !Actor->GetState().bSavePending && CatalogSelector.IsValid() && CatalogSelector->IsEnabled() && FSlateApplication::IsInitialized()
		&& Actor->GetArcadeSlateUserIndex() != INDEX_NONE)
	{
		SuspendForFocusLoss();
		FSlateApplication::Get().SetUserFocus(Actor->GetArcadeSlateUserIndex(), CatalogSelector, EFocusCause::Navigation);
		CatalogSelector->SetIsOpen(true, true, Actor->GetArcadeSlateUserIndex());
	}
	return FReply::Handled();
}

FReply SDaedalusDesktopArcade::SwitchGame()
{
	ADaedalusDesktopArcade* Actor = Game.Get();
	if (Actor && CanSwitchGame())
	{
		SuspendForFocusLoss();
		if (Actor->StartGame(CatalogChoiceId, Actor->GetState().Seed))
		{
			SyncSelection();
			return FocusReply();
		}
		CatalogError = TEXT("The selected game could not start. Your current run was kept.");
	}
	return FReply::Handled();
}

FReply SDaedalusDesktopArcade::KeepPlaying()
{
	if (ADaedalusDesktopArcade* Actor = Game.Get())
	{
		if (Actor->GetState().bSavePending) return FReply::Handled();
		ResetCatalogChoice();
		ResetHeldInput();
		Actor->PauseGame(false);
		return FocusReply();
	}
	return FReply::Handled();
}

FReply SDaedalusDesktopArcade::NextCircuit()
{
	if (ADaedalusDesktopArcade* Actor = Game.Get())
	{
		const FDaedalusDesktopArcadeState State = Actor->GetState();
		if (State.Id != TEXT("dungeon") || State.bSavePending) return FReply::Handled();
		const std::uint32_t Seed = daedalus::desktop::DungeonGame::NextCircuitSeed(static_cast<std::uint32_t>(State.Seed));
		if (Actor->StartGame(TEXT("dungeon"), static_cast<int32>(Seed)))
		{
			CatalogError.Reset();
			return FocusReply();
		}
		CatalogError = TEXT("The next circuit could not start. Your current circuit was kept.");
	}
	return FReply::Handled();
}

void SDaedalusDesktopArcade::ResetCatalogChoice()
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	if (!Actor || !CatalogSelector.IsValid()) return;
	CatalogChoiceId = Actor->GetSelectedGameId();
	CatalogError.Reset();
	for (const TSharedPtr<FString>& Item : GameItems)
		if (Item.IsValid() && *Item == CatalogChoiceId) { CatalogSelector->SetSelectedItem(Item); break; }
}

void SDaedalusDesktopArcade::SyncSelection()
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	if (!Actor || !CatalogSelector.IsValid()) return;
	const FString Id = Actor->GetSelectedGameId();
	if (Id == LastGameId) return;
	LastGameId = Id;
	ResetHeldInput();
	ResetCatalogChoice();
}

FText SDaedalusDesktopArcade::CurrentTitle() const
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	return FText::FromString(Actor ? TEXT("Current game: ") + Actor->GetState().Title : TEXT("Desktop Arcade unavailable"));
}

FText SDaedalusDesktopArcade::CatalogTitle() const
{
	if (const ADaedalusDesktopArcade* Actor = Game.Get())
		for (const FDaedalusDesktopArcadeEntry& Entry : Actor->GetAvailableGames())
			if (Entry.Id == CatalogChoiceId) return FText::FromString(Entry.Title);
	return FText::FromString(TEXT("Choose a game"));
}

FText SDaedalusDesktopArcade::CatalogNoticeText() const
{
	return FText::FromString(CatalogError.IsEmpty() ? TEXT("Switch game replaces the current run.") : CatalogError);
}

FText SDaedalusDesktopArcade::StatusText() const
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	if (!Actor) return FText::FromString(TEXT("Arcade unavailable."));
	const FDaedalusDesktopArcadeState State = Actor->GetState();
	FString Text = State.Id == TEXT("minesweeper") ? State.Note
		: FString::Printf(TEXT("Score %lld   Lives / health %d   Seed %d   %s"), State.Score, State.Lives, State.Seed, *State.Note);
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

EVisibility SDaedalusDesktopArcade::MinesweeperVisibility() const
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	return Actor && Actor->GetSelectedGameId() == TEXT("minesweeper") ? EVisibility::Visible : EVisibility::Collapsed;
}

FText SDaedalusDesktopArcade::MinesweeperDifficultyText() const
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	if (!Actor || Actor->GetSelectedGameId() != TEXT("minesweeper")) return FText::GetEmpty();
	const int32 Option = Actor->GetState().Option;
	const TCHAR* Board = Option == 0 ? TEXT("9 x 9 / 10 mines") : Option == 1 ? TEXT("16 x 16 / 40 mines")
		: Option == 2 ? TEXT("30 x 16 / 99 mines") : TEXT("unavailable");
	return FText::FromString(FString::Printf(TEXT("Current board: %s"), Board));
}

EVisibility SDaedalusDesktopArcade::PongVisibility() const
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	return Actor && Actor->GetSelectedGameId() == TEXT("pong") ? EVisibility::Visible : EVisibility::Collapsed;
}

EVisibility SDaedalusDesktopArcade::FootballVisibility() const
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	return Actor && Actor->GetSelectedGameId() == TEXT("football") ? EVisibility::Visible : EVisibility::Collapsed;
}

EVisibility SDaedalusDesktopArcade::DungeonVisibility() const
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	return Actor && Actor->GetSelectedGameId() == TEXT("dungeon") ? EVisibility::Visible : EVisibility::Collapsed;
}

EVisibility SDaedalusDesktopArcade::SegaVisibility() const
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	return Actor && Actor->GetSelectedGameId() == TEXT("sega_shooter") ? EVisibility::Visible : EVisibility::Collapsed;
}

EVisibility SDaedalusDesktopArcade::AsteroidsVisibility() const
{
	const ADaedalusDesktopArcade* Actor = Game.Get();
	return Actor && Actor->GetSelectedGameId() == TEXT("asteroids") ? EVisibility::Visible : EVisibility::Collapsed;
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
	FString Text = Id == TEXT("pong")
		? TEXT("Up/Down, W/S, D-pad or left stick: paddle. P / Start: pause. F2 / right-stick click: choose game. R: restart. Esc / Back: close. ")
		: TEXT("Move: WASD / arrows, D-pad or left stick. P / Start: pause. F2 / right-stick click: choose game. R: restart. Esc / Back: close. ");
	if (Id == TEXT("minesweeper")) Text += TEXT("F1 / left-stick click: How to play. Mouse left: reveal; right: flag; middle: open around a number when its flags match. J/Space or pad A/X: reveal. K/Enter or pad B: flag. Shift or pad Y/LB: open around a number when its flags match. F5: save board. F9: continue saved board. When paused, pad X saves and pad Y continues the saved board. Close leaves the save unchanged.");
	else if (Id == TEXT("dungeon")) Text += TEXT("J/Space or pad A/X: light. Shift or pad Y/LB: trail. K/Enter or pad B: reset the circuit.");
	else if (Id == TEXT("dodge_ball")) Text += TEXT("Space/Z/J or pad A: throw/catch; pad X/RB: throw press only; Shift/pad B: jump; Up: charge; K/Enter: confirm.");
	else if (Id == TEXT("shadow_ninja")) Text += TEXT("Space/A: jump; J/Z/X or pad B/X: sword; K/C or pad Y/RB: star; Shift/V or LB: spin; Up/Down: climb.");
	else if (Id == TEXT("contra")) Text += TEXT("Enter/Space or pad A: title start; literal arrow keys then B,A: source code. Space/W or pad A: jump; J/Z/Ctrl/X/RT: shoot; Down: crouch. Enter/R or pad A/Start: terminal retry.");
	else if (Id == TEXT("star_shooter")) Text += TEXT("F1 / left-stick click: How to play. Space/J/Z/X/RT: shoot; source pause menu Up/Down: select, J/X or Space/A: confirm, Shift/Y: resume. Game over: fresh pad A/Start or R/Restart retries. Difficulty buttons start a new run.");
	else if (Id == TEXT("asteroids") || Id == TEXT("sega_shooter")) Text += Id == TEXT("asteroids")
		? TEXT("Left/Right: turn; Up: thrust; hold K / left trigger: brake. Space/J/Z or pad face/bumper: shoot.")
		: TEXT("Space/J/Z or pad face/bumper: shoot.");
	else if (Id == TEXT("pong")) Text += TEXT("Move at impact to add spin. Space / pad A or J / pad X: serve early.");
	else if (Id == TEXT("football")) Text += TEXT("Space/J/Z or pad A/X: kick. Target practice: move around the ball to aim. During a shot, K/Enter or pad B sets it up again.");
	else Text += TEXT("J/Z/X: fire/sword, Space/A: jump/confirm, K/B/Enter: action. Source title screens use the cabinet launcher.");
	return FText::FromString(Text);
}

void SDaedalusDesktopArcade::ResetHeldInput()
{
	HeldKeys.Reset(); PreviousInput = {}; StickX = 0.f; StickY = 0.f; RightTrigger = 0.f; LeftTrigger = 0.f;
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
	if (bGameHelpOpen)
	{
		if (Actor->GetSelectedGameId() != HelpGameId)
		{
			const bool bRestoreFocus = FSlateApplication::IsInitialized() && FSlateApplication::Get().IsActive() && OwnsUserFocus(UserIndex);
			DismissGameHelp(false);
			if (bRestoreFocus) FocusGame(); // CoreTick does not dispatch the returned FReply.
		}
		else if (!Actor->GetState().bPaused) SuspendForFocusLoss();
	}
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
	if (bGameHelpOpen) return;
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
		if (Id == TEXT("asteroids"))
		{
			// B remains a fire button. Only the dedicated brake controls set Action here.
			Input.Action = Held(EKeys::K) || Held(EKeys::Gamepad_LeftTrigger) || LeftTrigger > 0.5f;
			bActionEdge = PressedKey == EKeys::K || PressedKey == EKeys::Gamepad_LeftTrigger;
		}
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

FReply SDaedalusDesktopArcade::OnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
	// A fire/accept key held before help opened must not press its newly focused button.
	if (bGameHelpOpen && Event.IsRepeat() && FSlateApplication::IsInitialized()
		&& FSlateApplication::Get().GetNavigationActionFromKey(Event) == EUINavigationAction::Accept)
		return FReply::Handled();
	return SCompoundWidget::OnPreviewKeyDown(Geometry, Event);
}

FReply SDaedalusDesktopArcade::OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
	const FKey Key = Event.GetKey();
	if (bGameHelpOpen)
	{
		if (Key == EKeys::Escape || Key == EKeys::Gamepad_Special_Left || Key == EKeys::Gamepad_FaceButton_Right
			|| Key == EKeys::F1 || Key == EKeys::Gamepad_LeftThumbstick)
			return Event.IsRepeat() ? FReply::Handled() : DismissGameHelp(false);
		if (Key == EKeys::PageUp || Key == EKeys::Gamepad_LeftShoulder) return ScrollGameHelp(-160.f);
		if (Key == EKeys::PageDown || Key == EKeys::Gamepad_RightShoulder) return ScrollGameHelp(160.f);
		return FReply::Unhandled(); // Native navigation remains inside the enabled help panel.
	}
	if (Key == EKeys::Escape || Key == EKeys::Gamepad_Special_Left)
	{
		if (!Event.IsRepeat())
		{
			if (CatalogSelector.IsValid() && CatalogSelector->IsOpen())
			{
				CatalogSelector->SetIsOpen(false, false, Event.GetUserIndex());
				if (FSlateApplication::IsInitialized() && CatalogSelector->IsEnabled())
					FSlateApplication::Get().SetUserFocus(Event.GetUserIndex(), CatalogSelector, EFocusCause::Navigation);
			}
			else if (ADaedalusDesktopArcade* Actor = Game.Get()) Actor->CloseArcade();
		}
		return FReply::Handled();
	}
	// Focused native catalog/buttons own their input, including Star's paused menu keys.
	if (!HasUserFocus(Event.GetUserIndex()).IsSet()) return FReply::Unhandled();
	if ((Key == EKeys::F1 || Key == EKeys::Gamepad_LeftThumbstick) && HasGameHelp())
		return Event.IsRepeat() ? FReply::Handled() : ShowGameHelp();
	if (Key == EKeys::F2 || Key == EKeys::Gamepad_RightThumbstick)
		return Event.IsRepeat() ? FReply::Handled() : BrowseCatalog();
	if (!Event.IsRepeat())
	{
		if (ADaedalusDesktopArcade* Actor = Game.Get())
		{
			const FDaedalusDesktopArcadeState State = Actor->GetState();
			if (State.Id == TEXT("star_shooter") && State.bOver
				&& (Key == EKeys::Gamepad_FaceButton_Bottom || Key == EKeys::Gamepad_Special_Right))
			{
				// Use the existing host restart: it owns the save fence, score submission and input cleanup.
				Actor->RestartGame();
				return FReply::Handled();
			}
			if (State.Id == TEXT("minesweeper"))
			{
				if (Key == EKeys::F5 || (State.bPaused && Key == EKeys::Gamepad_FaceButton_Left))
				{ Actor->SaveGame(); return FReply::Handled(); }
				if (Key == EKeys::F9 || (State.bPaused && Key == EKeys::Gamepad_FaceButton_Top))
				{ Actor->ResumeGame(); return FReply::Handled(); }
			}
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
			if (Key == EKeys::P || Key == EKeys::Gamepad_Special_Right) { Actor->PauseGame(!Actor->GetState().bPaused); return FReply::Handled(); }
			if (Key == EKeys::R) { Actor->RestartGame(); return FReply::Handled(); }
		}
		HeldKeys.Add(Key); PushInput(Key);
	}
	return FReply::Handled();
}

FReply SDaedalusDesktopArcade::OnKeyUp(const FGeometry& Geometry, const FKeyEvent& Event)
{
	if (bGameHelpOpen) return FReply::Unhandled();
	if (!HasUserFocus(Event.GetUserIndex()).IsSet()) return FReply::Unhandled();
	HeldKeys.Remove(Event.GetKey()); PushInput();
	return FReply::Handled();
}

FReply SDaedalusDesktopArcade::OnAnalogValueChanged(const FGeometry& Geometry, const FAnalogInputEvent& Event)
{
	if (bGameHelpOpen) return FReply::Unhandled();
	if (!HasUserFocus(Event.GetUserIndex()).IsSet()) return FReply::Unhandled();
	const float Value = FMath::IsFinite(Event.GetAnalogValue()) ? FMath::Clamp(Event.GetAnalogValue(), -1.f, 1.f) : 0.f;
	if (Event.GetKey() == EKeys::Gamepad_LeftX) StickX = Value;
	else if (Event.GetKey() == EKeys::Gamepad_LeftY) StickY = -Value;
	else if (Event.GetKey() == EKeys::Gamepad_RightTriggerAxis) RightTrigger = FMath::Max(0.f, Value);
	else if (Event.GetKey() == EKeys::Gamepad_LeftTriggerAxis) LeftTrigger = FMath::Max(0.f, Value);
	else return FReply::Handled();
	PushInput();
	return FReply::Handled();
}

FReply SDaedalusDesktopArcade::OnMouseButtonDown(const FGeometry& Geometry, const FPointerEvent& Event) { return bGameHelpOpen ? FocusGameHelp() : FocusReply(); }
FNavigationReply SDaedalusDesktopArcade::OnNavigation(const FGeometry& Geometry, const FNavigationEvent& Event)
{
	return !bGameHelpOpen && HasUserFocus(Event.GetUserIndex()).IsSet() ? FNavigationReply::Stop() : SCompoundWidget::OnNavigation(Geometry, Event);
}

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
