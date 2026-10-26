// SPDX-License-Identifier: MIT
#include "SDaedalusSynapsePanel.h"

#include "DaedalusSynapseTerminal.h"
#include "InputCoreTypes.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSeparator.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

FDaedalusSynapseView SDaedalusSynapsePanel::View() const
{
    return Terminal.IsValid() ? Terminal->GetView() : FDaedalusSynapseView();
}

bool SDaedalusSynapsePanel::HasOpenTerminal() const
{
    return Terminal.IsValid() && Terminal->IsPanelOpen();
}

bool SDaedalusSynapsePanel::OwnsUserFocus(int32 UserIndex) const
{
    return HasUserFocus(UserIndex).IsSet() || HasUserFocusedDescendants(UserIndex);
}

SDaedalusSynapsePanel::~SDaedalusSynapsePanel()
{
    if (PairingBox.IsValid()) PairingBox->SetText(FText::GetEmpty());
}

TSharedRef<SWidget> SDaedalusSynapsePanel::MakePairingInput()
{
    return SAssignNew(PairingBox, SEditableTextBox)
        .IsPassword(true)
        .HintText(FText::FromString(TEXT("Paste the private Synapse study-desk link")))
        .IsEnabled_Lambda([this] { return HasOpenTerminal() && View().bCanPair; })
        .ClearKeyboardFocusOnCommit(false)
        .OnVerifyTextChanged_Lambda([](const FText& Text, FText& Error)
        {
            if (Text.ToString().Len() <= 256) return true;
            Error = FText::FromString(TEXT("Use the private link shown by Synapse."));
            return false;
        });
}

void SDaedalusSynapsePanel::ClearPairingInput()
{
    if (PairingBox.IsValid()) PairingBox->SetText(FText::GetEmpty());
    PairingBox.Reset();
    // A new field has no Undo history that could restore the visible capability.
    if (PairingInputHost.IsValid()) PairingInputHost->SetContent(MakePairingInput());
}

TSharedRef<SWidget> SDaedalusSynapsePanel::Button(const TCHAR* Label,
    TFunction<void(ADaedalusSynapseTerminal&)> Action, TFunction<bool(const FDaedalusSynapseView&)> Enabled)
{
    return SNew(SButton).Text(FText::FromString(Label)).ContentPadding(FMargin(12.f, 8.f))
        .IsEnabled_Lambda([this, Enabled] { return HasOpenTerminal() && Enabled(View()); })
        .OnClicked_Lambda([this, Action]
        {
            if (HasOpenTerminal()) Action(*Terminal.Get());
            return FReply::Handled();
        });
}

void SDaedalusSynapsePanel::Construct(const FArguments& Args)
{
    Terminal = Args._Terminal;
    TSharedRef<SWrapBox> Scores = SNew(SWrapBox).UseAllottedSize(true);
    const TCHAR* Labels[] = { TEXT("0 Blackout"), TEXT("1 Wrong"), TEXT("2 Wrong / familiar"), TEXT("3 Hard"), TEXT("4 Good"), TEXT("5 Easy") };
    for (int32 Score = 0; Score <= 5; ++Score)
        Scores->AddSlot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))
        [Button(Labels[Score], [Score](ADaedalusSynapseTerminal& Actor) { Actor.ScoreCard(Score); },
            [](const FDaedalusSynapseView& State) { return State.bCanScore; })];

    ChildSlot
    [
        SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
        .BorderBackgroundColor(FLinearColor(0.02f, 0.035f, 0.055f, 0.97f)).Padding(24.f)
        .HAlign(HAlign_Center).VAlign(VAlign_Center)
        [
            SNew(SBox).MaxDesiredWidth(860.f).MaxDesiredHeight(740.f)
            [
                SNew(SScrollBox)
                + SScrollBox::Slot()
                [
                    SNew(SVerticalBox)
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)
                    [
                        SNew(SHorizontalBox)
                        + SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)
                        [SNew(STextBlock).Text(FText::FromString(TEXT("Synapse study desk"))).Font(FCoreStyle::GetDefaultFontStyle("Bold", 25))]
                        + SHorizontalBox::Slot().AutoWidth()
                        [SNew(SButton).Text(FText::FromString(TEXT("Close"))).OnClicked(this, &SDaedalusSynapsePanel::Close)]
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)
                    [SNew(STextBlock).Text(FText::FromString(TEXT("In Synapse, choose a track and enable Study desk. Recall each card, reveal its answer, then choose your score."))).AutoWrapText(true)]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [
                        SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
                        .BorderBackgroundColor(FLinearColor(0.045f, 0.10f, 0.13f, 1.f)).Padding(12.f)
                        [SNew(STextBlock).Text_Lambda([this] { return FText::FromString(View().Status); }).AutoWrapText(true)]
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [
                        SNew(SHorizontalBox)
                        + SHorizontalBox::Slot().FillWidth(1.f).Padding(0.f, 0.f, 8.f, 0.f)
                        [SAssignNew(PairingInputHost, SBox)[MakePairingInput()]]
                        + SHorizontalBox::Slot().AutoWidth()
                        [SNew(SButton).Text(FText::FromString(TEXT("Pair Synapse"))).ContentPadding(FMargin(12.f, 8.f))
                            .IsEnabled_Lambda([this] { return HasOpenTerminal() && View().bCanPair; }).OnClicked(this, &SDaedalusSynapsePanel::Pair)]
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)[SNew(SSeparator)]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)
                    [SNew(STextBlock).Text(this, &SDaedalusSynapsePanel::CardSummary).AutoWrapText(true)]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [
                        SNew(SVerticalBox).Visibility_Lambda([this] { return View().bHasCard ? EVisibility::Visible : EVisibility::Collapsed; })
                        + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)
                        [SNew(STextBlock).Text_Lambda([this] { return FText::FromString(View().Prompt); }).Font(FCoreStyle::GetDefaultFontStyle("Bold", 19)).AutoWrapText(true)]
                        + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                        [SNew(STextBlock).Text_Lambda([this] { return FText::FromString(View().Context); }).AutoWrapText(true)
                            .Visibility_Lambda([this] { return View().Context.IsEmpty() ? EVisibility::Collapsed : EVisibility::Visible; })]
                        + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                        [Button(TEXT("Reveal answer"), [](ADaedalusSynapseTerminal& Actor) { Actor.RevealCard(); }, [](const FDaedalusSynapseView& State) { return State.bCanReveal; })]
                        + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                        [
                            SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
                            .BorderBackgroundColor(FLinearColor(0.055f, 0.07f, 0.09f, 1.f)).Padding(14.f)
                            .Visibility_Lambda([this] { return View().bRevealed ? EVisibility::Visible : EVisibility::Collapsed; })
                            [SNew(STextBlock).Text_Lambda([this] { const auto State = View(); return FText::FromString(State.bRevealed ? State.Answer : FString()); })
                                .Font_Lambda([this] { return FCoreStyle::GetDefaultFontStyle(View().Kind.Equals(TEXT("code"), ESearchCase::IgnoreCase) ? "Mono" : "Regular", 16); }).AutoWrapText(true)]
                        ]
                        + SVerticalBox::Slot().AutoHeight()[Scores]
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)
                    [SNew(STextBlock).Text(this, &SDaedalusSynapsePanel::SaveGuidance).AutoWrapText(true)]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [
                        SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
                        .BorderBackgroundColor(FLinearColor(0.035f, 0.11f, 0.085f, 1.f)).Padding(12.f)
                        .Visibility_Lambda([this] { return View().bHasReceipt ? EVisibility::Visible : EVisibility::Collapsed; })
                        [SNew(STextBlock).Text_Lambda([this] { const auto State = View(); return FText::FromString(State.bHasReceipt ? State.ReceiptSummary : FString()); }).AutoWrapText(true)]
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [
                        SNew(SWrapBox).UseAllottedSize(true)
                        + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))
                        [Button(TEXT("Retry same save"), [](ADaedalusSynapseTerminal& Actor) { Actor.RetrySameSave(); }, [](const FDaedalusSynapseView& State) { return State.bCanRetry; })]
                        + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))
                        [Button(TEXT("Refresh cards"), [](ADaedalusSynapseTerminal& Actor) { Actor.RefreshCards(); }, [](const FDaedalusSynapseView& State) { return State.bCanRefresh; })]
                        + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))
                        [Button(TEXT("Disconnect Synapse"), [](ADaedalusSynapseTerminal& Actor) { Actor.DisconnectApp(); }, [](const FDaedalusSynapseView& State) { return State.bCanDisconnect; })]
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
                    [SNew(STextBlock).Text(FText::FromString(TEXT("Closing or revoking access cannot undo a saved review. An unconfirmed review may already be saved. Retry the same save before moving on; closing also clears this terminal's temporary retry details."))).AutoWrapText(true)]
                    + SVerticalBox::Slot().AutoHeight()
                    [SNew(STextBlock).Text(FText::FromString(TEXT("The private pairing link stays in memory. Esc or controller Menu closes this desk."))).AutoWrapText(true)]
                ]
            ]
        ]
    ];
}

FReply SDaedalusSynapsePanel::Pair()
{
    FString Link = PairingBox.IsValid() ? PairingBox->GetText().ToString() : FString();
    ClearPairingInput();
    if (HasOpenTerminal()) Terminal->PairLocalApp(Link);
    Link.Reset();
    return FReply::Handled();
}

FReply SDaedalusSynapsePanel::Close()
{
    ClearPairingInput();
    if (Terminal.IsValid()) Terminal->ClosePanel();
    return FReply::Handled();
}

FText SDaedalusSynapsePanel::CardSummary() const
{
    const auto State = View();
    if (State.bHasReceipt) return FText::FromString(TEXT("Review saved. Refresh cards for the current due count."));
    if (!State.bPaired) return FText::FromString(TEXT("Pair with the study desk approved in your local Synapse app."));
    return FText::FromString(FString::Printf(TEXT("%d due cards in the %d-card selection%s"), State.DueCount, State.SelectedCount,
        State.bHasCard ? TEXT("") : TEXT(" — no card displayed")));
}

FText SDaedalusSynapsePanel::SaveGuidance() const
{
    const auto State = View();
    if (State.bUncertain) return FText::FromString(TEXT("The last action is unconfirmed. A review may already be saved; follow the status above and retry the same save when available."));
    if (State.bHasReceipt) return FText::FromString(TEXT("Synapse confirmed the saved review below. Refresh cards when you are ready to continue."));
    if (State.bHasCard && !State.bRevealed) return FText::FromString(TEXT("Recall the answer, then reveal it before choosing a score."));
    if (State.bHasCard) return FText::FromString(TEXT("Choose a score yourself. Synapse applies and saves its existing review schedule."));
    return FText::GetEmpty();
}

FReply SDaedalusSynapsePanel::OnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    if (Event.GetKey() == EKeys::Escape || Event.GetKey() == EKeys::Gamepad_Special_Right) return Close();
    return SCompoundWidget::OnPreviewKeyDown(Geometry, Event);
}

FReply SDaedalusSynapsePanel::OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    if (Event.GetKey() == EKeys::Escape || Event.GetKey() == EKeys::Gamepad_Special_Right) return Close();
    return SCompoundWidget::OnKeyDown(Geometry, Event);
}
