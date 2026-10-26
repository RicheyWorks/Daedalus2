// SPDX-License-Identifier: MIT
#pragma once
class ADaedalusUsable : public AActor
{
public:
    int32 UseCount = 0;
};
class ADaedalusGalleryMotifRack : public ADaedalusUsable
{
public:
    void ReleaseStudies();
    void Fine(int32 Count);
    TArray<int32> Studies;
};
class ADaedalusJavaArcade : public ADaedalusUsable
{
public:
    void Bootstrap(const FString& Text);
    FString Status;
};
