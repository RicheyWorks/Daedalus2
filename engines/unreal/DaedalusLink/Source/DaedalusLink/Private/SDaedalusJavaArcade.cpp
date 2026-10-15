// SPDX-License-Identifier: MIT
#include "SDaedalusJavaArcade.h"
#include "Framework/Application/SlateApplication.h"
#include "InputCoreTypes.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SCheckBox.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SGridPanel.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSeparator.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
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
                        [Button(TEXT("Refresh"), [this] { if (Game.IsValid()) Game->RefreshSnapshot(); }, [this] { return Game.IsValid() && !State().bBusy && !State().SessionId.IsEmpty() && !State().bRemoteClosed; })]
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
    HintConfirmationGameId.Reset();
    if (!Game.IsValid() || !SecretBox.IsValid()) return FReply::Handled();
    const FString Secret = SecretBox->GetText().ToString();
    const bool Success = Game->Game == EDaedalusJavaGame::Sudoku
        ? Game->ConfigureSudokuCredentials(UsernameBox.IsValid() ? UsernameBox->GetText().ToString() : FString(), Secret)
        : Game->ConfigureBlackjackToken(Secret);
    SecretBox->SetText(FText::GetEmpty());
    if (UsernameBox.IsValid()) UsernameBox->SetText(FText::GetEmpty());
    LocalMessage = Success ? FString() : TEXT("Check the account fields. Passwords and service tokens are kept only in memory.");
    if (Success) ResetSudokuPresentation();
    FocusBoard();
    return FReply::Handled();
}
FText SDaedalusJavaArcade::StatusText() const
{
    const auto S = State();
    FString Text = S.Status + TEXT(" — ") + S.Message;
    if (!LocalMessage.IsEmpty()) Text += TEXT("\n") + LocalMessage;
    return FText::FromString(Text + (S.HintText.IsEmpty() ? FString() : TEXT("\nHint: ") + S.HintText));
}
TSharedRef<SWidget> SDaedalusJavaArcade::SudokuPanel()
{
    auto Starts = SNew(SHorizontalBox);
    for (int32 Difficulty = 1; Difficulty <= 5; ++Difficulty)
    {
        const FString Label = FString::Printf(TEXT("New %d"), Difficulty);
        Starts->AddSlot().AutoWidth().Padding(0, 0, 6, 0)
        [Button(*Label, [this, Difficulty] { HintConfirmationGameId.Reset(); if (Game.IsValid() && Game->StartSudokuGameWithModes(Difficulty, bNewSudokuChaos, bNewSudokuMirror, bNewSudokuTimeAttack)) ResetSudokuPresentation(); }, [this] { return Game.IsValid() && Game->HasCredentials() && !State().bBusy; })];
    }
    auto Grid = SNew(SGridPanel);
    for (int32 Index = 0; Index < 81; ++Index)
    {
        Grid->AddSlot(Index % 9, Index / 9).Padding(FMargin((Index % 3 == 0) ? 4.f : 1.f, (Index / 9 % 3 == 0) ? 4.f : 1.f, 1.f, 1.f))
        [
            SNew(SBox).WidthOverride(44).HeightOverride(44)
            [SNew(SButton).ButtonColorAndOpacity(this, &SDaedalusJavaArcade::CellColor, Index).ContentPadding(0)
                .ToolTipText(this, &SDaedalusJavaArcade::CellDescription, Index)
                .OnClicked_Lambda([this, Index] { return SelectCell(Index); })
                [SudokuCell(Index)]]
        ];
    }
    auto Digits = SNew(SHorizontalBox);
    for (int32 Value = 0; Value <= 9; ++Value)
    {
        Digits->AddSlot().AutoWidth().Padding(0, 0, 4, 0)
        [SudokuDigitButton(Value)];
    }
    return SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 12, 0)[SNew(STextBlock).Text(FText::FromString(TEXT("New game options:")))]
            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 12, 0)[SudokuMode(TEXT("Chaos"), &SDaedalusJavaArcade::bNewSudokuChaos)]
            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 12, 0)[SudokuMode(TEXT("Mirror"), &SDaedalusJavaArcade::bNewSudokuMirror)]
            + SHorizontalBox::Slot().AutoWidth()[SudokuMode(TEXT("Time Attack"), &SDaedalusJavaArcade::bNewSudokuTimeAttack)]
        ]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)[Starts]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
        [SNew(STextBlock).Text_Lambda([this]
        {
            const auto S = State();
            if (!S.bReady) return FText::FromString(TEXT("Current modes appear after the game is confirmed."));
            TArray<FString> Modes;
            if (S.bChaosMode) Modes.Add(TEXT("Chaos"));
            if (S.bMirrorMode) Modes.Add(TEXT("Mirror"));
            if (S.TimeLimitSeconds > 0) Modes.Add(TEXT("Time Attack"));
            return FText::FromString(TEXT("Current game: ") + (Modes.IsEmpty() ? FString(TEXT("Ordinary")) : FString::Join(Modes, TEXT(" / "))));
        }).AutoWrapText(true)]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)
        [SNew(STextBlock).Text_Lambda([this] { const auto S = State(); return FText::FromString(FString::Printf(TEXT("Difficulty %d  ·  Score %lld  ·  Lives %d  ·  Moves %lld  ·  Hints %lld  ·  Elapsed %lld s%s"), S.Difficulty, S.Score, S.Lives, S.MoveCount, S.HintCount, S.ElapsedSeconds, S.TimeLimitSeconds > 0 ? *FString::Printf(TEXT("  ·  Remaining %lld s"), S.SecondsLeft) : TEXT(""))); }).AutoWrapText(true)]
        + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 0, 0, 10)[Grid]
        + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 0, 0, 10)[Digits]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
        [
            SNew(SCheckBox).IsEnabled_Lambda([this] { return State().bCanAct; })
                .IsChecked_Lambda([this] { return bSudokuPencilMode ? ECheckBoxState::Checked : ECheckBoxState::Unchecked; })
                .OnCheckStateChanged_Lambda([this](ECheckBoxState Checked)
                {
                    SyncSudokuPresentation(State());
                    if (Checked != ECheckBoxState::Undetermined && (Checked == ECheckBoxState::Checked) != bSudokuPencilMode) ToggleSudokuPencil();
                    FocusBoard();
                })
            [SNew(STextBlock).Text(FText::FromString(TEXT("Pencil notes (N / Space)")))]
        ]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
        [SNew(STextBlock).Text_Lambda([this]
        {
            const auto S = State();
            if (S.Cells.Num() != 81) return FText::GetEmpty();
            int32 Filled = 0;
            for (int32 Value : S.Cells) if (Value != 0) ++Filled;
            return FText::FromString(FString::Printf(TEXT("Filled %d / 81. Notes clear on New, Open, Resume, Connect account or close. Saves keep the board. Erase an answer before adding notes. Repeated digits are highlighted."), Filled));
        }).AutoWrapText(true)]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)[Button(TEXT("Undo"), [this] { if (Game.IsValid()) Game->SudokuUndo(); }, [this] { return State().bCanAct; })]
            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)[Button(TEXT("Redo"), [this] { if (Game.IsValid()) Game->SudokuRedo(); }, [this] { return State().bCanAct; })]
            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)[Button(TEXT("Hint (Java gem cost)"), [this] { HintConfirmationGameId.Reset(); if (Game.IsValid()) Game->RequestSudokuHint(); }, [this] { return State().bCanAct; })]
            + SHorizontalBox::Slot().AutoWidth()[Button(TEXT("Save to Java"), [this] { if (Game.IsValid()) Game->SaveSudokuGame(); }, [this] { const auto S = State(); return S.bReady && S.bOwner && !S.bBusy; })]
        ]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)
        [
            SNew(SVerticalBox).Visibility_Lambda([this]
            {
                const auto S = State();
                return !HintConfirmationGameId.IsEmpty() && HintConfirmationGameId == S.SessionId && S.bCanAct
                    ? EVisibility::Visible : EVisibility::Collapsed;
            })
            + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 6)
            [SNew(STextBlock).Text(FText::FromString(TEXT("Buy a hint for this game? Hints cost gems at the Java service's current price."))).AutoWrapText(true)]
            + SVerticalBox::Slot().AutoHeight()
            [
                SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
                [Button(TEXT("Buy hint"), [this] { ConfirmSudokuHint(); }, [this] { const auto S = State(); return S.bCanAct && !HintConfirmationGameId.IsEmpty() && HintConfirmationGameId == S.SessionId; })]
                + SHorizontalBox::Slot().AutoWidth()[Button(TEXT("Cancel hint"), [this] { HintConfirmationGameId.Reset(); })]
            ]
        ]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().FillWidth(1).Padding(0, 0, 6, 0)[SAssignNew(ResumeBox, SEditableTextBox).HintText(FText::FromString(TEXT("Java game ID to open or resume")))]
            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)[Button(TEXT("Open"), [this] { HintConfirmationGameId.Reset(); if (Game.IsValid() && ResumeBox.IsValid() && Game->OpenSudokuGame(ResumeBox->GetText().ToString())) ResetSudokuPresentation(); }, [this] { return Game.IsValid() && Game->HasCredentials() && !State().bBusy; })]
            + SHorizontalBox::Slot().AutoWidth()[Button(TEXT("Resume"), [this] { HintConfirmationGameId.Reset(); if (Game.IsValid() && ResumeBox.IsValid() && Game->ResumeSudokuGame(ResumeBox->GetText().ToString())) ResetSudokuPresentation(); }, [this] { return Game.IsValid() && Game->HasCredentials() && !State().bBusy; })]
        ]
        + SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text_Lambda([this] { const auto S = State(); return FText::FromString(TEXT("Game ID: ") + S.SessionId + (S.bSolved ? TEXT("  ·  Java reports solved") : S.bTimeUp ? TEXT("  ·  Java reports time expired") : TEXT(""))); }).AutoWrapText(true)]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 6, 0, 0)
        [SNew(STextBlock).Text(FText::FromString(TEXT("Board keys: arrows wrap selection; type 0–9 / numpad to enter; N / Space toggles pencil notes; Backspace / Delete erases answer and notes; Home / End and Page Up / Down select row or column ends; Ctrl+Z / Ctrl+Y undo / redo; H asks before buying a hint; Escape closes the cabinet."))).AutoWrapText(true)];
}
TSharedRef<SWidget> SDaedalusJavaArcade::SudokuMode(const TCHAR* Label, bool SDaedalusJavaArcade::* Field)
{
    return SNew(SCheckBox)
        .IsEnabled_Lambda([this] { return !State().bBusy; })
        .IsChecked_Lambda([this, Field] { return this->*Field ? ECheckBoxState::Checked : ECheckBoxState::Unchecked; })
        .OnCheckStateChanged_Lambda([this, Field](ECheckBoxState Checked)
        {
            if (Checked != ECheckBoxState::Undetermined) this->*Field = Checked == ECheckBoxState::Checked;
            FocusBoard();
        })
        [SNew(STextBlock).Text(FText::FromString(Label))];
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
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 12)[BlackjackSettings()]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)
        [
            SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)
            [SNew(SButton).Text_Lambda([this]
                {
                    const auto S = State();
                    return FText::FromString(S.Phase == TEXT("INSURANCE") && S.PlayerHands.IsValidIndex(0) && S.PlayerHands[0].bBlackjack
                        ? TEXT("Take even money") : TEXT("Accept insurance"));
                })
                .IsEnabled_Lambda([this] { return Game.IsValid() && Game->IsBlackjackActionLegal(TEXT("insurance")) && State().bInsuranceAcceptAllowed; })
                .OnClicked_Lambda([this] { if (Game.IsValid()) Game->SubmitBlackjackAction(TEXT("insurance"), 0, true); FocusBoard(); return FReply::Handled(); })]
            + SHorizontalBox::Slot().AutoWidth().Padding(0, 0, 6, 0)[Button(TEXT("Decline insurance"), [this] { if (Game.IsValid()) Game->SubmitBlackjackAction(TEXT("insurance"), 0, false); }, [this] { return Game.IsValid() && Game->IsBlackjackActionLegal(TEXT("insurance")); })]
            + SHorizontalBox::Slot().AutoWidth()[Button(TEXT("End Java session"), [this] { if (Game.IsValid()) Game->CloseRemoteBlackjackSession(); }, [this] { const auto S = State(); return S.bReady && !S.bBusy && !S.bRemoteClosed; })]
        ]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)
        [Button(TEXT("Reset table and stats (1000 simulated credits)"), [this] { if (Game.IsValid()) Game->SubmitBlackjackAction(TEXT("newSession")); },
            [this] { return Game.IsValid() && Game->IsBlackjackActionLegal(TEXT("newSession")); })]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 12)
        [SNew(STextBlock).Text(this, &SDaedalusJavaArcade::BlackjackDetailsText).AutoWrapText(true)]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
        [SNew(STextBlock).Text(FText::FromString(TEXT("Table keys: Enter deal; R rebet; H hit; S stand; D double; P split; U surrender; C clear; I accept insurance / even money; N decline; 1–5 / numpad bet 1 / 5 / 25 / 100 / 500; L reload. Disabled actions stay unavailable. Escape closes the cabinet."))).AutoWrapText(true)]
        + SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(TEXT("Java hides the dealer hole card and future shoe. Closing this cabinet cancels local work; end the Java session first when ready. Unreached sessions expire in Java."))).AutoWrapText(true)];
}
TSharedRef<SWidget> SDaedalusJavaArcade::BlackjackRule(const TCHAR* Label, const TCHAR* Rule, bool FDaedalusJavaBlackjackRules::* Field)
{
    const FString RuleName(Rule);
    return SNew(SCheckBox)
        .IsEnabled_Lambda([this] { return Game.IsValid() && State().bBlackjackDetailsAvailable && Game->IsBlackjackActionLegal(TEXT("setRule")); })
        .IsChecked_Lambda([this, Field] { return State().BlackjackRules.*Field ? ECheckBoxState::Checked : ECheckBoxState::Unchecked; })
        .OnCheckStateChanged_Lambda([this, RuleName](ECheckBoxState Checked)
        {
            if (Game.IsValid() && Checked != ECheckBoxState::Undetermined) Game->SetBlackjackRule(RuleName, Checked == ECheckBoxState::Checked);
            FocusBoard();
        })
        [SNew(STextBlock).Text(FText::FromString(Label))];
}
TSharedRef<SWidget> SDaedalusJavaArcade::BlackjackSettings()
{
    auto Decks = SNew(SHorizontalBox);
    Decks->AddSlot().AutoWidth().Padding(0, 0, 8, 0)[SNew(STextBlock).Text(FText::FromString(TEXT("Decks:")))];
    for (int32 Count : { 1, 2, 4, 6, 8 })
    {
        const FString Label = FString::FromInt(Count);
        Decks->AddSlot().AutoWidth().Padding(0, 0, 6, 0)
        [Button(*Label, [this, Count] { if (Game.IsValid()) Game->SetBlackjackDecks(Count); },
            [this, Count] { return Game.IsValid() && State().bBlackjackDetailsAvailable && State().BlackjackRules.Decks != Count && Game->IsBlackjackActionLegal(TEXT("setDecks")); })];
    }
    auto Hands = SNew(SHorizontalBox);
    Hands->AddSlot().AutoWidth().Padding(0, 0, 8, 0)[SNew(STextBlock).Text(FText::FromString(TEXT("Maximum hands:")))];
    for (int32 Count : { 2, 3, 4 })
    {
        const FString Label = FString::FromInt(Count);
        Hands->AddSlot().AutoWidth().Padding(0, 0, 6, 0)
        [Button(*Label, [this, Count] { if (Game.IsValid()) Game->SetBlackjackSplitLimit(Count); },
            [this, Count] { return Game.IsValid() && State().bBlackjackDetailsAvailable && State().BlackjackRules.MaxHands != Count && Game->IsBlackjackActionLegal(TEXT("setSplitLimit")); })];
    }
    return SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)
        [SNew(STextBlock).Text_Lambda([this]
        {
            const auto S = State();
            return FText::FromString(S.bBlackjackDetailsAvailable
                ? FString::Printf(TEXT("Table settings: %d decks, up to %d hands. Changes apply after the table confirms them, between rounds."), S.BlackjackRules.Decks, S.BlackjackRules.MaxHands)
                : TEXT("Table settings are available after starting a Java session."));
        }).AutoWrapText(true)]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 6)[Decks]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 8)[Hands]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 4)[BlackjackRule(TEXT("Dealer hits soft 17"), TEXT("dealerHitsSoft17"), &FDaedalusJavaBlackjackRules::bDealerHitsSoft17)]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 4)[BlackjackRule(TEXT("Late surrender"), TEXT("lateSurrender"), &FDaedalusJavaBlackjackRules::bLateSurrender)]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 4)[BlackjackRule(TEXT("Offer insurance"), TEXT("offerInsurance"), &FDaedalusJavaBlackjackRules::bOfferInsurance)]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 4)[BlackjackRule(TEXT("Double after split"), TEXT("doubleAfterSplit"), &FDaedalusJavaBlackjackRules::bDoubleAfterSplit)]
        + SVerticalBox::Slot().AutoHeight()[BlackjackRule(TEXT("Split aces receive one card"), TEXT("splitAcesOneCard"), &FDaedalusJavaBlackjackRules::bSplitAcesOneCard)];
}
FText SDaedalusJavaArcade::BlackjackDetailsText() const
{
    const auto S = State();
    if (!S.bBlackjackDetailsAvailable) return FText::GetEmpty();
    const auto& R = S.BlackjackRules;
    const auto& T = S.BlackjackStats;
    const auto& Q = S.BlackjackShoe;
    FString Text = FString::Printf(TEXT("Blackjack payout %d:%d · Insurance payout %d:%d · Shoe penetration %.0f%%\nShoe: %d decks, %d cards remaining, reshuffle at %d remaining%s"),
        R.BlackjackPayoutNum, R.BlackjackPayoutDen, R.InsurancePayoutNum, R.InsurancePayoutDen, R.Penetration * 100.0,
        Q.Decks, Q.Remaining, Q.ReshuffleAt, Q.bNeedsShuffle ? TEXT(" · shuffle needed") : TEXT(""));
    Text += FString::Printf(TEXT("\nLast round net %lld · Insurance stake %lld · Insurance return %lld"), S.LastNet, S.LastInsurance, S.LastInsuranceReturn);
    if (!S.LastOutcomes.IsEmpty()) Text += TEXT("\nHand outcomes: ") + FString::Join(S.LastOutcomes, TEXT(", "));
    Text += FString::Printf(TEXT("\nSession: %d rounds · %d wins · %d losses · %d pushes · %d blackjacks · %d busts\n%d doubles · %d splits · %d surrenders · Peak credits %d\nWagered %s · Returned %s · Net %s"),
        T.Hands, T.Wins, T.Losses, T.Pushes, T.Blackjacks, T.Busts, T.Doubles, T.Splits, T.Surrenders, T.PeakBankroll, *T.TotalWagered, *T.TotalReturned, *T.Net);
    return FText::FromString(Text);
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
    if (S.Phase == TEXT("INSURANCE"))
        Text += S.PlayerHands.IsValidIndex(0) && S.PlayerHands[0].bBlackjack
            ? TEXT("\nDealer shows Ace. You have blackjack: take even money?")
            : TEXT("\nDealer shows Ace. Insurance?");
    if (S.bDealerValueAvailable)
        Text += FString::Printf(TEXT(" · Total %d%s%s%s"), S.DealerValue, S.bDealerSoft ? TEXT(" · soft") : TEXT(""), S.bDealerBust ? TEXT(" · bust") : TEXT(""), S.bDealerBlackjack ? TEXT(" · blackjack") : TEXT(""));
    if (S.InsuranceBet > 0) Text += FString::Printf(TEXT("\nInsurance stake %lld"), S.InsuranceBet);
    for (int32 I = 0; I < S.PlayerHands.Num(); ++I)
    {
        const auto& Hand = S.PlayerHands[I];
        Text += FString::Printf(TEXT("\n%sHand %d: %s  ·  Total %d  ·  Bet %lld"), I == S.ActiveHand ? TEXT("▶ ") : TEXT(""), I + 1, *Cards(S.PlayerHands[I].Cards), S.PlayerHands[I].Value, S.PlayerHands[I].Bet);
        if (Hand.bSoft) Text += TEXT(" · soft");
        if (Hand.bBust) Text += TEXT(" · bust");
        if (Hand.bBlackjack) Text += TEXT(" · blackjack");
        if (Hand.bDoubled) Text += TEXT(" · doubled");
        if (Hand.bSurrendered) Text += TEXT(" · surrendered");
        if (Hand.bFromSplit) Text += TEXT(" · split");
        if (Hand.bSplitAce) Text += TEXT(" · split ace");
        if (Hand.bStood) Text += TEXT(" · stood");
    }
    if (!S.ResultText.IsEmpty()) Text += TEXT("\n") + S.ResultText;
    return FText::FromString(Text);
}
FText SDaedalusJavaArcade::CellText(int32 Index) const
{
    const auto S = State();
    if (!S.Cells.IsValidIndex(Index)) return FText::FromString(TEXT("·"));
    if (S.Cells[Index] != 0) return FText::AsNumber(S.Cells[Index]);
    return FText::GetEmpty();
}
FText SDaedalusJavaArcade::CellNoteText(int32 Index, int32 Digit) const
{
    const auto S = State();
    return S.Cells.IsValidIndex(Index) && S.Cells[Index] == 0 && (PencilMask(Index, S) & (1 << Digit))
        ? FText::AsNumber(Digit) : FText::GetEmpty();
}
TSharedRef<SWidget> SDaedalusJavaArcade::SudokuCell(int32 Index)
{
    auto Marks = SNew(SGridPanel).FillColumn(0, 1.f).FillColumn(1, 1.f).FillColumn(2, 1.f)
        .FillRow(0, 1.f).FillRow(1, 1.f).FillRow(2, 1.f);
    for (int32 Digit = 1; Digit <= 9; ++Digit)
        Marks->AddSlot((Digit - 1) % 3, (Digit - 1) / 3).HAlign(HAlign_Center).VAlign(VAlign_Center)
        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 9))
            .ColorAndOpacity(FLinearColor(0.6f, 0.82f, 1.f)).Text(this, &SDaedalusJavaArcade::CellNoteText, Index, Digit)];
    return SNew(SOverlay).Visibility(EVisibility::HitTestInvisible)
        + SOverlay::Slot()[Marks]
        + SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
        [SNew(STextBlock).Font_Lambda([this, Index]
            {
                const auto S = State();
                return FCoreStyle::GetDefaultFontStyle(S.Givens.IsValidIndex(Index) && S.Givens[Index] ? "Bold" : "Regular", 20);
            }).Text(this, &SDaedalusJavaArcade::CellText, Index)];
}
FText SDaedalusJavaArcade::CellDescription(int32 Index) const
{
    const auto S = State();
    FString Description = FString::Printf(TEXT("Row %d, column %d: "), Index / 9 + 1, Index % 9 + 1);
    if (!S.Cells.IsValidIndex(Index)) return FText::FromString(Description + TEXT("no board"));
    if (S.Cells[Index] != 0)
        return FText::FromString(Description + FString::FromInt(S.Cells[Index])
            + (S.Givens.IsValidIndex(Index) && S.Givens[Index] ? TEXT(" (clue)") : TEXT(" (entry)")));
    TArray<FString> Marks;
    for (int32 Digit = 1; Digit <= 9; ++Digit) if (PencilMask(Index, S) & (1 << Digit)) Marks.Add(FString::FromInt(Digit));
    return FText::FromString(Description + (Marks.IsEmpty() ? FString(TEXT("empty")) : TEXT("notes ") + FString::Join(Marks, TEXT(", "))));
}
bool SDaedalusJavaArcade::VisibleDuplicate(int32 Index, const FDaedalusJavaArcadeState& S)
{
    if (S.Cells.Num() != 81 || !S.Cells.IsValidIndex(Index) || S.Cells[Index] == 0) return false;
    const int32 Row = Index / 9, Col = Index % 9;
    for (int32 Other = 0; Other < 81; ++Other)
        if (Other != Index && S.Cells[Other] == S.Cells[Index]
            && (Other / 9 == Row || Other % 9 == Col || (Other / 27 == Row / 3 && Other % 9 / 3 == Col / 3))) return true;
    return false; // Cosmetic only: never rejects a move or decides completion.
}
FSlateColor SDaedalusJavaArcade::CellColor(int32 Index) const
{
    const auto S = State();
    const bool bGiven = S.Givens.IsValidIndex(Index) && S.Givens[Index];
    if (VisibleDuplicate(Index, S)) return FLinearColor(0.7f, 0.13f, 0.13f, 1.f);
    if (SelectedCell == Index) return bGiven ? FLinearColor(0.12f, 0.44f, 0.5f, 1.f) : FLinearColor(0.06f, 0.35f, 0.42f, 1.f);
    if (S.Cells.IsValidIndex(Index) && S.Cells.IsValidIndex(SelectedCell) && S.Cells[SelectedCell] != 0 && S.Cells[Index] == S.Cells[SelectedCell])
        return bGiven ? FLinearColor(0.42f, 0.35f, 0.6f, 1.f) : FLinearColor(0.33f, 0.27f, 0.54f, 1.f);
    if (Index / 9 == SelectedCell / 9 || Index % 9 == SelectedCell % 9
        || (Index / 27 == SelectedCell / 27 && Index % 9 / 3 == SelectedCell % 9 / 3))
        return bGiven ? FLinearColor(0.29f, 0.29f, 0.38f, 1.f) : FLinearColor(0.16f, 0.16f, 0.28f, 1.f);
    return bGiven ? FLinearColor(0.24f, 0.24f, 0.24f, 1.f) : FLinearColor(0.12f, 0.12f, 0.12f, 1.f);
}
FReply SDaedalusJavaArcade::SelectCell(int32 Index) { SyncSudokuPresentation(State()); SelectedCell = FMath::Clamp(Index, 0, 80); FocusBoard(); return FReply::Handled(); }
void SDaedalusJavaArcade::FocusBoard()
{
    if (Game.IsValid() && FSlateApplication::IsInitialized() && Game->GetSlateUserIndex() != INDEX_NONE)
        FSlateApplication::Get().SetUserFocus(Game->GetSlateUserIndex(), SharedThis(this), EFocusCause::SetDirectly);
}
FReply SDaedalusJavaArcade::OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    if (!Game.IsValid()) return FReply::Unhandled();
    const FKey Key = Event.GetKey();
    if (Key == EKeys::Escape) { Game->CloseArcade(); return FReply::Handled(); }
    // Only the focused board/table owns shortcuts. Text fields and Slate buttons keep
    // their own editing/activation behavior; another local user cannot submit actions.
    if (Key.IsGamepadKey() || !OwnsKeyboardEvent(Event)) return FReply::Unhandled();
    if (State().Game == EDaedalusJavaGame::Blackjack)
        return Event.IsControlDown() || Event.IsShiftDown() ? FReply::Unhandled() : HandleBlackjackKey(Key);
    SyncSudokuPresentation(State());
    if (Event.IsControlDown())
    {
        if (Key == EKeys::Z) { HintConfirmationGameId.Reset(); Game->SudokuUndo(); return FReply::Handled(); }
        if (Key == EKeys::Y) { HintConfirmationGameId.Reset(); Game->SudokuRedo(); return FReply::Handled(); }
        return FReply::Unhandled();
    }
    if (Key == EKeys::H)
    {
        const auto S = State();
        if (S.bCanAct) HintConfirmationGameId = S.SessionId; // No purchase until explicit confirmation.
        return FReply::Handled();
    }
    HintConfirmationGameId.Reset();
    if (Key == EKeys::N || Key == EKeys::SpaceBar) { ToggleSudokuPencil(); return FReply::Handled(); }
    int32 Row = SelectedCell / 9, Col = SelectedCell % 9;
    if (Key == EKeys::Left) --Col;
    else if (Key == EKeys::Right) ++Col;
    else if (Key == EKeys::Up) --Row;
    else if (Key == EKeys::Down) ++Row;
    else if (Key == EKeys::Home) Col = 0;
    else if (Key == EKeys::End) Col = 8;
    else if (Key == EKeys::PageUp) Row = 0;
    else if (Key == EKeys::PageDown) Row = 8;
    else
    {
        // Digits enter only through OnKeyChar so shifted layouts/numpad cannot
        // dispatch the same intention once here and again as a typed character.
        if (Key == EKeys::BackSpace || Key == EKeys::Delete) { EnterSudokuDigit(0); return FReply::Handled(); }
        return FReply::Unhandled();
    }
    SelectedCell = ((Row + 9) % 9) * 9 + (Col + 9) % 9;
    Invalidate(EInvalidateWidgetReason::Paint);
    return FReply::Handled();
}

bool SDaedalusJavaArcade::OwnsKeyboardEvent(const FInputEvent& Event) const
{
    return Game.IsValid() && !Event.IsRepeat() && Event.GetUserIndex() == Game->GetSlateUserIndex()
        && HasUserFocus(Event.GetUserIndex()).IsSet() && !Event.IsAltDown() && !Event.IsCommandDown();
}
FReply SDaedalusJavaArcade::OnKeyChar(const FGeometry& Geometry, const FCharacterEvent& Event)
{
    if (!OwnsKeyboardEvent(Event) || Event.IsControlDown() || State().Game != EDaedalusJavaGame::Sudoku) return FReply::Unhandled();
    const TCHAR Character = Event.GetCharacter();
    if (Character < TEXT('0') || Character > TEXT('9')) return FReply::Unhandled();
    EnterSudokuDigit(Character - TEXT('0'));
    return FReply::Handled();
}
void SDaedalusJavaArcade::Tick(const FGeometry& Geometry, const double CurrentTime, const float DeltaTime)
{
    SCompoundWidget::Tick(Geometry, CurrentTime, DeltaTime);
    SyncSudokuPresentation(State());
}
void SDaedalusJavaArcade::ResetSudokuPresentation()
{
    NotesGameId.Reset(); LocalPencilMasks.Reset(); LocalPencilOverrides.Reset();
    bSudokuPencilMode = false; SelectedCell = 0;
}
void SDaedalusJavaArcade::SyncSudokuPresentation(const FDaedalusJavaArcadeState& S)
{
    if (S.Game != EDaedalusJavaGame::Sudoku) { ResetSudokuPresentation(); return; }
    // Never bind local notes to requested IDs or an incomplete bootstrap response.
    if (S.SessionId.IsEmpty() || S.Cells.Num() != 81 || S.Givens.Num() != 81 || S.SessionId == NotesGameId) return;
    NotesGameId = S.SessionId;
    LocalPencilMasks.Init(0, 81); LocalPencilOverrides.Init(false, 81);
    bSudokuPencilMode = false; SelectedCell = 0;
    for (int32 Index = 0; Index < 81; ++Index) if (S.Cells[Index] == 0) { SelectedCell = Index; break; }
    Invalidate(EInvalidateWidgetReason::Paint);
}
int32 SDaedalusJavaArcade::PencilMask(int32 Index, const FDaedalusJavaArcadeState& S) const
{
    if (!S.SessionId.IsEmpty() && S.SessionId == NotesGameId && LocalPencilOverrides.IsValidIndex(Index)
        && LocalPencilOverrides[Index] && LocalPencilMasks.IsValidIndex(Index)) return LocalPencilMasks[Index];
    return S.PencilMasks.IsValidIndex(Index) ? S.PencilMasks[Index] : 0;
}
bool SDaedalusJavaArcade::CanEnterSudokuDigit(int32 Value) const
{
    const auto S = State();
    return Game.IsValid() && S.Game == EDaedalusJavaGame::Sudoku && S.bCanAct && Value >= 0 && Value <= 9
        && S.Cells.IsValidIndex(SelectedCell) && S.Givens.IsValidIndex(SelectedCell) && !S.Givens[SelectedCell]
        && (Value == 0 || !bSudokuPencilMode || S.Cells[SelectedCell] == 0);
}
void SDaedalusJavaArcade::EnterSudokuDigit(int32 Value)
{
    const auto S = State();
    SyncSudokuPresentation(S);
    if (!CanEnterSudokuDigit(Value) || NotesGameId != S.SessionId || !LocalPencilMasks.IsValidIndex(SelectedCell)) return;
    HintConfirmationGameId.Reset();
    if (bSudokuPencilMode && Value != 0)
    {
        LocalPencilMasks[SelectedCell] = PencilMask(SelectedCell, S) ^ (1 << Value);
        LocalPencilOverrides[SelectedCell] = true;
    }
    else
    {
        // An explicit zero override prevents later snapshot fallback restoring erased notes.
        if (Value == 0) { LocalPencilMasks[SelectedCell] = 0; LocalPencilOverrides[SelectedCell] = true; }
        if (S.Cells[SelectedCell] != Value) Game->SubmitSudokuMove(SelectedCell / 9, SelectedCell % 9, Value);
    }
    Invalidate(EInvalidateWidgetReason::Paint);
}
void SDaedalusJavaArcade::ToggleSudokuPencil()
{
    const auto S = State();
    SyncSudokuPresentation(S);
    if (S.Game != EDaedalusJavaGame::Sudoku || !S.bCanAct || NotesGameId.IsEmpty()) return;
    bSudokuPencilMode = !bSudokuPencilMode;
    HintConfirmationGameId.Reset();
    Invalidate(EInvalidateWidgetReason::Paint);
}
TSharedRef<SWidget> SDaedalusJavaArcade::SudokuDigitButton(int32 Value)
{
    return SNew(SButton).ContentPadding(FMargin(8.f, 4.f)).IsEnabled_Lambda([this, Value] { return CanEnterSudokuDigit(Value); })
        .OnClicked_Lambda([this, Value] { EnterSudokuDigit(Value); FocusBoard(); return FReply::Handled(); })
        [
            SNew(SVerticalBox)
            + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
            [SNew(STextBlock).Text(FText::FromString(Value == 0 ? FString(TEXT("Erase")) : FString::FromInt(Value)))]
            + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)
            [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Regular", 9)).Text_Lambda([this, Value]
            {
                const auto S = State();
                if (Value == 0 || S.Cells.Num() != 81) return FText::GetEmpty();
                int32 Count = 0;
                for (int32 Cell : S.Cells) if (Cell == Value) ++Count;
                return FText::FromString(FString::Printf(TEXT("%d left"), FMath::Max(0, 9 - Count)));
            })]
        ];
}

void SDaedalusJavaArcade::ConfirmSudokuHint()
{
    const FString ConfirmedGameId = MoveTemp(HintConfirmationGameId);
    HintConfirmationGameId.Reset();
    const auto S = State();
    if (Game.IsValid() && S.Game == EDaedalusJavaGame::Sudoku && S.bCanAct
        && !ConfirmedGameId.IsEmpty() && ConfirmedGameId == S.SessionId) Game->RequestSudokuHint();
}

FReply SDaedalusJavaArcade::HandleBlackjackKey(const FKey& Key)
{
    // Original Swing/GDX TableKeys call the same enabled controls; Java owns legality.
    FString Action;
    int32 Amount = 0;
    bool bAcceptInsurance = false;
    if (Key == EKeys::Enter) Action = TEXT("deal");
    else if (Key == EKeys::R) Action = TEXT("rebet");
    else if (Key == EKeys::H) Action = TEXT("hit");
    else if (Key == EKeys::S) Action = TEXT("stand");
    else if (Key == EKeys::D) Action = TEXT("double");
    else if (Key == EKeys::P) Action = TEXT("split");
    else if (Key == EKeys::U) Action = TEXT("surrender");
    else if (Key == EKeys::C) Action = TEXT("clearBet");
    else if (Key == EKeys::I) { Action = TEXT("insurance"); bAcceptInsurance = true; }
    else if (Key == EKeys::N) Action = TEXT("insurance");
    else if (Key == EKeys::L) Action = TEXT("reload");
    else
    {
        const FKey Keys[] = { EKeys::One, EKeys::Two, EKeys::Three, EKeys::Four, EKeys::Five };
        const FKey Pads[] = { EKeys::NumPadOne, EKeys::NumPadTwo, EKeys::NumPadThree, EKeys::NumPadFour, EKeys::NumPadFive };
        const int32 Chips[] = { 1, 5, 25, 100, 500 };
        for (int32 I = 0; I < 5; ++I) if (Key == Keys[I] || Key == Pads[I]) { Action = TEXT("bet"); Amount = Chips[I]; break; }
    }
    if (Action.IsEmpty()) return FReply::Unhandled();
    if (Game.IsValid() && Game->IsBlackjackActionLegal(Action, Amount)
        && (!bAcceptInsurance || State().bInsuranceAcceptAllowed)) Game->SubmitBlackjackAction(Action, Amount, bAcceptInsurance);
    return FReply::Handled(); // Recognized disabled actions are inert and consumed.
}
