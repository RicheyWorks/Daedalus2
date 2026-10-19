// SPDX-License-Identifier: MIT
// G25 brew bench in Unreal: the client of POST /api/v1/brew/melody (docs/contracts/brew-melody-v1, youtube-master #316).
// Java (world.brew BrewBench behind the route) does every calculation; this file only gathers the kettle herbs, the
// records the jukebox has played, sends them once, and shows the parsed reply. Building, bounds and parsing live in
// DaedalusBrewMelodyCore.h (core-test/brew_melody_core_test.cpp, 18/18 against the contract's http-cases.json).
// The HTTP half follows the Kennel Isle trough (DaedalusTonic.cpp): https anywhere, http only to 127.0.0.1, bearer from
// ConfigureSession or DAEDALUS_BREW_ORIGIN / DAEDALUS_BREW_TOKEN (falling back to DAEDALUS_KENNEL_*), never saved.
#pragma once

#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusBrewMelodyCore.h"
#include "DaedalusBrewBench.generated.h"

class IHttpRequest;

DECLARE_DYNAMIC_MULTICAST_DELEGATE_ThreeParams(FDaedalusMelodyBrewed, const FString&, Item, int32, Tier, const FString&, FoundTune);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FDaedalusMelodyRefused, int32, Status, const FString&, Reason);

/** The Youtube Master Island brew bench: put 3 to 5 island herbs in the kettle, Interact, and the server brews the melody. */
UCLASS(Blueprintable)
class DAEDALUSLINK_API ADaedalusBrewBench : public ADaedalusUsable
{
	GENERATED_BODY()
public:
	ADaedalusBrewBench();
	virtual FString Prompt(const ADaedalusHero* Hero) const override;
	virtual bool Use(ADaedalusHero* Hero) override;

	/** Kettle contents: PitchTable.ISLAND_CANON herb names (Doleaf, Sharpcress, ...). Stages are optional, one per herb (1..4). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Brew") TArray<FString> Herbs;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Brew") TArray<int32> Stages;

	UFUNCTION(BlueprintCallable, Category = "Daedalus|Brew") bool ConfigureSession(const FString& Origin, const FString& Token);
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Brew") void ClearSession();
	/** False when the kettle is full, brewing, or the herb is not one of the twelve island herbs. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Brew") bool AddHerb(const FString& Herb);
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Brew") void ClearKettle();
	/** The jukebox played this record (stands in for BrewBench.playRecord); sent with the next brew. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Brew") bool RecordPlayed(const FString& RecordId);
	/** Send the kettle to the server. False (see LastError) when nothing was sent. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Brew") bool Brew();

	UFUNCTION(BlueprintPure, Category = "Daedalus|Brew") bool IsBrewing() const { return Pending.IsValid(); }
	UFUNCTION(BlueprintPure, Category = "Daedalus|Brew") TArray<FString> PlayedRecords() const { return Records; }
	UFUNCTION(BlueprintPure, Category = "Daedalus|Brew") FString LastItem() const { return LastItemId; }
	UFUNCTION(BlueprintPure, Category = "Daedalus|Brew") FString LastEffect() const { return LastEffectId; }
	UFUNCTION(BlueprintPure, Category = "Daedalus|Brew") FString LastFoundTune() const { return LastTune; }
	UFUNCTION(BlueprintPure, Category = "Daedalus|Brew") int32 LastTier() const { return LastTierValue; }
	UFUNCTION(BlueprintPure, Category = "Daedalus|Brew") TArray<int32> LastNotes() const { return LastNoteList; }
	UFUNCTION(BlueprintPure, Category = "Daedalus|Brew") FString LastError() const { return Error; }

	UPROPERTY(BlueprintAssignable, Category = "Daedalus|Brew") FDaedalusMelodyBrewed OnBrewed;
	UPROPERTY(BlueprintAssignable, Category = "Daedalus|Brew") FDaedalusMelodyRefused OnRefused;

protected:
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	bool HasSession();
	void Finish(int32 Status, const std::string& Text);
	void Tell(const FString& Line) const;

	TArray<FString> Records;
	// Deliberately not UPROPERTY/config/replicated: credentials are not asset data.
	FString ServerOrigin;
	FString BearerToken;
	uint64 Generation = 0;
	TSharedPtr<IHttpRequest, ESPMode::ThreadSafe> Pending;
	FString LastItemId, LastEffectId, LastTune, Error;
	int32 LastTierValue = 0;
	TArray<int32> LastNoteList;
};

/** The island jukebox: Interact plays the next record, and the nearest brew bench hears it (the records list of the next brew). */
UCLASS(Blueprintable)
class DAEDALUSLINK_API ADaedalusJukebox : public ADaedalusUsable
{
	GENERATED_BODY()
public:
	ADaedalusJukebox();
	virtual FString Prompt(const ADaedalusHero* Hero) const override;
	virtual bool Use(ADaedalusHero* Hero) override;

	/** Record item ids in play order (the twelve found-tune records by default). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Brew") TArray<FString> Records;
	/** The bench that listens; when empty, the nearest ADaedalusBrewBench within BenchReach. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Brew") TObjectPtr<ADaedalusBrewBench> Bench;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Brew") float BenchReach = 3000.f;

	UFUNCTION(BlueprintPure, Category = "Daedalus|Brew") FString NowPlaying() const { return Playing; }

private:
	ADaedalusBrewBench* FindBench() const;
	int32 Next = 0;
	FString Playing;
};