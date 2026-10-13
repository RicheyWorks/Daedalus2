// SPDX-License-Identifier: MIT

#pragma once

#include "CoreMinimal.h"
#include "DaedalusCastScriptCore.h"
#include "DaedalusOrrery.h"
#include "DaedalusTalker.generated.h"

class UTextRenderComponent;
class ADaedalusHero;

/**
 * A realm's NPC with a script (DCS 1, Content/Casts/<realm>.dcs): Curator Vell, the Frame-Hanger Twins, the
 * Gallery Guard... Interact talks; the lines go through the hero's dialogue box (SDaedalusDialogue) in the realm's
 * theme; an 'ask' comes back as the hero's choice and the script branches. Flags a script sets are kept on the
 * actor (Progress) and, for realm-wide flags, copied to every talker of the cast on the next talk.
 * Art: Mob_<Cast>_<Who> when Sol's export shipped; a placeholder block with a name label until then.
 */
UCLASS()
class DAEDALUSLINK_API ADaedalusTalker : public ADaedalusUsable
{
	GENERATED_BODY()

public:
	ADaedalusTalker();
	/** Which cast file (Content/Casts/<Cast>.dcs) and which character in it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Cast") FString Cast = TEXT("gallery-city");
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Daedalus|Cast") FString Who = TEXT("Curator Vell");
	/** The conversation's place and flags, one line (saved with the realm). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Cast") FString Progress;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Cast") int32 Talks = 0;
	/** Item ids this talker handed over (a 'give' line), for the harness. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus|Cast") FString Given;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Daedalus") TObjectPtr<UTextRenderComponent> Label;

	virtual FString Prompt(const ADaedalusHero* Hero) const override;
	virtual bool Use(ADaedalusHero* Hero) override;
	/** Bind a script now (after setting Cast/Who at spawn). Returns false with the parse error logged. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Cast") bool Rebind();
	/** Talk (what Interact does when this is the nearest usable). For Blueprints and the harness. */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Cast") bool TalkTo(ADaedalusHero* Hero) { return Use(Hero); }
	/** For the harness: "who=.. bound=1 where=start:0 flags=a,b talks=n". */
	UFUNCTION(BlueprintCallable, Category = "Daedalus|Cast") FString State() const;
	/** Realm-wide flags set by any talker of this cast in this world (e.g. heartstone_done lets the Choir sing). */
	static TSet<FString>& SharedFlags(const UWorld* World, const FString& Cast);

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type Reason) override;

private:
	void Continue(ADaedalusHero* Hero, int32 Choice);
	void Deliver(ADaedalusHero* Hero, const daedalus::cast::Beat& Beat);
	void OnChoice(const FString& Speaker, int32 Choice);

	TSharedPtr<daedalus::cast::Cast> Script;   // the whole cast file; the conversation points into it
	daedalus::cast::Conversation Talk;
	TWeakObjectPtr<ADaedalusHero> Talking;
	FDelegateHandle ChoiceHandle;
	bool bAsking = false;
};
