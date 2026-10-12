// SPDX-License-Identifier: MIT

#include "DaedalusHero.h"

#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "DaedalusGhost.h"
#include "DaedalusEncounters.h"
#include "DaedalusNav.h"
#include "DaedalusSettings.h"
#include "DaedalusTarget.h"
#include "EngineUtils.h"
#include "Dom/JsonObject.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/OverlapResult.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "Framework/Application/SlateApplication.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "HAL/IConsoleManager.h"
#include "HttpModule.h"
#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "SDaedalusFieldMenu.h"
#include "SDaedalusHud.h"
#include "SDaedalusSettingsMenu.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/ConstructorHelpers.h"
#include "Widgets/SWeakWidget.h"

// Tuning, settable in the console or DefaultEngine.ini [ConsoleVariables]; the settings menu writes most of them.
static TAutoConsoleVariable<float> CVarMouseSensitivity(TEXT("daedalus.MouseSensitivity"), 0.30f, TEXT("Degrees per horizontal mouse count (raw)."));
static TAutoConsoleVariable<float> CVarMouseSensitivityY(TEXT("daedalus.MouseSensitivityY"), 0.30f, TEXT("Degrees per vertical mouse count."));
static TAutoConsoleVariable<int32> CVarInvertMouseY(TEXT("daedalus.InvertMouseY"), 0, TEXT("1 inverts vertical mouse look."));
static TAutoConsoleVariable<float> CVarStickLookRate(TEXT("daedalus.StickLookRate"), 200.f, TEXT("Degrees per second at full look stick, sensitivity 5."));
static TAutoConsoleVariable<float> CVarStickSensX(TEXT("daedalus.StickSensX"), 5.f, TEXT("Look stick horizontal sensitivity, 1-10."));
static TAutoConsoleVariable<float> CVarStickSensY(TEXT("daedalus.StickSensY"), 5.f, TEXT("Look stick vertical sensitivity, 1-10."));
static TAutoConsoleVariable<int32> CVarInvertY(TEXT("daedalus.InvertY"), 0, TEXT("1 inverts vertical stick look."));
static TAutoConsoleVariable<int32> CVarInvertX(TEXT("daedalus.InvertX"), 0, TEXT("1 inverts horizontal stick look."));
static TAutoConsoleVariable<float> CVarLookAccel(TEXT("daedalus.LookAccel"), 3.f, TEXT("Look acceleration at full stick, 0-10."));
static TAutoConsoleVariable<float> CVarDeadzone(TEXT("daedalus.Deadzone"), 0.15f, TEXT("Stick deadzone used before settings load."));
static TAutoConsoleVariable<int32> CVarRumble(TEXT("daedalus.Rumble"), 1, TEXT("0 turns controller rumble off."));
static TAutoConsoleVariable<float> CVarRumbleScale(TEXT("daedalus.RumbleScale"), 1.f, TEXT("Rumble strength, 0-1."));
static TAutoConsoleVariable<FString> CVarServer(TEXT("daedalus.Server"), TEXT("http://localhost:8088"), TEXT("The Daedalus server (foe rules)."));

namespace
{
	UMaterialInterface* ShapeMaterial()
	{
		static UMaterialInterface* M = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
		return M;
	}

	// ADR-037's foe table, the same as daedalus-core's FoeKind; replaced by the server's /hero/rules when it answers.
	TArray<FDaedalusFoeRule>& Rules()
	{
		static TArray<FDaedalusFoeRule> R = {
			{TEXT("BLIGHT_SLIME"), TEXT("Blight slime"), 1, 1, 2},
			{TEXT("SHARDBACK"), TEXT("Shardback"), 2, 2, 5},
			{TEXT("DUST_WISP"), TEXT("Dust wisp"), 1, 1, 3},
			{TEXT("STONE_KNIGHT"), TEXT("Stone knight"), 6, 2, 50}};
		return R;
	}

	// Halo Infinite's button layouts, in our actions: each action lists its pad buttons.
	TMap<FName, TArray<FString>> PadButtons(int32 Layout)
	{
		TMap<FName, TArray<FString>> M;
		M.Add("Jump", {TEXT("Gamepad_FaceButton_Bottom")});
		M.Add("Dash", {TEXT("Gamepad_FaceButton_Right")});
		M.Add("Interact", {TEXT("Gamepad_FaceButton_Left")});
		M.Add("Switch", {TEXT("Gamepad_FaceButton_Top")});
		M.Add("Aim", {TEXT("Gamepad_LeftTriggerAxis")});
		M.Add("Attack", {TEXT("Gamepad_RightTriggerAxis")});
		M.Add("Melee", {TEXT("Gamepad_RightShoulder"), TEXT("Gamepad_RightThumbstick")});
		M.Add("Shoulder", {TEXT("Gamepad_LeftShoulder"), TEXT("Gamepad_DPad_Down")});
		M.Add("Sprint", {TEXT("Gamepad_LeftThumbstick")});
		M.Add("ViewCycle", {TEXT("Gamepad_DPad_Up")});
		switch (Layout)
		{
		case 1:   // Bumper Jumper: jump on LB, so the right thumb never leaves the look stick
			M["Jump"] = {TEXT("Gamepad_LeftShoulder")};
			M["Shoulder"] = {TEXT("Gamepad_FaceButton_Bottom"), TEXT("Gamepad_DPad_Down")};
			M["Melee"] = {TEXT("Gamepad_FaceButton_Right"), TEXT("Gamepad_RightThumbstick")};
			M["Dash"] = {TEXT("Gamepad_RightShoulder")};
			break;
		case 2:   // Bumper Ninja: jump on LB, melee on B, dash on A
			M["Jump"] = {TEXT("Gamepad_LeftShoulder")};
			M["Melee"] = {TEXT("Gamepad_FaceButton_Right"), TEXT("Gamepad_RightThumbstick")};
			M["Dash"] = {TEXT("Gamepad_FaceButton_Bottom")};
			M["Shoulder"] = {TEXT("Gamepad_RightShoulder"), TEXT("Gamepad_DPad_Down")};
			break;
		case 3:   // Boxer: melee on the left trigger, aim on LB
			M["Melee"] = {TEXT("Gamepad_LeftTriggerAxis"), TEXT("Gamepad_RightThumbstick")};
			M["Aim"] = {TEXT("Gamepad_LeftShoulder")};
			M["Shoulder"] = {TEXT("Gamepad_RightShoulder"), TEXT("Gamepad_DPad_Down")};
			break;
		case 4:   // Green Thumb: melee on B, dash on R3
			M["Melee"] = {TEXT("Gamepad_FaceButton_Right")};
			M["Dash"] = {TEXT("Gamepad_RightThumbstick")};
			M["Shoulder"] = {TEXT("Gamepad_RightShoulder"), TEXT("Gamepad_DPad_Down")};
			break;
		case 5:   // Recon: melee on Y, switch on B, dash on RB
			M["Melee"] = {TEXT("Gamepad_FaceButton_Top"), TEXT("Gamepad_RightThumbstick")};
			M["Switch"] = {TEXT("Gamepad_FaceButton_Right")};
			M["Dash"] = {TEXT("Gamepad_RightShoulder")};
			break;
		default:
			break;
		}
		return M;
	}
}

const TArray<FDaedalusFoeRule>& ADaedalusHero::FoeRules()
{
	return Rules();
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

	// A blocky body, the realm avatar's proportions (ADR-034) at 1 block = 100 cm. Body blocks hide from the
	// player's own camera in first person; the arm and weapon stay, Halo-style.
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

	SwordPivot = CreateDefaultSubobject<USceneComponent>(TEXT("SwordPivot"));
	SwordPivot->SetupAttachment(Body);
	SwordPivot->SetRelativeLocation(FVector(0.f, 63.f, 160.f));
	Arms.Add(Block(SwordPivot, TEXT("ArmR"), FVector(0.38f, 0.38f, 0.80f), FVector(0.f, 0.f, -35.f), Skin, false));
	SwordBlocks.Add(Block(SwordPivot, TEXT("Hilt"), FVector(0.10f, 0.30f, 0.10f), FVector(20.f, 0.f, -75.f), FLinearColor(0.35f, 0.22f, 0.1f), false));
	SwordBlocks.Add(Block(SwordPivot, TEXT("Blade"), FVector(1.10f, 0.08f, 0.14f), FVector(80.f, 0.f, -75.f), FLinearColor(0.85f, 0.88f, 0.95f), false));
	GunBlocks.Add(Block(SwordPivot, TEXT("GunBody"), FVector(0.62f, 0.14f, 0.16f), FVector(38.f, 0.f, -75.f), FLinearColor(0.12f, 0.13f, 0.16f), false));
	GunBlocks.Add(Block(SwordPivot, TEXT("GunGrip"), FVector(0.10f, 0.12f, 0.22f), FVector(14.f, 0.f, -90.f), FLinearColor(0.08f, 0.08f, 0.1f), false));
	GunTip = Block(SwordPivot, TEXT("GunTip"), FVector(0.08f, 0.16f, 0.18f), FVector(72.f, 0.f, -75.f), FLinearColor(0.36f, 0.82f, 0.96f), false);
	GunBlocks.Add(GunTip);
}

UStaticMeshComponent* ADaedalusHero::Block(USceneComponent* Parent, const FName Name, const FVector& Size,
                                           const FVector& At, const FLinearColor& Color, bool bBody)
{
	UStaticMeshComponent* C = CreateDefaultSubobject<UStaticMeshComponent>(Name);
	C->SetupAttachment(Parent);
	C->SetStaticMesh(Cube);
	C->SetRelativeLocation(At);
	C->SetRelativeScale3D(Size);
	C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	C->SetCastShadow(true);
	C->ComponentTags.Add(*FString::Printf(TEXT("color:%s"), *Color.ToFColor(true).ToHex()));
	if (bBody)
	{
		BodyBlocks.Add(C);
	}
	return C;
}

void ADaedalusHero::BeginPlay()
{
	Super::BeginPlay();
	LastGround = GetActorLocation();
	LoadProgress();
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
	FlashMaterial = ShapeMaterial();

	auto Make = [this](const TCHAR* Name, EInputActionValueType Type)
	{
		UInputAction* A = NewObject<UInputAction>(this, Name);
		A->ValueType = Type;
		return A;
	};
	const EInputActionValueType B = EInputActionValueType::Boolean;
	MoveAction = Make(TEXT("IA_Move"), EInputActionValueType::Axis2D);
	LookMouseAction = Make(TEXT("IA_LookMouse"), EInputActionValueType::Axis2D);
	LookStickAction = Make(TEXT("IA_LookStick"), EInputActionValueType::Axis2D);
	JumpAction = Make(TEXT("IA_Jump"), B);
	AttackAction = Make(TEXT("IA_Attack"), B);
	MeleeAction = Make(TEXT("IA_Melee"), B);
	DashAction = Make(TEXT("IA_Dash"), B);
	AimAction = Make(TEXT("IA_Aim"), B);
	SwitchAction = Make(TEXT("IA_Switch"), B);
	InteractAction = Make(TEXT("IA_Interact"), B);
	SprintAction = Make(TEXT("IA_Sprint"), B);
	ViewCycleAction = Make(TEXT("IA_ViewCycle"), B);
	CallVehicleAction = Make(TEXT("IA_CallVehicle"), B);
	ShoulderAction = Make(TEXT("IA_Shoulder"), B);
	MenuAction = Make(TEXT("IA_Menu"), B);
	ViewAction = Make(TEXT("IA_View"), B);
	Mapping = NewObject<UInputMappingContext>(this, TEXT("IMC_Hero"));

	FDaedalusSettings::Get().Load();
	RebuildBindings();
	ApplySettings();
	ShowWeapon();
	FetchFoeRules();

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
			EI->BindAction(AttackAction, ETriggerEvent::Started, this, &ADaedalusHero::AttackStart);
			EI->BindAction(AttackAction, ETriggerEvent::Triggered, this, &ADaedalusHero::AttackHeld);
			EI->BindAction(MeleeAction, ETriggerEvent::Started, this, &ADaedalusHero::Melee);
			EI->BindAction(DashAction, ETriggerEvent::Started, this, &ADaedalusHero::Dash);
			EI->BindAction(AimAction, ETriggerEvent::Started, this, &ADaedalusHero::AimOn);
			EI->BindAction(AimAction, ETriggerEvent::Completed, this, &ADaedalusHero::AimOff);
			EI->BindAction(SwitchAction, ETriggerEvent::Started, this, &ADaedalusHero::SwitchWeapon);
			EI->BindAction(SprintAction, ETriggerEvent::Started, this, &ADaedalusHero::SprintOn);
			EI->BindAction(SprintAction, ETriggerEvent::Completed, this, &ADaedalusHero::SprintOff);
			EI->BindAction(ViewCycleAction, ETriggerEvent::Started, this, &ADaedalusHero::CycleView);
			EI->BindAction(ShoulderAction, ETriggerEvent::Started, this, &ADaedalusHero::SwapShoulder);
			EI->BindAction(MenuAction, ETriggerEvent::Started, this, &ADaedalusHero::ToggleSettings);
			EI->BindAction(ViewAction, ETriggerEvent::Started, this, &ADaedalusHero::ToggleField);
			EI->BindAction(InteractAction, ETriggerEvent::Started, this, &ADaedalusHero::InteractPressed);
			EI->BindAction(CallVehicleAction, ETriggerEvent::Started, this, &ADaedalusHero::CallVehiclePressed);
		}
		if (GEngine && GEngine->GameViewport)
		{
			Hud = SNew(SDaedalusHud).Hero(this);
			HudHost = SNew(SWeakWidget).PossiblyNullContent(Hud.ToSharedRef());
			GEngine->GameViewport->AddViewportWidgetContent(HudHost.ToSharedRef(), 10);
		}
	}
}

// ------------------------------------------------------------------------------------------------------- bindings

// "Key[:flags]": y = drives the Y axis of a 2D action, - = negate, dz = radial deadzone, dz1 = axial deadzone.
// Stick: 1 = governed by the move stick's dead zone setting, 2 = by the look stick's.
void ADaedalusHero::MapSpec(UInputAction* A, const FString& Spec, int32 Stick)
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
	if (Flags.Contains(TEXT("dz")) || Stick != 0)
	{
		UInputModifierDeadZone* Dz = NewObject<UInputModifierDeadZone>(Mapping);
		Dz->LowerThreshold = FMath::Clamp(CVarDeadzone.GetValueOnGameThread(), 0.f, 0.9f);
		Dz->Type = (Flags.Contains(TEXT("dz1")) || Stick != 0) ? EDeadZoneType::Axial : EDeadZoneType::Radial;
		Map.Modifiers.Add(Dz);
		if (Stick == 1) LeftDeadzones.Add(Dz);
		if (Stick == 2) RightDeadzones.Add(Dz);
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

void ADaedalusHero::RebuildBindings()
{
	const FDaedalusSettings& S = FDaedalusSettings::Get();
	AppliedButtonLayout = FMath::RoundToInt(S.V("ButtonLayout"));
	AppliedStickLayout = FMath::RoundToInt(S.V("ThumbstickLayout"));
	Mapping->UnmapAll();
	LeftDeadzones.Reset();
	RightDeadzones.Reset();

	// Keyboard and mouse. Mouse look is raw: every count a high-polling mouse (Razer 8K) reports turns the same angle.
	MapSpec(MoveAction, TEXT("W:y"));
	MapSpec(MoveAction, TEXT("S:y-"));
	MapSpec(MoveAction, TEXT("D"));
	MapSpec(MoveAction, TEXT("A:-"));
	MapSpec(LookMouseAction, TEXT("Mouse2D"));
	MapSpec(JumpAction, TEXT("SpaceBar"));
	MapSpec(AttackAction, TEXT("LeftMouseButton"));
	MapSpec(MeleeAction, TEXT("Q"));
	MapSpec(MeleeAction, TEXT("J"));
	MapSpec(DashAction, TEXT("LeftShift"));
	MapSpec(AimAction, TEXT("RightMouseButton"));
	MapSpec(AimAction, TEXT("K"));
	MapSpec(SwitchAction, TEXT("One"));
	MapSpec(SwitchAction, TEXT("Two"));
	MapSpec(SwitchAction, TEXT("MouseScrollUp"));
	MapSpec(SwitchAction, TEXT("MouseScrollDown"));
	MapSpec(InteractAction, TEXT("E"));
	MapSpec(SprintAction, TEXT("LeftControl"));
	MapSpec(ViewCycleAction, TEXT("V"));
	MapSpec(CallVehicleAction, TEXT("G"));
	MapSpec(CallVehicleAction, TEXT("Gamepad_DPad_Right"));   // call a Ghost (ADR-043)
	MapSpec(ShoulderAction, TEXT("C"));
	MapSpec(MenuAction, TEXT("F1"));
	MapSpec(MenuAction, TEXT("F10"));
	MapSpec(ViewAction, TEXT("Tab"));
	MapSpec(ViewAction, TEXT("M"));

	// The pad's sticks: the thumbstick layout decides which stick axis drives what (Halo Infinite's four layouts).
	struct FAxis { const TCHAR* Key; int32 Stick; };
	FAxis MoveX{TEXT("Gamepad_LeftX"), 1}, MoveY{TEXT("Gamepad_LeftY"), 1}, LookX{TEXT("Gamepad_RightX"), 2}, LookY{TEXT("Gamepad_RightY"), 2};
	switch (AppliedStickLayout)
	{
	case 1:   // Southpaw: the sticks swapped
		MoveX = {TEXT("Gamepad_RightX"), 2}; MoveY = {TEXT("Gamepad_RightY"), 2};
		LookX = {TEXT("Gamepad_LeftX"), 1}; LookY = {TEXT("Gamepad_LeftY"), 1};
		break;
	case 2:   // Legacy: the left stick moves forward/back and turns; the right strafes and looks up/down
		MoveY = {TEXT("Gamepad_LeftY"), 1}; MoveX = {TEXT("Gamepad_RightX"), 2};
		LookX = {TEXT("Gamepad_LeftX"), 1}; LookY = {TEXT("Gamepad_RightY"), 2};
		break;
	case 3:   // Legacy Southpaw
		MoveY = {TEXT("Gamepad_RightY"), 2}; MoveX = {TEXT("Gamepad_LeftX"), 1};
		LookX = {TEXT("Gamepad_RightX"), 2}; LookY = {TEXT("Gamepad_LeftY"), 1};
		break;
	default:
		break;
	}
	MapSpec(MoveAction, MoveX.Key, MoveX.Stick);
	MapSpec(MoveAction, FString(MoveY.Key) + TEXT(":y"), MoveY.Stick);
	MapSpec(LookStickAction, LookX.Key, LookX.Stick);
	MapSpec(LookStickAction, FString(LookY.Key) + TEXT(":y"), LookY.Stick);

	// The pad's buttons: the button layout (Default, Bumper Jumper, Bumper Ninja, Boxer, Green Thumb, Recon).
	TMap<FName, UInputAction*> Actions;
	Actions.Add("Jump", JumpAction.Get());
	Actions.Add("Dash", DashAction.Get());
	Actions.Add("Interact", InteractAction.Get());
	Actions.Add("Switch", SwitchAction.Get());
	Actions.Add("Aim", AimAction.Get());
	Actions.Add("Attack", AttackAction.Get());
	Actions.Add("Melee", MeleeAction.Get());
	Actions.Add("Shoulder", ShoulderAction.Get());
	Actions.Add("Sprint", SprintAction.Get());
	Actions.Add("ViewCycle", ViewCycleAction.Get());
	for (const TPair<FName, TArray<FString>>& P : PadButtons(AppliedButtonLayout))
	{
		if (UInputAction** A = Actions.Find(P.Key))
		{
			for (const FString& K : P.Value)
			{
				MapSpec(*A, K);
			}
		}
	}
	MapSpec(MenuAction, TEXT("Gamepad_Special_Right"));   // Menu (three lines): the game menu
	MapSpec(ViewAction, TEXT("Gamepad_Special_Left"));    // View (two boxes): the field menu

	MapProfile();

	if (APlayerController* PC = Cast<APlayerController>(GetController()))
	{
		if (UEnhancedInputLocalPlayerSubsystem* Sub = ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(PC->GetLocalPlayer()))
		{
			Sub->RequestRebuildControlMappings();
		}
	}
}

FString ADaedalusHero::ControllerProfilePath()
{
	return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Config"), TEXT("DaedalusControllers.json"));
}

// Extra bindings for generic USB pads (RawInput names them GenericUSBController_Button1..20 / _Axis1..24):
// {"bindings": {"Jump": ["GenericUSBController_Button2"], ...}}. Type "showdebug enhancedinput" in Play to see names.
void ADaedalusHero::MapProfile()
{
	const FString Path = ControllerProfilePath();
	FString Text;
	if (!FFileHelper::LoadFileToString(Text, *Path))
	{
		Text = TEXT(R"JSON({
  "about": "Extra bindings for Daedalus. Keys are Unreal key names; flags after ':' are y (drives Y), - (negate), dz/dz1 (deadzone). Generic USB pads (Switch Pro, N64 USB, adapters) come through RawInput as GenericUSBController_*.",
  "bindings": {
    "Move":   ["GenericUSBController_Axis1:dz1", "GenericUSBController_Axis2:y-:dz1"],
    "LookStick": ["GenericUSBController_Axis3:dz1", "GenericUSBController_Axis4:y-:dz1"],
    "Jump":   ["GenericUSBController_Button2"],
    "Attack": ["GenericUSBController_Button8"],
    "Melee":  ["GenericUSBController_Button1"],
    "Dash":   ["GenericUSBController_Button3", "GenericUSBController_Button6"],
    "Aim":    ["GenericUSBController_Button5", "GenericUSBController_Button7"],
    "Switch": ["GenericUSBController_Button4"]
  },
  "layouts": {
    "n64_usb": "A=Button2 jump, B=Button1 melee, Z=Button7 aim/shield, R=Button6 dash, C-buttons=Axis3/4 or Buttons 9-12 look",
    "switch_pro_wired": "B(bottom)=Button2 jump, Y(left)=Button1 melee, A(right)=Button3 dash, X=Button4 switch, ZL=Button7 aim, ZR=Button8 attack"
  }
})JSON");
		FFileHelper::SaveStringToFile(Text, *Path);
	}
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	const TSharedPtr<FJsonObject>* Bindings = nullptr;
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid() || !Root->TryGetObjectField(TEXT("bindings"), Bindings))
	{
		return;
	}
	TMap<FString, UInputAction*> Actions;
	Actions.Add(TEXT("Move"), MoveAction.Get());
	Actions.Add(TEXT("LookStick"), LookStickAction.Get());
	Actions.Add(TEXT("Jump"), JumpAction.Get());
	Actions.Add(TEXT("Attack"), AttackAction.Get());
	Actions.Add(TEXT("Swing"), MeleeAction.Get());   // older profiles
	Actions.Add(TEXT("Melee"), MeleeAction.Get());
	Actions.Add(TEXT("Dash"), DashAction.Get());
	Actions.Add(TEXT("Aim"), AimAction.Get());
	Actions.Add(TEXT("Shield"), AimAction.Get());    // older profiles
	Actions.Add(TEXT("Switch"), SwitchAction.Get());
	Actions.Add(TEXT("Interact"), InteractAction.Get());
	for (const TPair<FString, UInputAction*>& Act : Actions)
	{
		const TArray<TSharedPtr<FJsonValue>>* Keys = nullptr;
		if (!(*Bindings)->TryGetArrayField(Act.Key, Keys) || !Keys) continue;
		for (const TSharedPtr<FJsonValue>& K : *Keys)
		{
			MapSpec(Act.Value, K->AsString());
		}
	}
}

TArray<FString> ADaedalusHero::DescribeBindings() const
{
	TArray<FString> Out;
	if (!Mapping) return Out;
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

// ---------------------------------------------------------------------------------------------- moving, looking

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
	const FVector2D In = V.Get<FVector2D>();
	const float Zoom = bAiming && CurrentWeapon == 1 ? 0.6f : 1.f;
	const float Invert = CVarInvertMouseY.GetValueOnGameThread() ? -1.f : 1.f;
	AddControllerYawInput(In.X * CVarMouseSensitivity.GetValueOnGameThread() * Zoom);
	AddControllerPitchInput(-In.Y * CVarMouseSensitivityY.GetValueOnGameThread() * Invert * Zoom);
}

void ADaedalusHero::LookStick(const FInputActionValue& V)
{
	// A stick is a rate: full deflection turns StickLookRate x (sensitivity / 5) degrees a second at any frame rate.
	// Held all the way out, look acceleration ramps it up over half a second.
	const float Dt = GetWorld() ? GetWorld()->GetDeltaSeconds() : 0.016f;
	const FVector2D In = V.Get<FVector2D>();
	LookHeld = In.Size() > 0.92f ? FMath::Min(LookHeld + Dt, 0.5f) : 0.f;
	const float Accel = 1.f + CVarLookAccel.GetValueOnGameThread() * 0.08f * (LookHeld / 0.5f);
	const float Zoom = bAiming && CurrentWeapon == 1 ? 0.6f : 1.f;
	const float Rate = CVarStickLookRate.GetValueOnGameThread() * Dt * Accel * Zoom;
	const float InvX = CVarInvertX.GetValueOnGameThread() ? -1.f : 1.f;
	const float InvY = CVarInvertY.GetValueOnGameThread() ? -1.f : 1.f;
	AddControllerYawInput(In.X * Rate * (CVarStickSensX.GetValueOnGameThread() / 5.f) * InvX);
	AddControllerPitchInput(-In.Y * Rate * (CVarStickSensY.GetValueOnGameThread() / 5.f) * InvY);
}

void ADaedalusHero::SprintOn()
{
	bSprinting = true;
}

void ADaedalusHero::SprintOff()
{
	bSprinting = false;
}

void ADaedalusHero::AimAt(FVector Point)
{
	if (AController* C = GetController())
	{
		C->SetControlRotation((Point - Camera->GetComponentLocation()).Rotation());
	}
}

// --------------------------------------------------------------------------------------------------- views

void ADaedalusHero::CycleView()
{
	SetSetting("CameraView", static_cast<float>((CameraView + 1) % 3));
}

void ADaedalusHero::SwapShoulder()
{
	SetSetting("Shoulder", ShoulderSide > 0.f ? 1.f : 0.f);
}

FString ADaedalusHero::ViewName() const
{
	switch (CameraView)
	{
	case 0: return TEXT("FIRST PERSON");
	case 1: return ShoulderSide > 0.f ? TEXT("SHOULDER  RIGHT") : TEXT("SHOULDER  LEFT");
	default: return TEXT("CLASSIC");
	}
}

bool ADaedalusHero::ShowsReticle() const
{
	return FDaedalusSettings::Get().V("Reticle") > 0.5f && (CameraView != 2 || CurrentWeapon == 1);
}

void ADaedalusHero::ApplyCameraView()
{
	const FDaedalusSettings& S = FDaedalusSettings::Get();
	UCharacterMovementComponent* Mv = GetCharacterMovement();
	const bool bFirst = CameraView == 0;
	for (UStaticMeshComponent* C : BodyBlocks)
	{
		if (C) C->SetOwnerNoSee(bFirst);   // the player doesn't see his own body in first person; others still do
	}
	switch (CameraView)
	{
	case 0:   // Halo Infinite: the camera is the eyes, and the hero turns with it
		Boom->TargetArmLength = 0.f;
		Boom->SocketOffset = FVector::ZeroVector;
		Boom->SetRelativeLocation(FVector(12.f, 0.f, 88.f));
		Boom->bEnableCameraLag = false;
		bUseControllerRotationYaw = true;
		Mv->bOrientRotationToMovement = false;
		SwordPivot->SetRelativeLocation(FVector(35.f, 38.f, 150.f));
		break;
	case 1:   // Gears of War: over the shoulder, strafing with the camera
		Boom->TargetArmLength = 270.f;
		Boom->SocketOffset = FVector(0.f, 72.f * ShoulderSide, 62.f);
		Boom->SetRelativeLocation(FVector(0.f, 0.f, 40.f));
		Boom->bEnableCameraLag = S.V("CameraLag") > 0.5f;
		bUseControllerRotationYaw = true;
		Mv->bOrientRotationToMovement = false;
		SwordPivot->SetRelativeLocation(FVector(0.f, 63.f, 160.f));
		break;
	default:   // Classic chase: the hero turns to where he walks
		Boom->TargetArmLength = S.V("CameraDistance");
		Boom->SocketOffset = FVector(0.f, 0.f, 120.f);
		Boom->SetRelativeLocation(FVector::ZeroVector);
		Boom->bEnableCameraLag = S.V("CameraLag") > 0.5f;
		bUseControllerRotationYaw = false;
		Mv->bOrientRotationToMovement = true;
		SwordPivot->SetRelativeLocation(FVector(0.f, 63.f, 160.f));
		break;
	}
}

// ------------------------------------------------------------------------------------------------ weapons

FString ADaedalusHero::WeaponName() const
{
	return CurrentWeapon == 1 ? TEXT("BLASTER") : TEXT("SWORD");
}

void ADaedalusHero::ShowWeapon()
{
	for (UStaticMeshComponent* C : SwordBlocks) if (C) C->SetVisibility(CurrentWeapon == 0);
	for (UStaticMeshComponent* C : GunBlocks) if (C) C->SetVisibility(CurrentWeapon == 1);
}

void ADaedalusHero::SwitchWeapon()
{
	CurrentWeapon = 1 - CurrentWeapon;
	bAiming = false;
	ShowWeapon();
	Rumble(0.15f, 0.05f);
}

void ADaedalusHero::AttackStart()
{
	if (CurrentWeapon == 0) Swing();
	else Fire();
}

void ADaedalusHero::AttackHeld()
{
	if (CurrentWeapon == 1) Fire();   // the blaster is automatic; Fire() keeps its own rate
}

void ADaedalusHero::Melee()
{
	Swing();
}

void ADaedalusHero::Swing()
{
	if (SwingLeft > 0.f) return;
	SwingLeft = SwingTime;
	++Swings;
	Rumble(0.25f, 0.08f);
	if (GetCharacterMovement()->IsFalling())
	{
		// Zelda II down-thrust: point the sword down and drive the hero at the ground (the blow lands in Landed).
		bThrusting = true;
		LaunchCharacter(FVector(0.f, 0.f, -1400.f), false, true);
		return;
	}
	// The blade's reach: an arc in front of the hero at chest height.
	HitArea(GetActorLocation() + GetActorForwardVector() * 130.f + FVector(0.f, 0.f, 20.f), 140.f, 30.f);
}

bool ADaedalusHero::Fire()
{
	if (FireCooldown > 0.f || bOverheated || !GetWorld()) return false;
	FireCooldown = 0.11f;   // about nine shots a second
	++ShotsFired;
	Heat = FMath::Min(1.f, Heat + 0.065f);
	Spread = FMath::Min(1.f, Spread + 0.22f);
	if (Heat >= 1.f)
	{
		bOverheated = true;   // vents until it cools (Tick)
		Rumble(0.6f, 0.2f);
	}

	// Hitscan from the reticle: the camera's line through the centre of the screen, spreading a little when hot.
	const FVector From = Camera->GetComponentLocation();
	const float Cone = FMath::DegreesToRadians(0.4f + Spread * 1.6f) * (bAiming ? 0.4f : 1.f);
	const FVector Dir = FMath::VRandCone(Camera->GetForwardVector(), Cone);
	const FVector To = From + Dir * 30000.f;
	FHitResult Hit;
	FCollisionQueryParams Q(TEXT("DaedalusBlaster"), false, this);
	const bool bHit = GetWorld()->LineTraceSingleByChannel(Hit, From, To, ECC_Visibility, Q);
	const FVector End = bHit ? FVector(Hit.ImpactPoint) : To;

	// A tracer from the muzzle to what it hit, a muzzle flash, and a spark where it landed.
	const FVector Muzzle = GunTip ? GunTip->GetComponentLocation() : From;
	const FVector Line = End - Muzzle;
	Flash(Muzzle + Line * 0.5f, FVector(Line.Size() / 100.f, 0.03f, 0.03f), Line.Rotation(), FLinearColor(0.4f, 0.9f, 1.f), 0.05f);
	Flash(Muzzle, FVector(0.12f), FRotator::ZeroRotator, FLinearColor(0.7f, 0.95f, 1.f), 0.04f);
	if (bHit)
	{
		Flash(Hit.ImpactPoint, FVector(0.22f), FRotator::ZeroRotator, FLinearColor(1.f, 0.85f, 0.4f), 0.10f);
		if (UPrimitiveComponent* C = Hit.GetComponent())
		{
			if (C->IsSimulatingPhysics()) C->AddImpulseAtLocation(Dir * 25000.f, Hit.ImpactPoint);
		}
		Damage(Hit.GetActor(), 10.f, From);
	}
	Rumble(0.12f, 0.04f);
	return true;
}

void ADaedalusHero::Damage(AActor* Target, float Amount, const FVector& From)
{
	ADaedalusTarget* Foe = Cast<ADaedalusTarget>(Target);
	if (!Foe) return;
	++Hits;
	SinceHit = 0.f;
	const bool bAlive = Foe->Health > 0.f;
	UGameplayStatics::ApplyDamage(Foe, Amount, GetController(), this, nullptr);
	if (bAlive && Foe->Health <= 0.f)
	{
		++Kills;
		Exp += Foe->ExpValue;   // ADR-037: every foe pays EXP
		Rumble(0.5f, 0.1f);
	}
}

void ADaedalusHero::HitArea(const FVector& Center, float Radius, float Amount)
{
	if (!GetWorld()) return;
	TArray<FOverlapResult> Overlaps;
	FCollisionQueryParams Q(TEXT("DaedalusSword"), false, this);
	GetWorld()->OverlapMultiByChannel(Overlaps, Center, FQuat::Identity, ECC_Visibility, FCollisionShape::MakeSphere(Radius), Q);
	TSet<AActor*> Seen;
	for (const FOverlapResult& O : Overlaps)
	{
		AActor* A = O.GetActor();
		if (A && !Seen.Contains(A))
		{
			Seen.Add(A);
			Damage(A, Amount, Center);
		}
	}
}

void ADaedalusHero::Flash(const FVector& At, const FVector& Size, const FRotator& Rot, const FLinearColor& Color, float Life)
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
	if (FlashMaterial)
	{
		UMaterialInstanceDynamic* M = UMaterialInstanceDynamic::Create(FlashMaterial, F);
		M->SetVectorParameterValue(TEXT("Color"), Color * 4.f);
		C->SetMaterial(0, M);
	}
	F->SetLifeSpan(Life);
}

void ADaedalusHero::AimOn()
{
	if (CurrentWeapon == 1)
	{
		bAiming = true;   // zoom
		return;
	}
	if (bShieldToggle && bShielding)
	{
		bShielding = false;
		return;
	}
	bShielding = true;
}

void ADaedalusHero::AimOff()
{
	bAiming = false;
	if (!bShieldToggle) bShielding = false;
}

void ADaedalusHero::Dash()
{
	LaunchCharacter(GetActorForwardVector() * DashSpeed + FVector(0.f, 0.f, 120.f), true, false);
}

void ADaedalusHero::Landed(const FHitResult& Hit)
{
	Super::Landed(Hit);
	if (bThrusting)
	{
		bThrusting = false;
		++Bounces;
		HitArea(GetActorLocation() - FVector(0.f, 0.f, 60.f), 200.f, 60.f);   // the thrust's blow on what's below
		Rumble(0.8f, 0.15f);
		LaunchCharacter(FVector(0.f, 0.f, 900.f), false, true);
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

int32 ADaedalusHero::SpawnFoes(int32 Count)
{
	UWorld* W = GetWorld();
	if (!W) return 0;
	const TArray<FDaedalusFoeRule>& R = Rules();
	const float Yaw = Controller ? Controller->GetControlRotation().Yaw : GetActorRotation().Yaw;
	const float Feet = GetActorLocation().Z - GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	FCollisionQueryParams Q(SCENE_QUERY_STAT(DaedalusFoeSpot), false, this);
	FCollisionObjectQueryParams Objects(ECC_WorldStatic);

	// Ground for a foe: on the hero's own level if there is any, fanning out from straight ahead; never over the void.
	auto FindSpot = [&](int32 i, FVector& Out) -> bool
	{
		for (const bool bSameLevel : {true, false})
		{
			for (const float Dist : {900.f, 700.f, 1100.f, 500.f})
			{
				for (int32 k = 0; k < 12; ++k)
				{
					const float Turn = (i - (Count - 1) * 0.5f) * 14.f + ((k % 2) ? 1.f : -1.f) * 25.f * ((k + 1) / 2);
					const FVector Try = GetActorLocation() + FRotator(0.f, Yaw + Turn, 0.f).Vector() * (Dist + 120.f * (i % 3));
					FHitResult Hit;
					if (!W->LineTraceSingleByObjectType(Hit, Try + FVector(0.f, 0.f, 400.f), Try - FVector(0.f, 0.f, 1500.f), Objects, Q)) continue;
					if (Hit.ImpactNormal.Z < 0.7f) continue;
					if (bSameLevel && FMath::Abs(Hit.ImpactPoint.Z - Feet) > 150.f) continue;
					Out = Hit.ImpactPoint + FVector(0.f, 0.f, 60.f);
					return true;
				}
			}
		}
		return false;
	};

	int32 Placed = 0;
	for (int32 i = 0; i < Count; ++i)
	{
		FVector Spot;
		if (!FindSpot(i, Spot)) continue;
		ADaedalusTarget* T = W->SpawnActorDeferred<ADaedalusTarget>(ADaedalusTarget::StaticClass(), FTransform(Spot), this,
			nullptr, ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn);
		if (!T) continue;
		const FDaedalusFoeRule& Rule = R[i % R.Num()];
		T->Kind = Rule.Kind;
		T->Title = Rule.Title;
		T->ExpValue = Rule.Exp;
		T->Health = Rule.Life * 30.f;   // a sword blow takes one life; the blaster takes three shots per life
		T->Power = Rule.Power;
		UGameplayStatics::FinishSpawningActor(T, FTransform(Spot));
		++Placed;
	}
	return Placed;
}

TArray<FString> ADaedalusHero::NavProbe(FVector From, FVector To)
{
	TArray<FString> Out;
	UDaedalusNav* Nav = GetWorld() ? GetWorld()->GetSubsystem<UDaedalusNav>() : nullptr;
	if (!Nav) return Out;
	TArray<FVector> Path;
	const bool bOk = Nav->FindPath(From, To, Path);
	Out.Add(FString::Printf(TEXT("found=%d length=%d expanded=%d"), bOk ? 1 : 0, Path.Num(), Nav->LastExpanded));
	const int32 SX = FMath::FloorToInt(From.X / UDaedalusNav::Cell), SY = FMath::FloorToInt(From.Y / UDaedalusNav::Cell);
	for (int32 DY = -2; DY <= 2; ++DY)
	{
		FString Row;
		for (int32 DX = -2; DX <= 2; ++DX)
		{
			float Z;
			Row += Nav->FloorAt(SX + DX, SY + DY, From.Z + 40.f, Z) ? FString::Printf(TEXT("%6.0f "), Z - From.Z) : FString(TEXT("  ---- "));
		}
		Out.Add(Row);
	}
	return Out;
}

FString ADaedalusHero::NavTrace(FVector At, float RefZ)
{
	UDaedalusNav* Nav = GetWorld() ? GetWorld()->GetSubsystem<UDaedalusNav>() : nullptr;
	FHitResult Hit;
	const bool bMine = GetWorld()->LineTraceSingleByObjectType(Hit, FVector(At.X, At.Y, RefZ + 300.f), FVector(At.X, At.Y, RefZ - 240.f),
		FCollisionObjectQueryParams(ECC_WorldStatic), FCollisionQueryParams(SCENE_QUERY_STAT(DaedalusNavTrace), false, this));
	const FString Mine = FString::Printf(TEXT("hero type=%d hit=%d z=%.0f || "), (int32)GetWorld()->WorldType, bMine ? 1 : 0, Hit.ImpactPoint.Z - RefZ);
	return Mine + (Nav ? Nav->TraceReport(At, RefZ) : FString(TEXT("no nav")));
}

FString ADaedalusHero::NavStats() const
{
	const UDaedalusNav* Nav = GetWorld() ? GetWorld()->GetSubsystem<UDaedalusNav>() : nullptr;
	return Nav ? Nav->Stats() : FString(TEXT("no nav"));
}

bool ADaedalusHero::Interact()
{
	UWorld* W = GetWorld();
	if (!W || IsSettingsOpen() || IsFieldOpen()) return false;
	ADaedalusGhost* Best = nullptr;
	float BestD = InteractReach * InteractReach;
	for (TActorIterator<ADaedalusGhost> It(W); It; ++It)
	{
		if (It->Rider) continue;
		const float D = FVector::DistSquared(It->GetActorLocation(), GetActorLocation());
		if (D <= BestD)
		{
			BestD = D;
			Best = *It;
		}
	}
	return Best && Best->Mount(this);
}

// One called Ghost at a time: calling again brings the parked one back instead of adding another.
void ADaedalusHero::CallVehiclePressed()
{
	if (IsSettingsOpen() || IsFieldOpen()) return;
	if (CalledGhost.IsValid() && CalledGhost->Rider) return;
	if (CalledGhost.IsValid()) CalledGhost->Destroy();
	CalledGhost = SpawnVehicle();
}

ADaedalusGhost* ADaedalusHero::SpawnVehicle()
{
	UWorld* W = GetWorld();
	if (!W) return nullptr;
	const float Yaw = Controller ? Controller->GetControlRotation().Yaw : GetActorRotation().Yaw;
	// Ground at the hero's own level, ahead first, then to the sides and behind (islands have ledges).
	const float Feet = GetActorLocation().Z - GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	FCollisionQueryParams Q(SCENE_QUERY_STAT(DaedalusVehicleSpot), false, this);
	FVector Spot = GetActorLocation() + FRotator(0.f, Yaw + 90.f, 0.f).Vector() * 250.f;
	bool bFound = false;
	for (const float Turn : {0.f, 90.f, -90.f, 45.f, -45.f, 180.f})
	{
		for (const float Dist : {300.f, 220.f})
		{
			const FVector Try = GetActorLocation() + FRotator(0.f, Yaw + Turn, 0.f).Vector() * Dist;
			FHitResult Hit;
			if (!bFound && W->LineTraceSingleByChannel(Hit, Try + FVector(0.f, 0.f, 300.f), Try - FVector(0.f, 0.f, 1500.f), ECC_Visibility, Q)
				&& FMath::Abs(Hit.ImpactPoint.Z - Feet) < 120.f)
			{
				Spot = Hit.ImpactPoint + FVector(0.f, 0.f, 120.f);
				bFound = true;
			}
		}
	}
	FActorSpawnParameters P;
	P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
	return W->SpawnActor<ADaedalusGhost>(ADaedalusGhost::StaticClass(), Spot, FRotator(0.f, Yaw, 0.f), P);
}

void ADaedalusHero::FetchFoeRules()
{
	const FString Url = CVarServer.GetValueOnGameThread() + TEXT("/api/v1/hero/rules");
	TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Req = FHttpModule::Get().CreateRequest();
	Req->SetURL(Url);
	Req->SetVerb(TEXT("GET"));
	Req->OnProcessRequestComplete().BindLambda([](FHttpRequestPtr, FHttpResponsePtr Resp, bool bOk)
	{
		if (!bOk || !Resp.IsValid() || Resp->GetResponseCode() != 200) return;   // keep the built-in table
		TSharedPtr<FJsonObject> Root;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Resp->GetContentAsString());
		const TArray<TSharedPtr<FJsonValue>>* Foes = nullptr;
		if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid() || !Root->TryGetArrayField(TEXT("foes"), Foes) || !Foes) return;
		TArray<FDaedalusFoeRule> Fresh;
		for (const TSharedPtr<FJsonValue>& V : *Foes)
		{
			const TSharedPtr<FJsonObject> O = V->AsObject();
			if (!O.IsValid()) continue;
			FDaedalusFoeRule F;
			F.Kind = O->GetStringField(TEXT("kind"));
			F.Title = O->GetStringField(TEXT("title"));
			F.Life = O->GetIntegerField(TEXT("life"));
			F.Power = O->GetIntegerField(TEXT("power"));
			F.Exp = O->GetIntegerField(TEXT("exp"));
			Fresh.Add(F);
		}
		if (Fresh.Num() > 0) Rules() = Fresh;
	});
	Req->ProcessRequest();
}

// ----------------------------------------------------------------------------------------------- every frame

void ADaedalusHero::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	UCharacterMovementComponent* Mv = GetCharacterMovement();

	// Islands float in the sky: remember the last ground, and fall back onto it instead of falling forever.
	if (Mv->IsMovingOnGround())
	{
		LastGround = GetActorLocation();
	}
	else if (!LastGround.IsZero() && !GetAttachParentActor() && GetActorLocation().Z < LastGround.Z - FallLimit)
	{
		Respawn();
	}

	// Vitals: the shield recharges after a quiet spell, then health.
	SinceDamaged += DeltaSeconds;
	if (Shield > MaxShield)
	{
		Shield = FMath::Max(MaxShield, Shield - 3.f * DeltaSeconds);   // overshield fades slowly
	}
	else if (SinceDamaged > ShieldDelay)
	{
		Shield = FMath::Min(MaxShield, Shield + ShieldRate * DeltaSeconds);
		if (Shield >= MaxShield) Health = FMath::Min(MaxHealth, Health + MaxHealth * 0.25f * DeltaSeconds);
	}

	// Speed: walking, sprinting, or slowed behind the shield.
	Mv->MaxWalkSpeed = bShielding ? 300.f : (bSprinting ? 950.f : 650.f);

	// The blaster cools; overheated, it vents until it's cool enough to fire again.
	FireCooldown = FMath::Max(0.f, FireCooldown - DeltaSeconds);
	Heat = FMath::Max(0.f, Heat - DeltaSeconds * (bOverheated ? 0.55f : 0.30f));
	if (bOverheated && Heat <= 0.15f) bOverheated = false;
	Spread = FMath::Max(0.f, Spread - DeltaSeconds * 3.f);
	SinceHit += DeltaSeconds;

	// Zoom: the aim button narrows the view with the blaster.
	const float WantFov = (bAiming && CurrentWeapon == 1) ? BaseFov * 0.6f : BaseFov;
	Camera->SetFieldOfView(FMath::FInterpTo(Camera->FieldOfView, WantFov, DeltaSeconds, 14.f));

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

	// The weapon arm: a sword arc, a thrust pointing down, or the blaster held level with where the camera looks.
	if (SwingLeft > 0.f)
	{
		SwingLeft = FMath::Max(0.f, SwingLeft - DeltaSeconds);
		const float T = 1.f - SwingLeft / SwingTime;
		SwordPivot->SetRelativeRotation(FRotator(bThrusting ? -90.f : FMath::Sin(T * PI) * -110.f, 0.f, 0.f));
	}
	else if (bThrusting)
	{
		SwordPivot->SetRelativeRotation(FRotator(-90.f, 0.f, 0.f));
	}
	else if (CurrentWeapon == 1 && Controller)
	{
		SwordPivot->SetRelativeRotation(FRotator(FRotator::NormalizeAxis(Controller->GetControlRotation().Pitch), 0.f, 0.f));
	}
	else
	{
		SwordPivot->SetRelativeRotation(FRotator(Sway * 0.6f, 0.f, 0.f));
	}
}

float ADaedalusHero::TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* DamageCauser)
{
	if (bInvulnerable || Damage <= 0.f || Health <= 0.f) return 0.f;
	// The sword's shield (aim with the sword) turns most of a blow from the front.
	if (bShielding && CurrentWeapon == 0 && DamageCauser)
	{
		const FVector ToCauser = (DamageCauser->GetActorLocation() - GetActorLocation()).GetSafeNormal2D();
		if (FVector::DotProduct(ToCauser, GetActorForwardVector()) > 0.3f) Damage *= 0.2f;
	}
	DamageTaken += Damage;
	SinceDamaged = 0.f;
	bHitFromSomewhere = DamageCauser != nullptr;
	if (DamageCauser) HitFrom = DamageCauser->GetActorLocation();
	const float OnShield = FMath::Min(Shield, Damage);
	Shield -= OnShield;
	Health = FMath::Max(0.f, Health - (Damage - OnShield));
	Rumble(Shield > 0.f ? 0.3f : 0.7f, 0.12f);
	if (Health <= 0.f) Fall();
	return Damage;
}

float ADaedalusHero::HitDirection() const
{
	// Relative to the camera's heading: on a Ghost the player's controller is the bike's.
	const AController* C = GetController();
	if (!C && GetWorld()) C = GetWorld()->GetFirstPlayerController();
	const float CamYaw = C ? C->GetControlRotation().Yaw : GetActorRotation().Yaw;
	const FVector To = HitFrom - GetActorLocation();
	return FMath::FindDeltaAngleDegrees(CamYaw, To.Rotation().Yaw);
}

// ----------------------------------------------------------------------------------------------- armor (ADR-047)

void ADaedalusHero::ApplyArmor()
{
	ArmorTier = FMath::Clamp(ArmorTier, 0, 3);
	const float Was = MaxShield;
	MaxShield = 100.f + 40.f * ArmorTier;
	ShieldDelay = 4.f - 0.5f * ArmorTier;
	ShieldRate = 50.f + 15.f * ArmorTier;
	if (Shield >= Was) Shield = FMath::Max(Shield, MaxShield);   // a full shield stays full at the new size
}

FString ADaedalusHero::ArmorName() const
{
	static const TCHAR* Names[] = {TEXT("RECRUIT"), TEXT("SCOUT"), TEXT("VANGUARD"), TEXT("PARAGON")};
	return Names[FMath::Clamp(ArmorTier, 0, 3)];
}

void ADaedalusHero::AddShieldCore()
{
	if (ArmorTier >= 3) { GiveOvershield(40.f); return; }   // maxed out: a core tops the shield past full instead
	++ShieldCores;
	if (ShieldCores >= 3)
	{
		ShieldCores = 0;
		++ArmorTier;
		ApplyArmor();
		Shield = MaxShield;
		Rumble(0.5f, 0.3f);
	}
	SaveProgress();
}

void ADaedalusHero::GiveOvershield(float Amount)
{
	Shield = FMath::Min(FMath::Max(Shield, MaxShield) + Amount, MaxShield * 2.f);
	SinceDamaged = 100.f;
}

void ADaedalusHero::SetArmorTier(int32 Tier)
{
	ArmorTier = Tier;
	ShieldCores = 0;
	ApplyArmor();
	Shield = MaxShield;
	SaveProgress();
}

static FString ProgressPath()
{
	return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("Config"), TEXT("DaedalusHero.json"));
}

void ADaedalusHero::LoadProgress()
{
	FString Text;
	TSharedPtr<FJsonObject> Root;
	if (FFileHelper::LoadFileToString(Text, *ProgressPath())
		&& FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Root) && Root.IsValid())
	{
		ArmorTier = Root->GetIntegerField(TEXT("armor_tier"));
		ShieldCores = Root->GetIntegerField(TEXT("shield_cores"));
		Exp = Root->GetIntegerField(TEXT("exp"));
	}
	ApplyArmor();
	Shield = MaxShield;
}

void ADaedalusHero::SaveProgress() const
{
	const FString Text = FString::Printf(TEXT("{\n  \"armor_tier\": %d,\n  \"shield_cores\": %d,\n  \"exp\": %d\n}\n"), ArmorTier, ShieldCores, Exp);
	FFileHelper::SaveStringToFile(Text, *ProgressPath());
}

FString ADaedalusHero::EncounterStats() const
{
	const UDaedalusEncounters* E = GetWorld() ? GetWorld()->GetSubsystem<UDaedalusEncounters>() : nullptr;
	return E ? E->Stats() : FString(TEXT("no encounters (editor world?)"));
}

int32 ADaedalusHero::SpawnPack()
{
	UDaedalusEncounters* E = GetWorld() ? GetWorld()->GetSubsystem<UDaedalusEncounters>() : nullptr;
	return E ? E->SpawnPack() : 0;
}

// Down: off any Ghost, back at the start (or the last ground) with full shield and health.
void ADaedalusHero::Fall()
{
	++Deaths;
	if (ADaedalusGhost* Bike = Cast<ADaedalusGhost>(GetAttachParentActor()))
	{
		Bike->Dismount();
	}
	FVector Start = LastGround;
	if (AGameModeBase* GM = GetWorld() ? GetWorld()->GetAuthGameMode() : nullptr)
	{
		if (AActor* Spot = GM->FindPlayerStart(GetController()))
		{
			Start = Spot->GetActorLocation();
		}
	}
	GetCharacterMovement()->StopMovementImmediately();
	bThrusting = false;
	SetActorLocation(Start + FVector(0.f, 0.f, 60.f), false, nullptr, ETeleportType::TeleportPhysics);
	LastGround = Start;
	Shield = MaxShield;
	Health = MaxHealth;
	SinceDamaged = 100.f;
}

void ADaedalusHero::Rumble(float Intensity, float Seconds) const
{
	if (!CVarRumble.GetValueOnGameThread()) return;
	// On a Ghost the player's controller is the bike's, so find it through the world.
	APlayerController* PC = Cast<APlayerController>(GetController());
	if (!PC && GetWorld()) PC = GetWorld()->GetFirstPlayerController();
	if (PC)
	{
		PC->PlayDynamicForceFeedback(Intensity * FMath::Clamp(CVarRumbleScale.GetValueOnGameThread(), 0.f, 1.f), Seconds,
		                             true, true, true, true);
	}
}

// -------------------------------------------------------------------------------------------- settings, menus

void ADaedalusHero::ApplySettings()
{
	const FDaedalusSettings& S = FDaedalusSettings::Get();
	S.PushCVars();
	BaseFov = S.V("FieldOfView");
	Camera->SetFieldOfView(BaseFov);
	bShieldToggle = FMath::RoundToInt(S.V("ShieldMode")) == 1;
	CameraView = FMath::Clamp(FMath::RoundToInt(S.V("CameraView")), 0, 2);
	ShoulderSide = FMath::RoundToInt(S.V("Shoulder")) == 1 ? -1.f : 1.f;
	if (Mapping && (AppliedButtonLayout != FMath::RoundToInt(S.V("ButtonLayout"))
		|| AppliedStickLayout != FMath::RoundToInt(S.V("ThumbstickLayout"))))
	{
		RebuildBindings();
	}
	for (UInputModifierDeadZone* Dz : LeftDeadzones) if (Dz) Dz->LowerThreshold = S.V("LeftDeadzone") / 100.f;
	for (UInputModifierDeadZone* Dz : RightDeadzones) if (Dz) Dz->LowerThreshold = S.V("RightDeadzone") / 100.f;
	ApplyCameraView();
}

bool ADaedalusHero::SetSetting(FName Id, float Value)
{
	if (!FDaedalusSettings::Get().Set(Id, Value)) return false;
	FDaedalusSettings::Get().Save();
	ApplySettings();
	return true;
}

float ADaedalusHero::GetSetting(FName Id) const
{
	return FDaedalusSettings::Get().V(Id);
}

void ADaedalusHero::ShowOverlay(const TSharedRef<SWidget>& Content, const TSharedRef<SWidget>& Focus, TSharedPtr<SWidget>& Host)
{
	APlayerController* PC = Cast<APlayerController>(GetController());
	if (!PC || !GEngine || !GEngine->GameViewport) return;
	Host = SNew(SWeakWidget).PossiblyNullContent(Content);
	GEngine->GameViewport->AddViewportWidgetContent(Host.ToSharedRef(), 100);
	FInputModeUIOnly Mode;
	Mode.SetWidgetToFocus(Focus);
	Mode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
	PC->SetInputMode(Mode);
	PC->bShowMouseCursor = true;
	FSlateApplication::Get().SetAllUserFocus(Focus, EFocusCause::SetDirectly);
	UGameplayStatics::SetGamePaused(this, true);
}

void ADaedalusHero::HideOverlay(TSharedPtr<SWidget>& Host)
{
	if (Host.IsValid() && GEngine && GEngine->GameViewport)
	{
		GEngine->GameViewport->RemoveViewportWidgetContent(Host.ToSharedRef());
	}
	Host.Reset();
	if (APlayerController* PC = Cast<APlayerController>(GetController()))
	{
		PC->SetInputMode(FInputModeGameOnly());
		PC->bShowMouseCursor = false;
	}
	UGameplayStatics::SetGamePaused(this, false);
}

void ADaedalusHero::ToggleSettings()
{
	if (Menu.IsValid())
	{
		Menu.Reset();
		HideOverlay(MenuHost);
		FDaedalusSettings::Get().Save();
		ApplySettings();
		return;
	}
	if (Field.IsValid()) return;
	Menu = SNew(SDaedalusSettingsMenu)
		.OnClose(FSimpleDelegate::CreateUObject(this, &ADaedalusHero::ToggleSettings))
		.OnChanged(FSimpleDelegate::CreateUObject(this, &ADaedalusHero::ApplySettings))
		.OnRespawn(FSimpleDelegate::CreateUObject(this, &ADaedalusHero::Respawn));
	ShowOverlay(Menu.ToSharedRef(), Menu.ToSharedRef(), MenuHost);
}

bool ADaedalusHero::IsSettingsOpen() const
{
	return Menu.IsValid();
}

void ADaedalusHero::ToggleField()
{
	if (Field.IsValid())
	{
		Field.Reset();
		HideOverlay(FieldHost);
		return;
	}
	if (Menu.IsValid()) return;
	Field = SNew(SDaedalusFieldMenu)
		.OnClose(FSimpleDelegate::CreateUObject(this, &ADaedalusHero::ToggleField))
		.Hero(this);
	ShowOverlay(Field.ToSharedRef(), Field.ToSharedRef(), FieldHost);
}

bool ADaedalusHero::IsFieldOpen() const
{
	return Field.IsValid();
}

FString ADaedalusHero::FieldInput(const FString& Command)
{
	if (!Field.IsValid()) return TEXT("closed");
	if (Command == TEXT("tab+")) Field->SelectTab(Field->GetTab() + 1);
	else if (Command == TEXT("tab-")) Field->SelectTab(Field->GetTab() - 1);
	return FString::Printf(TEXT("field tab %d islands %d"), Field->GetTab(), Field->MapIslands());
}

FString ADaedalusHero::MenuInput(const FString& Command)
{
	if (!Menu.IsValid()) return TEXT("closed");
	if (Command == TEXT("settings")) Menu->OpenSettings();
	else if (Command == TEXT("back")) Menu->Back();
	else if (Command == TEXT("tab+")) Menu->SelectTab(Menu->GetTab() + 1);
	else if (Command == TEXT("tab-")) Menu->SelectTab(Menu->GetTab() - 1);
	else if (Command == TEXT("up")) Menu->MoveRow(-1);
	else if (Command == TEXT("down")) Menu->MoveRow(+1);
	else if (Command == TEXT("left")) Menu->Adjust(-1);
	else if (Command == TEXT("right")) Menu->Adjust(+1);
	else if (Command == TEXT("accept")) Menu->Accept();
	else if (Command == TEXT("reset")) Menu->ResetTab();
	if (!Menu.IsValid()) return TEXT("closed");
	return Menu->InSettings() ? FString::Printf(TEXT("settings tab %d row %d"), Menu->GetTab(), Menu->GetRow()) : TEXT("pause");
}

void ADaedalusHero::EndPlay(const EEndPlayReason::Type Reason)
{
	SaveProgress();
	for (TSharedPtr<SWidget>* Host : {&MenuHost, &FieldHost, &HudHost})
	{
		if (Host->IsValid() && GEngine && GEngine->GameViewport)
		{
			GEngine->GameViewport->RemoveViewportWidgetContent(Host->ToSharedRef());
		}
		Host->Reset();
	}
	Menu.Reset();
	Field.Reset();
	Hud.Reset();
	Super::EndPlay(Reason);
}

ADaedalusGameMode::ADaedalusGameMode()
{
	DefaultPawnClass = ADaedalusHero::StaticClass();
}
