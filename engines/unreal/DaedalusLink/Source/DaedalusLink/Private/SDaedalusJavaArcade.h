// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "DaedalusJavaArcade.h"
#include "Fonts/SlateFontInfo.h"
#include "InputCoreTypes.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/Input/SComboBox.h"

class SEditableTextBox;
class SScrollBox;
class STextBlock;

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
    virtual FReply OnKeyUp(const FGeometry& Geometry, const FKeyEvent& Event) override;
    virtual void Tick(const FGeometry& AllottedGeometry, const double CurrentTime, const float DeltaTime) override;
    bool OwnsUserFocus(int32 UserIndex) const;

private:
    TSharedRef<SWidget> SudokuPanel();
    TSharedRef<SWidget> SudokuResult();
    static bool HasSudokuResult(const FDaedalusJavaArcadeState& Snapshot);
    TSharedRef<SWidget> BlackjackPanel();
    TSharedRef<SWidget> BlackjackOptions();
    TSharedRef<SWidget> Button(const TCHAR* Label, TFunction<void()> Action, TFunction<bool()> Enabled = [] { return true; });
    FDaedalusJavaArcadeState State() const;
    FReply SelectCell(int32 Index);
    FText CellText(int32 Index) const;
    FSlateFontInfo CellFont(int32 Index) const;
    FSlateColor CellColor(int32 Index) const;
    FText StatusText() const;
    FText SelectionText() const;
    FText SudokuFeedbackText() const;
    FReply ShowSudokuFeedback();
    void RebuildSavedGames();
    static FText SavedGameText(const FDaedalusSudokuSavedGame& Saved);
    FText SelectedSavedGameText() const;
    FText SavedGamesText() const;
    FReply RefreshSavedGames();
    FReply ResumeSelectedSavedGame();
    bool CanEditCell() const;
    void SubmitCellValue(int32 Value);
    static FString CardsText(const TArray<FDaedalusJavaCard>& Cards);
    FText TableHeadingText() const;
    FText DealerText() const;
    FText PlayerHandText(int32 Index) const;
    FText BlackjackGuideText() const;
    FReply Configure();
    void FocusBoard(bool bRevealGame = true);
    void RevealSelectedCell();
    void UpdateSudokuResultReveal();
    void UpdateBlackjackReveal();
    TWeakObjectPtr<ADaedalusJavaArcade> Game;
    TSharedPtr<SEditableTextBox> UsernameBox;
    TSharedPtr<SEditableTextBox> SecretBox;
    TSharedPtr<SEditableTextBox> ResumeBox;
    TSharedPtr<SScrollBox> CabinetScroll;
    TSharedPtr<STextBlock> CabinetStatus;
    TArray<TSharedPtr<SWidget>> SudokuCellWidgets;
    TSharedPtr<STextBlock> SudokuFeedbackRow;
    TSharedPtr<SWidget> SudokuResultPanel;
    TSharedPtr<SWidget> SudokuResultAction;
    TSharedPtr<SWidget> SudokuReviewAction;
    FKey SudokuResultFocusKey;
    bool bSudokuResultRevealArmed = false;
    FString RevealedSudokuResultSession;
    TArray<TSharedPtr<SWidget>> BlackjackHandWidgets;
    TSharedPtr<SWidget> BlackjackBetControls;
    TSharedPtr<STextBlock> BlackjackDealerRow;
    TSharedPtr<STextBlock> BlackjackResultRow;
    bool bBlackjackRevealPending = false;
    bool bBlackjackRevealArmed = false;
    bool bBlackjackNeedsSyncRevealed = false;
    FString RevealedBlackjackSession;
    int64 RevealedBlackjackRevision = -1;
    FString RevealedBlackjackPhase;
    int32 RevealedBlackjackHand = -2;
    TArray<TSharedPtr<FDaedalusSudokuSavedGame>> SavedGameOptions;
    TSharedPtr<SComboBox<TSharedPtr<FDaedalusSudokuSavedGame>>> SavedGamePicker;
    FString SelectedSavedGameId;
    TSharedPtr<SWidget> CabinetControls;
    int32 SelectedCell = 0;
    int32 SelectedDigit = 1;
    FString CredentialError;
};
