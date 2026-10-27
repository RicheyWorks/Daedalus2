// SPDX-License-Identifier: MIT
// G33 Seed-Song Spring in Unreal (youtube-master's world/brew/story chapter). The rules are DaedalusSeedSongCore.h,
// byte-identical in behaviour to SeedSongSpring/SpringChain/KeeperLines (core-test/seed_song_core_test.cpp, 392-line
// parity replayed by SeedSongParityTest). ADaedalusSeedSong is Keeper Oriel's gramophone: Interact opens a conversation
// to listen, hear a clue or review and confirm a mend using the loaded herbs. ADaedalusSeedSpring is one of
// the twelve springs: Interact draws from it. Tunes come from the plugin's Content/YTM/found_tunes.csv.
#pragma once

#include "CoreMinimal.h"
#include "DaedalusOrrery.h"
#include "DaedalusSeedSongCore.h"
#include "DaedalusSeedSongGuide.h"
#include "DaedalusSeedSong.generated.h"

class ADaedalusSeedSpring;
class APlayerController;

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
	virtual void Tick(float DeltaSeconds) override;

	/** Chapter seed (Java SeedSongSpring seed): which notes each record has lost. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|SeedSong") int64 Seed = 2026;
	/** Herbs brewed for the next record (island herb names). A confirmed mend attempt uses them up. */
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
	/** Existing authored spring display name; read-only, with the id as fallback before the chapter is ready. */
	UFUNCTION(BlueprintPure, Category = "Daedalus|SeedSong") FString SpringName(const FString& SpringId) const;
	UFUNCTION(BlueprintCallable, Category = "Daedalus|SeedSong") FString Talk();
	/** The chapter in this world (the first ADaedalusSeedSong), or null. */
	static ADaedalusSeedSong* Find(const UObject* WorldContext);

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	// The focused fixture exercises scene/controller binding without attaching a dialogue to a real viewport.
	friend class FDaedalusSeedSongGuidanceTest;
	bool Ensure();
	FString NextEvent();
	void Tell(const FString& Line) const;
	void ShowGuide(daedalus::seedsong::GuidePage Page, const FString& Line = FString());
	void OnGuideChoice(const FString& Speaker, int32 Choice);
	void StopGuide();
	bool IsGuideCurrent() const;
	void ShowWater(const FString& Notice = FString());
	void ReviewSpring(const FString& Notice = FString());
	ADaedalusSeedSpring* NearbyCleanSpring(const ADaedalusHero* Hero) const;
	bool IsGuidanceSpring(const ADaedalusSeedSpring* Spring) const;
	APlayerController* LocalGuideController() const;
	bool IsSpringReviewCurrent() const;
	bool LookAtReviewedSpring();
	daedalus::seedsong::GuideReview CurrentReview() const;
	TWeakObjectPtr<ADaedalusHero> ListeningHero;
	FDelegateHandle GuideHandle;
	FString GuideRealm;
	daedalus::seedsong::GuidePage CurrentGuidePage = daedalus::seedsong::GuidePage::Home;
	std::vector<daedalus::seedsong::GuideChoice> PresentedChoices;
	daedalus::seedsong::GuideReview PresentedReview;
	TWeakObjectPtr<ADaedalusSeedSpring> ReviewedSpring;
	TWeakObjectPtr<APlayerController> ReviewedController;
	FString ReviewedSpringId;
	FVector ReviewedSpringPoint = FVector::ZeroVector;
	bool bEndingPlay = false;
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
