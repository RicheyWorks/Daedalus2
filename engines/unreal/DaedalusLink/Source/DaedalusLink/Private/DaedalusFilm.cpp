// SPDX-License-Identifier: MIT

#include "DaedalusFilm.h"

#include "Components/SceneCaptureComponent2D.h"
#include "Engine/SceneCapture2D.h"
#include "Engine/World.h"

ASceneCapture2D* UDaedalusFilm::SpawnFilmCamera(const UObject* WorldContext)
{
	UWorld* W = WorldContext ? WorldContext->GetWorld() : nullptr;
	if (!W) return nullptr;
	FActorSpawnParameters P;
	P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	P.ObjectFlags |= RF_Transient;
	ASceneCapture2D* Cam = W->SpawnActor<ASceneCapture2D>(FVector::ZeroVector, FRotator::ZeroRotator, P);
	if (Cam)
	{
		USceneCaptureComponent2D* C = Cam->GetCaptureComponent2D();
		C->bCaptureEveryFrame = false;
		C->bCaptureOnMovement = false;
		C->CaptureSource = ESceneCaptureSource::SCS_FinalColorLDR;
	}
	return Cam;
}
