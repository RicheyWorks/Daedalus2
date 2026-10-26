// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "DaedalusPhotoPdfClient.h"
#include "Widgets/SCompoundWidget.h"

class ADaedalusPhotoPdfTerminal;
class SBox;
class SEditableTextBox;

/** Presentation only: the actor and existing PhotosToPDF companion own all work. */
class SDaedalusPhotoPdfPanel : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SDaedalusPhotoPdfPanel) {}
        SLATE_ARGUMENT(TWeakObjectPtr<ADaedalusPhotoPdfTerminal>, Terminal)
    SLATE_END_ARGS()

    void Construct(const FArguments& Args);
    virtual ~SDaedalusPhotoPdfPanel() override;
    virtual bool SupportsKeyboardFocus() const override { return true; }
    virtual FReply OnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    virtual FReply OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    bool OwnsUserFocus(int32 UserIndex) const;
    /** Also called by the actor before any external/lifecycle close. */
    void ClearPairingInput();

private:
    FDaedalusPhotoPdfView View() const;
    bool HasOpenTerminal() const;
    TSharedRef<SWidget> MakePairingInput();
    TSharedRef<SWidget> Button(const TCHAR* Label, TFunction<void(ADaedalusPhotoPdfTerminal&)> Action,
        TFunction<bool(const FDaedalusPhotoPdfView&)> Enabled);
    FReply Pair();
    FReply Close();
    FText SelectionText() const;
    FText ProgressText() const;

    TWeakObjectPtr<ADaedalusPhotoPdfTerminal> Terminal;
    TSharedPtr<SBox> PairingInputHost;
    TSharedPtr<SEditableTextBox> PairingBox;
};
