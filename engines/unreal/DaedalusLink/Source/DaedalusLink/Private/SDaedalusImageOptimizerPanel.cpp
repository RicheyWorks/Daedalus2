// SPDX-License-Identifier: MIT
#include "SDaedalusImageOptimizerPanel.h"

#include "DaedalusImageOptimizerTerminal.h"
#include "InputCoreTypes.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SCheckBox.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Input/SNumericEntryBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSeparator.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/Notifications/SProgressBar.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

FDaedalusImageOptimizerView SDaedalusImageOptimizerPanel::View() const
{
    return Terminal.IsValid() ? Terminal->GetView() : FDaedalusImageOptimizerView();
}
bool SDaedalusImageOptimizerPanel::HasOpenTerminal() const
{
    return Terminal.IsValid() && Terminal->IsPanelOpen();
}
bool SDaedalusImageOptimizerPanel::OwnsUserFocus(int32 UserIndex) const
{
    return HasUserFocus(UserIndex).IsSet() || HasUserFocusedDescendants(UserIndex);
}
SDaedalusImageOptimizerPanel::~SDaedalusImageOptimizerPanel()
{
    if (PairingBox.IsValid()) PairingBox->SetText(FText::GetEmpty());
}
TSharedRef<SWidget> SDaedalusImageOptimizerPanel::MakePairingInput()
{
    return SAssignNew(PairingBox, SEditableTextBox).IsPassword(true)
        .HintText(FText::FromString(TEXT("Paste the private Image Optimizer workbench link")))
        .IsEnabled_Lambda([this] { return HasOpenTerminal() && View().bCanPair; })
        .ClearKeyboardFocusOnCommit(false)
        .OnVerifyTextChanged_Lambda([](const FText& Text, FText& Error)
        {
            if (Text.ToString().Len() <= 256) return true;
            Error = FText::FromString(TEXT("Use the private link shown by Image Optimizer."));
            return false;
        });
}
void SDaedalusImageOptimizerPanel::ClearPairingInput()
{
    if (PairingBox.IsValid()) PairingBox->SetText(FText::GetEmpty());
    PairingBox.Reset();
    if (PairingInputHost.IsValid()) PairingInputHost->SetContent(MakePairingInput());
}
TSharedRef<SWidget> SDaedalusImageOptimizerPanel::Button(const TCHAR* Label,
    TFunction<void(ADaedalusImageOptimizerTerminal&)> Action, TFunction<bool(const FDaedalusImageOptimizerView&)> Enabled)
{
    return SNew(SButton).Text(FText::FromString(Label)).ContentPadding(FMargin(12.f, 8.f))
        .IsEnabled_Lambda([this, Enabled] { return HasOpenTerminal() && Enabled(View()); })
        .OnClicked_Lambda([this, Action] { if (HasOpenTerminal()) Action(*Terminal.Get()); return FReply::Handled(); });
}
void SDaedalusImageOptimizerPanel::EditSettings(TFunction<void(FDaedalusImageOptimizerSettings&)> Change)
{
    if (!HasOpenTerminal()) return;
    const auto State = View();
    if (!State.bCanEditSettings) return;
    auto Settings = State.Settings;
    Change(Settings);
    Terminal->SetSettings(Settings); // Local client settings only; no conversion starts here.
}
TSharedRef<SWidget> SDaedalusImageOptimizerPanel::FormatButton(const TCHAR* Label, uint8 Format)
{
    return SNew(SButton).Text(FText::FromString(Label)).ContentPadding(FMargin(12.f, 8.f))
        .IsEnabled_Lambda([this] { return HasOpenTerminal() && View().bCanEditSettings; })
        .ButtonColorAndOpacity_Lambda([this, Format]
        { return View().Settings.Format == Format ? FLinearColor(0.12f, 0.40f, 0.48f, 1.f) : FLinearColor(0.12f, 0.15f, 0.18f, 1.f); })
        .OnClicked_Lambda([this, Format]
        { EditSettings([Format](FDaedalusImageOptimizerSettings& Settings) { Settings.Format = Format; }); return FReply::Handled(); });
}
TSharedRef<SWidget> SDaedalusImageOptimizerPanel::SettingsPanel()
{
    return SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
        [SNew(STextBlock).Text(FText::FromString(TEXT("Output settings"))).Font(FCoreStyle::GetDefaultFontStyle("Bold", 18))]
        + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)
        [
            SNew(SWrapBox).UseAllottedSize(true)
            + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 14.f, 8.f))
            [
                SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 4.f)
                [SNew(STextBlock).Text(FText::FromString(TEXT("Quality (70-95%)")))]
                + SVerticalBox::Slot().AutoHeight()
                [SNew(SBox).WidthOverride(130.f)
                    [SNew(SNumericEntryBox<int32>).AllowSpin(false).MinValue(70).MaxValue(95)
                        .IsEnabled_Lambda([this] { return HasOpenTerminal() && View().bCanEditSettings; })
                        .Value_Lambda([this]() -> TOptional<int32> { return View().Settings.Quality; })
                        .OnValueCommitted_Lambda([this](int32 Value, ETextCommit::Type)
                        { EditSettings([Value](FDaedalusImageOptimizerSettings& Settings) { Settings.Quality = Value; }); })]]
            ]
            + SWrapBox::Slot().VAlign(VAlign_Center).Padding(FMargin(0.f, 0.f, 14.f, 8.f))
            [SNew(SCheckBox)
                .IsEnabled_Lambda([this] { return HasOpenTerminal() && View().bCanEditSettings; })
                .IsChecked_Lambda([this] { return View().Settings.bResize ? ECheckBoxState::Checked : ECheckBoxState::Unchecked; })
                .OnCheckStateChanged_Lambda([this](ECheckBoxState Value)
                { EditSettings([Value](FDaedalusImageOptimizerSettings& Settings) { Settings.bResize = Value == ECheckBoxState::Checked; }); })
                [SNew(STextBlock).Text(FText::FromString(TEXT("Resize large images")))]]
            + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 0.f, 8.f))
            [
                SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 4.f)
                [SNew(STextBlock).Text(FText::FromString(TEXT("Maximum width (1-4096)")))]
                + SVerticalBox::Slot().AutoHeight()
                [SNew(SBox).WidthOverride(160.f)
                    [SNew(SNumericEntryBox<int32>).AllowSpin(false).MinValue(1).MaxValue(4096)
                        .IsEnabled_Lambda([this] { return HasOpenTerminal() && View().bCanEditSettings; })
                        .Value_Lambda([this]() -> TOptional<int32> { return View().Settings.Width; })
                        .OnValueCommitted_Lambda([this](int32 Value, ETextCommit::Type)
                        { EditSettings([Value](FDaedalusImageOptimizerSettings& Settings) { Settings.Width = Value; }); })]]
            ]
        ]
        + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
        [
            SNew(SWrapBox).UseAllottedSize(true)
            + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))[FormatButton(TEXT("Keep format"), 0)]
            + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))[FormatButton(TEXT("PNG"), 1)]
            + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))[FormatButton(TEXT("JPEG"), 2)]
        ]
        + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
        [SNew(STextBlock).Text(FText::FromString(TEXT("JPEG removes transparency. PNG is lossless; quality has format-specific effects. Outputs may be larger than your originals. Settings stay frozen until this action is cleared."))).AutoWrapText(true)];
}
void SDaedalusImageOptimizerPanel::Construct(const FArguments& Args)
{
    Terminal = Args._Terminal;
    TSharedRef<SVerticalBox> Outputs = SNew(SVerticalBox);
    for (int32 Index = 1; Index <= 8; ++Index)
        Outputs->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
        [
            SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
            .BorderBackgroundColor(FLinearColor(0.045f, 0.10f, 0.13f, 1.f)).Padding(10.f)
            .Visibility_Lambda([this, Index] { FDaedalusImageOptimizerOutput Item; return Output(Index, Item) ? EVisibility::Visible : EVisibility::Collapsed; })
            [
                SNew(SHorizontalBox)
                + SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center).Padding(0.f, 0.f, 12.f, 0.f)
                [SNew(STextBlock).Text(this, &SDaedalusImageOptimizerPanel::OutputText, Index).AutoWrapText(true)]
                + SHorizontalBox::Slot().AutoWidth()
                [Button(TEXT("Export image"), [Index](ADaedalusImageOptimizerTerminal& Actor) { Actor.ExportImage(Index); },
                    [Index](const FDaedalusImageOptimizerView& State)
                    { for (const auto& Item : State.Outputs) if (Item.Index == Index) return State.bCanExport; return false; })]
            ]
        ];

    ChildSlot
    [
        SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
        .BorderBackgroundColor(FLinearColor(0.02f, 0.035f, 0.055f, 0.97f)).Padding(24.f)
        .HAlign(HAlign_Center).VAlign(VAlign_Center)
        [
            SNew(SBox).MaxDesiredWidth(940.f).MaxDesiredHeight(780.f)
            [SNew(SScrollBox) + SScrollBox::Slot()
                [
                    SNew(SVerticalBox)
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)
                    [
                        SNew(SHorizontalBox)
                        + SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)
                        [SNew(STextBlock).Text(FText::FromString(TEXT("Image Optimizer workbench"))).Font(FCoreStyle::GetDefaultFontStyle("Bold", 25))]
                        + SHorizontalBox::Slot().AutoWidth()
                        [SNew(SButton).Text(FText::FromString(TEXT("Close"))).OnClicked(this, &SDaedalusImageOptimizerPanel::Close)]
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)
                    [SNew(STextBlock).Text(FText::FromString(TEXT("Choose images on this computer and optimize them with your running Image Optimizer app."))).AutoWrapText(true)]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
                        .BorderBackgroundColor(FLinearColor(0.045f, 0.10f, 0.13f, 1.f)).Padding(12.f)
                        [SNew(STextBlock).Text_Lambda([this] { return FText::FromString(View().Status); }).AutoWrapText(true)]]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [
                        SNew(SHorizontalBox)
                        + SHorizontalBox::Slot().FillWidth(1.f).Padding(0.f, 0.f, 8.f, 0.f)
                        [SAssignNew(PairingInputHost, SBox)[MakePairingInput()]]
                        + SHorizontalBox::Slot().AutoWidth()
                        [SNew(SButton).Text(FText::FromString(TEXT("Pair local app"))).ContentPadding(FMargin(12.f, 8.f))
                            .IsEnabled_Lambda([this] { return HasOpenTerminal() && View().bCanPair; }).OnClicked(this, &SDaedalusImageOptimizerPanel::Pair)]
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)[SNew(SSeparator)]
                    + SVerticalBox::Slot().AutoHeight()[SettingsPanel()]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [SNew(STextBlock).Text(this, &SDaedalusImageOptimizerPanel::SelectionText).AutoWrapText(true)]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
                    [
                        SNew(SWrapBox).UseAllottedSize(true)
                        + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))
                        [Button(TEXT("Choose images"), [](ADaedalusImageOptimizerTerminal& Actor) { Actor.ChooseImages(); }, [](const FDaedalusImageOptimizerView& State) { return State.bCanSelect; })]
                        + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))
                        [SNew(SButton).ContentPadding(FMargin(12.f, 8.f))
                            .Text_Lambda([this] { const auto State = View(); return FText::FromString(State.bUncertain ? TEXT("Retry same action") : !State.JobId.IsEmpty() ? TEXT("Refresh same result") : TEXT("Optimize images")); })
                            .IsEnabled_Lambda([this] { return HasOpenTerminal() && View().bCanSubmit; })
                            .OnClicked_Lambda([this] { if (HasOpenTerminal()) Terminal->SubmitOrRetry(); return FReply::Handled(); })]
                        + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))
                        [Button(TEXT("Refresh"), [](ADaedalusImageOptimizerTerminal& Actor) { Actor.RefreshJob(); }, [](const FDaedalusImageOptimizerView& State) { return State.bCanRefresh; })]
                        + SWrapBox::Slot().Padding(FMargin(0.f, 0.f, 8.f, 8.f))
                        [Button(TEXT("Cancel / clear job"), [](ADaedalusImageOptimizerTerminal& Actor) { Actor.CancelJob(); }, [](const FDaedalusImageOptimizerView& State) { return State.bCanCancel; })]
                    ]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
                    [SNew(STextBlock).Text(this, &SDaedalusImageOptimizerPanel::ProgressText).AutoWrapText(true)]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [SNew(SProgressBar).Percent_Lambda([this]() -> TOptional<float>
                        { const auto State = View(); return State.Total > 0 ? FMath::Clamp(static_cast<float>(State.Completed) / State.Total, 0.f, 1.f) : 0.f; })]
                    + SVerticalBox::Slot().AutoHeight()[Outputs]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)
                    [Button(TEXT("Disconnect local app"), [](ADaedalusImageOptimizerTerminal& Actor) { Actor.DisconnectApp(); }, [](const FDaedalusImageOptimizerView& State) { return State.bCanDisconnect; })]
                    + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
                    [SNew(STextBlock).Text(FText::FromString(TEXT("Only chosen image bytes go to the local app. Originals are untouched; every export requires a new filename. Cancel asks the app to clear temporary outputs. Exported copies stay where you saved them."))).AutoWrapText(true)]
                    + SVerticalBox::Slot().AutoHeight()
                    [SNew(STextBlock).Text(FText::FromString(TEXT("The private pairing link stays in memory. Esc or controller Menu closes this workbench."))).AutoWrapText(true)]
                ]
            ]
        ]
    ];
}
bool SDaedalusImageOptimizerPanel::Output(int32 Index, FDaedalusImageOptimizerOutput& Out) const
{
    for (const auto& Item : View().Outputs) if (Item.Index == Index) { Out = Item; return true; }
    return false;
}
FText SDaedalusImageOptimizerPanel::OutputText(int32 Index) const
{
    FDaedalusImageOptimizerOutput Item;
    if (!Output(Index, Item)) return FText::GetEmpty();
    return FText::FromString(FString::Printf(TEXT("image-%d.%s  |  %d x %d  |  %d bytes (source %d bytes)"),
        Index, Item.Type == 1 ? TEXT("png") : TEXT("jpg"), Item.Width, Item.Height, Item.Bytes, Item.SourceBytes));
}
FText SDaedalusImageOptimizerPanel::SelectionText() const
{
    const auto State = View();
    if (State.SelectedNames.IsEmpty()) return FText::FromString(TEXT("No images selected. Choose 1-8 static PNG or JPEG files, up to 8 MiB each and 24 MiB including request framing."));
    FString Text;
    for (int32 Index = 0; Index < FMath::Min(State.SelectedNames.Num(), 8); ++Index)
    { if (Index != 0) Text += TEXT("\n"); Text += FString::Printf(TEXT("%d. %s"), Index + 1, *State.SelectedNames[Index]); }
    return FText::FromString(Text);
}
FText SDaedalusImageOptimizerPanel::ProgressText() const
{
    const auto State = View();
    if (State.bUncertain) return FText::FromString(TEXT("The last action is unconfirmed. Follow the status above to recover the same frozen action, retry cleanup or disconnect."));
    if (State.JobId.IsEmpty()) return FText::FromString(State.bBusy ? TEXT("Waiting for the local companion...") : TEXT("Choose images and settings, then optimize."));
    return FText::FromString(FString::Printf(TEXT("%s — %d of %d images complete"), *State.JobState, State.Completed, State.Total));
}
FReply SDaedalusImageOptimizerPanel::Pair()
{
    FString Link = PairingBox.IsValid() ? PairingBox->GetText().ToString() : FString();
    ClearPairingInput();
    if (HasOpenTerminal()) Terminal->PairLocalApp(Link);
    Link.Reset();
    return FReply::Handled();
}
FReply SDaedalusImageOptimizerPanel::Close()
{
    ClearPairingInput();
    if (Terminal.IsValid()) Terminal->ClosePanel();
    return FReply::Handled();
}
FReply SDaedalusImageOptimizerPanel::OnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    if (Event.GetKey() == EKeys::Escape || Event.GetKey() == EKeys::Gamepad_Special_Right) return Close();
    return SCompoundWidget::OnPreviewKeyDown(Geometry, Event);
}
FReply SDaedalusImageOptimizerPanel::OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    if (Event.GetKey() == EKeys::Escape || Event.GetKey() == EKeys::Gamepad_Special_Right) return Close();
    return SCompoundWidget::OnKeyDown(Geometry, Event);
}
