#include "DaedalusOceanTravelComponent.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "Components/StaticMeshComponent.h"
#include "Components/BoxComponent.h"
#include "Net/UnrealNetwork.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/LocalPlayer.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "InputMappingContext.h"
#include "InputAction.h"
#include "InputModifiers.h"
#include "DaedalusOceanDock.h"
#include "EngineUtils.h"
#include "CollisionQueryParams.h"

namespace
{
std::string Utf8(const FString& Text)
{
    const FTCHARToUTF8 Converted(*Text, Text.Len());
    return std::string(Converted.Get(), Converted.Length());
}
bool Finite(const FVector& Position)
{
    return FMath::IsFinite(Position.X) && FMath::IsFinite(Position.Y)
        && FMath::IsFinite(Position.Z);
}
}

ADaedalusOceanVessel::ADaedalusOceanVessel()
{
    VesselMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("VesselMesh"));
    VesselMesh->SetMobility(EComponentMobility::Movable);
    HullCollision = CreateDefaultSubobject<UBoxComponent>(TEXT("HullCollision"));
    HullCollision->SetBoxExtent(FVector(180,80,70));
    HullCollision->SetCollisionProfileName(TEXT("Pawn"));
    SetRootComponent(HullCollision);
    VesselMesh->SetupAttachment(HullCollision);
    VesselMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    bReplicates = true;
    SetReplicateMovement(true);
    PrimaryActorTick.bCanEverTick = true;
    CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
    CameraBoom->SetupAttachment(HullCollision);
    CameraBoom->SetRelativeLocation(FVector(0,0,100));
    CameraBoom->SetRelativeRotation(FRotator(-18,0,0));
    CameraBoom->TargetArmLength=650;
    CameraBoom->ProbeSize=15;
    ChaseCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("ChaseCamera"));
    ChaseCamera->SetupAttachment(CameraBoom,USpringArmComponent::SocketName);
}

UInputComponent* ADaedalusOceanVessel::CreatePlayerInputComponent()
{
    return NewObject<UEnhancedInputComponent>(this,TEXT("HelmInput"));
}
void ADaedalusOceanVessel::BeginPlay()
{
    Super::BeginPlay();
    OnRep_HullHalfExtent();
}
void ADaedalusOceanVessel::OnRep_HullHalfExtent()
{
    if (HullCollision) HullCollision->SetBoxExtent(HullHalfExtentCm,true);
}
bool ADaedalusOceanVessel::ConfigureHull(const FVector& HalfExtentCm)
{
    if (!HasAuthority() || GetController() || !GetWorld() || !HullCollision || !Finite(HalfExtentCm)
        || HalfExtentCm.GetMin()<10 || HalfExtentCm.GetMax()>5000) return false;
    const FVector Scale=HullCollision->GetComponentScale().GetAbs();
    if (!Finite(Scale) || Scale.GetMin()<=0 || !Finite(GetActorLocation())) return false;
    const FVector WorldExtent=HalfExtentCm*Scale;
    if (!Finite(WorldExtent) || WorldExtent.GetMax()>5000) return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(OceanHullConfiguration),false,this);
    if (GetWorld()->OverlapBlockingTestByProfile(HullCollision->GetComponentLocation(),
        HullCollision->GetComponentQuat(),HullCollision->GetCollisionProfileName(),
        FCollisionShape::MakeBox(WorldExtent),Query)) return false;
    HullHalfExtentCm=HalfExtentCm;
    OnRep_HullHalfExtent();
    ForceNetUpdate();
    return true;
}
void ADaedalusOceanVessel::SetupPlayerInputComponent(UInputComponent* Input)
{
    Super::SetupPlayerInputComponent(Input);
    RemoveHelmMapping();
    auto* Player=Cast<APlayerController>(GetController());
    auto* Enhanced=Cast<UEnhancedInputComponent>(Input);
    if (!Player || !Player->GetLocalPlayer() || !Enhanced) return;
    auto* Subsystem=ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(Player->GetLocalPlayer());
    if (!Subsystem) return;
    HelmMapping=NewObject<UInputMappingContext>(this);
    auto Make=[this]() {auto* Action=NewObject<UInputAction>(this);Action->ValueType=EInputActionValueType::Axis1D;return Action;};
    ForwardAction=Make();TurnAction=Make();DiveAction=Make();
    DockAction=NewObject<UInputAction>(this);DockAction->ValueType=EInputActionValueType::Boolean;
    auto Map=[this](UInputAction* Action,FKey Key,bool Negative=false) {
        auto& Binding=HelmMapping->MapKey(Action,Key);
        if (Negative) Binding.Modifiers.Add(NewObject<UInputModifierNegate>(HelmMapping));
    };
    Map(ForwardAction,ForwardKey);Map(ForwardAction,ReverseKey,true);Map(ForwardAction,EKeys::Gamepad_LeftY);
    Map(TurnAction,RightKey);Map(TurnAction,LeftKey,true);Map(TurnAction,EKeys::Gamepad_LeftX);
    Map(DiveAction,SurfaceKey);Map(DiveAction,DiveKey,true);
    Map(DiveAction,EKeys::Gamepad_LeftTriggerAxis);Map(DiveAction,EKeys::Gamepad_RightTriggerAxis,true);
    Map(DockAction,InteractKey);Map(DockAction,EKeys::Gamepad_FaceButton_Left);
    Enhanced->BindAction(DockAction,ETriggerEvent::Started,this,&ADaedalusOceanVessel::InputDock);
    for (auto Event : {ETriggerEvent::Triggered,ETriggerEvent::Completed,ETriggerEvent::Canceled})
    {
        Enhanced->BindAction(ForwardAction,Event,this,&ADaedalusOceanVessel::InputForward);
        Enhanced->BindAction(TurnAction,Event,this,&ADaedalusOceanVessel::InputTurn);
        Enhanced->BindAction(DiveAction,Event,this,&ADaedalusOceanVessel::InputDive);
    }
    Subsystem->AddMappingContext(HelmMapping,100);
    MappingController=Player;
    bLocalSender=true;
}
void ADaedalusOceanVessel::RemoveHelmMapping()
{
    if (auto* Player=MappingController.Get();Player && Player->GetLocalPlayer() && HelmMapping)
        if (auto* Subsystem=ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(Player->GetLocalPlayer()))
            Subsystem->RemoveMappingContext(HelmMapping);
    MappingController.Reset();LocalHelm=FVector::ZeroVector;LocalAge=1;SendAge=0;bLocalSender=false;
}
void ADaedalusOceanVessel::UnPossessed() {RemoveHelmMapping();Super::UnPossessed();}
void ADaedalusOceanVessel::OnRep_Controller()
{
    if (MappingController.Get()!=GetController()) RemoveHelmMapping();
    Super::OnRep_Controller();
}
void ADaedalusOceanVessel::EndPlay(const EEndPlayReason::Type Reason) {RemoveHelmMapping();Super::EndPlay(Reason);}
bool ADaedalusOceanVessel::SetLocalHelmInput(float Forward,float Turn,float Dive)
{
    if (!IsLocallyControlled() || !FMath::IsFinite(Forward) || !FMath::IsFinite(Turn) || !FMath::IsFinite(Dive)) return false;
    LocalHelm=FVector(FMath::Clamp(Forward,-1.f,1.f),FMath::Clamp(Turn,-1.f,1.f),FMath::Clamp(Dive,-1.f,1.f));
    LocalAge=0;bLocalSender=true;return true;
}
void ADaedalusOceanVessel::InputForward(const FInputActionValue& Value) {SetLocalHelmInput(Value.Get<float>(),LocalHelm.Y,LocalHelm.Z);}
void ADaedalusOceanVessel::InputTurn(const FInputActionValue& Value) {SetLocalHelmInput(LocalHelm.X,Value.Get<float>(),LocalHelm.Z);}
void ADaedalusOceanVessel::InputDive(const FInputActionValue& Value) {SetLocalHelmInput(LocalHelm.X,LocalHelm.Y,Value.Get<float>());}
void ADaedalusOceanVessel::InputDock()
{
    if (!IsLocallyControlled()) return;
    ADaedalusOceanDockControl* Nearest=nullptr;double Best=1000000;
    for (TActorIterator<ADaedalusOceanDockControl> It(GetWorld());It;++It)
    {
        const double Distance=FVector::DistSquared(GetActorLocation(),It->GetActorLocation());
        if (FMath::IsFinite(Distance) && FMath::IsFinite(It->InteractionReachCm)
            && It->InteractionReachCm>0 && It->InteractionReachCm<=1000
            && Distance<=It->InteractionReachCm*It->InteractionReachCm && Distance<Best)
        {Nearest=*It;Best=Distance;}
    }
    if (Nearest) RequestDockExit(Nearest);
}
void ADaedalusOceanVessel::RequestDockExit_Implementation(ADaedalusOceanDockControl* Dock)
{
    if (!HasAuthority() || !IsValid(Dock) || Dock->GetWorld()!=GetWorld()) return;
    auto* Player=Cast<APlayerController>(GetController());
    if (!IsValid(Player) || !Player->HasAuthority() || Player->GetPawn()!=this) return;
    Dock->ExitVessel(this);
}

void ADaedalusOceanVessel::SetHelmInput_Implementation(float Forward, float Turn, float Dive)
{
    if (!HasAuthority() || !IsValid(GetController()) || !FMath::IsFinite(Forward)
        || !FMath::IsFinite(Turn) || !FMath::IsFinite(Dive)) return;
    Helm = FVector(FMath::Clamp(Forward,-1.0f,1.0f),FMath::Clamp(Turn,-1.0f,1.0f),
                   FMath::Clamp(Dive,-1.0f,1.0f));
    InputAge = 0;
}

void ADaedalusOceanVessel::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ADaedalusOceanVessel,VesselType);
    DOREPLIFETIME(ADaedalusOceanVessel,CurrentRealm);
    DOREPLIFETIME(ADaedalusOceanVessel,CruiseSpeedCm);
    DOREPLIFETIME(ADaedalusOceanVessel,SeaLevelCm);
    DOREPLIFETIME(ADaedalusOceanVessel,MaxDepthCm);
    DOREPLIFETIME(ADaedalusOceanVessel,HullHalfExtentCm);
}

void ADaedalusOceanVessel::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (FMath::IsFinite(DeltaSeconds) && DeltaSeconds>0 && IsLocallyControlled() && bLocalSender)
    {
        LocalAge+=DeltaSeconds;SendAge+=DeltaSeconds;
        if (LocalAge>.5f) LocalHelm=FVector::ZeroVector;
        if (SendAge>=.05f) {SetHelmInput(LocalHelm.X,LocalHelm.Y,LocalHelm.Z);SendAge=0;}
    }
    if (!HasAuthority() || !FMath::IsFinite(DeltaSeconds) || DeltaSeconds <= 0) return;
    const float Dt = FMath::Min(DeltaSeconds,0.1f);
    InputAge += DeltaSeconds;
    if (!IsValid(GetController()) || InputAge > 0.5f) Helm = FVector::ZeroVector;
    if (!FMath::IsFinite(CruiseSpeedCm) || CruiseSpeedCm <= 0 || CruiseSpeedCm > 5000
        || !FMath::IsFinite(SeaLevelCm) || !FMath::IsFinite(MaxDepthCm)
        || MaxDepthCm <= 0 || MaxDepthCm > 100000
        || (VesselType != EDaedalusOceanVessel::Boat && VesselType != EDaedalusOceanVessel::Submarine))
    {
        Helm = FVector::ZeroVector; ForwardSpeed = 0; return;
    }
    ForwardSpeed = FMath::FInterpConstantTo(ForwardSpeed,static_cast<float>(Helm.X)*CruiseSpeedCm,Dt,300);
    FRotator Rotation = GetActorRotation();
    Rotation.Pitch = 0; Rotation.Roll = 0; Rotation.Yaw += Helm.Y * 60 * Dt;
    SetActorRotation(Rotation);
    FVector Delta = GetActorForwardVector() * ForwardSpeed * Dt;
    const double TargetZ = VesselType == EDaedalusOceanVessel::Boat ? SeaLevelCm
        : FMath::Clamp(GetActorLocation().Z + Helm.Z * 250 * Dt,
                       static_cast<double>(SeaLevelCm-MaxDepthCm),static_cast<double>(SeaLevelCm));
    Delta.Z = TargetZ-GetActorLocation().Z;
    AddActorWorldOffset(Delta,true);
}

bool UDaedalusOceanTravelComponent::IsHost() const
{
    return IsValid(GetOwner()) && GetOwner()->HasAuthority() && GetWorld()
        && GetWorld()->GetNetMode() != NM_Client;
}

bool UDaedalusOceanTravelComponent::ConfigureHost(const TArray<FString>& RegisteredRealms,
    const TArray<FDaedalusOceanDock>& Docks, const TArray<FDaedalusOceanConnection>& Connections)
{
    if (!IsHost() || RegisteredRealms.Num() > 32 || Docks.Num() > 1024
        || Connections.Num() > 4096) return false;
    // A reload cannot remove or relocate the exit of a boarded passenger.
    for (const auto& Session : BoardingAvatars)
        if (Session.Key.IsValid() && Session.Value.Avatar.IsValid()) return false;
    std::vector<std::string> Realms;
    std::vector<DaedalusOceanTravel::Dock> CoreDocks;
    std::vector<DaedalusOceanTravel::DockConnection> CoreConnections;
    for (const auto& Realm : RegisteredRealms) Realms.push_back(Utf8(Realm));
    for (const auto& Dock : Docks)
    {
        if (!Finite(Dock.BoardingLocation) || !Finite(Dock.ExitLocation)
            || !FMath::IsFinite(Dock.BoardingRadiusCm)
            || Dock.BoardingRadiusCm <= 0 || Dock.BoardingRadiusCm > 10000) return false;
        if (FVector::DistSquared(Dock.ExitLocation, Dock.BoardingLocation)
            > Dock.BoardingRadiusCm * Dock.BoardingRadiusCm) return false;
        CoreDocks.push_back({Utf8(Dock.Id), Utf8(Dock.Realm), Utf8(Dock.ArrivalAnchor), Dock.bUnderwater});
    }
    for (const auto& Connection : Connections)
        CoreConnections.push_back({Utf8(Connection.DepartureId), Utf8(Connection.DestinationId),
            Connection.bBoats, Connection.bSubmarines});
    // Build both next states before publishing either one.
    DaedalusOceanTravel::DockRegistry NextRegistry;
    auto NextDocks = Docks;
    if (!NextRegistry.Configure(Realms, CoreDocks, CoreConnections)) return false;
    Registry = MoveTemp(NextRegistry);
    ActiveDocks = MoveTemp(NextDocks);
    return true;
}

bool UDaedalusOceanTravelComponent::ResolveForPlayer(AController* Player,
    ADaedalusOceanVessel* Vessel, const FString& DepartureId, const FString& DestinationId,
    FString& DestinationRealm, FString& ArrivalAnchor) const
{
    DestinationRealm.Reset();
    ArrivalAnchor.Reset();
    if (!IsHost() || !IsValid(Player) || !IsValid(Vessel) || !Player->HasAuthority()
        || !Vessel->HasAuthority() || Player->GetWorld() != GetWorld()
        || Vessel->GetWorld() != GetWorld() || Player->GetPawn() != Vessel
        || Vessel->GetController() != Player) return false;
    DaedalusOceanTravel::Vessel Kind;
    switch (Vessel->VesselType)
    {
    case EDaedalusOceanVessel::Boat: Kind = DaedalusOceanTravel::Vessel::Boat; break;
    case EDaedalusOceanVessel::Submarine: Kind = DaedalusOceanTravel::Vessel::Submarine; break;
    default: return false;
    }
    const FVector Location = Vessel->GetActorLocation();
    if (!Finite(Location)) return false;
    const auto* Dock = ActiveDocks.FindByPredicate([&](const FDaedalusOceanDock& Candidate) {
        return Candidate.Id == DepartureId;
    });
    if (!Dock || FVector::DistSquared(Location, Dock->BoardingLocation)
        > Dock->BoardingRadiusCm * Dock->BoardingRadiusCm) return false;
    FString ShoreReturnRealm;
    if (const auto* Boarding = BoardingAvatars.Find(Player);
        Boarding && Boarding->Vessel.Get() == Vessel && Boarding->Avatar.IsValid())
        ShoreReturnRealm = Boarding->DepartureRealm;
    const auto Route = Registry.Resolve(Utf8(Vessel->CurrentRealm), Utf8(DepartureId),
                                       Utf8(DestinationId), Kind, Utf8(ShoreReturnRealm));
    if (!Route.Allowed) return false;
    DestinationRealm = UTF8_TO_TCHAR(Route.DestinationRealm.c_str());
    ArrivalAnchor = UTF8_TO_TCHAR(Route.ArrivalAnchor.c_str());
    return true;
}

bool UDaedalusOceanTravelComponent::BoardAtDock(AController* Player,
    ADaedalusOceanVessel* Vessel, const FString& DockId)
{
    if (!IsHost() || !IsValid(Player) || !IsValid(Vessel) || !Player->HasAuthority()
        || !Vessel->HasAuthority() || Player->GetWorld() != GetWorld()
        || Vessel->GetWorld() != GetWorld() || Vessel->GetController()) return false;
    APawn* Avatar = Player->GetPawn();
    if (!IsValid(Avatar) || Avatar == Vessel || Avatar->GetWorld() != GetWorld()
        || !Avatar->HasAuthority() || Avatar->GetController() != Player) return false;
    // Do not replace a live boarding session with another avatar or vessel.
    if (const auto* Prior = BoardingAvatars.Find(Player); Prior && Prior->Avatar.IsValid()) return false;
    if (Vessel->VesselType != EDaedalusOceanVessel::Boat
        && Vessel->VesselType != EDaedalusOceanVessel::Submarine) return false;
    const auto* Dock = ActiveDocks.FindByPredicate([&](const FDaedalusOceanDock& Candidate) {
        return Candidate.Id == DockId;
    });
    if (!Dock || Dock->Realm != Vessel->CurrentRealm
        || (Dock->bUnderwater && Vessel->VesselType == EDaedalusOceanVessel::Boat)) return false;
    for (APawn* Pawn : {Avatar, static_cast<APawn*>(Vessel)})
    {
        const FVector Position = Pawn->GetActorLocation();
        if (!Finite(Position) || FVector::DistSquared(Position, Dock->BoardingLocation)
            > Dock->BoardingRadiusCm * Dock->BoardingRadiusCm) return false;
    }
    Player->Possess(Vessel);
    if (Player->GetPawn() != Vessel || Vessel->GetController() != Player) return false;
    const FString DepartureRealm = DaedalusOceanTravel::IsOceanRealm(Utf8(Dock->Realm)) ? FString() : Dock->Realm;
    BoardingAvatars.Add(Player, {Avatar, Vessel, Avatar->GetActorEnableCollision(), Avatar->IsHidden(), DepartureRealm});
    Avatar->SetActorEnableCollision(false);
    Avatar->SetActorHiddenInGame(true);
    return true;
}

bool UDaedalusOceanTravelComponent::DisembarkAtDock(AController* Player,
    ADaedalusOceanVessel* Vessel, const FString& DockId)
{
    if (!IsHost() || !IsValid(Player) || !IsValid(Vessel) || !Player->HasAuthority()
        || !Vessel->HasAuthority() || Player->GetWorld() != GetWorld()
        || Vessel->GetWorld() != GetWorld() || Player->GetPawn() != Vessel
        || Vessel->GetController() != Player) return false;
    const auto* Original = BoardingAvatars.Find(Player);
    if (!Original || Original->Vessel.Get() != Vessel) return false;
    APawn* Avatar = Original ? Original->Avatar.Get() : nullptr;
    if (!IsValid(Avatar) || Avatar == Vessel || !Avatar->HasAuthority()
        || Avatar->GetWorld() != GetWorld() || Avatar->GetController()) return false;
    const auto* Dock = ActiveDocks.FindByPredicate([&](const FDaedalusOceanDock& Candidate) {
        return Candidate.Id == DockId;
    });
    const FVector Position = Vessel->GetActorLocation();
    if (!Dock || Dock->Realm != Vessel->CurrentRealm || !Finite(Position)
        || FVector::DistSquared(Position, Dock->BoardingLocation)
            > Dock->BoardingRadiusCm * Dock->BoardingRadiusCm) return false;
    // Collision-aware teleport refuses an obstructed exit before possession changes.
    Avatar->SetActorEnableCollision(Original->bCollision);
    if (!Avatar->TeleportTo(Dock->ExitLocation, Avatar->GetActorRotation(), false, false))
    {
        Avatar->SetActorEnableCollision(false);
        return false;
    }
    Player->Possess(Avatar);
    if (Player->GetPawn() != Avatar || Avatar->GetController() != Player)
    {
        Avatar->SetActorEnableCollision(false);
        return false;
    }
    Avatar->SetActorHiddenInGame(Original->bHidden);
    BoardingAvatars.Remove(Player);
    return true;
}
