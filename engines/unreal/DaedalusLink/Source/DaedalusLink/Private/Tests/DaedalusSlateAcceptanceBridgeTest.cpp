// SPDX-License-Identifier: MIT
#include "DaedalusSlateAcceptanceBridge.h"

#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
#include "Framework/Application/SlateApplication.h"
#include "Misc/AutomationTest.h"

// Requires a real initialized editor Slate application. No mock application,
// native OS window, saved map, asset, inspector ref, or production UI is used.
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusSlateVirtualButtonTest,
    "Daedalus.Slate.Acceptance.VirtualButton",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FDaedalusSlateVirtualButtonTest::RunTest(const FString& Parameters)
{
    const FDaedalusSlateAcceptanceResult Result = FDaedalusSlateAcceptanceBridge::RunButtonFixture();
    if (!TestTrue(*Result.FailureReason, Result.bRan))
    {
        return false;
    }
    TestTrue(TEXT("Detached widget cannot resolve to an application path"), Result.bDetachedWidgetRejected);
    TestTrue(TEXT("Right mouse button cannot activate SButton"), Result.bWrongButtonRejected);
    TestTrue(TEXT("Disabled SButton cannot invoke callback"), Result.bDisabledButtonRejected);
    TestTrue(TEXT("Enabled left pointer down routes to actual SButton callback"), Result.bEnabledClickHandled);
    TestEqual(TEXT("Exactly one OnClicked callback"), Result.ClickCount, 1);
    TestTrue(TEXT("Nonfocusable fixture preserves virtual user focus"), Result.bVirtualFocusPreserved);
    TestTrue(TEXT("Pointer up releases button state"), Result.bButtonReleased);
    TestTrue(TEXT("Hardware keyboard focus remains unchanged"), Result.bKeyboardFocusPreserved);
    TestTrue(TEXT("Active top-level window remains unchanged"), Result.bActiveWindowPreserved);
    TestTrue(TEXT("Temporary virtual user is unregistered"), Result.bVirtualUserReleased);
    TestTrue(TEXT("Temporary window no longer resolves its widget"), Result.bWindowUnregistered);
    TestTrue(*Result.FailureReason, Result.Passed());
    return !HasAnyErrors();
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusSlateRepeatCleanupTest,
    "Daedalus.Slate.Acceptance.RepeatCleanup",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FDaedalusSlateRepeatCleanupTest::RunTest(const FString& Parameters)
{
    if (!TestTrue(TEXT("Editor has initialized Slate"), FSlateApplication::IsInitialized()))
    {
        return false;
    }
    FSlateApplication& App = FSlateApplication::Get();
    const TSharedPtr<SWidget> OriginalFocus = App.GetKeyboardFocusedWidget();
    const TSharedPtr<SWindow> OriginalActiveWindow = App.GetActiveTopLevelWindow();
    const FDaedalusSlateAcceptanceResult First = FDaedalusSlateAcceptanceBridge::RunButtonFixture();
    const FDaedalusSlateAcceptanceResult Second = FDaedalusSlateAcceptanceBridge::RunButtonFixture();
    TestTrue(TEXT("First isolated fixture passes"), First.Passed());
    TestTrue(TEXT("Second isolated fixture passes without stale callback or path state"), Second.Passed());
    TestEqual(TEXT("Second run starts with its own callback count"), Second.ClickCount, 1);
    TestTrue(TEXT("Repeated execution preserves the original keyboard focus"), App.GetKeyboardFocusedWidget() == OriginalFocus);
    TestTrue(TEXT("Repeated execution preserves the original active window"), App.GetActiveTopLevelWindow() == OriginalActiveWindow);
    return !HasAnyErrors();
}
#endif
