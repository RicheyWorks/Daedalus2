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
#include "Dom/JsonObject.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

// Controller tuning, settable in the console or in DefaultEngine.ini [ConsoleVariables].
static TAutoConsoleVariable<float> CVarMouseSensitivity(TEXT("daedalus.MouseSensitivity"), 0.30f,
	TEXT("Degrees of camera turn per mouse count (raw, no smoothing)."));
static TAutoConsoleVariable<float> CVarStickLookRate(TEXT("daedalus.StickLookRate"), 200.f,
	TEXT("Degrees per second at full right-stick deflection."));
static TAutoConsoleVariable<int32> CVarInvertY(TEXT("daedalus.InvertY"), 0, TEXT("1 inverts vertical look."));
static TAutoConsoleVariable<float> CVarDeadzone(TEXT("daedalus.Deadzone"), 0.15f,
	TEXT("Stick deadzone (0-0.9), read when the hero spawns."));
static TAutoConsoleVariable<int32> CVarRumble(TEXT("daedalus.Rumble"), 1, TEXT("0 turns controller rumble off."));

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
	auto Make = [this](const TCHAR* Name, EInputActionValueType Type)
	{
		UInputAction* A = NewObject<UInputAction>(this, Name);
		A->ValueType = Type;
		return A;
	};
	MoveAction = Make(TEXT("IA_Move"), EInputActionValueType::Axis2D);
	LookMouseAction = Make(TEXT("IA_LookMouse"), EInputActionValueType::Axis2D);
	LookStickAction = Make(TEXT("IA_LookStick"), EInputActionValueType::Axis2D);
	JumpAction = Make(TEXT("IA_Jump"), EInputActionValueType::Boolean);
	SwingAction = Make(TEXT("IA_Swing"), EInputActionValueType::Boolean);
	DashAction = Make(TEXT("IA_Dash"), EInputActionValueType::Boolean);
	ShieldAction = Make(TEXT("IA_Shield"), EInputActionValueType::Boolean);
	Mapping = NewObject<UInputMappingContext>(this, TEXT("IMC_Hero"));

	// Keyboard and mouse. The mouse is raw (no smoothing, no frame-rate scaling): every count a high-polling
	// mouse (Razer 8K) reports turns the camera by the same angle.
	MapSpec(MoveAction, TEXT("W:y"));
	MapSpec(MoveAction, TEXT("S:y-"));
	MapSpec(MoveAction, TEXT("D"));
	MapSpec(MoveAction, TEXT("A:-"));
	MapSpec(LookMouseAction, TEXT("Mouse2D"));
	MapSpec(JumpAction, TEXT("SpaceBar"));
	MapSpec(SwingAction, TEXT("LeftMouseButton"));
	MapSpec(SwingAction, TEXT("J"));
	MapSpec(DashAction, TEXT("LeftShift"));
	MapSpec(ShieldAction, TEXT("RightMouseButton"));
	MapSpec(ShieldAction, TEXT("K"));

	// XInput pads: Xbox Elite Series 2 (paddles mirror face buttons), GameSir and Razer Wolverine/Kishi in
	// XInput mode. Sticks get a radial deadzone; the right stick turns at a rate, not by its deflection per frame.
	MapSpec(MoveAction, TEXT("Gamepad_Left2D:dz"));
	MapSpec(MoveAction, TEXT("Gamepad_DPad_Up:y"));
	MapSpec(MoveAction, TEXT("Gamepad_DPad_Down:y-"));
	MapSpec(MoveAction, TEXT("Gamepad_DPad_Right"));
	MapSpec(MoveAction, TEXT("Gamepad_DPad_Left:-"));
	MapSpec(LookStickAction, TEXT("Gamepad_Right2D:dz"));
	MapSpec(JumpAction, TEXT("Gamepad_FaceButton_Bottom"));
	MapSpec(SwingAction, TEXT("Gamepad_FaceButton_Left"));
	MapSpec(SwingAction, TEXT("Gamepad_RightTriggerAxis"));
	MapSpec(DashAction, TEXT("Gamepad_FaceButton_Right"));
	MapSpec(DashAction, TEXT("Gamepad_RightShoulder"));
	MapSpec(ShieldAction, TEXT("Gamepad_LeftTriggerAxis"));
	MapSpec(ShieldAction, TEXT("Gamepad_LeftShoulder"));

	// Everything else (Switch Pro, N64 USB pads and adapters, arcade sticks) comes from the profile file.
	MapProfile();

	if (APlayerController* PC = Cast<APlayerController>(GetController()))
	{
		if (UEnhancedInputLocalPlayerSubsystem* Sub = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
		{
			Sub->AddMappingContext(Mapping, 0);
		}
		if (UEnhancedInputComponent* EI = Cast<UEnhancedInputComponent>(InputComponent))
		{
			EI->BindAction(MoveAction, ETriggerEvent::Triggered, this, &ADaedalusHero::Move);
			EI->BindAction(LookMouseAction, ETriggerEvent::Triggered, this, &ADaedalusHero::LookMouse);
			EI->BindAction(LookStickAction, ETriggerEvent::Triggered, this, &ADaedalusHero::LookStick);
			EI->BindAction(JumpAction, ETriggerEvent::Started, this, &ACharacter::Jump);
			EI->BindAction(JumpAction, ETriggerEvent::Completed, this, &ACharacter::StopJumping);
			EI->BindAction(SwingAction, ETriggerEvent::Started, this, &ADaedalusHero::Swing);
			EI->BindAction(DashAction, ETriggerEvent::Started, this, &ADaedalusHero::Dash);
			EI->BindAction(ShieldAction, ETriggerEvent::Started, this, &ADaedalusHero::ShieldOn);
			EI->BindAction(ShieldAction, ETriggerEvent::Completed, this, &ADaedalusHero::ShieldOff);
		}
	}
}

// "Key[:flags]": y = this key drives the Y axis of a 2D action, - = negate it, dz = radial deadzone
// (daedalus.Deadzone), dz1 = an axial deadzone for a single generic axis.
void ADaedalusHero::MapSpec(UInputAction* A, const FString& Spec)
{
	FString KeyName = Spec, Flags;
	Spec.Split(TEXT(":"), &KeyName, &Flags);
	const FKey Key(*KeyName.TrimStartAndEnd());
	if (!Key.IsValid())
	{
		UE_LOG(LogTemp, Warning, TEXT("Daedalus controls: no key named '%s' (is its plugin on? RawInput for generic USB pads)"), *KeyName);
		return;
	}
	FEnhancedActionKeyMapping& Map = Mapping->MapKey(A, Key);
	if (Flags.Contains(TEXT("dz")))
	{
		UInputModifierDeadZone* Dz = NewObject<UInputModifierDeadZone>(Mapping);
		Dz->LowerThreshold = FMath::Clamp(CVarDeadzone.GetValueOnGameThread(), 0.f, 0.9f);
		Dz->Type = Flags.Contains(TEXT("dz1")) ? EDeadZoneType::Axial : EDeadZoneType::Radial;
		Map.Modifiers.Add(Dz);
	}
	if (Flags.Contains(TEXT("y")))
	{
		UInputModifierSwizzleAxis* Sw = NewObject<UInputModifierSwizzleAxis>(Mapping);
		Sw->Order = EInputAxisSwizzle::YXZ;
		Map.Modifiers.Add(Sw);
	}
	if (Flags.Contains(TEXT("-")))
	{
		Map.Modifiers.Add(NewObject<UInputModifierNegate>(Mapping));
	}
}

FString ADaedalusHero::ControllerProfilePath()
{
	return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Config"), TEXT("DaedalusControllers.json"));
}

// The profile maps more keys onto the same actions: {"bindings": {"Jump": ["GenericUSBController_Button2"], ...}}.
// Key names are Unreal's (RawInput names generic pads GenericUSBController_Button1..20 and _Axis1..24; type
// "showdebug enhancedinput" in Play to see what a button is called). First run writes a default with Switch Pro
// and N64-USB layouts, which differ between adapters, so edit it to taste.
void ADaedalusHero::MapProfile()
{
	const FString Path = ControllerProfilePath();
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *Path))
	{
		Text = TEXT(R"JSON({
  "about": "Extra bindings for Daedalus. Keys are Unreal key names; flags after ':' are y (drives Y), - (negate), dz (deadzone). Generic USB pads (Switch Pro, N64 USB, adapters) come through RawInput as GenericUSBController_*.",
  "bindings": {
    "Move":   ["GenericUSBController_Axis1:dz1", "GenericUSBController_Axis2:y-:dz1"],
    "LookStick": ["GenericUSBController_Axis3:dz1", "GenericUSBController_Axis4:y-:dz1"],
    "Jump":   ["GenericUSBController_Button2"],
    "Swing":  ["GenericUSBController_Button1", "GenericUSBController_Button8"],
    "Dash":   ["GenericUSBController_Button3", "GenericUSBController_Button6"],
    "Shield": ["GenericUSBController_Button5", "GenericUSBController_Button7"]
  },
  "layouts": {
    "n64_usb": "A=Button2 jump, B=Button1 swing, Z=Button7 shield, R=Button6 dash, C-buttons=Axis3/4 or Buttons 9-12 look",
    "switch_pro_wired": "B(bottom)=Button2 jump, Y(left)=Button1 swing, A(right)=Button3 dash, ZL=Button7 shield, ZR=Button8 swing"
  }
})JSON");
		FFileHelper::SaveStringToFile(Text, *Path);
	}
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		UE_LOG(LogTemp, Warning, TEXT("Daedalus controls: %s is not valid JSON; using the built-in bindings"), *Path);
		return;
	}
	const TSharedPtr<FJsonObject>* Bindings = nullptr;
	if (!Root->TryGetObjectField(TEXT("bindings"), Bindings))
	{
		return;
	}
	TMap<FString, UInputAction*> Actions;
	Actions.Add(TEXT("Move"), MoveAction.Get());
	Actions.Add(TEXT("LookMouse"), LookMouseAction.Get());
	Actions.Add(TEXT("LookStick"), LookStickAction.Get());
	Actions.Add(TEXT("Jump"), JumpAction.Get());
	Actions.Add(TEXT("Swing"), SwingAction.Get());
	Actions.Add(TEXT("Dash"), DashAction.Get());
	Actions.Add(TEXT("Shield"), ShieldAction.Get());
	for (const auto& Pair : (*Bindings)->Values)
	{
		UInputAction* const* A = Actions.Find(Pair.Key);
		const TArray<TSharedPtr<FJsonValue>>* Keys = nullptr;
		if (!A || !Pair.Value->TryGetArray(Keys))
		{
			continue;
		}
		for (const TSharedPtr<FJsonValue>& K : *Keys)
		{
			MapSpec(*A, K->AsString());
		}
	}
}

TArray<FString> ADaedalusHero::DescribeBindings() const
{
	TArray<FString> Out;
	if (!Mapping)
	{
		return Out;
	}
	for (const FEnhancedActionKeyMapping& M : Mapping->GetMappings())
	{
		FString Mods;
		for (const TObjectPtr<UInputModifier>& Mod : M.Modifiers)
		{
			Mods += TEXT(" ") + (Mod ? Mod->GetClass()->GetName().Replace(TEXT("InputModifier"), TEXT("")) : FString(TEXT("?")));
		}
		Out.Add(FString::Printf(TEXT("%s <- %s%s"), M.Action ? *M.Action->GetName() : TEXT("?"), *M.Key.ToString(), *Mods));
	}
	return Out;
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

void ADaedalusHero::LookMouse(const FInputActionValue& V)
{
	// Raw counts times a sensitivity: no smoothing and no frame-time scaling.
	const FVector2D In = V.Get<FVector2D>() * CVarMouseSensitivity.GetValueOnGameThread();
	const float Invert = CVarInvertY.GetValueOnGameThread() ? -1.f : 1.f;
	AddControllerYawInput(In.X);
	AddControllerPitchInput(-In.Y * Invert);
}

void ADaedalusHero::LookStick(const FInputActionValue& V)
{
	// A stick is a rate: full deflection turns StickLookRate degrees a second, whatever the frame rate.
	const float Dt = GetWorld() ? GetWorld()->GetDeltaSeconds() : 0.016f;
	const FVector2D In = V.Get<FVector2D>() * CVarStickLookRate.GetValueOnGameThread() * Dt;
	const float Invert = CVarInvertY.GetValueOnGameThread() ? -1.f : 1.f;
	AddControllerYawInput(In.X);
	AddControllerPitchInput(-In.Y * Invert);
}

void ADaedalusHero::ShieldOn()
{
	bShielding = true;
	GetCharacterMovement()->MaxWalkSpeed = 300.f;
}

void ADaedalusHero::ShieldOff()
{
	bShielding = false;
	GetCharacterMovement()->MaxWalkSpeed = 650.f;
}

void ADaedalusHero::Rumble(float Intensity, float Seconds) const
{
	if (!CVarRumble.GetValueOnGameThread())
	{
		return;
	}
	if (APlayerController* PC = Cast<APlayerController>(GetController()))
	{
		PC->PlayDynamicForceFeedback(Intensity, Seconds, true, true, true, true);
	}
}

void ADaedalusHero::Swing()
{
	if (SwingLeft > 0.f) return;
	SwingLeft = SwingTime;
	++Swings;
	Rumble(0.25f, 0.08f);
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
	if (!bThrusting && GetVelocity().Z < -1600.f)
	{
		Rumble(0.5f, 0.12f);   // a hard landing
	}
	if (bThrusting)
	{
		bThrusting = false;
		++Bounces;
		Rumble(0.8f, 0.15f);
		LaunchCharacter(FVector(0.f, 0.f, 900.f), false, true);   // the bounce off what the thrust hit
	}
}

void ADaedalusHero::Respawn()
{
	GetCharacterMovement()->StopMovementImmediately();
	bThrusting = false;
	SetActorLocation(LastGround + FVector(0.f, 0.f, 60.f), false, nullptr, ETeleportType::TeleportPhysics);
	++Respawns;
	Rumble(0.5f, 0.25f);
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
