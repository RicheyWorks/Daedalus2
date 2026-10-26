// SPDX-License-Identifier: MIT

#include "SDaedalusMinesweeper.h"

#include "DaedalusMinesweeper.h"
#include "Brushes/SlateColorBrush.h"
#include "InputCoreTypes.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Layout/SUniformGridPanel.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

namespace DaedalusMinesweeperUI
{
	// Minesweeper Pro's retro-theme.css: grey raised cells and the original eight number colors.
	const FLinearColor Grey = FLinearColor::FromSRGBColor(FColor(192, 192, 192));
	const FLinearColor Revealed = FLinearColor::FromSRGBColor(FColor(217, 217, 217));
	const FLinearColor Shadow = FLinearColor::FromSRGBColor(FColor(123, 123, 123));
	const FLinearColor MineHit = FLinearColor::FromSRGBColor(FColor(255, 68, 68));
	const FLinearColor Flag = FLinearColor::FromSRGBColor(FColor(204, 0, 0));
	const FColor Numbers[] = { FColor::Black, FColor(0, 0, 255), FColor(0, 123, 0), FColor(255, 0, 0),
		FColor(0, 0, 123), FColor(123, 0, 0), FColor(0, 123, 123), FColor::Black, FColor(123, 123, 123) };
	const FSlateBrush* White() { return FCoreStyle::Get().GetBrush("GenericWhiteBox"); }
	FSlateFontInfo Font(const char* Weight, int32 Size) { return FCoreStyle::GetDefaultFontStyle(Weight, Size); }
}

namespace DMUI = DaedalusMinesweeperUI;

void SDaedalusMinesweeper::Construct(const FArguments& InArgs)
{
	Game = InArgs._Game;
	OnClose = InArgs._OnClose;
	ToolbarStyle = FCoreStyle::Get().GetWidgetStyle<FButtonStyle>("Button");
	ToolbarStyle.SetNormal(FSlateColorBrush(DMUI::Grey));
	ToolbarStyle.SetHovered(FSlateColorBrush(FLinearColor::FromSRGBColor(FColor(212, 212, 212))));
	ToolbarStyle.SetPressed(FSlateColorBrush(FLinearColor::FromSRGBColor(FColor(176, 176, 176))));

	TSharedRef<SUniformGridPanel> Grid = SNew(SUniformGridPanel).SlotPadding(0.f);
	for (int32 Row = 0; Row < 8; ++Row)
		for (int32 Column = 0; Column < 8; ++Column) Grid->AddSlot(Column, Row)[BuildCell(Row, Column)];

	ChildSlot
	[
		SNew(SBorder).BorderImage(DMUI::White()).BorderBackgroundColor(FLinearColor(0.f, 0.f, 0.f, 0.75f)).Padding(16.f)
		[
			SNew(SScaleBox).Stretch(EStretch::ScaleToFit).StretchDirection(EStretchDirection::DownOnly)
			[
				SNew(SBox).WidthOverride(480.f).HeightOverride(640.f)
				[
					SNew(SBorder).BorderImage(DMUI::White()).BorderBackgroundColor(DMUI::Grey).Padding(18.f)
					[
						SNew(SVerticalBox)
						+ SVerticalBox::Slot().AutoHeight()
						[
							SNew(STextBlock).Text(FText::FromString(TEXT("MINESWEEPER PRO")))
							.Font(DMUI::Font("Bold", 26)).ColorAndOpacity(FLinearColor::Black).Justification(ETextJustify::Center)
						]
						+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 12.f)
						[
							SNew(STextBlock).Text_Lambda([this]() { return CounterText(); })
							.Font(DMUI::Font("Bold", 16)).ColorAndOpacity(FLinearColor::Black).Justification(ETextJustify::Center)
						]
						+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
						[
							SNew(SBorder).BorderImage(DMUI::White()).BorderBackgroundColor(DMUI::Shadow).Padding(4.f)[Grid]
						]
						+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 12.f)
						[
							SNew(STextBlock).Text_Lambda([this]() { return StatusText(); }).AutoWrapText(true)
							.Font(DMUI::Font("Bold", 15)).ColorAndOpacity(FLinearColor::Black).Justification(ETextJustify::Center)
						]
						+ SVerticalBox::Slot().AutoHeight()
						[
							SNew(SHorizontalBox)
							+ SHorizontalBox::Slot().FillWidth(1.f).Padding(2.f)
							[
								SNew(SButton).ButtonStyle(&ToolbarStyle).ContentPadding(FMargin(8.f, 7.f)).IsFocusable(false)
								.OnClicked_Lambda([this]() { ToggleFlagMode(); return FReply::Handled(); })
								[
									SNew(STextBlock).Text_Lambda([this]() { return FText::FromString(bFlagMode ? TEXT("Flag mode: ON") : TEXT("Flag mode: OFF")); })
									.Font(DMUI::Font("Bold", 13)).ColorAndOpacity(FLinearColor::Black).Justification(ETextJustify::Center)
								]
							]
							+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)[ActionButton(TEXT("Reset"), FSimpleDelegate::CreateSP(this, &SDaedalusMinesweeper::Reset))]
							+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)[ActionButton(TEXT("New seed"), FSimpleDelegate::CreateSP(this, &SDaedalusMinesweeper::NewSeed))]
							+ SHorizontalBox::Slot().AutoWidth().Padding(2.f)[ActionButton(TEXT("Close"), OnClose)]
						]
						+ SVerticalBox::Slot().FillHeight(1.f).VAlign(VAlign_Bottom).Padding(0.f, 12.f, 0.f, 0.f)
						[
							SNew(STextBlock).Text(FText::FromString(TEXT("Left click: reveal (or flag in Flag mode)\nRight click: flag   F: Flag mode   R: Reset   Esc: Close")))
							.Font(DMUI::Font("Regular", 13)).ColorAndOpacity(FLinearColor::Black).Justification(ETextJustify::Center)
						]
						]
					]
				]
		]
	];
}

TSharedRef<SWidget> SDaedalusMinesweeper::ActionButton(const TCHAR* Label, FSimpleDelegate Action)
{
	return SNew(SButton).ButtonStyle(&ToolbarStyle).ContentPadding(FMargin(10.f, 7.f)).IsFocusable(false)
		.OnClicked_Lambda([Action]() { Action.ExecuteIfBound(); return FReply::Handled(); })
		[SNew(STextBlock).Text(FText::FromString(Label)).Font(DMUI::Font("Bold", 13)).ColorAndOpacity(FLinearColor::Black)];
}

TSharedRef<SWidget> SDaedalusMinesweeper::BuildCell(int32 Row, int32 Column)
{
	auto EdgeVisible = [this, Row, Column]() { return CellRevealed(Row, Column) ? EVisibility::Collapsed : EVisibility::HitTestInvisible; };
	return SNew(SBox).WidthOverride(44.f).HeightOverride(44.f)
	[
		SNew(SBorder).BorderImage(DMUI::White()).Padding(1.f)
		.BorderBackgroundColor_Lambda([this, Row, Column]() { return FSlateColor(CellRevealed(Row, Column) ? DMUI::Shadow : DMUI::Grey); })
		.OnMouseButtonDown_Lambda([this, Row, Column](const FGeometry&, const FPointerEvent& Event) { return CellPressed(Row, Column, Event); })
		.ToolTipText(FText::FromString(FString::Printf(TEXT("Row %d, column %d"), Row + 1, Column + 1)))
		[
			SNew(SOverlay)
			+ SOverlay::Slot()
			[
				SNew(SBorder).BorderImage(DMUI::White()).BorderBackgroundColor_Lambda([this, Row, Column]() { return CellBackground(Row, Column); })
				.Padding(0.f).HAlign(HAlign_Center).VAlign(VAlign_Center)
				[
					SNew(STextBlock).Text_Lambda([this, Row, Column]() { return CellText(Row, Column); })
					.Font(DMUI::Font("Bold", 22)).ColorAndOpacity_Lambda([this, Row, Column]() { return CellColor(Row, Column); })
				]
			]
			+ SOverlay::Slot().VAlign(VAlign_Top)[SNew(SBox).HeightOverride(2.f).Visibility_Lambda(EdgeVisible)[SNew(SImage).Image(DMUI::White()).ColorAndOpacity(FLinearColor::White)]]
			+ SOverlay::Slot().HAlign(HAlign_Left)[SNew(SBox).WidthOverride(2.f).Visibility_Lambda(EdgeVisible)[SNew(SImage).Image(DMUI::White()).ColorAndOpacity(FLinearColor::White)]]
			+ SOverlay::Slot().VAlign(VAlign_Bottom)[SNew(SBox).HeightOverride(2.f).Visibility_Lambda(EdgeVisible)[SNew(SImage).Image(DMUI::White()).ColorAndOpacity(DMUI::Shadow)]]
			+ SOverlay::Slot().HAlign(HAlign_Right)[SNew(SBox).WidthOverride(2.f).Visibility_Lambda(EdgeVisible)[SNew(SImage).Image(DMUI::White()).ColorAndOpacity(DMUI::Shadow)]]
		]
	];
}

bool SDaedalusMinesweeper::CellRevealed(int32 Row, int32 Column) const
{
	const ADaedalusMinesweeper* Actor = Game.Get();
	return Actor && Actor->GetCell(Row, Column).bRevealed;
}

FText SDaedalusMinesweeper::CellText(int32 Row, int32 Column) const
{
	const ADaedalusMinesweeper* Actor = Game.Get();
	if (!Actor) return FText::GetEmpty();
	const FDaedalusMinesweeperCell Cell = Actor->GetCell(Row, Column);
	if (!Cell.bValid) return FText::GetEmpty();
	if (Cell.bRevealed)
	{
		if (Cell.bMine) return FText::FromString(TEXT("*"));
		return Cell.Adjacent > 0 ? FText::AsNumber(Cell.Adjacent) : FText::GetEmpty();
	}
	return Cell.bFlagged ? FText::FromString(TEXT("F")) : FText::GetEmpty();
}

FSlateColor SDaedalusMinesweeper::CellColor(int32 Row, int32 Column) const
{
	const ADaedalusMinesweeper* Actor = Game.Get();
	if (!Actor) return FSlateColor(FLinearColor::Black);
	const FDaedalusMinesweeperCell Cell = Actor->GetCell(Row, Column);
	if (Cell.bFlagged && !Cell.bRevealed) return FSlateColor(DMUI::Flag);
	return FSlateColor(FLinearColor::FromSRGBColor(DMUI::Numbers[Cell.bRevealed && !Cell.bMine ? FMath::Clamp(Cell.Adjacent, 0, 8) : 0]));
}

FSlateColor SDaedalusMinesweeper::CellBackground(int32 Row, int32 Column) const
{
	const ADaedalusMinesweeper* Actor = Game.Get();
	if (!Actor) return FSlateColor(DMUI::Grey);
	const FDaedalusMinesweeperCell Cell = Actor->GetCell(Row, Column);
	return FSlateColor(Cell.bRevealed ? Cell.bMine ? DMUI::MineHit : DMUI::Revealed : DMUI::Grey);
}

FReply SDaedalusMinesweeper::CellPressed(int32 Row, int32 Column, const FPointerEvent& Event)
{
	if (ADaedalusMinesweeper* Actor = Game.Get())
	{
		if (Event.GetEffectingButton() == EKeys::RightMouseButton) Actor->ToggleFlag(Row, Column);
		else if (Event.GetEffectingButton() == EKeys::LeftMouseButton)
		{
			if (bFlagMode) Actor->ToggleFlag(Row, Column);
			else Actor->RevealCell(Row, Column);
		}
	}
	return FReply::Handled().SetUserFocus(AsShared(), EFocusCause::SetDirectly);
}

FText SDaedalusMinesweeper::CounterText() const
{
	const ADaedalusMinesweeper* Actor = Game.Get();
	if (!Actor) return FText::FromString(TEXT("Board unavailable"));
	const FDaedalusMinesweeperState State = Actor->GetState();
	return FText::FromString(FString::Printf(TEXT("Mines %d   Flags %d   Score %d   Time %.1fs\nSeed %d"),
		State.Mines, State.Flags, State.Score, static_cast<double>(State.ElapsedMilliseconds) / 1000.0, State.Seed));
}

FText SDaedalusMinesweeper::StatusText() const
{
	const ADaedalusMinesweeper* Actor = Game.Get();
	if (!Actor) return FText::FromString(TEXT("Board unavailable. Close to return."));
	const FDaedalusMinesweeperState State = Actor->GetState();
	if (State.Outcome == EDaedalusMinesweeperOutcome::Won) return FText::FromString(TEXT("You won! Reset to replay, or try a new seed."));
	if (State.Outcome == EDaedalusMinesweeperOutcome::Lost) return FText::FromString(TEXT("Mine hit. Reset to replay, or try a new seed."));
	return FText::FromString(FString::Printf(TEXT("8 x 8 / 10 mines     Safe cells revealed: %d / %d"), State.Revealed, State.Rows * State.Columns - State.Mines));
}

void SDaedalusMinesweeper::Reset()
{
	if (ADaedalusMinesweeper* Actor = Game.Get()) Actor->StartRetro(Actor->GetState().Seed);
	bFlagMode = false;
}

void SDaedalusMinesweeper::NewSeed()
{
	if (ADaedalusMinesweeper* Actor = Game.Get())
	{
		const int32 Seed = Actor->GetState().Seed;
		Actor->StartRetro(Seed == MAX_int32 ? MIN_int32 : Seed + 1);
	}
	bFlagMode = false;
}

void SDaedalusMinesweeper::ToggleFlagMode()
{
	bFlagMode = !bFlagMode;
}

FReply SDaedalusMinesweeper::OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
	const FKey Key = Event.GetKey();
	if (Key == EKeys::Escape || Key == EKeys::Gamepad_FaceButton_Right) OnClose.ExecuteIfBound();
	else if (!Event.IsRepeat() && Key == EKeys::F) ToggleFlagMode();
	else if (!Event.IsRepeat() && Key == EKeys::R) Reset();
	// UIOnly plus handled keys prevents the Hero's menus/actions from opening behind this board.
	return FReply::Handled();
}

FNavigationReply SDaedalusMinesweeper::OnNavigation(const FGeometry& Geometry, const FNavigationEvent& Event)
{
	return FNavigationReply::Stop();
}
