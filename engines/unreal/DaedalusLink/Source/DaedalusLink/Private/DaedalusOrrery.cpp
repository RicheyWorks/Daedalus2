// SPDX-License-Identifier: MIT

#include "DaedalusOrrery.h"

#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "DaedalusHero.h"
#include "DaedalusSkyDirector.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"

// ------------------------------------------------------------------------------------------------ the herbs

const TArray<UDaedalusOrrery::FHerb>& UDaedalusOrrery::Herbs()
{
	// 24 herbs, one per sky hour; each constellation has one day bloom (6:00..17:59) and one night bloom.
	static const TArray<FHerb> H = {
		{TEXT("Dawnthistle"), 6, TEXT("Keeper")}, {TEXT("Midnightmint"), 0, TEXT("Keeper")},
		{TEXT("Sunsprig"), 8, TEXT("Lantern")}, {TEXT("Duskmallow"), 18, TEXT("Lantern")},
		{TEXT("Orbitfern"), 9, TEXT("Ark")}, {TEXT("Moonvetch"), 21, TEXT("Ark")},
		{TEXT("Eclipsebell"), 13, TEXT("Shard")}, {TEXT("Meteorsage"), 1, TEXT("Shard")},
		{TEXT("Equinoxbalm"), 10, TEXT("Wanderer")}, {TEXT("Cometcress"), 3, TEXT("Wanderer")},
		{TEXT("Heartstonebloom"), 7, TEXT("Hearth")}, {TEXT("Starsedge"), 22, TEXT("Hearth")},
		{TEXT("Zenithclover"), 11, TEXT("Spindle")}, {TEXT("Nebulawort"), 23, TEXT("Spindle")},
		{TEXT("Noonspire"), 12, TEXT("Crown")}, {TEXT("Polarisroot"), 2, TEXT("Crown")},
		{TEXT("Driftfennel"), 16, TEXT("Tide")}, {TEXT("Nadirmoss"), 4, TEXT("Tide")},
		{TEXT("Quasarthyme"), 14, TEXT("Forge")}, {TEXT("Twilightsorrel"), 19, TEXT("Forge")},
		{TEXT("Solsticerue"), 15, TEXT("Kite")}, {TEXT("Auroraleaf"), 5, TEXT("Kite")},
		{TEXT("Lunarlily"), 17, TEXT("Loom")}, {TEXT("Galaxygrass"), 20, TEXT("Loom")},
	};
	return H;
}

const UDaedalusOrrery::FHerb* UDaedalusOrrery::Herb(const FString& Name)
{
	for (const FHerb& H : Herbs())
		if (Name == H.Name) return &H;
	return nullptr;
}

const TArray<FString>& UDaedalusOrrery::Constellations()
{
	static const TArray<FString> C = {TEXT("Keeper"), TEXT("Lantern"), TEXT("Ark"), TEXT("Shard"), TEXT("Wanderer"),
		TEXT("Hearth"), TEXT("Spindle"), TEXT("Crown"), TEXT("Tide"), TEXT("Forge"), TEXT("Kite"), TEXT("Loom")};
	return C;
}

UDaedalusOrrery* UDaedalusOrrery::Get(const UObject* WorldContext)
{
	const UWorld* W = WorldContext ? WorldContext->GetWorld() : nullptr;
	return W ? W->GetSubsystem<UDaedalusOrrery>() : nullptr;
}

float UDaedalusOrrery::Hour() const
{
	if (const ADaedalusSkyDirector* Sky = ADaedalusSkyDirector::Find(this)) return Sky->GetHour();
	const UWorld* W = GetWorld();
	const double T = W ? W->GetTimeSeconds() : 0.0;
	return static_cast<float>(FMath::Fmod(StartHour + T / FMath::Max(SecondsPerHour, 1.f), 24.0));
}

FString UDaedalusOrrery::BrewOf(const FString& A, const FString& B)
{
	const FHerb* X = Herb(A);
	const FHerb* Y = Herb(B);
	if (!X || !Y || A == B) return FString();
	if (FCString::Strcmp(X->Constellation, Y->Constellation) == 0) return FString(X->Constellation) + TEXT(" Brew");
	if (IsDay(X->Hour) != IsDay(Y->Hour))
	{
		static const TCHAR* Eclipses[] = {TEXT("Umbra"), TEXT("Penumbra"), TEXT("Corona"), TEXT("Diamondring"),
			TEXT("Baileybeads"), TEXT("Totality"), TEXT("Annular"), TEXT("Hybrid")};
		return FString(TEXT("Eclipse Brew: ")) + Eclipses[(X->Hour + Y->Hour) % 8];
	}
	return FString();
}

FString UDaedalusOrrery::Steep(ADaedalusHero* Hero)
{
	if (!bCleanWater)
	{
		Say(TEXT("The kettle water is gritty. The aqueduct filter must be fixed first."));
		return FString();
	}
	if (Satchel.Num() == 0)
	{
		Say(TEXT("Your satchel is empty. Starblooms can only be picked in their own hour."));
		return FString();
	}
	FString Made;
	if (Satchel.Num() >= 2)
	{
		Made = BrewOf(Satchel.Last(), Satchel[Satchel.Num() - 2]);
		if (!Made.IsEmpty()) Satchel.SetNum(Satchel.Num() - 2);
	}
	if (Made.IsEmpty())
	{
		Made = Satchel.Last() + TEXT(" Tea");
		Satchel.Pop();
	}
	Brews.Add(Made);
	// What it does: brews restore and shield; eclipse brews overcharge.
	if (Hero)
	{
		if (Made.StartsWith(TEXT("Eclipse")))
		{
			Hero->GiveOvershield(100.f);
			Hero->Health = Hero->MaxHealth;
		}
		else if (Made.EndsWith(TEXT("Brew")))
		{
			Hero->Health = Hero->MaxHealth;
			Hero->Shield = Hero->MaxShield;
		}
		else
		{
			Hero->Health = FMath::Min(Hero->MaxHealth, Hero->Health + 25.f);
		}
	}
	if (Made.StartsWith(TEXT("Eclipse")))
	{
		Say(FString::Printf(TEXT("%s! The kettle goes dark, then blazes. You feel unbreakable."), *Made));
		Advance(8);
	}
	else if (Made.EndsWith(TEXT("Brew")))
	{
		Say(FString::Printf(TEXT("%s. Two blooms of one constellation, steeped as one. You feel whole."), *Made));
		Advance(5);   // a brew also counts as the first tea
		Advance(6);
	}
	else
	{
		Say(FString::Printf(TEXT("%s. Warm and faintly glowing."), *Made));
		Advance(5);
	}
	return Made;
}

void UDaedalusOrrery::Say(const FString& Line)
{
	Message = Line;
	MessageAt = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
	UE_LOG(LogTemp, Log, TEXT("Orrery: %s"), *Line);
}

void UDaedalusOrrery::Advance(int32 ToStep)
{
	// Steps only move forward, and only from the step right before (so the logbook reads in order). Step 7 needs
	// all twelve charts home.
	if (ToStep != Step + 1) return;
	if (ToStep == 7 && Charts.Num() < Constellations().Num()) return;
	Step = ToStep;
	if (Step == 6 && Charts.Num() >= Constellations().Num()) Step = 7;
}

FString UDaedalusOrrery::MessageLine() const
{
	const double Now = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0;
	return Now - MessageAt < 7.0 ? Message : FString();
}

FString UDaedalusOrrery::QuestLine() const
{
	static const TCHAR* Steps[] = {
		TEXT("Meet the Keeper at the ark dock"),
		TEXT("Fix the clogged sand filter on the aqueduct"),
		TEXT("Find the Lantern star chart in the herb rings"),
		TEXT("Harvest a starbloom in its own hour"),
		TEXT("Steep your first tea at a kettle"),
		TEXT("Steep a constellation brew (two blooms of one constellation)"),
		TEXT("Recover all twelve star charts around the rim"),
		TEXT("Steep an eclipse brew (a day bloom and a night bloom)"),
		TEXT("Point the great telescope at the new moon"),
	};
	const int32 S = FMath::Clamp(Step, 0, 8);
	const int32 H = FMath::FloorToInt(Hour());
	const int32 M = FMath::FloorToInt(FMath::Frac(Hour()) * 60.f);
	FString Extra = S == 6 ? FString::Printf(TEXT(" (%d/12)"), Charts.Num()) : FString();
	return FString::Printf(TEXT("%02d:%02d   LOGBOOK: %s%s"), H, M, Steps[S], *Extra);
}

FString UDaedalusOrrery::SatchelLine() const
{
	if (Satchel.Num() == 0) return FString();
	return TEXT("SATCHEL: ") + FString::Join(Satchel, TEXT(", "));
}

FString UDaedalusOrrery::State() const
{
	return FString::Printf(TEXT("step=%d hour=%.2f clean=%d harvests=%d satchel=%s brews=%s charts=%d"), Step, Hour(),
		bCleanWater ? 1 : 0, Harvests, *FString::Join(Satchel, TEXT("|")), *FString::Join(Brews, TEXT("|")), Charts.Num());
}

// ------------------------------------------------------------------------------------------------ usable

ADaedalusUsable::ADaedalusUsable()
{
	PrimaryActorTick.bCanEverTick = false;
	Body = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Body"));
	RootComponent = Body;
	Body->SetMobility(EComponentMobility::Movable);
	Body->SetCollisionProfileName(TEXT("BlockAllDynamic"));
	Glow = CreateDefaultSubobject<UPointLightComponent>(TEXT("Glow"));
	Glow->SetupAttachment(Body);
	Glow->SetIntensity(0.f);
	Glow->SetAttenuationRadius(500.f);
	Glow->SetCastShadows(false);
	Tags.Add(TEXT("DaedalusUsable"));
}

bool ADaedalusUsable::SetArt(const FString& Kind, const FString& Asset, float Scale)
{
	const FString Path = FString::Printf(TEXT("/Game/Daedalus/Art/%s/%s/%s/StaticMeshes/%s.%s"), *Kind, *Asset, *Asset, *Asset, *Asset);
	if (UStaticMesh* M = LoadObject<UStaticMesh>(nullptr, *Path))
	{
		Body->SetStaticMesh(M);
		Body->SetRelativeScale3D(FVector(Scale));
		return true;
	}
	return false;
}

ADaedalusUsable* ADaedalusUsable::Nearest(const ADaedalusHero* Hero, float Reach)
{
	if (!Hero || !Hero->GetWorld()) return nullptr;
	ADaedalusUsable* Best = nullptr;
	float BestD = Reach * Reach;
	for (TActorIterator<ADaedalusUsable> It(Hero->GetWorld()); It; ++It)
	{
		const float D = FVector::DistSquared(It->GetActorLocation(), Hero->GetActorLocation());
		if (D < BestD)
		{
			BestD = D;
			Best = *It;
		}
	}
	return Best;
}

// ------------------------------------------------------------------------------------------------ starbloom

ADaedalusStarbloom::ADaedalusStarbloom()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickInterval = 0.5f;
	Body->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
}

void ADaedalusStarbloom::BeginPlay()
{
	Super::BeginPlay();
	SetArt(TEXT("Prop"), FString::Printf(TEXT("Prop_Orr_Herb_%s_Bud"), *Species), 4.f);
}

bool ADaedalusStarbloom::IsBlooming() const
{
	const UDaedalusOrrery* O = UDaedalusOrrery::Get(this);
	const UDaedalusOrrery::FHerb* H = UDaedalusOrrery::Herb(Species);
	if (!O || !H) return false;
	return !bPicked && FMath::FloorToInt(O->Hour()) == H->Hour;
}

void ADaedalusStarbloom::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const UDaedalusOrrery* O = UDaedalusOrrery::Get(this);
	const UDaedalusOrrery::FHerb* Hb = UDaedalusOrrery::Herb(Species);
	if (bPicked && O && Hb && FMath::FloorToInt(O->Hour()) != Hb->Hour) bPicked = false;   // its hour passed: regrown
	const bool bBloom = IsBlooming();
	if (bBloom != bShownBloom)
	{
		bShownBloom = bBloom;
		SetArt(TEXT("Prop"), FString::Printf(TEXT("Prop_Orr_Herb_%s_%s"), *Species, bBloom ? TEXT("Bloom") : TEXT("Bud")), 4.f);
		Glow->SetIntensity(bBloom ? 4000.f : 0.f);
	}
	if (bBloom) Glow->SetIntensity(3000.f + 1500.f * FMath::Sin(GetWorld()->GetTimeSeconds() * 3.f));
}

FString ADaedalusStarbloom::Prompt(const ADaedalusHero* Hero) const
{
	const UDaedalusOrrery::FHerb* H = UDaedalusOrrery::Herb(Species);
	if (IsBlooming()) return FString::Printf(TEXT("Harvest %s (%s)"), *Species, H ? H->Constellation : TEXT(""));
	return FString::Printf(TEXT("%s: blooms at %02d:00"), *Species, H ? H->Hour : 0);
}

bool ADaedalusStarbloom::Use(ADaedalusHero* Hero)
{
	UDaedalusOrrery* O = UDaedalusOrrery::Get(this);
	const UDaedalusOrrery::FHerb* H = UDaedalusOrrery::Herb(Species);
	if (!O || !H) return false;
	if (!IsBlooming())
	{
		O->Say(FString::Printf(TEXT("The %s is closed tight. It opens at %02d:00, when its stars rise."), *Species, H->Hour));
		return false;
	}
	O->Satchel.Add(Species);
	++O->Harvests;
	bPicked = true;
	O->Say(FString::Printf(TEXT("You pick the %s while it shines. (%s, a %s bloom)"), *Species, H->Constellation,
		UDaedalusOrrery::IsDay(H->Hour) ? TEXT("day") : TEXT("night")));
	O->Advance(4);
	return true;
}

// ------------------------------------------------------------------------------------------------ kettle

ADaedalusKettle::ADaedalusKettle() {}

void ADaedalusKettle::BeginPlay()
{
	Super::BeginPlay();
	SetArt(TEXT("Prop"), TEXT("Prop_Orr_Interior_Steeping_Kettle"), 2.f);
	Glow->SetIntensity(1500.f);
	Glow->SetLightColor(FLinearColor(1.f, 0.7f, 0.35f));
}

FString ADaedalusKettle::Prompt(const ADaedalusHero* Hero) const
{
	const UDaedalusOrrery* O = UDaedalusOrrery::Get(this);
	if (!O) return TEXT("Steep");
	if (O->Satchel.Num() >= 2)
	{
		const FString B = UDaedalusOrrery::BrewOf(O->Satchel.Last(), O->Satchel[O->Satchel.Num() - 2]);
		if (!B.IsEmpty()) return TEXT("Steep: ") + B;
	}
	return O->Satchel.Num() ? TEXT("Steep: ") + O->Satchel.Last() + TEXT(" Tea") : FString(TEXT("Steeping kettle (satchel empty)"));
}

bool ADaedalusKettle::Use(ADaedalusHero* Hero)
{
	UDaedalusOrrery* O = UDaedalusOrrery::Get(this);
	return O && !O->Steep(Hero).IsEmpty();
}

// ------------------------------------------------------------------------------------------------ filter

ADaedalusWaterFilter::ADaedalusWaterFilter() {}

void ADaedalusWaterFilter::BeginPlay()
{
	Super::BeginPlay();
	SetArt(TEXT("Prop"), TEXT("Prop_Orr_Sand_Filter"), 1.f);
}

FString ADaedalusWaterFilter::Prompt(const ADaedalusHero* Hero) const
{
	const UDaedalusOrrery* O = UDaedalusOrrery::Get(this);
	return O && O->bCleanWater ? FString(TEXT("Sand filter (running clear)")) : FString(TEXT("Reseat the clogged sand filter"));
}

bool ADaedalusWaterFilter::Use(ADaedalusHero* Hero)
{
	UDaedalusOrrery* O = UDaedalusOrrery::Get(this);
	if (!O) return false;
	if (O->bCleanWater)
	{
		O->Say(TEXT("Clear water hums through the sand. The troughs and the kettles are full."));
		return false;
	}
	O->bCleanWater = true;
	Glow->SetLightColor(FLinearColor(0.3f, 0.6f, 1.f));
	Glow->SetIntensity(2500.f);
	O->Say(TEXT("You dig out the storm grit and reseat the sand. The aqueduct runs clear again: the water is drinkable."));
	O->Advance(2);
	return true;
}

// ------------------------------------------------------------------------------------------------ star chart

ADaedalusStarChart::ADaedalusStarChart()
{
	PrimaryActorTick.bCanEverTick = true;
	Body->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
}

void ADaedalusStarChart::BeginPlay()
{
	Super::BeginPlay();
	SetArt(TEXT("Item"), FString::Printf(TEXT("Item_Orr_Constellation_Chart_%s"), *Constellation), 2.5f);
	Glow->SetLightColor(FLinearColor(1.f, 0.9f, 0.5f));
	Glow->SetIntensity(2500.f);
}

void ADaedalusStarChart::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	AddActorLocalRotation(FRotator(0.f, 40.f * DeltaSeconds, 0.f));   // turns slowly in the wind, catching the light
}

FString ADaedalusStarChart::Prompt(const ADaedalusHero* Hero) const
{
	return FString::Printf(TEXT("Pick up the %s chart"), *Constellation);
}

bool ADaedalusStarChart::Use(ADaedalusHero* Hero)
{
	UDaedalusOrrery* O = UDaedalusOrrery::Get(this);
	if (!O) return false;
	O->Charts.AddUnique(Constellation);
	FString Pair;
	for (const UDaedalusOrrery::FHerb& H : UDaedalusOrrery::Herbs())
		if (Constellation == H.Constellation) Pair += (Pair.IsEmpty() ? FString() : FString(TEXT(" + "))) + H.Name;
	O->Say(FString::Printf(TEXT("The %s chart. Its stars are drawn over two herbs: %s. (%d/12)"), *Constellation, *Pair, O->Charts.Num()));
	if (Constellation == TEXT("Lantern")) O->Advance(3);
	if (O->Step == 6) O->Advance(7);   // Advance moves to 7 only once all twelve are home
	Destroy();
	return true;
}

// ------------------------------------------------------------------------------------------------ keeper

ADaedalusKeeper::ADaedalusKeeper()
{
	Name = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Name"));
	Name->SetupAttachment(Body);
	Name->SetText(FText::FromString(TEXT("Keeper Ostra")));
	Name->SetHorizontalAlignment(EHTA_Center);
	Name->SetWorldSize(28.f);
	Name->SetTextRenderColor(FColor(255, 220, 140));
	Name->SetRelativeLocation(FVector(0.f, 0.f, 230.f));
	Name->SetRelativeRotation(FRotator(0.f, 90.f, 0.f));
}

void ADaedalusKeeper::BeginPlay()
{
	Super::BeginPlay();
	if (!SetArt(TEXT("Mob"), TEXT("Mob_Orr_Keeper_Ostra"), 1.15f)) SetArt(TEXT("Mob"), TEXT("Mob_Realm_Party_Sage_Body"), 1.f);
	Glow->SetIntensity(800.f);
}

FString ADaedalusKeeper::Prompt(const ADaedalusHero* Hero) const
{
	return TEXT("Talk to Keeper Ostra");
}

bool ADaedalusKeeper::Use(ADaedalusHero* Hero)
{
	UDaedalusOrrery* O = UDaedalusOrrery::Get(this);
	if (!O) return false;
	static const TCHAR* Lines[] = {
		TEXT("Keeper Ostra: \"An ark! Welcome to the Orrery. The Long Storm clogged our aqueduct filter, west of the summit. Clean water first; then we talk herbs.\""),
		TEXT("Keeper Ostra: \"The filter sits where the aqueduct comes down the west spoke. Dig out the grit.\""),
		TEXT("Keeper Ostra: \"Water runs clear, bless you. The storm scattered my star charts. The Lantern chart blew into the herb rings; start there.\""),
		TEXT("Keeper Ostra: \"Each starbloom opens only in its own hour. Watch the sky clock, and stand by the plant when its stars rise.\""),
		TEXT("Keeper Ostra: \"A fresh bloom! Take it to the kettle in the steeping house and steep it.\""),
		TEXT("Keeper Ostra: \"Two blooms of one constellation make a brew. The charts show which two belong together.\""),
		TEXT("Keeper Ostra: \"The rest of my charts are out on the rim. Each one marks two herbs. Bring them all home.\""),
		TEXT("Keeper Ostra: \"All twelve! Now the old secret: steep a day bloom with a night bloom of another sky. An eclipse in a cup.\""),
		TEXT("Keeper Ostra: \"You steeped an eclipse. The dome's vault will open for you, and the great telescope is waiting. There is a new moon out there, traveller.\""),
	};
	const int32 S = FMath::Clamp(O->Step, 0, 8);
	O->Say(Lines[S]);
	++Talks;
	O->Advance(1);
	return true;
}

// ------------------------------------------------------------------------------------------------ islanders

ADaedalusIslander::ADaedalusIslander()
{
	PrimaryActorTick.bCanEverTick = true;
	Body->SetCollisionProfileName(TEXT("Pawn"));
	Label = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Label"));
	Label->SetupAttachment(Body);
	Label->SetHorizontalAlignment(EHTA_Center);
	Label->SetWorldSize(22.f);
	Label->SetTextRenderColor(FColor(235, 225, 200));
	Label->SetRelativeLocation(FVector(0.f, 0.f, 215.f));
}

void ADaedalusIslander::BeginPlay()
{
	Super::BeginPlay();
	SetArt(TEXT("Mob"), TEXT("Mob_Orr_") + Who, 1.f);
	FString Shown = Who;
	Shown.ReplaceInline(TEXT("_"), TEXT(" "));
	Label->SetText(FText::FromString(Shown));
	if (Home.IsZero()) Home = GetActorLocation();
	if (Work.IsZero()) Work = Home;
	if (Plaza.IsZero()) Plaza = Home;
}

FVector ADaedalusIslander::Target() const
{
	const UDaedalusOrrery* O = UDaedalusOrrery::Get(this);
	const float H = O ? O->Hour() : 12.f;
	if (H >= 22.f || H < 6.f) return Home;
	if (H >= 18.f) return Plaza;
	return Work;
}

void ADaedalusIslander::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const float Dt = FMath::Min(DeltaSeconds, 0.1f);
	Talking = FMath::Max(0.f, Talking - Dt);
	const UDaedalusOrrery* O = UDaedalusOrrery::Get(this);
	const float H = O ? O->Hour() : 12.f;
	Doing = (H >= 22.f || H < 6.f) ? TEXT("home") : H >= 18.f ? TEXT("plaza") : TEXT("work");
	// Face the hero while talking; otherwise walk to the hour's spot, following the ground.
	if (Talking > 0.f)
	{
		if (const APawn* P = UGameplayStatics::GetPlayerPawn(this, 0))
		{
			const FVector To = P->GetActorLocation() - GetActorLocation();
			SetActorRotation(FRotator(0.f, To.Rotation().Yaw - 90.f, 0.f));
		}
		return;
	}
	const FVector Goal = Target();
	FVector To = Goal - GetActorLocation();
	To.Z = 0.f;
	if (To.Size() < 60.f) return;
	const FVector Step = To.GetSafeNormal() * 130.f * Dt;
	FVector Next = GetActorLocation() + Step;
	FHitResult Hit;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(DaedalusIslander), false, this);
	if (GetWorld()->LineTraceSingleByChannel(Hit, Next + FVector(0, 0, 300.f), Next - FVector(0, 0, 600.f), ECC_WorldStatic, Q))
		Next.Z = FMath::FInterpTo(GetActorLocation().Z, Hit.ImpactPoint.Z, Dt, 10.f);
	SetActorLocationAndRotation(Next, FRotator(0.f, To.Rotation().Yaw - 90.f, FMath::Sin(GetWorld()->GetTimeSeconds() * 9.f) * 2.f));
}

FString ADaedalusIslander::Prompt(const ADaedalusHero* Hero) const
{
	FString Shown = Who;
	Shown.ReplaceInline(TEXT("_"), TEXT(" "));
	return TEXT("Talk to ") + Shown;
}

bool ADaedalusIslander::Use(ADaedalusHero* Hero)
{
	UDaedalusOrrery* O = UDaedalusOrrery::Get(this);
	if (!O) return false;
	TArray<FString> Parts;
	Lines.ParseIntoArray(Parts, TEXT("|"));
	const float H = O->Hour();
	const int32 Slot = (H >= 22.f || H < 6.f) ? 3 : H >= 18.f ? 2 : H >= 11.f ? 1 : 0;
	FString Shown = Who;
	Shown.ReplaceInline(TEXT("_"), TEXT(" "));
	const FString Line = Parts.IsValidIndex(Slot) ? Parts[Slot] : (Parts.Num() ? Parts[0] : FString(TEXT("Fair skies.")));
	O->Say(FString::Printf(TEXT("%s: \"%s\""), *Shown, *Line));
	Talking = 4.f;
	return true;
}
