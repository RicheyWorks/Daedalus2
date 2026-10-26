// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "Styling/SlateTypes.h"
#include "Widgets/SCompoundWidget.h"

class ADaedalusMinesweeper;

/** Local presentation only; all mutations go through ADaedalusMinesweeper and its portable core. */
class SDaedalusMinesweeper : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SDaedalusMinesweeper) {}
		SLATE_ARGUMENT(TWeakObjectPtr<ADaedalusMinesweeper>, Game)
		SLATE_EVENT(FSimpleDelegate, OnClose)
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);
	virtual bool SupportsKeyboardFocus() const override { return true; }
	virtual FReply OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
	virtual FNavigationReply OnNavigation(const FGeometry& Geometry, const FNavigationEvent& Event) override;

private:
	TSharedRef<SWidget> BuildCell(int32 Row, int32 Column);
	TSharedRef<SWidget> ActionButton(const TCHAR* Label, FSimpleDelegate Action);
	FReply CellPressed(int32 Row, int32 Column, const FPointerEvent& Event);
	FText CellText(int32 Row, int32 Column) const;
	FSlateColor CellColor(int32 Row, int32 Column) const;
	FSlateColor CellBackground(int32 Row, int32 Column) const;
	bool CellRevealed(int32 Row, int32 Column) const;
	FText StatusText() const;
	FText CounterText() const;
	void Reset();
	void NewSeed();
	void ToggleFlagMode();

	TWeakObjectPtr<ADaedalusMinesweeper> Game;
	FSimpleDelegate OnClose;
	FButtonStyle ToolbarStyle;
	bool bFlagMode = false;
};
