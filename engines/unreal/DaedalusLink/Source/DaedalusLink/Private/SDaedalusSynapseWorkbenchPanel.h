// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "Widgets/SCompoundWidget.h"

class ADaedalusSynapseWorkbenchTerminal;
class UDaedalusSynapseWorkbenchBridge;
class SEditableTextBox;
class SBox;
class SWebBrowser;
class IWebBrowserWindow;
struct FWebNavigationRequest;

class SDaedalusSynapseWorkbenchPanel final : public SCompoundWidget
{
public:
    SLATE_BEGIN_ARGS(SDaedalusSynapseWorkbenchPanel) {}
        SLATE_ARGUMENT(TWeakObjectPtr<ADaedalusSynapseWorkbenchTerminal>, Terminal)
        SLATE_ARGUMENT(UDaedalusSynapseWorkbenchBridge*, Workspace)
    SLATE_END_ARGS()
    void Construct(const FArguments& InArgs);
    virtual ~SDaedalusSynapseWorkbenchPanel() override;
    virtual bool SupportsKeyboardFocus() const override { return true; }
    virtual FReply OnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    bool Pair(const FString& Link);
    void Shutdown();
    void ClearPairingInput();
    bool OwnsUserFocus(uint32 UserIndex) const;
    bool HasApprovedDocument() const;
private:
    FReply PairClicked();
    FReply CloseClicked();
    bool BeforeNavigate(const FString& Url, const FWebNavigationRequest& Request);
    bool ResourceOverride(const FString& Method, const FString& Url, FString& Body);
    void LoadingStarted();
    void Loaded();
    void Failed();
    void Message(const TCHAR* Text);
    bool AllowedResource(const FString& Url) const;
    bool AllowedDocument(const FString& Url) const;
    static bool ParseLink(const FString& Link, FString& OutOrigin);
    TWeakObjectPtr<ADaedalusSynapseWorkbenchTerminal> Terminal;
    TWeakObjectPtr<UDaedalusSynapseWorkbenchBridge> Workspace;
    TSharedPtr<SEditableTextBox> PairingInput;
    TSharedPtr<SBox> PairingHost;
    TSharedPtr<SBox> BrowserBox;
    TSharedPtr<SWebBrowser> Browser;
    TSharedPtr<IWebBrowserWindow> BrowserWindow;
    FString Origin;
    FString ContextId;
    bool bStarted = false;
    bool bClosing = false;
    bool bApprovedNavigation = false;
};
