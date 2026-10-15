// SPDX-License-Identifier: MIT
#include "SDaedalusApprovedWorkspacePanel.h"
#include "DaedalusApprovedWorkspaceTerminal.h"
#include "InputCoreTypes.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
FDaedalusApprovedWorkspaceView SDaedalusApprovedWorkspacePanel::View() const
{ return Terminal.IsValid() ? Terminal->GetView() : FDaedalusApprovedWorkspaceView(); }
bool SDaedalusApprovedWorkspacePanel::OwnsUserFocus(int32 UserIndex) const
{ return HasUserFocus(UserIndex).IsSet() || HasUserFocusedDescendants(UserIndex); }
SDaedalusApprovedWorkspacePanel::~SDaedalusApprovedWorkspacePanel()
{ if (PairingBox.IsValid()) PairingBox->SetText(FText::GetEmpty()); }
TSharedRef<SWidget> SDaedalusApprovedWorkspacePanel::MakePairingInput()
{
    return SAssignNew(PairingBox,SEditableTextBox).IsPassword(true).ClearKeyboardFocusOnCommit(false)
        .HintText(FText::FromString(TEXT("Paste this app's private approved-workspace link")))
        .IsEnabled_Lambda([this] { return Terminal.IsValid() && Terminal->IsPanelOpen() && View().bCanPair; })
        .OnVerifyTextChanged_Lambda([](const FText& Text,FText& Error)
        { if (Text.ToString().Len() <= 256) return true; Error=FText::FromString(TEXT("Use the exact private workspace link.")); return false; });
}
void SDaedalusApprovedWorkspacePanel::ClearPairingInput()
{
    if (PairingBox.IsValid()) PairingBox->SetText(FText::GetEmpty());
    PairingBox.Reset();
    if (PairingInputHost.IsValid()) PairingInputHost->SetContent(MakePairingInput());
}
TSharedRef<SWidget> SDaedalusApprovedWorkspacePanel::Button(const TCHAR* Label,
    TFunction<void(ADaedalusApprovedWorkspaceTerminal&)> Action,TFunction<bool(const FDaedalusApprovedWorkspaceView&)> Enabled)
{
    return SNew(SButton).Text(FText::FromString(Label)).ContentPadding(FMargin(12.f,8.f))
        .IsEnabled_Lambda([this,Enabled] { return Terminal.IsValid() && Terminal->IsPanelOpen() && Enabled(View()); })
        .OnClicked_Lambda([this,Action,Enabled]
        { if (Terminal.IsValid() && Terminal->IsPanelOpen() && Enabled(View())) Action(*Terminal.Get()); return FReply::Handled(); });
}
void SDaedalusApprovedWorkspacePanel::Construct(const FArguments& Args)
{
    Terminal=Args._Terminal;
    ChildSlot
    [SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
        .BorderBackgroundColor(FLinearColor(0.02f,0.035f,0.055f,0.97f)).Padding(24.f).HAlign(HAlign_Center).VAlign(VAlign_Center)
        [SNew(SBox).MaxDesiredWidth(900.f).MaxDesiredHeight(760.f)
            [SNew(SScrollBox)+SScrollBox::Slot()
                [SNew(SVerticalBox)
                    +SVerticalBox::Slot().AutoHeight().Padding(0.f,0.f,0.f,14.f)
                    [SNew(STextBlock).Text_Lambda([this] { return FText::FromString(Terminal.IsValid()?Terminal->ApplicationLabel():TEXT("Approved workspace")); })
                        .Font(FCoreStyle::GetDefaultFontStyle("Bold",24))]
                    +SVerticalBox::Slot().AutoHeight().Padding(0.f,0.f,0.f,14.f)
                    [SNew(STextBlock).Text(FText::FromString(TEXT("Choose files or a folder, settings and an output destination in the desktop app, then explicitly approve that plan. This object starts and monitors only that frozen plan."))).AutoWrapText(true)]
                    +SVerticalBox::Slot().AutoHeight().Padding(0.f,0.f,0.f,14.f)
                    [SAssignNew(PairingInputHost,SBox)[MakePairingInput()]]
                    +SVerticalBox::Slot().AutoHeight().Padding(0.f,0.f,0.f,14.f)
                    [SNew(SButton).Text(FText::FromString(TEXT("Pair approved workspace")))
                        .IsEnabled_Lambda([this] { return View().bCanPair; }).OnClicked(this,&SDaedalusApprovedWorkspacePanel::Pair)]
                    +SVerticalBox::Slot().AutoHeight().Padding(0.f,0.f,0.f,14.f)
                    [SNew(STextBlock).Text_Lambda([this] { return FText::FromString(View().Status); }).AutoWrapText(true)]
                    +SVerticalBox::Slot().AutoHeight().Padding(0.f,0.f,0.f,14.f)
                    [SNew(STextBlock).Text(this,&SDaedalusApprovedWorkspacePanel::Details).AutoWrapText(true)]
                    +SVerticalBox::Slot().AutoHeight().Padding(0.f,0.f,0.f,14.f)
                    [SNew(SWrapBox).UseAllottedSize(true)
                        +SWrapBox::Slot().Padding(FMargin(0.f,0.f,8.f,8.f))
                        [Button(TEXT("Start / retry same approved action"),[](ADaedalusApprovedWorkspaceTerminal& Actor){Actor.StartWorkspace();},[](const FDaedalusApprovedWorkspaceView& State){return State.bCanStart;})]
                        +SWrapBox::Slot().Padding(FMargin(0.f,0.f,8.f,8.f))
                        [Button(TEXT("Refresh actual progress"),[](ADaedalusApprovedWorkspaceTerminal& Actor){Actor.RefreshJob();},[](const FDaedalusApprovedWorkspaceView& State){return State.bCanRefresh;})]
                        +SWrapBox::Slot().Padding(FMargin(0.f,0.f,8.f,8.f))
                        [Button(TEXT("Cancel unfinished work"),[](ADaedalusApprovedWorkspaceTerminal& Actor){Actor.CancelWorkspace();},[](const FDaedalusApprovedWorkspaceView& State){return State.bCanCancel;})]
                        +SWrapBox::Slot().Padding(FMargin(0.f,0.f,8.f,8.f))
                        [Button(TEXT("Revoke local access"),[](ADaedalusApprovedWorkspaceTerminal& Actor){Actor.DisconnectApp();},[](const FDaedalusApprovedWorkspaceView& State){return State.bCanDisconnect;})]]
                    +SVerticalBox::Slot().AutoHeight().Padding(0.f,0.f,0.f,14.f)
                    [SNew(STextBlock).Text(FText::FromString(TEXT("The desktop app saves results in the destination you approved. Existing files are preserved; conflicts and skips have separate counts. Cancellation or closing can leave already committed outputs. A failed or canceled plan needs a new desktop approval for new work. The private link stays in process memory."))).AutoWrapText(true)]
                    +SVerticalBox::Slot().AutoHeight()
                    [SNew(SButton).Text(FText::FromString(TEXT("Close workspace"))).OnClicked(this,&SDaedalusApprovedWorkspacePanel::Close)]
                ]
            ]
        ]
    ];
}
FText SDaedalusApprovedWorkspacePanel::Details() const
{
    const auto State=View();
    const FString Cancellation = State.bHasCanceledCount
        ? FString::Printf(TEXT("Canceled inputs: %d; cancellation requested: %s"),State.Canceled,State.bCancelRequested?TEXT("yes"):TEXT("no"))
        : State.bCancelRequested ? TEXT("Cancellation requested; unfinished input count is not reported by this app.") : TEXT("");
    return FText::FromString(FString::Printf(TEXT("Plan: %s\nMode: %s\n%s\nState reported by app: %s\nInputs: %d  Processed: %d  Saved/optimized: %d  Failed: %d  Skipped: %d  Destination conflicts: %d\n%s\nExpires: %s"),
        *State.PlanId,*State.Mode,*State.Settings,*State.State,State.Total,State.Completed,State.Saved,State.Failed,State.Skipped,State.Conflicts,*Cancellation,*State.ExpiresAt));
}
FReply SDaedalusApprovedWorkspacePanel::Pair()
{
    FString Link=PairingBox.IsValid()?PairingBox->GetText().ToString():FString(); ClearPairingInput();
    if (Terminal.IsValid() && Terminal->IsPanelOpen() && View().bCanPair) Terminal->PairLocalApp(Link);
    Link.Reset(); return FReply::Handled();
}
FReply SDaedalusApprovedWorkspacePanel::Close()
{ ClearPairingInput(); if (Terminal.IsValid()) Terminal->ClosePanel(); return FReply::Handled(); }
FReply SDaedalusApprovedWorkspacePanel::OnPreviewKeyDown(const FGeometry& Geometry,const FKeyEvent& Event)
{
    if (Event.GetKey()==EKeys::Escape || Event.GetKey()==EKeys::Gamepad_Special_Right) return Close();
    return SCompoundWidget::OnPreviewKeyDown(Geometry,Event);
}
FReply SDaedalusApprovedWorkspacePanel::OnKeyDown(const FGeometry& Geometry,const FKeyEvent& Event)
{ return OnPreviewKeyDown(Geometry,Event); }
