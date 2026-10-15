// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "DaedalusJavaArcade.h"
#include "InputCoreTypes.h"
#include "Input/Events.h"
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
    virtual FReply OnKeyChar(const FGeometry& Geometry, const FCharacterEvent& Event) override;
    virtual void Tick(const FGeometry& Geometry, const double CurrentTime, const float DeltaTime) override;
    bool OwnsUserFocus(int32 UserIndex) const;

private:
    TSharedRef<SWidget> SudokuPanel();
    TSharedRef<SWidget> SudokuMode(const TCHAR* Label, bool SDaedalusJavaArcade::* Field);
    TSharedRef<SWidget> BlackjackPanel();
    TSharedRef<SWidget> BlackjackSettings();
    TSharedRef<SWidget> BlackjackRule(const TCHAR* Label, const TCHAR* Rule, bool FDaedalusJavaBlackjackRules::* Field);
    TSharedRef<SWidget> Button(const TCHAR* Label, TFunction<void()> Action, TFunction<bool()> Enabled = [] { return true; });
    FDaedalusJavaArcadeState State() const;
    FReply SelectCell(int32 Index);
    FText CellText(int32 Index) const;
    FText CellNoteText(int32 Index, int32 Digit) const;
    FText CellDescription(int32 Index) const;
    FSlateColor CellColor(int32 Index) const;
    TSharedRef<SWidget> SudokuCell(int32 Index);
    TSharedRef<SWidget> SudokuDigitButton(int32 Value);
    bool OwnsKeyboardEvent(const FInputEvent& Event) const;
    bool CanEnterSudokuDigit(int32 Value) const;
    void EnterSudokuDigit(int32 Value);
    void ToggleSudokuPencil();
    void SyncSudokuPresentation(const FDaedalusJavaArcadeState& S);
    void ResetSudokuPresentation();
    int32 PencilMask(int32 Index, const FDaedalusJavaArcadeState& S) const;
    static bool VisibleDuplicate(int32 Index, const FDaedalusJavaArcadeState& S);
    FText StatusText() const;
    FText TableText() const;
    FText BlackjackDetailsText() const;
    FReply HandleBlackjackKey(const FKey& Key);
    void ConfirmSudokuHint();
    FReply Configure();
    void FocusBoard();
    TWeakObjectPtr<ADaedalusJavaArcade> Game;
    TSharedPtr<SEditableTextBox> UsernameBox;
    TSharedPtr<SEditableTextBox> SecretBox;
    TSharedPtr<SEditableTextBox> ResumeBox;
    int32 SelectedCell = 0;
    bool bNewSudokuChaos = false;
    bool bNewSudokuMirror = false;
    bool bNewSudokuTimeAttack = false;
    FString LocalMessage;
    FString HintConfirmationGameId;
    // View-local overrides, including explicit zero, survive same-board snapshots.
    FString NotesGameId;
    TArray<int32> LocalPencilMasks;
    TArray<bool> LocalPencilOverrides;
    bool bSudokuPencilMode = false;
};
