// SPDX-License-Identifier: MIT

#include "DaedalusHero.h"

#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	UMaterialInterface* ShapeMaterial()
	{
		static UMaterialInterface* M = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
		return M;
	}
}

ADaedalusHero::ADaedalusHero()
{
	PrimaryActorTick.bCanEverTick = true;
	static ConstructorHelpers::FObjectFinder<UStaticMesh> CubeFinder(TEXT("/Engine/BasicShapes/Cube.Cube"));
	Cube = CubeFinder.Object;
	GetCapsuleComponent()->InitCapsuleSize(34.f, 92.f);

	bUseControllerRotationYaw = false;
	UCharacterMovementComponent* M = GetCharacterMovement();
	M->bOrientRotationToMovement = true;
	M->RotationRate = FRotator(0.f, 720.f, 0.f);
	M->MaxWalkSpeed = 650.f;
	M->JumpZVelocity = 760.f;
	M->AirControl = 0.65f;
	M->GravityScale = 1.6f;
	M->BrakingDecelerationWalking = 2400.f;

	Boom = CreateDefaultSubobject<USpringArmComponent>(TEXT("Boom"));
	Boom->SetupAttachment(RootComponent);
	Boom->TargetArmLength = 650.f;
	Boom->SocketOffset = FVector(0.f, 0.f, 120.f);
	Boom->bUsePawnControlRotation = true;
	Boom->bEnableCameraLag = true;
	Boom->CameraLagSpeed = 10.f;

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(Boom, USpringArmComponent::SocketName);
	Camera->bUsePawnControlRotation = false;
	Camera->SetFieldOfView(80.f);

	// A blocky body: the same proportions as the realm's avatar (ADR-034), at 1 block = 100 cm.
	Body = CreateDefaultSubobject<USceneComponent>(TEXT("Body"));
	Body->SetupAttachment(RootComponent);
	Body->SetRelativeLocation(FVector(0.f, 0.f, -92.f));
	const FLinearColor Skin(0.96f, 0.80f, 0.19f), Shirt(0.05f, 0.41f, 0.67f), Pants(0.29f, 0.59f, 0.29f);
	Legs.Add(Block(Body, TEXT("LegL"), FVector(0.42f, 0.42f, 0.85f), FVector(0.f, -22.f, 42.f), Pants));
	Legs.Add(Block(Body, TEXT("LegR"), FVector(0.42f, 0.42f, 0.85f), FVector(0.f, 22.f, 42.f), Pants));
	Block(Body, TEXT("Torso"), FVector(0.44f, 0.86f, 0.80f), FVector(0.f, 0.f, 125.f), Shirt);
	Arms.Add(Block(Body, TEXT("ArmL"), FVector(0.38f, 0.38f, 0.80f), FVector(0.f, -63.f, 125.f), Skin));
	Block(Body, TEXT("Head"), FVector(0.5f, 0.5f, 0.5f), FVector(0.f, 0.f, 192.f), Skin);
	Block(Body, TEXT("EyeL"), FVector(0.02f, 0.08f, 0.08f), FVector(26.f, -10.f, 198.f), FLinearColor(0.02f, 0.02f, 0.02f));
	Block(Body, TEXT("EyeR"), FVector(0.02f, 0.08f, 0.08f), FVector(26.f, 10.f, 198.f), FLinearColor(0.02f, 0.02f, 0.02f));
	Block(Body, TEXT("Shield"), FVector(0.08f, 0.55f, 0.65f), FVector(10.f, -88.f, 120.f), FLinearColor(0.55f, 0.1f, 0.08f));

	// The sword arm swings about the shoulder.
	SwordPivot = CreateDefaultSubobject<USceneComponent>(TEXT("SwordPivot"));
	SwordPivot->SetupAttachment(Body);
	SwordPivot->SetRelativeLocation(FVector(0.f, 63.f, 160.f));
	Arms.Add(Block(SwordPivot, TEXT("ArmR"), FVector(0.38f, 0.38f, 0.80f), FVector(0.f, 0.f, -35.f), Skin));
	Block(SwordPivot, TEXT("Hilt"), FVector(0.10f, 0.30f, 0.10f), FVector(20.f, 0.f, -75.f), FLinearColor(0.35f, 0.22f, 0.1f));
	Block(SwordPivot, TEXT("Blade"), FVector(1.10f, 0.08f, 0.14f), FVector(80.f, 0.f, -75.f), FLinearColor(0.85f, 0.88f, 0.95f));
}

UStaticMeshComponent* ADaedalusHero::Block(USceneComponent* Parent, const FName Name, const FVector& Size,
                                           const FVector& At, const FLinearColor& Color)
{
	UStaticMeshComponent* C = CreateDefaultSubobject<UStaticMeshComponent>(Name);
	C->SetupAttachment(Parent);
	C->SetStaticMesh(Cube);
	C->SetRelativeLocation(At);
	C->SetRelativeScale3D(Size);
	C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	C->SetCastShadow(true);
	C->ComponentTags.Add(*FString::Printf(TEXT("color:%s"), *Color.ToFColor(true).ToHex()));
	return C;
}

void ADaedalusHero::BeginPlay()
{
	Super::BeginPlay();
	LastGround = GetActorLocation();
	// Colours: one dynamic material per block, tinted from the colour tag set in the constructor.
	TArray<UStaticMeshComponent*> Blocks;
	GetComponents<UStaticMeshComponent>(Blocks);
	for (UStaticMeshComponent* C : Blocks)
	{
		for (const FName& Tag : C->ComponentTags)
		{
			FString S = Tag.ToString();
			if (S.RemoveFromStart(TEXT("color:")) && ShapeMaterial())
			{
				UMaterialInstanceDynamic* MID = UMaterialInstanceDynamic::Create(ShapeMaterial(), this);
				MID->SetVectorParameterValue(TEXT("Color"), FLinearColor(FColor::FromHex(S)));
				C->SetMaterial(0, MID);
			}
		}
	}

	// Input, made at runtime so the hero needs no assets.
	MoveAction = NewObject<UInputAction>(this, TEXT("IA_Move"));
	MoveAction->ValueType = EInputActionValueType::Axis2D;
	LookAction = NewObject<UInputAction>(this, TEXT("IA_Look"));
	LookAction->ValueType = EInputActionValueType::Axis2D;
	JumpAction = NewObject<UInputAction>(this, TEXT("IA_Jump"));
	SwingAction = NewObject<UInputAction>(this, TEXT("IA_Swing"));
	DashAction = NewObject<UInputAction>(this, TEXT("IA_Dash"));
	Mapping = NewObject<UInputMappingContext>(this, TEXT("IMC_Hero"));

	auto MapAxis = [this](UInputAction* A, FKey Key, bool bNegate, bool bSwizzle)
	{
		FEnhancedActionKeyMapping& Map = Mapping->MapKey(A, Key);
		if (bSwizzle)
		{
			UInputModifierSwizzleAxis* Sw = NewObject<UInputModifierSwizzleAxis>(Mapping);
			Sw->Order = EInputAxisSwizzle::YXZ;
			Map.Modifiers.Add(Sw);
		}
		if (bNegate)
		{
			Map.Modifiers.Add(NewObject<UInputModifierNegate>(Mapping));
		}
	};
	MapAxis(MoveAction, EKeys::W, false, true);
	MapAxis(MoveAction, EKeys::S, true, true);
	MapAxis(MoveAction, EKeys::D, false, false);
	MapAxis(MoveAction, EKeys::A, true, false);
	Mapping->MapKey(MoveAction, EKeys::Gamepad_Left2D);
	Mapping->MapKey(LookAction, EKeys::Mouse2D);
	Mapping->MapKey(LookAction, EKeys::Gamepad_Right2D);
	Mapping->MapKey(JumpAction, EKeys::SpaceBar);
	Mapping->MapKey(JumpAction, EKeys::Gamepad_FaceButton_Bottom);
	Mapping->MapKey(SwingAction, EKeys::LeftMouseButton);
	Mapping->MapKey(SwingAction, EKeys::J);
	Mapping->MapKey(SwingAction, EKeys::Gamepad_FaceButton_Left);
	Mapping->MapKey(DashAction, EKeys::LeftShift);
	Mapping->MapKey(DashAction, EKeys::Gamepad_FaceButton_Right);

	if (APlayerController* PC = Cast<APlayerController>(GetController()))
	{
		if (UEnhancedInputLocalPlayerSubsystem* Sub = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
		{
			Sub->AddMappingContext(Mapping, 0);
		}
		if (UEnhancedInputComponent* EI = Cast<UEnhancedInputComponent>(InputComponent))
		{
			EI->BindAction(MoveAction, ETriggerEvent::Triggered, this, &ADaedalusHero::Move);
			EI->BindAction(LookAction, ETriggerEvent::Triggered, this, &ADaedalusHero::Look);
			EI->BindAction(JumpAction, ETriggerEvent::Started, this, &ACharacter::Jump);
			EI->BindAction(JumpAction, ETriggerEvent::Completed, this, &ACharacter::StopJumping);
			EI->BindAction(SwingAction, ETriggerEvent::Started, this, &ADaedalusHero::Swing);
			EI->BindAction(DashAction, ETriggerEvent::Started, this, &ADaedalusHero::Dash);
		}
	}
}

void ADaedalusHero::SetupPlayerInputComponent(UInputComponent* Input)
{
	Super::SetupPlayerInputComponent(Input);   // bindings are added in BeginPlay, once the actions exist
}

void ADaedalusHero::Move(const FInputActionValue& V)
{
	const FVector2D In = V.Get<FVector2D>();
	if (!Controller) return;
	const FRotator Yaw(0.f, Controller->GetControlRotation().Yaw, 0.f);
	AddMovementInput(FRotationMatrix(Yaw).GetUnitAxis(EAxis::X), In.Y);
	AddMovementInput(FRotationMatrix(Yaw).GetUnitAxis(EAxis::Y), In.X);
}

void ADaedalusHero::Look(const FInputActionValue& V)
{
	const FVector2D In = V.Get<FVector2D>();
	AddControllerYawInput(In.X);
	AddControllerPitchInput(-In.Y);
}

void ADaedalusHero::Swing()
{
	if (SwingLeft > 0.f) return;
	SwingLeft = SwingTime;
	++Swings;
	if (GetCharacterMovement()->IsFalling())
	{
		// Zelda II down-thrust: point the sword down and drive the hero at the ground.
		bThrusting = true;
		LaunchCharacter(FVector(0.f, 0.f, -1400.f), false, true);
	}
}

void ADaedalusHero::Dash()
{
	const FVector Fwd = GetActorForwardVector();
	LaunchCharacter(Fwd * DashSpeed + FVector(0.f, 0.f, 120.f), true, false);
}

void ADaedalusHero::Landed(const FHitResult& Hit)
{
	Super::Landed(Hit);
	if (bThrusting)
	{
		bThrusting = false;
		++Bounces;
		LaunchCharacter(FVector(0.f, 0.f, 900.f), false, true);   // the bounce off what the thrust hit
	}
}

void ADaedalusHero::Respawn()
{
	GetCharacterMovement()->StopMovementImmediately();
	bThrusting = false;
	SetActorLocation(LastGround + FVector(0.f, 0.f, 60.f), false, nullptr, ETeleportType::TeleportPhysics);
	++Respawns;
}

void ADaedalusHero::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	// Islands float in the sky: remember the last ground, and fall back onto it instead of falling forever.
	const UCharacterMovementComponent* Mv = GetCharacterMovement();
	if (Mv->IsMovingOnGround())
	{
		LastGround = GetActorLocation();
	}
	else if (!LastGround.IsZero() && GetActorLocation().Z < LastGround.Z - FallLimit)
	{
		Respawn();
	}
	// Walk cycle: legs and the free arm swing with speed.
	const float Speed = GetVelocity().Size2D();
	WalkPhase += DeltaSeconds * FMath::Clamp(Speed / 60.f, 0.f, 14.f);
	const float Sway = FMath::Sin(WalkPhase) * FMath::Clamp(Speed / 650.f, 0.f, 1.f) * 35.f;
	if (Legs.Num() == 2)
	{
		Legs[0]->SetRelativeRotation(FRotator(Sway, 0.f, 0.f));
		Legs[1]->SetRelativeRotation(FRotator(-Sway, 0.f, 0.f));
	}
	if (Arms.Num() >= 1)
	{
		Arms[0]->SetRelativeRotation(FRotator(-Sway, 0.f, 0.f));
	}
	// Sword: a quick arc forward and back, or straight down during a thrust.
	if (SwingLeft > 0.f)
	{
		SwingLeft = FMath::Max(0.f, SwingLeft - DeltaSeconds);
		const float T = 1.f - SwingLeft / SwingTime;
		const float Pitch = bThrusting ? -90.f : FMath::Sin(T * PI) * -110.f;
		SwordPivot->SetRelativeRotation(FRotator(Pitch, 0.f, 0.f));
	}
	else
	{
		SwordPivot->SetRelativeRotation(bThrusting ? FRotator(-90.f, 0.f, 0.f) : FRotator(Sway * 0.6f, 0.f, 0.f));
	}
}

ADaedalusGameMode::ADaedalusGameMode()
{
	DefaultPawnClass = ADaedalusHero::StaticClass();
}
