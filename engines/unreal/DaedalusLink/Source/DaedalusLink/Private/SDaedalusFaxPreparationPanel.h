// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "DaedalusFaxPreparationClient.h"
#include "Widgets/SCompoundWidget.h"

class ADaedalusFaxPreparationTerminal;
class SBox;
class SEditableTextBox;

/** Presentation for one desktop-approved preparation. No prepare/confirm/send operation. */
class SDaedalusFaxPreparationPanel : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SDaedalusFaxPreparationPanel) {}
        SLATE_ARGUMENT(TWeakObjectPtr<ADaedalusFaxPreparationTerminal>, Terminal)
    SLATE_END_ARGS()

    void Construct(const FArguments& Args);
    virtual ~SDaedalusFaxPreparationPanel() override;
    virtual bool SupportsKeyboardFocus() const override { return true; }
    virtual FReply OnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    virtual FReply OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    bool OwnsUserFocus(int32 UserIndex) const;
    /** Also called by the actor for lifecycle closes; replacement removes Undo history. */
    void ClearPairingInput();

private:
    FDaedalusFaxPreparationView View() const;
    bool HasOpenTerminal() const;
    TSharedRef<SWidget> MakePairingInput();
    TSharedRef<SWidget> Button(const TCHAR* Label, TFunction<void(ADaedalusFaxPreparationTerminal&)> Action,
        TFunction<bool(const FDaedalusFaxPreparationView&)> Enabled);
    FText JobDetails() const;
    FText ActionGuidance() const;
    void ClearCancellation();
    bool IsCancellationArmed() const;
    FReply ArmCancellation();
    FReply ConfirmCancellation();
    FReply Pair();
    FReply Close();

    TWeakObjectPtr<ADaedalusFaxPreparationTerminal> Terminal;
    TSharedPtr<SBox> PairingInputHost;
    TSharedPtr<SEditableTextBox> PairingBox;
    bool bCancellationArmed = false;
    FDaedalusFaxPreparationView CancellationSelection;
};
