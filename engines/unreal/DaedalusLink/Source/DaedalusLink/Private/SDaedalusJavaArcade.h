// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "DaedalusJavaArcade.h"
#include "Widgets/SCompoundWidget.h"

class SEditableTextBox;

/** Small local board/table presentation. Controls send intentions; Java decides all outcomes. */
class SDaedalusJavaArcade : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SDaedalusJavaArcade) {}
        SLATE_ARGUMENT(TWeakObjectPtr<ADaedalusJavaArcade>, Game)
    SLATE_END_ARGS()
    void Construct(const FArguments& Args);
    virtual bool SupportsKeyboardFocus() const override { return true; }
    virtual FReply OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    bool OwnsUserFocus(int32 UserIndex) const;

private:
    TSharedRef<SWidget> SudokuPanel();
    TSharedRef<SWidget> BlackjackPanel();
    TSharedRef<SWidget> Button(const TCHAR* Label, TFunction<void()> Action, TFunction<bool()> Enabled = [] { return true; });
    FDaedalusJavaArcadeState State() const;
    FReply SelectCell(int32 Index);
    FText CellText(int32 Index) const;
    FSlateColor CellColor(int32 Index) const;
    FText StatusText() const;
    FText SelectionText() const;
    bool CanEditCell() const;
    void SubmitCellValue(int32 Value);
    FText TableText() const;
    FReply Configure();
    void FocusBoard();
    TWeakObjectPtr<ADaedalusJavaArcade> Game;
    TSharedPtr<SEditableTextBox> UsernameBox;
    TSharedPtr<SEditableTextBox> SecretBox;
    TSharedPtr<SEditableTextBox> ResumeBox;
    TSharedPtr<SWidget> CabinetControls;
    int32 SelectedCell = 0;
    int32 SelectedDigit = 1;
    FString LocalMessage;
};
