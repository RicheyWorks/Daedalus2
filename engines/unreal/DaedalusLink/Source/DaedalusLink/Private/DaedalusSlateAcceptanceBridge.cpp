// SPDX-License-Identifier: MIT
#include "DaedalusSlateAcceptanceBridge.h"

#if WITH_EDITOR
#include "Framework/Application/SlateApplication.h"
#include "Framework/Application/SlateUser.h"
#include "Input/Events.h"
#include "Input/Reply.h"
#include "InputCoreTypes.h"
#include "Layout/WidgetPath.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/SVirtualWindow.h"
#include "Widgets/SNullWidget.h"

namespace
{
// Owns only a newly allocated virtual user; never borrows an existing user's focus
// or pointer state. Handle destruction unregisters it in installed UE5.8.3.
class FScopedSlateFixture
{
public:
    explicit FScopedSlateFixture(FSlateApplication& InApp)
        : App(InApp), Window(SNew(SVirtualWindow).Size(FVector2D(160, 80)))
    {
        TSet<int32> ExistingUsers;
        App.ForEachUser([&ExistingUsers](FSlateUser& User)
        {
            ExistingUsers.Add(User.GetUserIndex());
        }, true);

        // Virtual indices are distinct from Slate user indices. Skip borrowed
        // handles without mutating them; bound the search instead of stealing one.
        for (int32 Candidate = 0; Candidate < 32; ++Candidate)
        {
            TSharedPtr<FSlateVirtualUserHandle> Handle = App.FindOrCreateVirtualUser(Candidate);
            if (!ExistingUsers.Contains(Handle->GetUserIndex()))
            {
                VirtualUser = MoveTemp(Handle);
                break;
            }
        }
    }

    ~FScopedSlateFixture()
    {
        Cleanup();
    }

    void Register(const TSharedRef<SButton>& Button)
    {
        Window->SetContent(Button);
        App.RegisterVirtualWindow(Window);
        bRegistered = true;
    }

    void Cleanup()
    {
        // Clear fixture focus while its registered path is still valid. The
        // hardware keyboard user's focus is never reassigned by this fixture.
        if (VirtualUser.IsValid())
        {
            App.ClearUserFocus(VirtualUser->GetUserIndex(), EFocusCause::SetDirectly);
            VirtualUser.Reset();
        }
        if (bRegistered)
        {
            // The fast path finder follows live parent links even after window
            // unregistration. Detach only our content before checking removal.
            Window->SetContent(SNullWidget::NullWidget);
            App.UnregisterVirtualWindow(Window);
            bRegistered = false;
            bUnregisterCalled = true;
        }
    }

    FSlateApplication& App;
    TSharedRef<SVirtualWindow> Window;
    TSharedPtr<FSlateVirtualUserHandle> VirtualUser;
    bool bRegistered = false;
    bool bUnregisterCalled = false;
};
}

FDaedalusSlateAcceptanceResult FDaedalusSlateAcceptanceBridge::RunButtonFixture()
{
    FDaedalusSlateAcceptanceResult Result;
    if (!IsInGameThread())
    {
        Result.FailureReason = TEXT("Fixture requires the editor game thread.");
        return Result;
    }
    if (!FSlateApplication::IsInitialized())
    {
        Result.FailureReason = TEXT("Fixture requires an initialized Slate application.");
        return Result;
    }

    FSlateApplication& App = FSlateApplication::Get();
    const TSharedPtr<SWidget> PreviousKeyboardFocus = App.GetKeyboardFocusedWidget();
    const TSharedPtr<SWindow> PreviousActiveWindow = App.GetActiveTopLevelWindow();
    FScopedSlateFixture Fixture(App);
    if (!Fixture.VirtualUser.IsValid())
    {
        Result.FailureReason = TEXT("No unused virtual-user slot within the fixture's bounded search.");
        return Result;
    }
    const int32 UserIndex = Fixture.VirtualUser->GetUserIndex();
    if (!App.GetUser(UserIndex).IsValid() || !App.GetUser(UserIndex)->IsVirtualUser())
    {
        Result.FailureReason = TEXT("Slate did not allocate an isolated virtual user.");
        return Result;
    }
    const TSharedPtr<SWidget> PreviousVirtualFocus = App.GetUserFocusedWidget(UserIndex);

    TSharedRef<SButton> Button = SNew(SButton)
        .ClickMethod(EButtonClickMethod::MouseDown)
        .IsFocusable(false)
        .OnClicked_Lambda([&Result]()
        {
            ++Result.ClickCount;
            return FReply::Handled();
        });
    const TSharedRef<SButton> DetachedButton = SNew(SButton);
    FWidgetPath DetachedPath;
    Result.bDetachedWidgetRejected = !App.GeneratePathToWidgetUnchecked(DetachedButton, DetachedPath);
    Fixture.Register(Button);

    FWidgetPath Path;
    if (!App.GeneratePathToWidgetUnchecked(Button, Path) || !Path.IsValid()
        || Path.GetWindow() != Fixture.Window || Path.Widgets.Last().Widget != Button)
    {
        Result.FailureReason = TEXT("Could not resolve the button exclusively inside the virtual fixture window.");
        return Result;
    }
    // GeneratePathToWidgetUnchecked supplies geometry, not the per-widget
    // pointer entries required by FEventRouter. Its valid-looking path crashes
    // routing in UE5.8.3 when GetVirtualPointerPosition(0) indexes an empty array.
    // The public pointer-aware constructor adds an optional entry per widget;
    // an unset optional is the correct identity transform for this 2D fixture.
    TArray<FWidgetAndPointer> PointerWidgets;
    PointerWidgets.Reserve(Path.Widgets.Num());
    for (int32 Index = 0; Index < Path.Widgets.Num(); ++Index)
    {
        PointerWidgets.Emplace(Path.Widgets[Index]);
    }
    FWidgetPath PointerPath{MakeArrayView(PointerWidgets)};
    if (PointerWidgets.IsEmpty() || !PointerPath.IsValid()
        || PointerPath.Widgets.Num() != Path.Widgets.Num()
        || PointerPath.GetWindow() != Fixture.Window
        || PointerPath.Widgets.Last().Widget != Button)
    {
        Result.FailureReason = TEXT("Pointer path did not preserve the isolated fixture identity.");
        return Result;
    }
    for (int32 Index = 0; Index < Path.Widgets.Num(); ++Index)
    {
        if (PointerPath.Widgets[Index].Widget != Path.Widgets[Index].Widget
            || PointerPath.GetVirtualPointerPosition(Index).IsSet())
        {
            Result.FailureReason = TEXT("Pointer path changed widget identity or the 2D transform.");
            return Result;
        }
    }
    const FVector2D Position = PointerPath.Widgets.Last().Geometry.GetAbsolutePosition();
    const auto PointerEvent = [UserIndex, Position](FKey EffectingButton, bool bPressed)
    {
        TSet<FKey> PressedButtons;
        if (bPressed)
        {
            PressedButtons.Add(EffectingButton);
        }
        return FPointerEvent(static_cast<uint32>(UserIndex), 0, Position, Position,
            PressedButtons, EffectingButton, 0.0f, FModifierKeysState());
    };

    // Route only to the verified fixture path. These public APIs bypass global
    // hardware input dispatch/preprocessors and do not move the OS cursor.
    const FReply WrongButton = App.RoutePointerDownEvent(PointerPath, PointerEvent(EKeys::RightMouseButton, true));
    App.RoutePointerUpEvent(PointerPath, PointerEvent(EKeys::RightMouseButton, false));
    Result.bWrongButtonRejected = !WrongButton.IsEventHandled() && Result.ClickCount == 0;

    Button->SetEnabled(false);
    const FReply Disabled = App.RoutePointerDownEvent(PointerPath, PointerEvent(EKeys::LeftMouseButton, true));
    App.RoutePointerUpEvent(PointerPath, PointerEvent(EKeys::LeftMouseButton, false));
    Result.bDisabledButtonRejected = !Disabled.IsEventHandled() && Result.ClickCount == 0;

    Button->SetEnabled(true);
    const FReply Enabled = App.RoutePointerDownEvent(PointerPath, PointerEvent(EKeys::LeftMouseButton, true));
    Result.bEnabledClickHandled = Enabled.IsEventHandled() && Result.ClickCount == 1;
    Result.bVirtualFocusPreserved = App.GetUserFocusedWidget(UserIndex) == PreviousVirtualFocus;
    App.RoutePointerUpEvent(PointerPath, PointerEvent(EKeys::LeftMouseButton, false));
    Result.bButtonReleased = !Button->IsPressed();
    Result.bRan = true;

    Fixture.Cleanup();
    FWidgetPath RemovedPath;
    Result.bWindowUnregisterCalled = Fixture.bUnregisterCalled;
    Result.bOwnedContentDetached = !Button->GetParentWidget().IsValid()
        && !App.GeneratePathToWidgetUnchecked(Button, RemovedPath);
    Result.bVirtualUserReleased = !App.GetUser(UserIndex).IsValid();
    Result.bKeyboardFocusPreserved = App.GetKeyboardFocusedWidget() == PreviousKeyboardFocus;
    Result.bActiveWindowPreserved = App.GetActiveTopLevelWindow() == PreviousActiveWindow;
    if (!Result.Passed())
    {
        Result.FailureReason = TEXT("One or more native fixture observations failed; inspect result fields.");
    }
    return Result;
}
#endif
