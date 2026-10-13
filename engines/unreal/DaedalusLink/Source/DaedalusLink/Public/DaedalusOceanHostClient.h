#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DaedalusOceanHostClient.generated.h"

class IHttpRequest;
USTRUCT(BlueprintType)
struct FDaedalusOceanChunkView
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) int32 X=0;
    UPROPERTY(BlueprintReadOnly) int32 Y=0;
    UPROPERTY(BlueprintReadOnly) int32 Z=0;
    UPROPERTY(BlueprintReadOnly) int64 Revision=0;
    UPROPERTY(BlueprintReadOnly) TArray<FString> Palette;
    UPROPERTY(BlueprintReadOnly) TArray<uint8> Blocks;
};
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FDaedalusOceanChunkReceived,const FDaedalusOceanChunkView&,Chunk);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FDaedalusOceanRequestFailed,int32,Status,const FString&,Reason);

/** Local read client; caller supplies a trusted login origin/token. No automatic world edits. */
UCLASS(ClassGroup=(Daedalus),meta=(BlueprintSpawnableComponent))
class DAEDALUSLINK_API UDaedalusOceanHostClient : public UActorComponent
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable,Category="Daedalus|Ocean") bool ConfigureSession(const FString& Origin,const FString& Token);
    UFUNCTION(BlueprintCallable,Category="Daedalus|Ocean") bool RequestChunk(int32 X,int32 Y,int32 Z);
    UFUNCTION(BlueprintCallable,Category="Daedalus|Ocean") void ClearSession();
    UPROPERTY(BlueprintAssignable) FDaedalusOceanChunkReceived OnChunk;
    UPROPERTY(BlueprintAssignable) FDaedalusOceanRequestFailed OnFailure;
    virtual void OnComponentDestroyed(bool bDestroyingHierarchy) override;
    static bool DecodeChunk(const FString& Json,int32 X,int32 Y,int32 Z,FDaedalusOceanChunkView& Out);
private:
    // Deliberately not UPROPERTY/config/replicated: credentials are not asset data.
    FString ServerOrigin;
    FString BearerToken;
    uint64 Generation=0;
    TSharedPtr<IHttpRequest,ESPMode::ThreadSafe> Pending;
};
