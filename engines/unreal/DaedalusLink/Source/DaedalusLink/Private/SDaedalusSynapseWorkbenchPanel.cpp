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
    const FString AppPath = TEXT("/realm/synapse-workbench/");
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
    Terminal = Args._Terminal; Workspace = Args._Workspace;
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
                [SNew(STextBlock).Text(FText::FromString(TEXT("Synapse realm workbench")))]
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
                        .HintText(FText::FromString(TEXT("Private Realm workbench link from desktop Synapse")))
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
                    return FText::FromString(Terminal.IsValid() ? Terminal->GetLocalMessage() : TEXT("Workbench closed."));
                })
            ]
            + SVerticalBox::Slot().FillHeight(1.f)
            [SAssignNew(BrowserBox, SBox).MinDesiredWidth(760.f).MinDesiredHeight(400.f)]
        ]
    ];
}

SDaedalusSynapseWorkbenchPanel::~SDaedalusSynapseWorkbenchPanel() { Shutdown(); }

bool SDaedalusSynapseWorkbenchPanel::ParseLink(const FString& Link, FString& OutOrigin)
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
    const FString Suffix = AppPath + TEXT("#token=");
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
    if (bStarted || bClosing || !Terminal.IsValid() || !Workspace.IsValid()) return false;
    FString SelectedOrigin;
    if (!ParseLink(Link, SelectedOrigin))
    { Message(TEXT("Use the private Realm workbench link shown by desktop Synapse.")); return false; }
    IWebBrowserModule& Module = IWebBrowserModule::Get();
    IWebBrowserSingleton* Singleton = Module.GetSingleton();
    if (!Module.IsWebModuleAvailable() || !Singleton || Singleton->IsShuttingDown())
    { Message(TEXT("The embedded browser is unavailable in this build.")); return false; }
    Origin = MoveTemp(SelectedOrigin);
    ContextId = TEXT("DaedalusSynapse-") + FGuid::NewGuid().ToString(EGuidFormats::Digits);
    FBrowserContextSettings Context(ContextId);
    Context.CookieStorageLocation.Empty(); // CEF: empty cache_path is an isolated in-memory context.
    Context.bPersistSessionCookies = false;
    Context.bIgnoreCertificateErrors = false;
    if (!Singleton->RegisterContext(Context))
    { Origin.Reset(); ContextId.Reset(); Message(TEXT("A private browser context could not be created.")); return false; }
    if (bClosing || !Terminal.IsValid() || !Workspace.IsValid())
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
    if (bClosing || !Terminal.IsValid() || !Workspace.IsValid())
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
    Message(TEXT("Opening the desktop-approved Synapse interface. Saved actions use the same vault."));
    BrowserWindow->LoadURL(Link);
    return true;
}

bool SDaedalusSynapseWorkbenchPanel::AllowedDocument(const FString& Url) const
{
    if (Origin.IsEmpty()) return false;
    const FString Base = Origin + AppPath;
    if (Url == Base) return true;
    FString ParsedOrigin;
    return ParseLink(Url, ParsedOrigin) && ParsedOrigin == Origin;
}
bool SDaedalusSynapseWorkbenchPanel::HasApprovedDocument() const
{
    return !bClosing && bApprovedNavigation && BrowserWindow.IsValid() && !BrowserWindow->IsClosing()
        && AllowedDocument(BrowserWindow->GetUrl());
}
bool SDaedalusSynapseWorkbenchPanel::BeforeNavigate(const FString& Url, const FWebNavigationRequest& Request)
{
    const bool Allowed = !bClosing && Request.bIsMainFrame && !Request.bIsRedirect && AllowedDocument(Url);
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
    const FString Assets = AppPath + TEXT("assets/");
    if (Path.StartsWith(Assets, ESearchCase::CaseSensitive)) return SafeLeaf(Path.Mid(Assets.Len()));
    if (Path == AppPath + TEXT("favicon.svg")) return true;
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
    if (bClosing && !Origin.IsEmpty() && Method == TEXT("POST") && Url == Origin + TEXT("/workbench/v1/revoke")) return false;
    if (!bClosing && (Method == TEXT("GET") || Method == TEXT("POST")) && AllowedResource(Url)) return false;
    Body.Empty(); // UE's load interceptor supplies this empty local response instead of contacting the URL.
    return true;
}
void SDaedalusSynapseWorkbenchPanel::LoadingStarted()
{
    if (!bClosing && bApprovedNavigation && BrowserWindow.IsValid() && Workspace.IsValid())
        BrowserWindow->BindUObject(TEXT("workspace"), Workspace.Get(), false);
}
void SDaedalusSynapseWorkbenchPanel::Loaded()
{
    if (!HasApprovedDocument() || !Workspace.IsValid()) return;
    BrowserWindow->BindUObject(TEXT("workspace"), Workspace.Get(), false);
    Message(TEXT("Synapse remains local. Select files explicitly; JSON exports omit image bytes and settings."));
}
void SDaedalusSynapseWorkbenchPanel::Failed()
{
    Message(TEXT("Synapse could not load. Close this panel and create a fresh workbench link on the desktop."));
}
void SDaedalusSynapseWorkbenchPanel::Message(const TCHAR* Text)
{
    ADaedalusSynapseWorkbenchTerminal* Owner = Terminal.Get();
    if (!bClosing && Owner) Owner->SetLocalMessage(Text);
}
void SDaedalusSynapseWorkbenchPanel::Shutdown()
{
    if (bClosing) return;
    bClosing = true; bApprovedNavigation = false;
    if (Workspace.IsValid()) Workspace->Invalidate();
    if (BrowserWindow.IsValid())
    {
        // Fixed lifecycle notification only; delivery is best effort and never rolls back saved actions.
        BrowserWindow->ExecuteJavascript(TEXT("window.dispatchEvent(new Event('pagehide'));"));
        if (Workspace.IsValid()) BrowserWindow->UnbindUObject(TEXT("workspace"), Workspace.Get(), false);
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
    if (PairingInput.IsValid() && Terminal.IsValid()) Terminal->PairLocalApp(PairingInput->GetText().ToString());
    return FReply::Handled();
}
FReply SDaedalusSynapseWorkbenchPanel::CloseClicked()
{
    if (Terminal.IsValid()) Terminal->ClosePanel();
    return FReply::Handled();
}
FReply SDaedalusSynapseWorkbenchPanel::OnPreviewKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    // Once loaded, the original Synapse review UI owns Escape (end the review).
    if (Event.GetKey() == EKeys::Escape && !Browser.IsValid()) return CloseClicked();
    if (Event.GetKey() == EKeys::F12 || (Event.IsControlDown() && Event.IsShiftDown() && Event.GetKey() == EKeys::I))
        return FReply::Handled();
    return SCompoundWidget::OnPreviewKeyDown(Geometry, Event);
}
