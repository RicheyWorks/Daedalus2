// SPDX-License-Identifier: MIT

#include "DaedalusRealmPortal.h"
#include "DaedalusHero.h"
#include "DaedalusLinkModule.h"
#include "Components/BoxComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/World.h"

ADaedalusRealmPortal::ADaedalusRealmPortal()
{
	PrimaryActorTick.bCanEverTick = false;
	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	SetRootComponent(Box);
	Box->SetBoxExtent(FVector(300.f, 300.f, 250.f));
	Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Box->SetCollisionResponseToAllChannels(ECR_Ignore);
	Box->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
	Box->SetGenerateOverlapEvents(true);
	Sign = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Sign"));
	Sign->SetupAttachment(Box);
	Sign->SetRelativeLocation(FVector(0.f, 0.f, 320.f));
	Sign->SetWorldSize(90.f);
	Sign->SetHorizontalAlignment(EHTA_Center);
	Sign->SetTextRenderColor(FColor(255, 240, 120));
}

void ADaedalusRealmPortal::BeginPlay()
{
	Super::BeginPlay();
	Box->OnComponentBeginOverlap.AddDynamic(this, &ADaedalusRealmPortal::OnOverlap);
	if (Sign) Sign->SetText(FText::FromString(FString::Printf(TEXT("%s %s"), *Via.ToUpper(), *Target)));
	// A hero standing in the box at play start (he just landed here) is not a crossing.
	ReadyAt = GetWorld() ? GetWorld()->GetTimeSeconds() + CooldownSeconds : 0.0;
}

void ADaedalusRealmPortal::OnOverlap(UPrimitiveComponent*, AActor* Other, UPrimitiveComponent*, int32, bool, const FHitResult&)
{
	if (ADaedalusHero* H = Cast<ADaedalusHero>(Other)) Cross(H);
}

FString ADaedalusRealmPortal::Cross(ADaedalusHero* Hero)
{
	UWorld* W = GetWorld();
	if (!Hero || !W) return TEXT("refused: no hero");
	const double Now = W->GetTimeSeconds();
	// A hero who just arrived (any portal, this one included) is not crossing: the landing marker's portal
	// overlaps him the moment he lands.
	if (Now < ReadyAt || Now - Hero->LastRealmSwitchAt < CooldownSeconds) { LastResult = TEXT("cooldown"); return LastResult; }
	ReadyAt = Now + CooldownSeconds;
	LastResult = Hero->SwitchRealm(Target, Via, Detail);
	if (LastResult.StartsWith(TEXT("ok"))) ++Crossings;
	UE_LOG(LogDaedalus, Log, TEXT("Portal %s: %s"), *GetActorNameOrLabel(), *LastResult);
	return LastResult;
}

FString ADaedalusRealmPortal::PortalState() const
{
	return FString::Printf(TEXT("portal=%s via=%s detail=%s crossings=%d last=%s"), *Target, *Via, Detail.IsEmpty() ? TEXT("-") : *Detail, Crossings, LastResult.IsEmpty() ? TEXT("-") : *LastResult);
}
