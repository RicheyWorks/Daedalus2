// SPDX-License-Identifier: MIT
#include "DaedalusLegacyHlodFixture.h"
#if WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR
#include "Misc/AutomationTest.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusLegacyHlodFixturePolicy,
    "Daedalus.Editor.HLODFixture.Policy", EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FDaedalusLegacyHlodFixturePolicy::RunTest(const FString& Parameters)
{
    using DaedalusLegacyHlodFixture::CheckPolicy;
    TestTrue(TEXT("One new local two-source Merge tier"), CheckPolicy(false, false, false, true, 2, 0));
    TestFalse(TEXT("Forced project hierarchy is not changed"), CheckPolicy(true, false, false, true, 2, 0));
    TestFalse(TEXT("Description-backed persistence is outside R1"), CheckPolicy(false, true, false, true, 2, 0));
    TestFalse(TEXT("World Partition is a distinct route"), CheckPolicy(false, false, true, true, 2, 0));
    TestFalse(TEXT("Existing loaded or disk package cannot be replaced"), CheckPolicy(false, false, false, false, 2, 0));
    TestFalse(TEXT("Zero sources"), CheckPolicy(false, false, false, true, 0, 0));
    TestFalse(TEXT("One source"), CheckPolicy(false, false, false, true, 1, 0));
    TestFalse(TEXT("Unexpected extra source"), CheckPolicy(false, false, false, true, 3, 0));
    TestFalse(TEXT("Negative tier"), CheckPolicy(false, false, false, true, 2, -1));
    TestFalse(TEXT("Extra tier"), CheckPolicy(false, false, false, true, 2, 1));
    return true;
}
#endif
