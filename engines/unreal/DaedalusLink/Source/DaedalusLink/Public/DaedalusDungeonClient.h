// SPDX-License-Identifier: MIT
#pragma once
#include "CoreMinimal.h"
#include "DaedalusDungeonCore.h"
class IHttpRequest;

// Optional host-owned consumer. Call on the game thread; never expose credentials to UI.
// Claude's realm UI can own MakeShared<FDaedalusDungeonClient>() and read State().
class DAEDALUSLINK_API FDaedalusDungeonClient : public TSharedFromThis<FDaedalusDungeonClient> {
public:
    ~FDaedalusDungeonClient();
    bool Configure(const FString& BaseUrl, const FString& SessionBearer);
    bool Refresh();
    bool Choose(int32 Index);
    void Cancel();
    const DaedalusDungeon::Session& State() const {return Policy;}
    const FString& Error() const {return LastError;}
private:
    bool Send(uint64 Id, const FString& Verb, const FString& Path, const FString& Body);
    FString Base, Bearer, Prefix, LastError;
    DaedalusDungeon::Session Policy;
    uint64 PendingId=0;
    TSharedPtr<IHttpRequest, ESPMode::ThreadSafe> Active;
};
