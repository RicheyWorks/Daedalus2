// SPDX-License-Identifier: MIT
#include "SDaedalusPhotoPdfPanel.h"

#include "DaedalusPhotoPdfTerminal.h"
#include "InputCoreTypes.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSeparator.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/Notifications/SProgressBar.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

FDaedalusPhotoPdfView SDaedalusPhotoPdfPanel::View() const
{
    return Terminal.IsValid() ? Terminal->GetView() : FDaedalusPhotoPdfView();
}

bool SDaedalusPhotoPdfPanel::HasOpenTerminal() const
{
    return Terminal.IsValid() && Terminal->IsPanelOpen();
}

bool SDaedalusPhotoPdfPanel::OwnsUserFocus(int32 UserIndex) const
{
    return HasUserFocus(UserIndex).IsSet() || HasUserFocusedDescendants(UserIndex);
}

SDaedalusPhotoPdfPanel::~SDaedalusPhotoPdfPanel()
{
    if (PairingBox.IsValid()) PairingBox->SetText(FText::GetEmpty());
}

TSharedRef<SWidget> SDaedalusPhotoPdfPanel::MakePairingInput()
{
    return SAssignNew(PairingBox, SEditableTextBox)
        .IsPassword(true)
        .HintText(FText::FromString(TEXT("Paste the private PhotosToPDF pairing link")))
        .IsEnabled_Lambda([this] { return HasOpenTerminal() && View().bCanPair; })
        .ClearKeyboardFocusOnCommit(false)
        .OnVerifyTextChanged_Lambda([](const FText& Text, FText& Error)
        {
            if (Text.ToString().Len() <= 256) return true;
            Error = FText::FromString(TEXT("Use the pairing link shown by PhotosToPDF."));
            return false;
        });
}

void SDaedalusPhotoPdfPanel::ClearPairingInput()
{
    if (PairingBox.IsValid()) PairingBox->SetText(FText::GetEmpty());
    // Replace the field so a later Undo cannot restore a pairing link in the visible input.
    PairingBox.Reset();
    if (PairingInputHost.IsValid()) PairingInputHost->SetContent(MakePairingInput());
}

TSharedRef<SWidget> SDaedalusPhotoPdfPanel::Button(const TCHAR* Label,
    TFunction<void(ADaedalusPhotoPdfTerminal&)> Action, TFunction<bool(const FDaedalusPhotoPdfView&)> Enabled)
{
    return SNew(SButton)
        .Text(FText::FromString(Label))
        .ContentPadding(FMargin(12.f, 8.f))
        .IsEnabled_Lambda([this, Enabled] { return HasOpenTerminal() && Enabled(View()); })
        .OnClicked_Lambda([this, Action]
        {
            if (HasOpenTerminal()) Action(*Terminal.Get());
            return FReply::Handled();
        });
}

void SDaedalusPhotoPdfPanel::Construct(const FArguments& Args)
{
    Terminal = Args._Terminal;
    TSharedRef<SWrapBox> Outputs = SNew(SWrapBox).UseAllottedSize(true);
    for (int32 Index = 1; Index <= 8; ++Index)
    {
        const FString Label = FString::Printf(TEXT("Export PDF %d"), Index);
        Outputs->AddSlot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))
        [
            SNew(SBox).Visibility_Lambda([this, Index] { return View().OutputCount >= Index ? EVisibility::Visible : EVisibility::Collapsed; })
            [Button(*Label, [Index](ADaedalusPhotoPdfTerminal& Actor) { Actor.ExportPdf(Index); },
                [Index](const FDaedalusPhotoPdfView& State) { return State.bCanExport && State.OutputCount >= Index; })]
        ];
    }

    ChildSlot
    [
        SNew(SBorder)
        .BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
        .BorderBackgroundColor(FLinearColor(0.02f, 0.035f, 0.055f, 0.97f))
        .Padding(24.f)
        .HAlign(HAlign_Center)
        .VAlign(VAlign_Center)
        [
            SNew(SBox).MaxDesiredWidth(900.f).MaxDesiredHeight(760.f)
            [
                SNew(SScrollBox)
                + SScrollBox::Slot()
                [
                    SNew(SVerticalBox)
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [
                        SNew(SHorizontalBox)
                        + SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)
                        [SNew(STextBlock).Font(FCoreStyle::GetDefaultFontStyle("Bold", 26)).Text(FText::FromString(TEXT("Photos to PDF")))]
                        + SHorizontalBox::Slot().AutoWidth()
                        [SNew(SButton).Text(FText::FromString(TEXT("Close"))).OnClicked(this, &SDaedalusPhotoPdfPanel::Close)]
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)
                    [SNew(STextBlock).Text(FText::FromString(TEXT("Choose photos on this computer. Your PhotosToPDF app creates one PDF per photo."))).AutoWrapText(true)]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [
                        SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
                        .BorderBackgroundColor(FLinearColor(0.045f, 0.10f, 0.13f, 1.f)).Padding(12.f)
                        [SNew(STextBlock).Text_Lambda([this] { return FText::FromString(View().Status); }).AutoWrapText(true)]
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
                    [SNew(STextBlock).Text_Lambda([this] { return FText::FromString(View().bPaired ? TEXT("Local PhotosToPDF companion paired") : TEXT("Start PhotosToPDF and enable its Realm bridge to pair")); }).AutoWrapText(true)]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [
                        SNew(SHorizontalBox)
                        + SHorizontalBox::Slot().FillWidth(1.f).Padding(0.f, 0.f, 8.f, 0.f)
                        [SAssignNew(PairingInputHost, SBox)[MakePairingInput()]]
                        + SHorizontalBox::Slot().AutoWidth()
                        [SNew(SButton).Text(FText::FromString(TEXT("Pair local app"))).ContentPadding(FMargin(12.f, 8.f))
                            .IsEnabled_Lambda([this] { return HasOpenTerminal() && View().bCanPair; }).OnClicked(this, &SDaedalusPhotoPdfPanel::Pair)]
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [SNew(SSeparator)]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
                    [SNew(STextBlock).Text(FText::FromString(TEXT("Photos"))).Font(FCoreStyle::GetDefaultFontStyle("Bold", 18))]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [SNew(STextBlock).Text(this, &SDaedalusPhotoPdfPanel::SelectionText).AutoWrapText(true)]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [
                        SNew(SWrapBox).UseAllottedSize(true)
                        + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))
                        [Button(TEXT("Choose photos"), [](ADaedalusPhotoPdfTerminal& Actor) { Actor.ChoosePhotos(); }, [](const FDaedalusPhotoPdfView& State) { return State.bCanSelect; })]
                        + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))
                        [SNew(SButton).ContentPadding(FMargin(12.f, 8.f))
                            .Text_Lambda([this] { return FText::FromString(View().bUncertain ? TEXT("Retry same conversion") : TEXT("Convert photos")); })
                            .IsEnabled_Lambda([this] { return HasOpenTerminal() && View().bCanSubmit; })
                            .OnClicked_Lambda([this] { if (HasOpenTerminal()) Terminal->SubmitOrRetry(); return FReply::Handled(); })]
                        + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))
                        [Button(TEXT("Refresh"), [](ADaedalusPhotoPdfTerminal& Actor) { Actor.RefreshJob(); }, [](const FDaedalusPhotoPdfView& State) { return State.bCanRefresh; })]
                        + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))
                        [Button(TEXT("Cancel / delete job"), [](ADaedalusPhotoPdfTerminal& Actor) { Actor.CancelJob(); }, [](const FDaedalusPhotoPdfView& State) { return State.bCanCancel; })]
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
                    [SNew(STextBlock).Text(this, &SDaedalusPhotoPdfPanel::ProgressText).AutoWrapText(true)]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [SNew(SProgressBar).Percent_Lambda([this]() -> TOptional<float>
                        {
                            const FDaedalusPhotoPdfView State = View();
                            return State.Total > 0 ? FMath::Clamp(static_cast<float>(State.Completed) / static_cast<float>(State.Total), 0.f, 1.f) : 0.f;
                        })]
                    + SVerticalBox::Slot().AutoHeight()[Outputs]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [SNew(STextBlock).Text(FText::FromString(TEXT("Exports use a new PDF filename. Existing files are never replaced."))).AutoWrapText(true)]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [Button(TEXT("Disconnect local app"), [](ADaedalusPhotoPdfTerminal& Actor) { Actor.DisconnectApp(); }, [](const FDaedalusPhotoPdfView& State) { return State.bCanDisconnect; })]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
                    [SNew(STextBlock).Text(FText::FromString(TEXT("Only your chosen photos go to the local app. The private pairing link stays in memory. Cancel / delete removes the companion job; exported PDFs stay where you saved them."))).AutoWrapText(true)]
                    + SVerticalBox::Slot().AutoHeight()
                    [SNew(STextBlock).Text(FText::FromString(TEXT("Esc or controller Menu closes this terminal."))).AutoWrapText(true)]
                ]
            ]
        ]
    ];
}

FReply SDaedalusPhotoPdfPanel::Pair()
{
    FString Link = PairingBox.IsValid() ? PairingBox->GetText().ToString() : FString();
    ClearPairingInput();
    if (HasOpenTerminal()) Terminal->PairLocalApp(Link);
    Link.Reset();
    return FReply::Handled();
}

FReply SDaedalusPhotoPdfPanel::Close()
{
    ClearPairingInput();
    if (Terminal.IsValid()) Terminal->ClosePanel();
    return FReply::Handled();
}

FText SDaedalusPhotoPdfPanel::SelectionText() const
{
    const FDaedalusPhotoPdfView State = View();
    if (State.SelectedNames.IsEmpty()) return FText::FromString(TEXT("No photos selected. Choose up to 8 PNG or JPEG files, at most 8 MiB each and 24 MiB per batch."));
    FString Text;
    for (int32 I = 0; I < FMath::Min(State.SelectedNames.Num(), 8); ++I)
    {
        if (I != 0) Text += TEXT("\n");
        Text += FString::Printf(TEXT("%d. %s"), I + 1, *State.SelectedNames[I]);
    }
    return FText::FromString(Text);
}

FText SDaedalusPhotoPdfPanel::ProgressText() const
{
    const FDaedalusPhotoPdfView State = View();
    if (State.bUncertain)
    {
        if (State.bCanSubmit) return FText::FromString(TEXT("The request outcome is unknown. Retry the same conversion to recover it before changing photos."));
        return FText::FromString(TEXT("The last action is unconfirmed. Follow the status above to refresh, retry cleanup or disconnect."));
    }
    if (State.JobId.IsEmpty()) return FText::FromString(State.bBusy ? TEXT("Waiting for the local companion...") : TEXT("Choose photos, then convert."));
    return FText::FromString(FString::Printf(TEXT("%s — %d of %d photos complete"), *State.JobState, State.Completed, State.Total));
}

FReply SDaedalusPhotoPdfPanel::OnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    if (Event.GetKey() == EKeys::Escape || Event.GetKey() == EKeys::Gamepad_Special_Right) return Close();
    return SCompoundWidget::OnPreviewKeyDown(Geometry, Event);
}

FReply SDaedalusPhotoPdfPanel::OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    if (Event.GetKey() == EKeys::Escape || Event.GetKey() == EKeys::Gamepad_Special_Right) return Close();
    return SCompoundWidget::OnKeyDown(Geometry, Event);
}
