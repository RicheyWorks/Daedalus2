// SPDX-License-Identifier: MIT
#include "SDaedalusSynapseWorkbenchPanel.h"
#include "DaedalusSynapseWorkbenchTerminal.h"
#include "DaedalusSynapseWorkbenchFiles.h"
#include "IWebBrowserDialog.h"
#include "IWebBrowserSingleton.h"
#include "IWebBrowserWindow.h"
#include "WebBrowserModule.h"
#include "SWebBrowser.h"
#include "InputCoreTypes.h"
#include "Misc/Guid.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SNullWidget.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
    bool SafeLeaf(const FString& Text)
    {
        if (Text.IsEmpty() || Text.Len() > 128 || Text.Contains(TEXT(".."))) return false;
        for (TCHAR C : Text)
            if (!((C >= 'a' && C <= 'z') || (C >= 'A' && C <= 'Z') || (C >= '0' && C <= '9')
                || C == '-' || C == '_' || C == '.')) return false;
        return true;
    }
}

void SDaedalusSynapseWorkbenchPanel::Construct(const FArguments& Args)
{
    Profile = Args._Profile;
    Terminal = Args._Terminal;
    Callbacks = Args._Callbacks;
    // The two bindings are intentionally distinct. The Fax profile cannot bind the Synapse UObject.
    Workspace = Profile == EDaedalusWorkbenchProfile::Fax ? Args._NativeWorkspace : static_cast<UObject*>(Args._Workspace);
    ChildSlot
    [
        SNew(SBorder).BorderImage(FCoreStyle::Get().GetBrush("WhiteBrush"))
        .BorderBackgroundColor(FLinearColor(0.02f, 0.035f, 0.055f, 0.98f)).Padding(12.f)
        [
            SNew(SVerticalBox)
            + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
            [
                SNew(SHorizontalBox)
                + SHorizontalBox::Slot().FillWidth(1.f)
                [SNew(STextBlock).Text(FText::FromString(Profile == EDaedalusWorkbenchProfile::Fax
                    ? TEXT("Fax Trident private workbench") : TEXT("Synapse realm workbench")))]
                + SHorizontalBox::Slot().AutoWidth()
                [SNew(SButton).Text(FText::FromString(TEXT("Close"))).OnClicked(this, &SDaedalusSynapseWorkbenchPanel::CloseClicked)]
            ]
            + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
            [
                SAssignNew(PairingHost, SBox)
                [
                    SNew(SHorizontalBox)
                    + SHorizontalBox::Slot().FillWidth(1.f).Padding(0.f, 0.f, 8.f, 0.f)
                    [
                        SAssignNew(PairingInput, SEditableTextBox).IsPassword(true)
                        .HintText(FText::FromString(Profile == EDaedalusWorkbenchProfile::Fax
                            ? TEXT("Private workbench link from desktop Fax Trident") : TEXT("Private Realm workbench link from desktop Synapse")))
                        .ClearKeyboardFocusOnCommit(false)
                        .OnVerifyTextChanged_Lambda([](const FText& Text, FText& Error)
                        {
                            if (Text.ToString().Len() <= 192) return true;
                            Error = FText::FromString(TEXT("Use the local Realm workbench pairing link."));
                            return false;
                        })
                    ]
                    + SHorizontalBox::Slot().AutoWidth()
                    [SNew(SButton).Text(FText::FromString(TEXT("Open approved workbench"))).OnClicked(this, &SDaedalusSynapseWorkbenchPanel::PairClicked)]
                ]
            ]
            + SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
            [
                SNew(STextBlock).AutoWrapText(true).Text_Lambda([this]
                {
                    return FText::FromString(OwnerMessage());
                })
            ]
            + SVerticalBox::Slot().FillHeight(1.f)
            [SAssignNew(BrowserBox, SBox).MinDesiredWidth(760.f).MinDesiredHeight(400.f)]
        ]
    ];
}

SDaedalusSynapseWorkbenchPanel::~SDaedalusSynapseWorkbenchPanel() { Shutdown(); }

FString SDaedalusSynapseWorkbenchPanel::AppPath() const
{ return Profile == EDaedalusWorkbenchProfile::Fax ? TEXT("/realm/fax-workbench/") : TEXT("/realm/synapse-workbench/"); }
const TCHAR* SDaedalusSynapseWorkbenchPanel::BindingName() const
{ return Profile == EDaedalusWorkbenchProfile::Fax ? TEXT("faxfiles") : TEXT("workspace"); }
bool SDaedalusSynapseWorkbenchPanel::HasOwner() const
{
    return Profile == EDaedalusWorkbenchProfile::Fax
        ? Callbacks.IsValid() && Callbacks->IsOwnerValid && Callbacks->IsOwnerValid()
        : Terminal.IsValid();
}
FString SDaedalusSynapseWorkbenchPanel::OwnerMessage() const
{
    if (Profile == EDaedalusWorkbenchProfile::Fax)
        return Callbacks.IsValid() && Callbacks->GetMessage ? Callbacks->GetMessage() : TEXT("Workbench closed.");
    return Terminal.IsValid() ? Terminal->GetLocalMessage() : TEXT("Workbench closed.");
}
bool SDaedalusSynapseWorkbenchPanel::ParseLink(const FString& Link, FString& OutOrigin) const
{
    const FString Prefix = TEXT("http://127.0.0.1:");
    if (Link.Len() > 192 || !Link.StartsWith(Prefix, ESearchCase::CaseSensitive)) return false;
    int32 Slash = INDEX_NONE;
    Slash = Link.Find(TEXT("/"), ESearchCase::CaseSensitive, ESearchDir::FromStart, Prefix.Len());
    if (Slash < Prefix.Len() + 1 || Slash > Prefix.Len() + 5) return false;
    const FString PortText = Link.Mid(Prefix.Len(), Slash - Prefix.Len());
    if (PortText[0] == TEXT('0')) return false;
    int32 Port = 0;
    for (TCHAR C : PortText) { if (C < '0' || C > '9') return false; Port = Port * 10 + C - '0'; }
    if (Port < 1 || Port > 65535) return false;
    const FString Suffix = AppPath() + TEXT("#token=");
    if (!Link.Mid(Slash).StartsWith(Suffix, ESearchCase::CaseSensitive)) return false;
    const FString Token = Link.Mid(Slash + Suffix.Len());
    if (Token.Len() != 43) return false;
    for (TCHAR C : Token)
        if (!((C >= 'a' && C <= 'z') || (C >= 'A' && C <= 'Z') || (C >= '0' && C <= '9') || C == '_' || C == '-')) return false;
    OutOrigin = Link.Left(Slash);
    return true;
}

bool SDaedalusSynapseWorkbenchPanel::Pair(const FString& Link)
{
    const TSharedRef<SDaedalusSynapseWorkbenchPanel> KeepAlive = SharedThis(this);
    if (bStarted || bClosing || !HasOwner() || !Workspace.IsValid()) return false;
    FString SelectedOrigin;
    if (!ParseLink(Link, SelectedOrigin))
    { Message(Profile == EDaedalusWorkbenchProfile::Fax ? TEXT("Use the private workbench link shown by desktop Fax Trident.")
        : TEXT("Use the private Realm workbench link shown by desktop Synapse.")); return false; }
    IWebBrowserModule& Module = IWebBrowserModule::Get();
    IWebBrowserSingleton* Singleton = Module.GetSingleton();
    if (!Module.IsWebModuleAvailable() || !Singleton || Singleton->IsShuttingDown())
    { Message(TEXT("The embedded browser is unavailable in this build.")); return false; }
    Origin = MoveTemp(SelectedOrigin);
    ContextId = (Profile == EDaedalusWorkbenchProfile::Fax ? TEXT("DaedalusFax-") : TEXT("DaedalusSynapse-"))
        + FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FBrowserContextSettings Context(ContextId);
    Context.CookieStorageLocation.Empty(); // CEF: empty cache_path is an isolated in-memory context.
    Context.bPersistSessionCookies = false;
    Context.bIgnoreCertificateErrors = false;
    if (!Singleton->RegisterContext(Context))
    { Origin.Reset(); ContextId.Reset(); Message(TEXT("A private browser context could not be created.")); return false; }
    if (bClosing || !HasOwner() || !Workspace.IsValid())
    { Singleton->UnregisterContext(Context.Id); ContextId.Reset(); Origin.Reset(); return false; }
    FCreateBrowserWindowSettings Settings;
    Settings.InitialURL = TEXT("about:blank");
    Settings.Context = Context;
    Settings.bInterceptLoadRequests = true;
    Settings.bThumbMouseButtonNavigation = false;
    Settings.bShowErrorMessage = false;
    Settings.bEnablePaymentRequest = false;
    Settings.BrowserFrameRate = 24;
    BrowserWindow = Singleton->CreateBrowserWindow(Settings);
    if (!BrowserWindow.IsValid())
    {
        Singleton->UnregisterContext(Context.Id); ContextId.Reset(); Origin.Reset();
        Message(TEXT("The embedded browser could not be created.")); return false;
    }
    if (bClosing || !HasOwner() || !Workspace.IsValid())
    {
        BrowserWindow->CloseBrowser(true, false); BrowserWindow.Reset();
        Singleton->UnregisterContext(Context.Id); ContextId.Reset(); Origin.Reset(); return false;
    }
    SAssignNew(Browser, SWebBrowser, BrowserWindow)
        .InitialURL(TEXT("about:blank")).ShowControls(false).ShowAddressBar(false).ShowErrorMessage(false)
        .SupportsThumbMouseButtonNavigation(false).BrowserFrameRate(24)
        .OnBeforeNavigation(this, &SDaedalusSynapseWorkbenchPanel::BeforeNavigate)
        .OnLoadUrl(this, &SDaedalusSynapseWorkbenchPanel::ResourceOverride)
        .OnBeforePopup_Lambda([](FString, FString) { return true; })
        .OnSuppressContextMenu_Lambda([] { return true; })
        .OnShowDialog_Lambda([](const TWeakPtr<IWebBrowserDialog>&) { return EWebBrowserDialogEventResponse::Ignore; })
        .OnConsoleMessage_Lambda([](const FString&, const FString&, int32, EWebBrowserConsoleLogSeverity) {})
        .OnLoadStarted(this, &SDaedalusSynapseWorkbenchPanel::LoadingStarted)
        .OnLoadCompleted(this, &SDaedalusSynapseWorkbenchPanel::Loaded)
        .OnLoadError(this, &SDaedalusSynapseWorkbenchPanel::Failed);
    bStarted = true;
    BrowserBox->SetContent(Browser.ToSharedRef());
    ClearPairingInput(); // Destroy the field and Undo history; no token is retained in reflected actor data.
    Message(Profile == EDaedalusWorkbenchProfile::Fax ? TEXT("Opening the desktop-approved Fax workbench. No transmission is requested.")
        : TEXT("Opening the desktop-approved Synapse interface. Saved actions use the same vault."));
    BrowserWindow->LoadURL(Profile == EDaedalusWorkbenchProfile::Fax ? Link + TEXT("&host=daedalus-fax-v1") : Link);
    return true;
}

bool SDaedalusSynapseWorkbenchPanel::AllowedDocument(const FString& Url) const
{
    if (Origin.IsEmpty()) return false;
    const FString Base = Origin + AppPath();
    if (Url == Base) return true;
    FString Candidate = Url;
    const FString Marker = TEXT("&host=daedalus-fax-v1");
    if (Profile == EDaedalusWorkbenchProfile::Fax && Candidate.EndsWith(Marker, ESearchCase::CaseSensitive))
        Candidate.LeftChopInline(Marker.Len()); // Pasted links still use the original strict grammar.
    FString ParsedOrigin;
    return ParseLink(Candidate, ParsedOrigin) && ParsedOrigin == Origin;
}
bool SDaedalusSynapseWorkbenchPanel::HasApprovedDocument() const
{
    return !bClosing && (Profile != EDaedalusWorkbenchProfile::Fax || !bFaxGrantRevoked.Load())
        && bApprovedNavigation && BrowserWindow.IsValid() && !BrowserWindow->IsClosing()
        && AllowedDocument(BrowserWindow->GetUrl());
}
bool SDaedalusSynapseWorkbenchPanel::BeforeNavigate(const FString& Url, const FWebNavigationRequest& Request)
{
    const bool Allowed = !bClosing && Request.bIsMainFrame && !Request.bIsRedirect && AllowedDocument(Url);
    if (Profile == EDaedalusWorkbenchProfile::Fax && bApprovedNavigation && Request.bIsMainFrame && !Allowed) bFaxGrantRevoked.Store(true);
    if (Allowed) bApprovedNavigation = true;
    return !Allowed; // All subframes, external locations, file/data URLs and redirects are blocked.
}
bool SDaedalusSynapseWorkbenchPanel::AllowedResource(const FString& Url) const
{
    if (AllowedDocument(Url)) return true;
    if (Url.StartsWith(TEXT("blob:") + Origin + TEXT("/"), ESearchCase::CaseSensitive))
    {
        FGuid Id; return FGuid::ParseExact(Url.Mid(5 + Origin.Len() + 1), EGuidFormats::DigitsWithHyphens, Id);
    }
    if (!Url.StartsWith(Origin + TEXT("/"), ESearchCase::CaseSensitive)) return false;
    const FString Path = Url.Mid(Origin.Len());
    if (Path.Contains(TEXT("?")) || Path.Contains(TEXT("#")) || Path.Contains(TEXT("%")) || Path.Contains(TEXT("\\")) || Path.Contains(TEXT(".."))) return false;
    if (Profile == EDaedalusWorkbenchProfile::Fax)
    {
        // The Fax page has nonce-protected inline assets and only these fixed local APIs.
        return Path == TEXT("/v1/capabilities") || Path == TEXT("/v1/contacts/search")
            || Path == TEXT("/v1/history/by-number") || Path == TEXT("/v1/history/recent") || Path == TEXT("/v1/status")
            || Path == TEXT("/v1/metadata") || Path == TEXT("/v1/suggestions") || Path == TEXT("/v1/selected-text")
            || Path == TEXT("/v1/admin/stats") || Path == TEXT("/v1/qr") || Path == TEXT("/v1/grant");
    }
    const FString Assets = AppPath() + TEXT("assets/");
    if (Path.StartsWith(Assets, ESearchCase::CaseSensitive)) return SafeLeaf(Path.Mid(Assets.Len()));
    if (Path == AppPath() + TEXT("favicon.svg")) return true;
    const FString Api = TEXT("/workbench/v1/");
    if (!Path.StartsWith(Api, ESearchCase::CaseSensitive)) return false;
    const FString Route = Path.Mid(Api.Len());
    if (Route == TEXT("session") || Route == TEXT("rpc") || Route == TEXT("discard") || Route == TEXT("revoke")
        || Route == TEXT("upload/image") || Route == TEXT("upload/import")) return true;
    for (const FString& Prefix : { FString(TEXT("action/")), FString(TEXT("download/")) })
    {
        if (!Route.StartsWith(Prefix, ESearchCase::CaseSensitive)) continue;
        FGuid Id; return FGuid::ParseExact(Route.Mid(Prefix.Len()), EGuidFormats::DigitsWithHyphens, Id);
    }
    if (Route.StartsWith(TEXT("asset/"), ESearchCase::CaseSensitive))
    {
        const FString Name = Route.Mid(6);
        int32 Dot = INDEX_NONE;
        if (!Name.FindLastChar(TEXT('.'), Dot)) return false;
        FGuid Id;
        const FString Ext = Name.Mid(Dot + 1);
        return FGuid::ParseExact(Name.Left(Dot), EGuidFormats::DigitsWithHyphens, Id)
            && (Ext == TEXT("png") || Ext == TEXT("jpg") || Ext == TEXT("jpeg"));
    }
    return false;
}
bool SDaedalusSynapseWorkbenchPanel::ResourceOverride(const FString& Method, const FString& Url, FString& Body)
{
    // Teardown may still deliver the page's one authenticated keepalive revoke.
    if (Profile == EDaedalusWorkbenchProfile::Fax)
    {
        const bool bDeleteGrant = !Origin.IsEmpty() && Method == TEXT("DELETE") && Url == Origin + TEXT("/v1/grant");
        if (bDeleteGrant)
        { bFaxGrantRevoked.Store(true); return false; } // End local exports before forwarding an explicit revoke.
        if (!bClosing && AllowedResource(Url))
        {
            if (Method == TEXT("GET") && (AllowedDocument(Url) || Url == Origin + TEXT("/v1/capabilities")
                || Url.StartsWith(TEXT("blob:") + Origin + TEXT("/"), ESearchCase::CaseSensitive))) return false;
            if (Method == TEXT("POST") && Url != Origin + TEXT("/v1/capabilities") && Url != Origin + TEXT("/v1/grant")
                && Url.StartsWith(Origin + TEXT("/v1/"), ESearchCase::CaseSensitive)) return false;
        }
    }
    else
    {
        if (bClosing && !Origin.IsEmpty() && Method == TEXT("POST") && Url == Origin + TEXT("/workbench/v1/revoke")) return false;
        if (!bClosing && (Method == TEXT("GET") || Method == TEXT("POST")) && AllowedResource(Url)) return false;
    }
    Body.Empty(); // UE's load interceptor supplies this empty local response instead of contacting the URL.
    return true;
}
void SDaedalusSynapseWorkbenchPanel::LoadingStarted()
{
    if (!bClosing && bApprovedNavigation) ++DocumentGeneration;
    if (!bClosing && bApprovedNavigation && BrowserWindow.IsValid() && Workspace.IsValid())
        BrowserWindow->BindUObject(BindingName(), Workspace.Get(), false);
}
void SDaedalusSynapseWorkbenchPanel::Loaded()
{
    if (!HasApprovedDocument() || !Workspace.IsValid()) return;
    BrowserWindow->BindUObject(BindingName(), Workspace.Get(), false);
    Message(Profile == EDaedalusWorkbenchProfile::Fax ? TEXT("Desktop-approved USER tools or separate ADMIN statistics. Exports use a new file you select; no fax is sent.")
        : TEXT("Synapse remains local. Select files explicitly; JSON exports omit image bytes and settings."));
}
void SDaedalusSynapseWorkbenchPanel::Failed()
{
    Message(Profile == EDaedalusWorkbenchProfile::Fax ? TEXT("Fax workbench could not load. Close and approve a fresh local link in the desktop app.")
        : TEXT("Synapse could not load. Close this panel and create a fresh workbench link on the desktop."));
}
void SDaedalusSynapseWorkbenchPanel::Message(const TCHAR* Text)
{
    if (bClosing) return;
    if (Profile == EDaedalusWorkbenchProfile::Fax)
    { if (Callbacks.IsValid() && Callbacks->SetMessage) Callbacks->SetMessage(FString(Text)); }
    else if (ADaedalusSynapseWorkbenchTerminal* Owner = Terminal.Get()) Owner->SetLocalMessage(Text);
}
void SDaedalusSynapseWorkbenchPanel::Shutdown()
{
    if (bClosing) return;
    bClosing = true; bApprovedNavigation = false;
    if (Profile == EDaedalusWorkbenchProfile::Fax)
    { if (Callbacks.IsValid() && Callbacks->Invalidate) Callbacks->Invalidate(); }
    else if (UDaedalusSynapseWorkbenchBridge* Bridge = Cast<UDaedalusSynapseWorkbenchBridge>(Workspace.Get())) Bridge->Invalidate();
    if (BrowserWindow.IsValid())
    {
        // Fixed lifecycle notification only; delivery is best effort and never rolls back saved actions.
        BrowserWindow->ExecuteJavascript(TEXT("window.dispatchEvent(new Event('pagehide'));"));
        if (Workspace.IsValid()) BrowserWindow->UnbindUObject(BindingName(), Workspace.Get(), false);
        BrowserWindow->StopLoad();
        BrowserWindow->CloseBrowser(true, false);
    }
    if (BrowserBox.IsValid()) BrowserBox->SetContent(SNullWidget::NullWidget);
    Browser.Reset(); BrowserWindow.Reset();
    // Retain only the literal loopback origin until this panel dies, for the teardown revoke guard.
    if (!ContextId.IsEmpty() && IWebBrowserModule::IsAvailable())
    {
        IWebBrowserSingleton* Singleton = IWebBrowserModule::Get().GetSingleton();
        if (Singleton && !Singleton->IsShuttingDown()) Singleton->UnregisterContext(ContextId);
    }
    ContextId.Reset(); ClearPairingInput();
}
void SDaedalusSynapseWorkbenchPanel::ClearPairingInput()
{
    if (PairingInput.IsValid()) PairingInput->SetText(FText::GetEmpty());
    if (PairingHost.IsValid()) PairingHost->SetContent(SNullWidget::NullWidget);
    PairingInput.Reset();
}
bool SDaedalusSynapseWorkbenchPanel::OwnsUserFocus(uint32 UserIndex) const
{ return HasUserFocus(UserIndex).IsSet() || HasUserFocusedDescendants(UserIndex); }
FReply SDaedalusSynapseWorkbenchPanel::PairClicked()
{
    if (PairingInput.IsValid() && HasOwner())
    {
        if (Profile == EDaedalusWorkbenchProfile::Fax)
        { if (Callbacks.IsValid() && Callbacks->Pair) Callbacks->Pair(PairingInput->GetText().ToString()); }
        else Terminal->PairLocalApp(PairingInput->GetText().ToString());
    }
    return FReply::Handled();
}
FReply SDaedalusSynapseWorkbenchPanel::CloseClicked()
{
    const TSharedRef<SDaedalusSynapseWorkbenchPanel> KeepAlive = SharedThis(this);
    if (Profile == EDaedalusWorkbenchProfile::Fax)
    { if (Callbacks.IsValid() && Callbacks->Close) Callbacks->Close(); }
    else if (Terminal.IsValid()) Terminal->ClosePanel();
    return FReply::Handled();
}
FReply SDaedalusSynapseWorkbenchPanel::OnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    // Once loaded, the original Synapse review UI owns Escape (end the review).
    if (Event.GetKey() == EKeys::Escape && (Profile == EDaedalusWorkbenchProfile::Fax || !Browser.IsValid())) return CloseClicked();
    if (Event.GetKey() == EKeys::F12 || (Event.IsControlDown() && Event.IsShiftDown() && Event.GetKey() == EKeys::I))
        return FReply::Handled();
    return SCompoundWidget::OnPreviewKeyDown(Geometry, Event);
}
