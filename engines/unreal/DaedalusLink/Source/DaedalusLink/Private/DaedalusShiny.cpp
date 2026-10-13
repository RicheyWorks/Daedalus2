// SPDX-License-Identifier: MIT

#include "DaedalusShiny.h"

#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	UStaticMesh* SparkMesh()
	{
		static UStaticMesh* M = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere"));
		return M;
	}

	/** The unlit emissive glow import_world_package.py makes (parameters Color, Intensity); the engine's lit basic
	 * material when a project hasn't imported yet, so a shiny still shows its sparks. */
	UMaterialInterface* SparkMaterial()
	{
		static UMaterialInterface* M = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Daedalus/Art/Materials/M_DaedalusGlow.M_DaedalusGlow"));
		static UMaterialInterface* Fallback = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
		return M ? M : Fallback;
	}
}

namespace DaedalusShiny
{
	FLinearColor Hue(float T)
	{
		return FLinearColor::MakeFromHSV8(static_cast<uint8>(FMath::Frac(T) * 255.f), 200, 255);
	}

	void Attach(AActor* Owner, USceneComponent* Under, float Size, FState& State)
	{
		if (!Owner || !Under) return;
		Detach(State);
		State.Size = FMath::Max(Size, 40.f);
		State.Time = 0.f;

		UPointLightComponent* L = NewObject<UPointLightComponent>(Owner, TEXT("ShinyGlow"));
		L->SetMobility(EComponentMobility::Movable);   // a runtime component is Static by default, and Static never moves
		L->SetupAttachment(Under);
		L->SetRelativeLocation(FVector(0.f, 0.f, State.Size * 0.6f));
		L->SetIntensityUnits(ELightUnits::Candelas);
		L->SetIntensity(40.f);                       // the lighting fix of 2026-10-13: nothing over 100 cd
		L->SetAttenuationRadius(State.Size * 3.f);
		L->SetSourceRadius(State.Size * 0.25f);
		L->SetCastShadows(false);
		L->SetLightColor(Hue(0.f));
		L->RegisterComponent();
		State.Light = L;

		UMaterialInterface* Base = SparkMaterial();
		for (int32 i = 0; i < Sparks; ++i)
		{
			UStaticMeshComponent* S = NewObject<UStaticMeshComponent>(Owner, *FString::Printf(TEXT("ShinySpark%d"), i));
			S->SetMobility(EComponentMobility::Movable);
			S->SetupAttachment(Under);
			S->SetStaticMesh(SparkMesh());
			S->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			S->SetCastShadow(false);
			const float Px = FMath::Clamp(State.Size * 0.06f, 4.f, 16.f);   // sphere mesh is 100 cm
			S->SetRelativeScale3D(FVector(Px / 100.f));
			if (Base)
			{
				UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(Base, Owner);
				M->SetVectorParameterValue(TEXT("Color"), Hue(static_cast<float>(i) / Sparks));
				M->SetScalarParameterValue(TEXT("Intensity"), 10.f);
				S->SetMaterial(0, M);
			}
			S->RegisterComponent();
			State.Sparks.Add(S);
		}
		Tick(State, 0.f);
	}

	void Tick(FState& State, float Dt)
	{
		State.Time += Dt;
		const float T = State.Time;
		const float Cycle = T / 4.f;
		if (UPointLightComponent* L = State.Light.Get())
		{
			L->SetLightColor(Hue(Cycle));
			L->SetIntensity(30.f + 15.f * FMath::Sin(T * 2.4f));
		}
		const float R = State.Size * 0.7f;
		for (int32 i = 0; i < State.Sparks.Num(); ++i)
		{
			UStaticMeshComponent* S = State.Sparks[i].Get();
			if (!S) continue;
			const float Phase = 2.f * PI * i / FMath::Max(1, State.Sparks.Num());
			const float A = T * 1.3f + Phase;
			const float Bob = FMath::Sin(T * 2.1f + Phase * 1.7f);
			S->SetRelativeLocation(FVector(FMath::Cos(A) * R, FMath::Sin(A) * R, State.Size * (0.55f + 0.3f * Bob)));
			if (UMaterialInstanceDynamic* M = Cast<UMaterialInstanceDynamic>(S->GetMaterial(0)))
			{
				M->SetVectorParameterValue(TEXT("Color"), Hue(Cycle + static_cast<float>(i) / State.Sparks.Num()));
				M->SetScalarParameterValue(TEXT("Intensity"), 8.f + 6.f * Bob);
			}
		}
	}

	void Detach(FState& State)
	{
		for (const TWeakObjectPtr<UStaticMeshComponent>& S : State.Sparks)
			if (UStaticMeshComponent* C = S.Get()) C->DestroyComponent();
		State.Sparks.Reset();
		if (UPointLightComponent* L = State.Light.Get()) L->DestroyComponent();
		State.Light = nullptr;
	}
}
