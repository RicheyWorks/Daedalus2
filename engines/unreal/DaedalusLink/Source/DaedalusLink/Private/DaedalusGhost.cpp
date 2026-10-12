// SPDX-License-Identifier: MIT

#include "DaedalusGhost.h"

#include "Camera/CameraComponent.h"
#include "Components/BoxComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DaedalusHero.h"
#include "DaedalusTarget.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "HAL/IConsoleManager.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	float CVarF(const TCHAR* Name, float Fallback)
	{
		const IConsoleVariable* C = IConsoleManager::Get().FindConsoleVariable(Name);
		return C ? C->GetFloat() : Fallback;
	}

	UMaterialInterface* GhostMaterial()
	{
		static UMaterialInterface* M = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
		return M;
	}
}

ADaedalusGhost::ADaedalusGhost()
{
	PrimaryActorTick.bCanEverTick = true;
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeFinder(TEXT("/Engine/BasicShapes/Cube.Cube"));
	Cube = CubeFinder.Object;

	Hull = CreateDefaultSubobject<UBoxComponent>(TEXT("Hull"));
	RootComponent = Hull;
	Hull->InitBoxExtent(FVector(130.f, 70.f, 40.f));
	Hull->SetCollisionProfileName(TEXT("Pawn"));

	// A blocky Ghost: a long low body, two side pods with the guns, a seat, glowing intakes.
	Frame = CreateDefaultSubobject<USceneComponent>(TEXT("Frame"));
	Frame->SetupAttachment(Hull);
	const FLinearColor Purple(0.36f, 0.22f, 0.62f), Dark(0.12f, 0.1f, 0.18f), Glow(0.45f, 0.85f, 1.f);
	Part(TEXT("Body"), FVector(2.4f, 0.9f, 0.45f), FVector(0.f, 0.f, 0.f), Purple);
	Part(TEXT("Nose"), FVector(0.8f, 0.6f, 0.3f), FVector(150.f, 0.f, -5.f), Purple);
	Part(TEXT("PodL"), FVector(1.8f, 0.4f, 0.4f), FVector(10.f, -75.f, -10.f), Dark);
	Part(TEXT("PodR"), FVector(1.8f, 0.4f, 0.4f), FVector(10.f, 75.f, -10.f), Dark);
	Part(TEXT("Seat"), FVector(0.6f, 0.5f, 0.25f), FVector(-60.f, 0.f, 30.f), Dark);
	Part(TEXT("IntakeL"), FVector(0.15f, 0.3f, 0.2f), FVector(-115.f, -75.f, -10.f), Glow);
	Part(TEXT("IntakeR"), FVector(0.15f, 0.3f, 0.2f), FVector(-115.f, 75.f, -10.f), Glow);
	GunL = Part(TEXT("GunL"), FVector(0.5f, 0.1f, 0.1f), FVector(115.f, -75.f, -10.f), Glow);
	GunR = Part(TEXT("GunR"), FVector(0.5f, 0.1f, 0.1f), FVector(115.f, 75.f, -10.f), Glow);

	Boom = CreateDefaultSubobject<USpringArmComponent>(TEXT("Boom"));
	Boom->SetupAttachment(Hull);
	Boom->TargetArmLength = 720.f;
	Boom->SocketOffset = FVector(0.f, 0.f, 220.f);
	Boom->bUsePawnControlRotation = true;
	Boom->bEnableCameraLag = true;
	Boom->CameraLagSpeed = 8.f;
	Boom->bDoCollisionTest = true;
	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(Boom, USpringArmComponent::SocketName);
	Camera->SetFieldOfView(85.f);

	AutoPossessPlayer = EAutoReceiveInput::Disabled;
}

UStaticMeshComponent* ADaedalusGhost::Part(const FName Name, const FVector& Size, const FVector& At, const FLinearColor& Color)
{
	UStaticMeshComponent* C = CreateDefaultSubobject<UStaticMeshComponent>(Name);
	C->SetupAttachment(Frame);
	C->SetStaticMesh(Cube);
	C->SetRelativeLocation(At);
	C->SetRelativeScale3D(Size);
	C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	C->ComponentTags.Add(*FString::Printf(TEXT("color:%s"), *Color.ToFColor(true).ToHex()));
	return C;
}

void ADaedalusGhost::BeginPlay()
{
	Super::BeginPlay();
	LastGround = GetActorLocation();
	TArray<UStaticMeshComponent*> Parts;
	GetComponents<UStaticMeshComponent>(Parts);
	for (UStaticMeshComponent* C : Parts)
	{
		for (const FName& Tag : C->ComponentTags)
		{
			FString S = Tag.ToString();
			if (S.RemoveFromStart(TEXT("color:")) && GhostMaterial())
			{
				UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(GhostMaterial(), this);
				M->SetVectorParameterValue(TEXT("Color"), FLinearColor(FColor::FromHex(S)));
				C->SetMaterial(0, M);
			}
		}
	}

	auto Make = [this](const TCHAR* Name, EInputActionValueType Type)
	{
		UInputAction* A = NewObject<UInputAction>(this, Name);
		A->ValueType = Type;
		return A;
	};
	MoveAction = Make(TEXT("IA_GhostMove"), EInputActionValueType::Axis2D);
	LookAction = Make(TEXT("IA_GhostLook"), EInputActionValueType::Axis2D);
	LookMouseAction = Make(TEXT("IA_GhostLookMouse"), EInputActionValueType::Axis2D);
	FireAction = Make(TEXT("IA_GhostFire"), EInputActionValueType::Boolean);
	BoostAction = Make(TEXT("IA_GhostBoost"), EInputActionValueType::Boolean);
	ExitAction = Make(TEXT("IA_GhostExit"), EInputActionValueType::Boolean);
	Mapping = NewObject<UInputMappingContext>(this, TEXT("IMC_Ghost"));
	auto Map = [this](UInputAction* A, const FKey& K, bool bY, bool bNeg, bool bDz)
	{
		FEnhancedActionKeyMapping& M = Mapping->MapKey(A, K);
		if (bDz)
		{
			UInputModifierDeadZone* Dz = NewObject<UInputModifierDeadZone>(Mapping);
			Dz->LowerThreshold = 0.15f;
			M.Modifiers.Add(Dz);
		}
		if (bY)
		{
			UInputModifierSwizzleAxis* Sw = NewObject<UInputModifierSwizzleAxis>(Mapping);
			Sw->Order = EInputAxisSwizzle::YXZ;
			M.Modifiers.Add(Sw);
		}
		if (bNeg) M.Modifiers.Add(NewObject<UInputModifierNegate>(Mapping));
	};
	Map(MoveAction, EKeys::W, true, false, false);
	Map(MoveAction, EKeys::S, true, true, false);
	Map(MoveAction, EKeys::D, false, false, false);
	Map(MoveAction, EKeys::A, false, true, false);
	Map(MoveAction, EKeys::Gamepad_Left2D, false, false, true);
	Map(LookAction, EKeys::Gamepad_Right2D, false, false, true);
	Map(LookMouseAction, EKeys::Mouse2D, false, false, false);
	Map(FireAction, EKeys::LeftMouseButton, false, false, false);
	Map(FireAction, EKeys::Gamepad_RightTriggerAxis, false, false, false);
	Map(BoostAction, EKeys::LeftShift, false, false, false);
	Map(BoostAction, EKeys::Gamepad_LeftShoulder, false, false, false);
	Map(BoostAction, EKeys::Gamepad_LeftTriggerAxis, false, false, false);
	Map(ExitAction, EKeys::E, false, false, false);
	Map(ExitAction, EKeys::Gamepad_FaceButton_Left, false, false, false);
}

void ADaedalusGhost::PossessedBy(AController* NewController)
{
	Super::PossessedBy(NewController);
	APlayerController* PC = Cast<APlayerController>(NewController);
	if (!PC || !Mapping) return;
	if (UEnhancedInputLocalPlayerSubsystem* Sub = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
	{
		Sub->AddMappingContext(Mapping, 1);
	}
}

// Called by PawnClientRestart when the player's controller takes the bike (after BeginPlay made the actions).
void ADaedalusGhost::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);
	if (UEnhancedInputComponent* EI = Cast<UEnhancedInputComponent>(PlayerInputComponent))
	{
		EI->ClearActionBindings();
		EI->BindAction(MoveAction, ETriggerEvent::Triggered, this, &ADaedalusGhost::Move);
		EI->BindAction(MoveAction, ETriggerEvent::Completed, this, &ADaedalusGhost::Move);
		EI->BindAction(LookAction, ETriggerEvent::Triggered, this, &ADaedalusGhost::Look);
		EI->BindAction(LookMouseAction, ETriggerEvent::Triggered, this, &ADaedalusGhost::LookMouse);
		EI->BindAction(FireAction, ETriggerEvent::Triggered, this, &ADaedalusGhost::TriggerHeld);
		EI->BindAction(BoostAction, ETriggerEvent::Started, this, &ADaedalusGhost::BoostOn);
		EI->BindAction(BoostAction, ETriggerEvent::Completed, this, &ADaedalusGhost::BoostOff);
		EI->BindAction(ExitAction, ETriggerEvent::Started, this, &ADaedalusGhost::Dismount);
	}
}

void ADaedalusGhost::UnPossessed()
{
	if (APlayerController* PC = Cast<APlayerController>(GetController()))
	{
		if (UEnhancedInputLocalPlayerSubsystem* Sub = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
		{
			Sub->RemoveMappingContext(Mapping);
		}
	}
	Stick = FVector2D::ZeroVector;
	bBoost = false;
	Super::UnPossessed();
}

bool ADaedalusGhost::Mount(ADaedalusHero* Hero)
{
	if (!Hero || Rider) return false;
	AController* C = Hero->GetController();
	if (!C) return false;
	Rider = Hero;
	Hero->SetActorHiddenInGame(true);
	Hero->SetActorEnableCollision(false);
	Hero->GetCharacterMovement()->DisableMovement();
	Hero->AttachToActor(this, FAttachmentTransformRules::SnapToTargetNotIncludingScale);
	const FRotator Look = C->GetControlRotation();
	C->Possess(this);
	C->SetControlRotation(Look);
	return true;
}

void ADaedalusGhost::Dismount()
{
	ADaedalusHero* Hero = Rider;
	AController* C = GetController();
	if (!Hero || !C) return;
	Rider = nullptr;
	Hero->DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
	const FVector Side = GetActorLocation() + GetActorRightVector() * -180.f + FVector(0.f, 0.f, 80.f);
	Hero->SetActorLocation(Side, false, nullptr, ETeleportType::TeleportPhysics);
	Hero->SetActorHiddenInGame(false);
	Hero->SetActorEnableCollision(true);
	Hero->GetCharacterMovement()->SetMovementMode(MOVE_Falling);
	const FRotator Look = C->GetControlRotation();
	C->Possess(Hero);
	C->SetControlRotation(Look);
}

void ADaedalusGhost::Move(const FInputActionValue& V)
{
	Stick = V.Get<FVector2D>();
}

void ADaedalusGhost::Look(const FInputActionValue& V)
{
	const FVector2D In = V.Get<FVector2D>();
	const float Dt = GetWorld() ? GetWorld()->GetDeltaSeconds() : 0.016f;
	const float Rate = CVarF(TEXT("daedalus.StickLookRate"), 200.f) * Dt;
	const float InvY = CVarF(TEXT("daedalus.InvertY"), 0.f) > 0.5f ? -1.f : 1.f;
	const float InvX = CVarF(TEXT("daedalus.InvertX"), 0.f) > 0.5f ? -1.f : 1.f;
	AddControllerYawInput(In.X * Rate * CVarF(TEXT("daedalus.StickSensX"), 5.f) / 5.f * InvX);
	AddControllerPitchInput(-In.Y * Rate * CVarF(TEXT("daedalus.StickSensY"), 5.f) / 5.f * InvY);
}

void ADaedalusGhost::LookMouse(const FInputActionValue& V)
{
	const FVector2D In = V.Get<FVector2D>();
	const float InvY = CVarF(TEXT("daedalus.InvertMouseY"), 0.f) > 0.5f ? -1.f : 1.f;
	AddControllerYawInput(In.X * CVarF(TEXT("daedalus.MouseSensitivity"), 0.3f));
	AddControllerPitchInput(-In.Y * CVarF(TEXT("daedalus.MouseSensitivityY"), 0.3f) * InvY);
}

void ADaedalusGhost::Drive(float Forward, float Right, bool bInBoost)
{
	Stick = FVector2D(FMath::Clamp(Right, -1.f, 1.f), FMath::Clamp(Forward, -1.f, 1.f));
	bBoost = bInBoost;
}

bool ADaedalusGhost::FireGuns()
{
	if (FireCooldown > 0.f || bOverheated || !GetWorld()) return false;
	FireCooldown = 0.085f;   // the guns alternate, about twelve bolts a second
	Heat = FMath::Min(1.f, Heat + 0.045f);
	if (Heat >= 1.f) bOverheated = true;
	bLeftGun = !bLeftGun;
	Shot((bLeftGun ? GunL : GunR)->GetComponentLocation() + GetActorForwardVector() * 30.f);
	return true;
}

void ADaedalusGhost::Shot(const FVector& Muzzle)
{
	++ShotsFired;
	// Aim where the camera looks: find the point under the screen's centre, then fire from the gun at it.
	const FVector Eye = Camera->GetComponentLocation();
	const FVector EyeEnd = Eye + Camera->GetForwardVector() * 30000.f;
	FHitResult Aim;
	FCollisionQueryParams Q(TEXT("GhostAim"), true, this);
	if (Rider) Q.AddIgnoredActor(Rider);
	const FVector Target = GetWorld()->LineTraceSingleByChannel(Aim, Eye, EyeEnd, ECC_Visibility, Q) ? FVector(Aim.ImpactPoint) : EyeEnd;
	const FVector Dir = FMath::VRandCone((Target - Muzzle).GetSafeNormal(), FMath::DegreesToRadians(0.6f));
	FHitResult Hit;
	const bool bHit = GetWorld()->LineTraceSingleByChannel(Hit, Muzzle, Muzzle + Dir * 30000.f, ECC_Visibility, Q);
	const FVector End = bHit ? FVector(Hit.ImpactPoint) : Muzzle + Dir * 30000.f;

	// A bolt from the gun to the hit, and a flash where it lands.
	auto Spark = [this](const FVector& At, const FVector& Size, const FRotator& Rot, const FLinearColor& Color, float Life)
	{
		FActorSpawnParameters P;
		P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		AStaticMeshActor* F = GetWorld()->SpawnActor<AStaticMeshActor>(At, Rot, P);
		if (!F) return;
		UStaticMeshComponent* C = F->GetStaticMeshComponent();
		C->SetMobility(EComponentMobility::Movable);
		C->SetStaticMesh(Cube);
		C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		C->SetCastShadow(false);
		F->SetActorScale3D(Size);
		if (GhostMaterial())
		{
			UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(GhostMaterial(), F);
			M->SetVectorParameterValue(TEXT("Color"), Color * 4.f);
			C->SetMaterial(0, M);
		}
		F->SetLifeSpan(Life);
	};
	const FVector Line = End - Muzzle;
	Spark(Muzzle + Line * 0.5f, FVector(Line.Size() / 100.f, 0.05f, 0.05f), Line.Rotation(), FLinearColor(0.5f, 0.85f, 1.f), 0.05f);
	if (bHit)
	{
		Spark(Hit.ImpactPoint, FVector(0.3f), FRotator::ZeroRotator, FLinearColor(0.6f, 0.9f, 1.f), 0.1f);
		if (UPrimitiveComponent* P = Hit.GetComponent())
		{
			if (P->IsSimulatingPhysics()) P->AddImpulseAtLocation(Dir * 40000.f, Hit.ImpactPoint);
		}
		if (ADaedalusTarget* Foe = Cast<ADaedalusTarget>(Hit.GetActor()))
		{
			++Hits;
			const bool bAlive = Foe->Health > 0.f;
			UGameplayStatics::ApplyDamage(Foe, 12.f, GetController(), this, nullptr);
			if (bAlive && Foe->Health <= 0.f && Rider)
			{
				++Rider->Kills;
				Rider->Exp += Foe->ExpValue;
			}
		}
	}
}

void ADaedalusGhost::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const float Dt = FMath::Min(DeltaSeconds, 0.05f);
	FireCooldown = FMath::Max(0.f, FireCooldown - Dt);
	Heat = FMath::Max(0.f, Heat - Dt * (bOverheated ? 0.5f : 0.3f));
	if (bOverheated && Heat <= 0.15f) bOverheated = false;

	// Steer to the camera's heading (Halo's Ghost), throttle and strafe with the stick.
	const FRotator Yaw(0.f, Controller ? Controller->GetControlRotation().Yaw : GetActorRotation().Yaw, 0.f);
	const FRotator Now = GetActorRotation();
	const float NewYaw = FMath::FixedTurn(Now.Yaw, Yaw.Yaw, 240.f * Dt);
	const FVector Fwd = FRotator(0.f, NewYaw, 0.f).Vector();
	const FVector Right = FRotator(0.f, NewYaw + 90.f, 0.f).Vector();
	const float Top = bBoost ? BoostSpeed : TopSpeed;
	const FVector Want = Fwd * Stick.Y * Top + Right * Stick.X * Top * 0.55f;
	const FVector Flat(Velocity.X, Velocity.Y, 0.f);
	const FVector NewFlat = FMath::VInterpTo(Flat, Want, Dt, Controller ? 2.4f : 1.2f);

	// Hover: trace down; spring to HoverHeight over ground, fall where there is none.
	FHitResult Ground;
	FCollisionQueryParams Q(TEXT("GhostHover"), false, this);
	if (Rider) Q.AddIgnoredActor(Rider);
	const FVector Here = GetActorLocation();
	bGrounded = GetWorld()->LineTraceSingleByChannel(Ground, Here, Here - FVector(0.f, 0.f, HoverHeight * 2.5f), ECC_Visibility, Q);
	float Vz = Velocity.Z;
	if (bGrounded)
	{
		const float Gap = (Here.Z - Ground.ImpactPoint.Z) - HoverHeight;
		Vz = FMath::FInterpTo(Vz, -Gap * 6.f, Dt, 8.f);
		LastGround = Here;
	}
	else
	{
		Vz -= 1800.f * Dt;   // gravity off an edge
	}
	Velocity = FVector(NewFlat.X, NewFlat.Y, FMath::Max(Vz, -4000.f));

	FHitResult Bump;
	SetActorLocation(Here + Velocity * Dt, true, &Bump);
	if (Bump.bBlockingHit)
	{
		Velocity = FVector::VectorPlaneProject(Velocity, Bump.Normal) * 0.6f;   // glance off what it hit
	}

	// Lean into turns and strafes.
	Bank = FMath::FInterpTo(Bank, Stick.X * 14.f + FMath::FindDeltaAngleDegrees(Now.Yaw, Yaw.Yaw) * 0.25f, Dt, 6.f);
	SetActorRotation(FRotator(0.f, NewYaw, 0.f));
	Frame->SetRelativeRotation(FRotator(-Stick.Y * 4.f, 0.f, FMath::Clamp(Bank, -25.f, 25.f)));

	// Far below the last ground: back onto it.
	if (!bGrounded && Here.Z < LastGround.Z - 3000.f)
	{
		SetActorLocation(LastGround + FVector(0.f, 0.f, 200.f), false, nullptr, ETeleportType::TeleportPhysics);
		Velocity = FVector::ZeroVector;
	}
}
