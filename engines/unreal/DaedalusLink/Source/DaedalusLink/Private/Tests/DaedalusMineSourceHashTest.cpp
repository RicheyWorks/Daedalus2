// SPDX-License-Identifier: MIT
#include "Misc/AutomationTest.h"

#if WITH_EDITOR && WITH_DEV_AUTOMATION_TESTS
#include "DaedalusMineSourceHash.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FDaedalusMineSourceHashTest,
    "Daedalus.Editor.Animation.MineSourceSha256",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FDaedalusMineSourceHashTest::RunTest(const FString& Parameters)
{
    (void)Parameters;
    FString Digest = TEXT("old");
    const uint8 Empty = 0;
    TestTrue(TEXT("Empty input hashes"), DaedalusMineSourceHash::Compute(&Empty, 0, Digest));
    TestEqual(TEXT("Empty vector"), Digest,
        TEXT("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"));
    const ANSICHAR Abc[] = "abc";
    TestTrue(TEXT("abc hashes"), DaedalusMineSourceHash::Compute(
        reinterpret_cast<const uint8*>(Abc), 3, Digest));
    TestEqual(TEXT("abc vector"), Digest,
        TEXT("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"));
    const ANSICHAR Multi[] = "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq";
    TestTrue(TEXT("Multi-block input hashes"), DaedalusMineSourceHash::Compute(
        reinterpret_cast<const uint8*>(Multi), sizeof(Multi) - 1, Digest));
    TestEqual(TEXT("Multi-block vector"), Digest,
        TEXT("248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"));
    TestFalse(TEXT("Null nonempty input refused"), DaedalusMineSourceHash::Compute(nullptr, 1, Digest));
    TestTrue(TEXT("Refusal clears stale digest"), Digest.IsEmpty());
    return true;
}
#endif
