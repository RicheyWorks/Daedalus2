// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "DaedalusShardsteadComponent.h"
#include "Widgets/SCompoundWidget.h"
class SVerticalBox;
/** Embeddable Production tab page. Display-only: canonical host DTOs, no inventory mutation. */
class SDaedalusShardstead : public SCompoundWidget {
public:
    SLATE_BEGIN_ARGS(SDaedalusShardstead) {}
        SLATE_ARGUMENT(FString, ThemeName)
    SLATE_END_ARGS()
    void Construct(const FArguments& Args);
    void Refresh(const FDaedalusIslandStats& Stats,const TArray<FDaedalusIslandClaimRow>& Claims);
    /** Local authoritative host only. Remote clients must supply their authenticated DTO. */
    bool RefreshFromHost(const UDaedalusShardsteadComponent* Source,const FString& CrewKey);
private:
    FString ThemeName;
    FDaedalusIslandStats Stats;
    TArray<FDaedalusIslandClaimRow> Claims;
    TSharedPtr<SVerticalBox> Body;
    void Rebuild();
    TSharedRef<SWidget> Card(int32 Resource) const;
};
