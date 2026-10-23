// SPDX-License-Identifier: MIT
#include "SDaedalusJavaArcade.h"
#include "Framework/Application/SlateApplication.h"
#include "InputCoreTypes.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SGridPanel.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSeparator.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

FDaedalusJavaArcadeState SDaedalusJavaArcade::State() const { return Game.IsValid() ? Game->GetState() : FDaedalusJavaArcadeState(); }
bool SDaedalusJavaArcade::OwnsUserFocus(int32 UserIndex) const { return HasUserFocus(UserIndex).IsSet() || HasUserFocusedDescendants(UserIndex); }
TSharedRef<SWidget> SDaedalusJavaArcade::Button(const TCHAR* Label, TFunction<void()> Action, TFunction<bool()> Enabled)
{
    return SNew(SButton).Text(FText::FromString(Label)).IsEnabled_Lambda([Enabled] { return Enabled(); })
        .OnClicked_Lambda([this, Action] { Action(); FocusBoard(); return FReply::Handled(); });
}
void SDaedalusJavaArcade::Construct(const FArguments& Args)
{
    Game = Args._Game;
    const auto IsSudoku = [this] { return Game.IsValid() && Game->Game == EDaedalusJavaGame::Sudoku; };
    const auto IsBlackjack = [this] { return Game.IsValid() && Game->Game == EDaedalusJavaGame::Blackjack; };
    const auto RefreshButton = Button(TEXT("Refresh"), [this] { if (Game.IsValid()) Game->RefreshSnapshot(); }, [this] { return Game.IsValid() && !State().bBusy && !State().SessionId.IsEmpty() && !State().bRemoteClosed; });
    CabinetControls = RefreshButton;
    ChildSlot
    [
        SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush")).BorderBackgroundColor(FLinearColor(0.025f, 0.04f, 0.06f, 0.97f)).Padding(24)
        [
            SNew(SBox).HAlign(HAlign_Center).MaxDesiredWidth(980)
            [
                SNew(SScrollBox)
                + SScrollBox::Slot()
                [
                    SNew(SVerticalBox)
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 12)
                    [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Bold", 25)).Text_Lambda([this] { return FText::FromString(Game.IsValid() && Game->Game == EDaedalusJavaGame::Blackjack ? TEXT("Blackjack — simulated credits") : TEXT("Sudoku")); })]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
                    [SNew(STextBlock).Text(this, &SDaedalusJavaArcade::StatusText).AutoWrapText(true)]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 12)
                    [
                        SNew(SHorizontalBox)
                        + SHorizontalBox::Slot().FillWidth(1).Padding(0, 0, 8, 0)
                        [SAssignNew(UsernameBox, SEditableTextBox).HintText(FText::FromString(TEXT("Sudoku account name"))).Visibility_Lambda([IsSudoku] { return IsSudoku() ? EVisibility::Visible : EVisibility::Collapsed; })]
                        + SHorizontalBox::Slot().FillWidth(1).Padding(0, 0, 8, 0)
                        [SAssignNew(SecretBox, SEditableTextBox).IsPassword(true).HintText_Lambda([IsBlackjack] { return FText::FromString(IsBlackjack() ? TEXT("Local service token") : TEXT("Password")); })]
                        + SHorizontalBox::Slot().AutoWidth()
                        [SNew(SButton).Text(FText::FromString(TEXT("Connect account"))).IsEnabled_Lambda([this] { return !State().bBusy; }).OnClicked(this, &SDaedalusJavaArcade::Configure)]
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 12)
                    [
                        SNew(SHorizontalBox)
                        + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 8, 0)
                        [RefreshButton]
                        + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 8, 0)
                        [Button(TEXT("Recover create"), [this] { if (Game.IsValid()) Game->RetryBlackjackCreate(); }, [this] { return Game.IsValid() && Game->Game == EDaedalusJavaGame::Blackjack && State().bNeedsSync && State().SessionId.IsEmpty() && !State().bBusy; })]
                        + SHorizontalBox::Slot().AutoWidth()
                        [Button(TEXT("Close cabinet"), [this] { if (Game.IsValid()) Game->CloseArcade(); })]
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 12)[SNew(SSeparator)]
                    + SVerticalBox::Slot().AutoHeight()[SNew(SBox).Visibility_Lambda([IsSudoku] { return IsSudoku() ? EVisibility::Visible : EVisibility::Collapsed; })[SudokuPanel()]]
                    + SVerticalBox::Slot().AutoHeight()[SNew(SBox).Visibility_Lambda([IsBlackjack] { return IsBlackjack() ? EVisibility::Visible : EVisibility::Collapsed; })[BlackjackPanel()]]
                ]
            ]
        ]
    ];
}
FReply SDaedalusJavaArcade::Configure()
{
    if (!Game.IsValid() || !SecretBox.IsValid()) return FReply::Handled();
    const FString Secret = SecretBox->GetText().ToString();
    const bool Success = Game->Game == EDaedalusJavaGame::Sudoku
        ? Game->ConfigureSudokuCredentials(UsernameBox.IsValid() ? UsernameBox->GetText().ToString() : FString(), Secret)
        : Game->ConfigureBlackjackToken(Secret);
    SecretBox->SetText(FText::GetEmpty());
    if (UsernameBox.IsValid()) UsernameBox->SetText(FText::GetEmpty());
    LocalMessage = Success ? FString() : TEXT("Check the account fields. Passwords and service tokens are kept only in memory.");
    FocusBoard();
    return FReply::Handled();
}
FText SDaedalusJavaArcade::StatusText() const
{
    const auto S = State();
    const FString Text = LocalMessage.IsEmpty() ? S.Status + TEXT(" — ") + S.Message : LocalMessage;
    return FText::FromString(Text + (S.HintText.IsEmpty() ? FString() : TEXT("\nHint: ") + S.HintText));
}
TSharedRef<SWidget> SDaedalusJavaArcade::SudokuPanel()
{
    auto Starts = SNew(SHorizontalBox);
    for (int32 Difficulty = 1; Difficulty <= 5; ++Difficulty)
    {
        const FString Label = FString::Printf(TEXT("Level %d"), Difficulty);
        Starts->AddSlot().AutoWidth().Padding(0, 0, 6, 0)
        [Button(*Label, [this, Difficulty] { if (Game.IsValid()) Game->StartSudokuGame(Difficulty); }, [this] { return Game.IsValid() && Game->HasCredentials() && !State().bBusy; })];
    }
    auto Grid = SNew(SGridPanel);
    for (int32 Index = 0; Index < 81; ++Index)
    {
        Grid->AddSlot(Index % 9, Index / 9).Padding(FMargin((Index % 3 == 0) ? 4.f : 1.f, (Index / 9 % 3 == 0) ? 4.f : 1.f, 1.f, 1.f))
        [
            SNew(SBox).WidthOverride(44).HeightOverride(44)
            [SNew(SButton).ButtonColorAndOpacity(this, &SDaedalusJavaArcade::CellColor, Index).ContentPadding(0)
                .OnClicked_Lambda([this, Index] { return SelectCell(Index); })
                [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 20)).Justification(ETextJustify::Center).Text(this, &SDaedalusJavaArcade::CellText, Index)]]
        ];
    }
    auto Digits = SNew(SHorizontalBox);
    for (int32 Value = 0; Value <= 9; ++Value)
    {
        const FString Label = Value == 0 ? TEXT("Erase") : FString::FromInt(Value);
        Digits->AddSlot().AutoWidth().Padding(0, 0, 4, 0)
        [Button(*Label, [this, Value] { SubmitCellValue(Value); }, [this] { return CanEditCell(); })];
    }
    return SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 6)
        [SNew(STextBlock).Text(FText::FromString(TEXT("New puzzle — difficulty")))]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)[Starts]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)
        [SNew(STextBlock).Text_Lambda([this] { const auto S = State(); return FText::FromString(FString::Printf(TEXT("Difficulty %d  ·  Score %lld  ·  Lives %d  ·  Moves %lld  ·  Elapsed %lld s%s"), S.Difficulty, S.Score, S.Lives, S.MoveCount, S.ElapsedSeconds, S.TimeLimitSeconds > 0 ? *FString::Printf(TEXT("  ·  Remaining %lld s"), S.SecondsLeft) : TEXT(""))); }).AutoWrapText(true)]
        + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 0, 0, 10)[Grid]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
        [SNew(STextBlock).Text(this, &SDaedalusJavaArcade::SelectionText).AutoWrapText(true)]
        + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 0, 0, 10)[Digits]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)
        [SNew(STextBlock).Text(FText::FromString(TEXT("Arrows / D-pad: cell. LB / RB: choose digit. Enter / pad A: enter it. 1–9: enter directly. Delete / pad X: erase. Ctrl+Z / pad Y: undo; Ctrl+Y: redo. F5 / Start: save to Java. F6: refresh. Pad B: cabinet controls. Esc / Back: close."))).AutoWrapText(true)]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)[Button(TEXT("Undo"), [this] { if (Game.IsValid()) Game->SudokuUndo(); }, [this] { return State().bCanAct; })]
            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)[Button(TEXT("Redo"), [this] { if (Game.IsValid()) Game->SudokuRedo(); }, [this] { return State().bCanAct; })]
            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)[Button(TEXT("Hint (Java gem cost)"), [this] { if (Game.IsValid()) Game->RequestSudokuHint(); }, [this] { return State().bCanAct; })]
            + SHorizontalBox::Slot().AutoWidth()[Button(TEXT("Save to Java"), [this] { if (Game.IsValid()) Game->SaveSudokuGame(); }, [this] { return State().bReady && State().bOwner; })]
        ]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().FillWidth(1).Padding(0, 0, 6, 0)[SAssignNew(ResumeBox, SEditableTextBox).HintText(FText::FromString(TEXT("Saved Java game ID")))]
            + SHorizontalBox::Slot().AutoWidth()[Button(TEXT("Resume"), [this] { if (Game.IsValid() && ResumeBox.IsValid()) Game->ResumeSudokuGame(ResumeBox->GetText().ToString()); }, [this] { return Game.IsValid() && Game->HasCredentials() && !State().bBusy; })]
        ]
        + SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text_Lambda([this] { const auto S = State(); return FText::FromString(TEXT("Game ID: ") + S.SessionId + (S.bSolved ? TEXT("  ·  Java reports solved") : S.bTimeUp ? TEXT("  ·  Java reports time expired") : TEXT(""))); }).AutoWrapText(true)];
}
TSharedRef<SWidget> SDaedalusJavaArcade::BlackjackPanel()
{
    auto Chips = SNew(SHorizontalBox);
    for (int32 Amount : { 1, 5, 25, 100, 500 })
    {
        const FString Label = FString::Printf(TEXT("Bet %d"), Amount);
        Chips->AddSlot().AutoWidth().Padding(0, 0, 6, 0)
        [Button(*Label, [this, Amount] { if (Game.IsValid()) Game->SubmitBlackjackAction(TEXT("bet"), Amount); }, [this, Amount] { return Game.IsValid() && Game->IsBlackjackActionLegal(TEXT("bet"), Amount); })];
    }
    auto Actions = SNew(SHorizontalBox);
    const TArray<FString> Names = { TEXT("clearBet"), TEXT("rebet"), TEXT("deal"), TEXT("hit"), TEXT("stand"), TEXT("double"), TEXT("split"), TEXT("surrender"), TEXT("reload") };
    for (const FString& Name : Names)
        Actions->AddSlot().AutoWidth().Padding(0, 0, 6, 0)[Button(*Name, [this, Name] { if (Game.IsValid()) Game->SubmitBlackjackAction(Name); }, [this, Name] { return Game.IsValid() && Game->IsBlackjackActionLegal(Name); })];
    return SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 12)
        [Button(TEXT("Start Java session"), [this] { if (Game.IsValid()) Game->StartBlackjackSession(); }, [this] { const auto S = State(); return Game.IsValid() && Game->HasCredentials() && !S.bBusy && (S.SessionId.IsEmpty() || S.bRemoteClosed); })]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 12)[SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 22)).Text(this, &SDaedalusJavaArcade::TableText).AutoWrapText(true)]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)[Chips]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)[Actions]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)[Button(TEXT("Accept insurance"), [this] { if (Game.IsValid()) Game->SubmitBlackjackAction(TEXT("insurance"), 0, true); }, [this] { return Game.IsValid() && Game->IsBlackjackActionLegal(TEXT("insurance")) && State().bInsuranceAcceptAllowed; })]
            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)[Button(TEXT("Decline insurance"), [this] { if (Game.IsValid()) Game->SubmitBlackjackAction(TEXT("insurance"), 0, false); }, [this] { return Game.IsValid() && Game->IsBlackjackActionLegal(TEXT("insurance")); })]
            + SHorizontalBox::Slot().AutoWidth()[Button(TEXT("End Java session"), [this] { if (Game.IsValid()) Game->CloseRemoteBlackjackSession(); }, [this] { return State().bReady && !State().bRemoteClosed; })]
        ]
        + SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(TEXT("Java hides the dealer hole card and future shoe. Closing this cabinet cancels local work; end the Java session first when ready. Unreached sessions expire in Java."))).AutoWrapText(true)];
}
FText SDaedalusJavaArcade::TableText() const
{
    const auto S = State();
    FString Text = FString::Printf(TEXT("%s  ·  Credits %lld  ·  Bet %lld  ·  Revision %lld\n"), *S.Phase, S.Bankroll, S.PendingBet, S.Revision);
    auto Cards = [](const TArray<FDaedalusJavaCard>& List)
    {
        FString Out;
        for (const auto& C : List) { if (!Out.IsEmpty()) Out += TEXT("   "); Out += C.Rank + TEXT(" ") + C.Suit; }
        return Out;
    };
    Text += TEXT("Dealer: ") + Cards(S.DealerCards);
    for (int32 I = 0; I < S.HiddenDealerCards; ++I) Text += TEXT("   [hidden]");
    Text += TEXT("\n") + S.DealerCaption;
    for (int32 I = 0; I < S.PlayerHands.Num(); ++I)
        Text += FString::Printf(TEXT("\n%sHand %d: %s  ·  Total %d  ·  Bet %lld"), I == S.ActiveHand ? TEXT("▶ ") : TEXT(""), I + 1, *Cards(S.PlayerHands[I].Cards), S.PlayerHands[I].Value, S.PlayerHands[I].Bet);
    if (!S.ResultText.IsEmpty()) Text += TEXT("\n") + S.ResultText;
    return FText::FromString(Text);
}
FText SDaedalusJavaArcade::CellText(int32 Index) const
{
    const auto S = State();
    if (!S.Cells.IsValidIndex(Index)) return FText::FromString(TEXT("·"));
    if (S.Cells[Index] != 0) return FText::AsNumber(S.Cells[Index]);
    FString Marks;
    if (S.PencilMasks.IsValidIndex(Index)) for (int32 Digit = 1; Digit <= 9; ++Digit) if (S.PencilMasks[Index] & (1 << Digit)) Marks += FString::FromInt(Digit);
    return FText::FromString(Marks);
}
FSlateColor SDaedalusJavaArcade::CellColor(int32 Index) const
{
    const auto S = State();
    if (SelectedCell == Index) return FLinearColor(0.2f, 0.5f, 0.8f, 1.f);
    return S.Givens.IsValidIndex(Index) && S.Givens[Index] ? FLinearColor(0.3f, 0.35f, 0.4f, 1.f) : FLinearColor(0.15f, 0.2f, 0.25f, 1.f);
}
FReply SDaedalusJavaArcade::SelectCell(int32 Index) { SelectedCell = FMath::Clamp(Index, 0, 80); FocusBoard(); return FReply::Handled(); }
bool SDaedalusJavaArcade::CanEditCell() const
{
    const auto S = State();
    return Game.IsValid() && S.Game == EDaedalusJavaGame::Sudoku && S.bCanAct
        && S.Cells.IsValidIndex(SelectedCell) && S.Givens.IsValidIndex(SelectedCell) && !S.Givens[SelectedCell];
}
void SDaedalusJavaArcade::SubmitCellValue(int32 Value)
{
    if (Value < 0 || Value > 9) return;
    if (Value > 0) SelectedDigit = Value;
    if (CanEditCell()) Game->SubmitSudokuMove(SelectedCell / 9, SelectedCell % 9, Value);
    // Keep the cursor and visible value until Java reconciles; never queue or project an edit.
}
FText SDaedalusJavaArcade::SelectionText() const
{
    const auto S = State();
    if (!S.Cells.IsValidIndex(SelectedCell) || !S.Givens.IsValidIndex(SelectedCell))
        return FText::FromString(TEXT("Connect an account, then choose a difficulty or resume a saved game."));
    FString Text = FString::Printf(TEXT("Row %d, column %d · Selected digit %d · "), SelectedCell / 9 + 1, SelectedCell % 9 + 1, SelectedDigit);
    if (S.Givens[SelectedCell]) Text += FString::Printf(TEXT("Fixed clue %d. Choose another cell to enter a number."), S.Cells[SelectedCell]);
    else if (S.Cells[SelectedCell]) Text += FString::Printf(TEXT("Entry %d.%s"), S.Cells[SelectedCell], S.bCanAct ? TEXT(" Replace or erase it.") : TEXT(""));
    else Text += TEXT("Empty cell.");
    if (S.bSolved) Text += TEXT(" Java reports this puzzle solved.");
    else if (S.bTimeUp) Text += TEXT(" Java reports time expired.");
    else if (S.bBusy) Text += TEXT(" Waiting for Java; entries are not queued.");
    else if (S.bNeedsSync) Text += TEXT(" Refresh before entering another number.");
    return FText::FromString(Text);
}
void SDaedalusJavaArcade::FocusBoard()
{
    if (Game.IsValid() && FSlateApplication::IsInitialized() && Game->GetSlateUserIndex() != INDEX_NONE)
        FSlateApplication::Get().SetUserFocus(Game->GetSlateUserIndex(), SharedThis(this), EFocusCause::SetDirectly);
}
FReply SDaedalusJavaArcade::OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    if (!Game.IsValid()) return FReply::Unhandled();
    const FKey Key = Event.GetKey();
    if (Key == EKeys::Escape || Key == EKeys::Gamepad_Special_Left) { Game->CloseArcade(); return FReply::Handled(); }
    // Text fields and focused buttons own their keys. Only direct board focus edits the puzzle.
    if (!HasUserFocus(Event.GetUserIndex()).IsSet() || State().Game != EDaedalusJavaGame::Sudoku) return FReply::Unhandled();
    const auto Board = State();
    // Before a board arrives, native Slate navigation must still reach account/new/resume controls.
    if (Board.Cells.Num() != 81 || Board.Givens.Num() != 81) return FReply::Unhandled();
    // Keep held keys from falling through to Slate navigation or replaying a mutation.
    if (Event.IsRepeat()) return FReply::Handled();
    if (Key == EKeys::Gamepad_FaceButton_Right)
    {
        if (FSlateApplication::IsInitialized())
        {
            if (CabinetControls.IsValid() && CabinetControls->IsEnabled())
                FSlateApplication::Get().SetUserFocus(Event.GetUserIndex(), CabinetControls, EFocusCause::Navigation);
            else if (UsernameBox.IsValid())
                FSlateApplication::Get().SetUserFocus(Event.GetUserIndex(), UsernameBox, EFocusCause::Navigation);
        }
        return FReply::Handled();
    }
    int32 Row = SelectedCell / 9, Col = SelectedCell % 9;
    if (Key == EKeys::Left || Key == EKeys::Gamepad_DPad_Left) --Col;
    else if (Key == EKeys::Right || Key == EKeys::Gamepad_DPad_Right) ++Col;
    else if (Key == EKeys::Up || Key == EKeys::Gamepad_DPad_Up) --Row;
    else if (Key == EKeys::Down || Key == EKeys::Gamepad_DPad_Down) ++Row;
    else
    {
        if (Key == EKeys::Gamepad_LeftShoulder || Key == EKeys::Gamepad_RightShoulder)
        {
            SelectedDigit = (SelectedDigit + (Key == EKeys::Gamepad_RightShoulder ? 1 : 8) - 1) % 9 + 1;
            Invalidate(EInvalidateWidgetReason::Paint);return FReply::Handled();
        }
        const auto S = State();
        if (Key == EKeys::F5 || Key == EKeys::Gamepad_Special_Right)
        { if (S.bReady && S.bOwner) Game->SaveSudokuGame();return FReply::Handled(); }
        if (Key == EKeys::F6) { if (!S.bBusy && !S.SessionId.IsEmpty() && !S.bRemoteClosed) Game->RefreshSnapshot();return FReply::Handled(); }
        if ((Event.IsControlDown() && Key == EKeys::Z) || Key == EKeys::Gamepad_FaceButton_Top)
        { if (S.bCanAct) Game->SudokuUndo();return FReply::Handled(); }
        if (Event.IsControlDown() && Key == EKeys::Y) { if (S.bCanAct) Game->SudokuRedo();return FReply::Handled(); }
        if (Key == EKeys::Enter || Key == EKeys::Gamepad_FaceButton_Bottom) { SubmitCellValue(SelectedDigit);return FReply::Handled(); }
        const FKey Keys[] = { EKeys::Zero, EKeys::One, EKeys::Two, EKeys::Three, EKeys::Four, EKeys::Five, EKeys::Six, EKeys::Seven, EKeys::Eight, EKeys::Nine };
        const FKey Pads[] = { EKeys::NumPadZero, EKeys::NumPadOne, EKeys::NumPadTwo, EKeys::NumPadThree, EKeys::NumPadFour, EKeys::NumPadFive, EKeys::NumPadSix, EKeys::NumPadSeven, EKeys::NumPadEight, EKeys::NumPadNine };
        for (int32 Value = 0; Value <= 9; ++Value) if (Key == Keys[Value] || Key == Pads[Value]) { SubmitCellValue(Value); return FReply::Handled(); }
        if (Key == EKeys::BackSpace || Key == EKeys::Delete || Key == EKeys::Gamepad_FaceButton_Left) { SubmitCellValue(0); return FReply::Handled(); }
        return FReply::Unhandled();
    }
    SelectedCell = FMath::Clamp(Row, 0, 8) * 9 + FMath::Clamp(Col, 0, 8);
    Invalidate(EInvalidateWidgetReason::Paint);
    return FReply::Handled();
}
