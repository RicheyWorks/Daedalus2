// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "DaedalusApprovedWorkspaceClient.h"
#include "Widgets/SCompoundWidget.h"
class ADaedalusApprovedWorkspaceTerminal;
class SEditableTextBox;
class SBox;
class SDaedalusApprovedWorkspacePanel : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SDaedalusApprovedWorkspacePanel) {}
        SLATE_ARGUMENT(TWeakObjectPtr<ADaedalusApprovedWorkspaceTerminal>, Terminal)
    SLATE_END_ARGS()
    void Construct(const FArguments& Args);
    virtual ~SDaedalusApprovedWorkspacePanel() override;
    virtual bool SupportsKeyboardFocus() const override { return true; }
    virtual FReply OnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    virtual FReply OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    bool OwnsUserFocus(int32 UserIndex) const;
    void ClearPairingInput();
private:
    FDaedalusApprovedWorkspaceView View() const;
    TSharedRef<SWidget> MakePairingInput();
    TSharedRef<SWidget> Button(const TCHAR* Label, TFunction<void(ADaedalusApprovedWorkspaceTerminal&)> Action,
        TFunction<bool(const FDaedalusApprovedWorkspaceView&)> Enabled);
    FReply Pair();
    FReply Close();
    FText Details() const;
    TWeakObjectPtr<ADaedalusApprovedWorkspaceTerminal> Terminal;
    TSharedPtr<SEditableTextBox> PairingBox;
    TSharedPtr<SBox> PairingInputHost;
};
