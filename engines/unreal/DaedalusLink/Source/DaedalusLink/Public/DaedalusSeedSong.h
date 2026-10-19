// SPDX-License-Identifier: MIT
// G33 Seed-Song Spring in Unreal (youtube-master's world/brew/story chapter). The rules are DaedalusSeedSongCore.h,
// byte-identical in behaviour to SeedSongSpring/SpringChain/KeeperLines (core-test/seed_song_core_test.cpp, 392-line
// parity replayed by SeedSongParityTest). ADaedalusSeedSong is Keeper Oriel's gramophone: Interact restores the next
// scratched record with the kettle herbs (or talks and hints when the kettle is empty). ADaedalusSeedSpring is one of
// the twelve springs: Interact draws from it. Tunes come from the plugin's Content/YTM/found_tunes.csv.
#pragma once

#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusSeedSongCore.h"
#include "DaedalusSeedSong.generated.h"

/** The tunes and the chapter that points into them; kept together on the heap so the pointers stay valid. */
struct FDaedalusSeedSongState
{
	std::vector<daedalus::seedsong::Tune> Tunes;
	TUniquePtr<daedalus::seedsong::Chapter> Chapter;
};

UCLASS(Blueprintable)
class DAEDALUSLINK_API ADaedalusSeedSong : public ADaedalusUsable
{
	GENERATED_BODY()
public:
	ADaedalusSeedSong();
	virtual FString Prompt(const ADaedalusHero* Hero) const override;
	virtual bool Use(ADaedalusHero* Hero) override;

	/** Chapter seed (Java SeedSongSpring seed): which notes each record has lost. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|SeedSong") int64 Seed = 2026;
	/** Herbs brewed for the next record (island herb names). Interact uses them up. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|SeedSong") TArray<FString> KettleHerbs;

	UFUNCTION(BlueprintPure, Category = "Daedalus|SeedSong") bool IsReady() const { return State.IsValid() && State->Chapter.IsValid(); }
	UFUNCTION(BlueprintPure, Category = "Daedalus|SeedSong") int32 RecordCount() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|SeedSong") int32 RestoredCount() const;
	UFUNCTION(BlueprintPure, Category = "Daedalus|SeedSong") int32 CleanSprings() const;
	/** The first record not yet restored, or empty when the choir is whole. */
	UFUNCTION(BlueprintPure, Category = "Daedalus|SeedSong") FString NextRecord() const;
	/** Restore one record with these herbs; returns the outcome name (RESTORED, NEEDLE_SKIPS, ...). */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|SeedSong") FString Restore(const FString& RecordItem, const TArray<FString>& Herbs);
	/** Draw from a spring; returns "OUTCOME item amount". */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|SeedSong") FString Draw(const FString& SpringId);
	UFUNCTION(BlueprintCallable, Category = "Daedalus|SeedSong") FString Talk();
	/** The chapter in this world (the first ADaedalusSeedSong), or null. */
	static ADaedalusSeedSong* Find(const UObject* WorldContext);

protected:
	virtual void BeginPlay() override;

private:
	bool Ensure();
	FString NextEvent();
	void Tell(const FString& Line) const;
	TSharedPtr<FDaedalusSeedSongState> State;
	int32 Events = 0;
};

UCLASS(Blueprintable)
class DAEDALUSLINK_API ADaedalusSeedSpring : public ADaedalusUsable
{
	GENERATED_BODY()
public:
	ADaedalusSeedSpring();
	virtual FString Prompt(const ADaedalusHero* Hero) const override;
	virtual bool Use(ADaedalusHero* Hero) override;
	/** spring_1 .. spring_12 (SpringChain.island()). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|SeedSong") FString SpringId = TEXT("spring_1");
};