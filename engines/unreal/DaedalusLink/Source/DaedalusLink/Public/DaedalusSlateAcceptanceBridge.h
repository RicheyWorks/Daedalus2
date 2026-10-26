// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"

#if WITH_EDITOR
/** Observations from a disposable Slate fixture, not acceptance of a production UI. */
struct DAEDALUSLINK_API FDaedalusSlateAcceptanceResult
{
    bool bRan = false;
    bool bDetachedWidgetRejected = false;
    bool bWrongButtonRejected = false;
    bool bDisabledButtonRejected = false;
    bool bEnabledClickHandled = false;
    bool bVirtualFocusPreserved = false;
    bool bButtonReleased = false;
    bool bKeyboardFocusPreserved = false;
    bool bActiveWindowPreserved = false;
    bool bVirtualUserReleased = false;
    // Explicit API call, not independent enumeration of Slate's private registry.
    bool bWindowUnregisterCalled = false;
    bool bOwnedContentDetached = false;
    int32 ClickCount = 0;
    FString FailureReason;

    bool Passed() const
    {
        return bRan && bDetachedWidgetRejected && bWrongButtonRejected
            && bDisabledButtonRejected && bEnabledClickHandled && bVirtualFocusPreserved
            && bButtonReleased && bKeyboardFocusPreserved && bActiveWindowPreserved && bVirtualUserReleased
            && bWindowUnregisterCalled && bOwnedContentDetached
            && ClickCount == 1 && FailureReason.IsEmpty();
    }
};

/**
 * Editor game-thread acceptance fixture using actual Slate routing and SButton.
 * Has no caller-selected widget, command, reference, key, or mouse position.
 * Registers only an offscreen virtual window and a temporary virtual input user.
 * Does not create an OS window, drive the hardware cursor, tick Slate, or save assets.
 * PR185/202's read-only inspector/parser contract is deliberately independent.
 */
class DAEDALUSLINK_API FDaedalusSlateAcceptanceBridge
{
public:
    static FDaedalusSlateAcceptanceResult RunButtonFixture();
};
#endif
