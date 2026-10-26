// SPDX-License-Identifier: MIT
#include "bad_cpp_shadow.h"
// Owner and Children in comments are fine: FString Owner; auto Children=Studies;
void ADaedalusGalleryMotifRack::Fine(int32 Count)
{
    auto StudyList=Studies; const FString Label = TEXT("FString Owner;");
    Owner = nullptr; Studies.Reset(); return;
    int32 Total = Count + StudyList.Num();
    FString Children; // preflight: allow P12
    (void)Total; (void)Label;
}
static void Free(int32 Owner) { int32 Studies = Owner; (void)Studies; }
