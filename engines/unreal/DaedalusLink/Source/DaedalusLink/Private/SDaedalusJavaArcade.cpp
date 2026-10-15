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
        const FString Label = FString::Printf(TEXT("New %d"), Difficulty);
        Starts->AddSlot().AutoWidth().Padding(0, 0, 6, 0)
        [Button(*Label, [this, Difficulty] { if (Game.IsValid()) Game->StartSudokuGameWithModes(Difficulty, bNewSudokuChaos, bNewSudokuMirror, bNewSudokuTimeAttack); }, [this] { return Game.IsValid() && Game->HasCredentials() && !State().bBusy; })];
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
        [Button(*Label, [this, Value] { if (Game.IsValid()) Game->SubmitSudokuMove(SelectedCell / 9, SelectedCell % 9, Value); }, [this] { const auto S = State(); return S.bCanAct && S.Givens.IsValidIndex(SelectedCell) && !S.Givens[SelectedCell]; })];
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
        [SNew(STextBlock).Text_Lambda([this] { const auto S = State(); return FText::FromString(FString::Printf(TEXT("Difficulty %d  ·  Score %lld  ·  Lives %d  ·  Moves %lld  ·  Elapsed %lld s%s"), S.Difficulty, S.Score, S.Lives, S.MoveCount, S.ElapsedSeconds, S.TimeLimitSeconds > 0 ? *FString::Printf(TEXT("  ·  Remaining %lld s"), S.SecondsLeft) : TEXT(""))); }).AutoWrapText(true)]
        + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 0, 0, 10)[Grid]
        + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0, 0, 0, 10)[Digits]
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
            + SHorizontalBox::Slot().AutoWidth()[Button(TEXT("End Java session"), [this] { if (Game.IsValid()) Game->CloseRemoteBlackjackSession(); }, [this] { return State().bReady && !State().bRemoteClosed; })]
        ]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 10)
        [Button(TEXT("Reset table and stats (1000 simulated credits)"), [this] { if (Game.IsValid()) Game->SubmitBlackjackAction(TEXT("newSession")); },
            [this] { return Game.IsValid() && Game->IsBlackjackActionLegal(TEXT("newSession")); })]
        + SVerticalBox::Slot().AutoHeight().Padding(0, 0, 0, 12)
        [SNew(STextBlock).Text(this, &SDaedalusJavaArcade::BlackjackDetailsText).AutoWrapText(true)]
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
    if (State().Game != EDaedalusJavaGame::Sudoku || Event.IsRepeat()) return FReply::Unhandled();
    int32 Row = SelectedCell / 9, Col = SelectedCell % 9;
    if (Key == EKeys::Left) --Col;
    else if (Key == EKeys::Right) ++Col;
    else if (Key == EKeys::Up) --Row;
    else if (Key == EKeys::Down) ++Row;
    else
    {
        const FKey Keys[] = { EKeys::Zero, EKeys::One, EKeys::Two, EKeys::Three, EKeys::Four, EKeys::Five, EKeys::Six, EKeys::Seven, EKeys::Eight, EKeys::Nine };
        const FKey Pads[] = { EKeys::NumPadZero, EKeys::NumPadOne, EKeys::NumPadTwo, EKeys::NumPadThree, EKeys::NumPadFour, EKeys::NumPadFive, EKeys::NumPadSix, EKeys::NumPadSeven, EKeys::NumPadEight, EKeys::NumPadNine };
        for (int32 Value = 0; Value <= 9; ++Value) if (Key == Keys[Value] || Key == Pads[Value]) { Game->SubmitSudokuMove(Row, Col, Value); return FReply::Handled(); }
        if (Key == EKeys::BackSpace || Key == EKeys::Delete) { Game->SubmitSudokuMove(Row, Col, 0); return FReply::Handled(); }
        return FReply::Unhandled();
    }
    SelectedCell = FMath::Clamp(Row, 0, 8) * 9 + FMath::Clamp(Col, 0, 8);
    Invalidate(EInvalidateWidgetReason::Paint);
    return FReply::Handled();
}
