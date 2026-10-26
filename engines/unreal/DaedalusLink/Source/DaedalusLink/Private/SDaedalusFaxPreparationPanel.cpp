// SPDX-License-Identifier: MIT
#include "SDaedalusFaxPreparationPanel.h"

#include "DaedalusFaxPreparationTerminal.h"
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

FDaedalusFaxPreparationView SDaedalusFaxPreparationPanel::View() const
{
    return Terminal.IsValid() ? Terminal->GetView() : FDaedalusFaxPreparationView();
}

bool SDaedalusFaxPreparationPanel::HasOpenTerminal() const
{
    return Terminal.IsValid() && Terminal->IsPanelOpen();
}

bool SDaedalusFaxPreparationPanel::OwnsUserFocus(int32 UserIndex) const
{
    return HasUserFocus(UserIndex).IsSet() || HasUserFocusedDescendants(UserIndex);
}

SDaedalusFaxPreparationPanel::~SDaedalusFaxPreparationPanel()
{
    if (PairingBox.IsValid()) PairingBox->SetText(FText::GetEmpty());
    PairingBox.Reset();
    ClearCancellation();
}

TSharedRef<SWidget> SDaedalusFaxPreparationPanel::MakePairingInput()
{
    return SAssignNew(PairingBox, SEditableTextBox).IsPassword(true)
        .HintText(FText::FromString(TEXT("Paste the private Fax Trident preparation link")))
        .IsEnabled_Lambda([this] { return HasOpenTerminal() && View().bCanPair; })
        .ClearKeyboardFocusOnCommit(false)
        .OnVerifyTextChanged_Lambda([](const FText& Text, FText& Error)
        {
            if (Text.ToString().Len() <= 256) return true;
            Error = FText::FromString(TEXT("Use the private preparation link shown by Fax Trident."));
            return false;
        });
}

void SDaedalusFaxPreparationPanel::ClearPairingInput()
{
    if (PairingBox.IsValid()) PairingBox->SetText(FText::GetEmpty());
    PairingBox.Reset();
    if (PairingInputHost.IsValid()) PairingInputHost->SetContent(MakePairingInput());
    ClearCancellation();
}

TSharedRef<SWidget> SDaedalusFaxPreparationPanel::Button(const TCHAR* Label,
    TFunction<void(ADaedalusFaxPreparationTerminal&)> Action, TFunction<bool(const FDaedalusFaxPreparationView&)> Enabled)
{
    return SNew(SButton).Text(FText::FromString(Label)).ContentPadding(FMargin(12.f, 8.f))
        .IsEnabled_Lambda([this, Enabled] { return HasOpenTerminal() && Enabled(View()); })
        .OnClicked_Lambda([this, Action, Enabled]
        {
            if (HasOpenTerminal() && Enabled(View()))
            {
                ClearCancellation();
                Action(*Terminal.Get());
            }
            return FReply::Handled();
        });
}

void SDaedalusFaxPreparationPanel::Construct(const FArguments& Args)
{
    Terminal = Args._Terminal;
    ChildSlot
    [
        SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
        .BorderBackgroundColor(FLinearColor(0.02f, 0.035f, 0.055f, 0.97f)).Padding(24.f)
        .HAlign(HAlign_Center).VAlign(VAlign_Center)
        [
            SNew(SBox).MaxDesiredWidth(900.f).MaxDesiredHeight(760.f)
            [
                SNew(SScrollBox) + SScrollBox::Slot()
                [
                    SNew(SVerticalBox)
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)
                    [
                        SNew(SHorizontalBox)
                        + SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)
                        [SNew(STextBlock).Text(FText::FromString(TEXT("Fax preparation desk"))).Font(FCoreStyle::GetDefaultFontStyle("Bold", 25))]
                        + SHorizontalBox::Slot().AutoWidth()
                        [SNew(SButton).Text(FText::FromString(TEXT("Close"))).OnClicked(this, &SDaedalusFaxPreparationPanel::Close)]
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)
                    [SNew(STextBlock).Text(FText::FromString(TEXT("In Fax Trident, prepare one selected PDF and explicitly approve local realm access. Pair its private preparation link here."))).AutoWrapText(true)]
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
                        [SNew(SButton).Text(FText::FromString(TEXT("Pair Fax Trident"))).ContentPadding(FMargin(12.f, 8.f))
                            .IsEnabled_Lambda([this] { return HasOpenTerminal() && View().bCanPair; }).OnClicked(this, &SDaedalusFaxPreparationPanel::Pair)]
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)[SNew(SSeparator)]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [SNew(STextBlock).Text(this, &SDaedalusFaxPreparationPanel::JobDetails).AutoWrapText(true)]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
                    [
                        SNew(SWrapBox).UseAllottedSize(true)
                        + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))
                        [Button(TEXT("Refresh selected job"), [](ADaedalusFaxPreparationTerminal& Actor) { Actor.RefreshJob(); },
                            [](const FDaedalusFaxPreparationView& State) { return State.bCanRefresh; })]
                        + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))
                        [Button(TEXT("Download review PDF"), [](ADaedalusFaxPreparationTerminal& Actor) { Actor.ExportPdf(); },
                            [](const FDaedalusFaxPreparationView& State) { return State.bCanExport; })]
                        + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))
                        [SNew(SButton).Text(FText::FromString(TEXT("Cancel prepared job..."))).ContentPadding(FMargin(12.f, 8.f))
                            .IsEnabled_Lambda([this] { return HasOpenTerminal() && View().bCanCancel; })
                            .OnClicked(this, &SDaedalusFaxPreparationPanel::ArmCancellation)]
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [
                        SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
                        .BorderBackgroundColor(FLinearColor(0.18f, 0.085f, 0.04f, 1.f)).Padding(12.f)
                        .Visibility_Lambda([this] { return IsCancellationArmed() ? EVisibility::Visible : EVisibility::Collapsed; })
                        [
                            SNew(SVerticalBox)
                            + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)
                            [SNew(STextBlock).Text(FText::FromString(TEXT("Cancel the selected preparation shown above? This asks the server to cancel that job and delete its snapshot. Its source upload keeps its one-hour lease. A racing action in the desktop app may prevent cancellation."))).AutoWrapText(true)]
                            + SVerticalBox::Slot().AutoHeight()
                            [
                                SNew(SWrapBox).UseAllottedSize(true)
                                + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))
                                [SNew(SButton).Text(FText::FromString(TEXT("Confirm cancellation of selected job"))).ContentPadding(FMargin(12.f, 8.f))
                                    .IsEnabled_Lambda([this] { return IsCancellationArmed(); }).OnClicked(this, &SDaedalusFaxPreparationPanel::ConfirmCancellation)]
                                + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))
                                [SNew(SButton).Text(FText::FromString(TEXT("Keep prepared job"))).ContentPadding(FMargin(12.f, 8.f))
                                    .OnClicked_Lambda([this] { ClearCancellation(); return FReply::Handled(); })]
                            ]
                        ]
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [SNew(STextBlock).Text(this, &SDaedalusFaxPreparationPanel::ActionGuidance).AutoWrapText(true)]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [Button(TEXT("Revoke local access"), [this](ADaedalusFaxPreparationTerminal& Actor) { ClearPairingInput(); Actor.DisconnectApp(); },
                        [](const FDaedalusFaxPreparationView& State) { return State.bCanDisconnect; })]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)
                    [SNew(STextBlock).Text(FText::FromString(TEXT("PREPARED means prepared, not sent. This object cannot upload, prepare, confirm or transmit a fax. The desktop app can act on the job separately; refresh to see its latest reported state."))).AutoWrapText(true)]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)
                    [SNew(STextBlock).Text(FText::FromString(TEXT("Closing clears this terminal and requests local grant revocation. Local revocation does not cancel the server job or delete the source upload; follow the status above for its result. The server keeps uploads for one hour and job documents for up to 24 hours. Saved PDF copies remain where you saved them."))).AutoWrapText(true)]
                    + SVerticalBox::Slot().AutoHeight()
                    [SNew(STextBlock).Text(FText::FromString(TEXT("The private pairing link stays in memory. Esc or controller Menu closes this desk."))).AutoWrapText(true)]
                ]
            ]
        ]
    ];
}

FText SDaedalusFaxPreparationPanel::JobDetails() const
{
    const auto State = View();
    if (!State.bHasJob) return FText::FromString(TEXT("No approved job displayed. Pair the preparation selected in your local Fax Trident app."));
    return FText::FromString(FString::Printf(TEXT("Approved job: %s\nRecipient: %s\nSHA-256: %s\nPages: %d  |  PDF bytes: %lld\nJob expires: %s\nLocal access expires: %s\nCurrent state reported by Fax Trident: %s"),
        *State.FaxId, *State.Recipient, *State.DocumentSha256, State.PageCount, static_cast<long long>(State.ByteCount),
        *State.ExpiresAt, *State.GrantExpiresAt, *State.JobState));
}

FText SDaedalusFaxPreparationPanel::ActionGuidance() const
{
    const auto State = View();
    if (State.bUncertain) return FText::FromString(TEXT("The last action is unconfirmed. If cancellation was requested, it may already have been accepted. Follow the status above and refresh the same approved job when available."));
    if (State.bBusy) return FText::FromString(TEXT("Waiting for the local Fax Trident companion..."));
    if (State.bHasJob) return FText::FromString(TEXT("Download requests the exact approved PDF and asks where to save a new file. Refresh and cancellation happen only when you choose them."));
    return FText::GetEmpty();
}

void SDaedalusFaxPreparationPanel::ClearCancellation()
{
    bCancellationArmed = false;
    CancellationSelection = FDaedalusFaxPreparationView();
}

bool SDaedalusFaxPreparationPanel::IsCancellationArmed() const
{
    if (!bCancellationArmed || !HasOpenTerminal()) return false;
    const auto State = View();
    return State.bCanCancel && State.bHasJob && State.FaxId == CancellationSelection.FaxId
        && State.Recipient == CancellationSelection.Recipient && State.DocumentSha256 == CancellationSelection.DocumentSha256
        && State.PageCount == CancellationSelection.PageCount && State.ByteCount == CancellationSelection.ByteCount
        && State.ExpiresAt == CancellationSelection.ExpiresAt && State.JobState == CancellationSelection.JobState;
}

FReply SDaedalusFaxPreparationPanel::ArmCancellation()
{
    ClearCancellation();
    if (HasOpenTerminal())
    {
        const auto State = View();
        if (State.bCanCancel && State.bHasJob) { CancellationSelection = State; bCancellationArmed = true; }
    }
    return FReply::Handled();
}

FReply SDaedalusFaxPreparationPanel::ConfirmCancellation()
{
    const bool bCanCancel = IsCancellationArmed();
    ClearCancellation();
    if (bCanCancel && HasOpenTerminal()) Terminal->CancelPreparation();
    return FReply::Handled();
}

FReply SDaedalusFaxPreparationPanel::Pair()
{
    FString Link = PairingBox.IsValid() ? PairingBox->GetText().ToString() : FString();
    ClearPairingInput();
    if (HasOpenTerminal() && View().bCanPair) Terminal->PairLocalApp(Link);
    Link.Reset();
    return FReply::Handled();
}

FReply SDaedalusFaxPreparationPanel::Close()
{
    ClearPairingInput();
    if (Terminal.IsValid()) Terminal->ClosePanel();
    return FReply::Handled();
}

FReply SDaedalusFaxPreparationPanel::OnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    if (Event.GetKey() == EKeys::Escape || Event.GetKey() == EKeys::Gamepad_Special_Right) return Close();
    return SCompoundWidget::OnPreviewKeyDown(Geometry, Event);
}

FReply SDaedalusFaxPreparationPanel::OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    if (Event.GetKey() == EKeys::Escape || Event.GetKey() == EKeys::Gamepad_Special_Right) return Close();
    return SCompoundWidget::OnKeyDown(Geometry, Event);
}
