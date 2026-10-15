// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "DaedalusSynapseClient.h"
#include "Widgets/SCompoundWidget.h"

class ADaedalusSynapseTerminal;
class SBox;
class SEditableTextBox;

/** Plain-text presentation of the running Synapse app's selected study desk. */
class SDaedalusSynapsePanel : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SDaedalusSynapsePanel) {}
        SLATE_ARGUMENT(TWeakObjectPtr<ADaedalusSynapseTerminal>, Terminal)
    SLATE_END_ARGS()

    void Construct(const FArguments& Args);
    virtual ~SDaedalusSynapsePanel() override;
    virtual bool SupportsKeyboardFocus() const override { return true; }
    virtual FReply OnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    virtual FReply OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    bool OwnsUserFocus(int32 UserIndex) const;
    /** Called by the actor before every lifecycle close as well as by this panel. */
    void ClearPairingInput();

private:
    FDaedalusSynapseView View() const;
    bool HasOpenTerminal() const;
    TSharedRef<SWidget> MakePairingInput();
    TSharedRef<SWidget> Button(const TCHAR* Label, TFunction<void(ADaedalusSynapseTerminal&)> Action,
        TFunction<bool(const FDaedalusSynapseView&)> Enabled);
    FReply Pair();
    FReply Close();
    FText CardSummary() const;
    FText SaveGuidance() const;

    TWeakObjectPtr<ADaedalusSynapseTerminal> Terminal;
    TSharedPtr<SBox> PairingInputHost;
    TSharedPtr<SEditableTextBox> PairingBox;
};
