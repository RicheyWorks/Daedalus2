#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DaedalusOceanHostClient.generated.h"

class IHttpRequest;
USTRUCT(BlueprintType)
struct FDaedalusOceanChunkView
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Ocean") int32 X=0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Ocean") int32 Y=0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Ocean") int32 Z=0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Ocean") int64 Revision=0;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Ocean") TArray<FString> Palette;
    UPROPERTY(BlueprintReadOnly, Category="Daedalus|Ocean") TArray<uint8> Blocks;
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
    UPROPERTY(BlueprintAssignable, Category="Daedalus|Ocean") FDaedalusOceanChunkReceived OnChunk;
    UPROPERTY(BlueprintAssignable, Category="Daedalus|Ocean") FDaedalusOceanRequestFailed OnFailure;
    virtual void OnComponentDestroyed(bool bDestroyingHierarchy) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    static bool DecodeChunk(const FString& Json,int32 X,int32 Y,int32 Z,FDaedalusOceanChunkView& Out);
private:
    // Deliberately not UPROPERTY/config/replicated: credentials are not asset data.
    FString ServerOrigin;
    FString BearerToken;
    uint64 Generation=0;
    TSharedPtr<IHttpRequest,ESPMode::ThreadSafe> Pending;
};
