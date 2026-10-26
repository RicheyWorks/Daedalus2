// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "DaedalusImageOptimizerClient.h"
#include "Widgets/SCompoundWidget.h"

class ADaedalusImageOptimizerTerminal;
class SBox;
class SEditableTextBox;

/** Presentation only; selected bytes/settings and all image work belong to the app client. */
class SDaedalusImageOptimizerPanel : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SDaedalusImageOptimizerPanel) {}
        SLATE_ARGUMENT(TWeakObjectPtr<ADaedalusImageOptimizerTerminal>, Terminal)
    SLATE_END_ARGS()

    void Construct(const FArguments& Args);
    virtual ~SDaedalusImageOptimizerPanel() override;
    virtual bool SupportsKeyboardFocus() const override { return true; }
    virtual FReply OnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    virtual FReply OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    bool OwnsUserFocus(int32 UserIndex) const;
    void ClearPairingInput();

private:
    FDaedalusImageOptimizerView View() const;
    bool HasOpenTerminal() const;
    bool Output(int32 Index, FDaedalusImageOptimizerOutput& Out) const;
    FText OutputText(int32 Index) const;
    FText SelectionText() const;
    FText ProgressText() const;
    TSharedRef<SWidget> MakePairingInput();
    TSharedRef<SWidget> SettingsPanel();
    TSharedRef<SWidget> FormatButton(const TCHAR* Label, uint8 Format);
    TSharedRef<SWidget> Button(const TCHAR* Label, TFunction<void(ADaedalusImageOptimizerTerminal&)> Action,
        TFunction<bool(const FDaedalusImageOptimizerView&)> Enabled);
    void EditSettings(TFunction<void(FDaedalusImageOptimizerSettings&)> Change);
    FReply Pair();
    FReply Close();

    TWeakObjectPtr<ADaedalusImageOptimizerTerminal> Terminal;
    TSharedPtr<SBox> PairingInputHost;
    TSharedPtr<SEditableTextBox> PairingBox;
};
