// SPDX-License-Identifier: MIT
#include "DaedalusMailRouteBoard.h"
#include "DaedalusMailRouteSession.h"
#include "DaedalusHero.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "ProceduralMeshComponent.h"
#include "UObject/ConstructorHelpers.h"

namespace DaedalusMailPlan
{
    FVector Point(const daedalus::parcels::Coord& Cube)
    {
        const auto Depot=daedalus::parcels::Depot().At();
        // Canonical inset only. Never convert this to an asserted scene position.
        return FVector(0.f,static_cast<double>(Cube.X-Depot.X)*0.8,static_cast<double>(Depot.Z-Cube.Z)*0.8);
    }
    struct Drawing
    {
        TArray<FVector> Vertices;
        TArray<int32> Triangles;
        TArray<FLinearColor> Colours;
        void Triangle(const FVector& A,const FVector& B,const FVector& C,const FLinearColor& Colour)
        {
            const int32 Start=Vertices.Num();
            Vertices.Add(A); Vertices.Add(B); Vertices.Add(C);
            Triangles.Add(Start); Triangles.Add(Start+1); Triangles.Add(Start+2);
            Colours.Add(Colour); Colours.Add(Colour); Colours.Add(Colour);
        }
        void Line(FVector A,FVector B,double Width,const FLinearColor& Colour,bool Arrow=false)
        {
            const FVector Direction=(B-A).GetSafeNormal();
            if (Direction.IsNearlyZero()) return;
            const FVector Side(0.f,-Direction.Z*Width,Direction.Y*Width);
            Triangle(A-Side,B-Side,B+Side,Colour); Triangle(A-Side,B+Side,A+Side,Colour);
            if (Arrow && FVector::Dist(A,B)>4.0)
            {
                const FVector Tip=(A+B)*0.5;
                const FVector Base=Tip-Direction*3.0;
                Triangle(Tip,Base+Side*3.0,Base-Side*3.0,Colour);
            }
        }
        void Mark(const FVector& P,const FLinearColor& Colour)
        {
            const FVector Y(0.f,1.8,0.f), Z(0.f,0.f,1.8);
            Triangle(P-Y-Z,P+Y-Z,P+Y+Z,Colour); Triangle(P-Y-Z,P+Y+Z,P-Y+Z,Colour);
        }
    };
}

ADaedalusMailRouteBoard::ADaedalusMailRouteBoard()
{
    PrimaryActorTick.bCanEverTick=false;
    static ConstructorHelpers::FObjectFinder<UStaticMesh> Cube(TEXT("/Engine/BasicShapes/Cube.Cube"));
    if (Cube.Succeeded()) Body->SetStaticMesh(Cube.Object);
    Body->SetRelativeScale3D(FVector(0.2f,2.5f,6.f));
    Glow->SetIntensity(0.f);
    Readout=CreateDefaultSubobject<UTextRenderComponent>(TEXT("MailReadout"));
    Readout->SetupAttachment(Body);
    Readout->SetAbsolute(false,false,true);
    Readout->SetRelativeLocation(FVector(70.f,0.f,12.f));
    Readout->SetWorldSize(8.f);
    Readout->SetHorizontalAlignment(EHTA_Center);
    Readout->SetVerticalAlignment(EVRTA_TextTop);
    Readout->SetTextRenderColor(FColor(255,240,190));
    Readout->SetText(FText::FromString(TEXT("Mail route inactive\nConnect a courier session and host adapter.")));
    StreetPlan=CreateDefaultSubobject<UProceduralMeshComponent>(TEXT("StreetPlan"));
    StreetPlan->SetupAttachment(Body);
    StreetPlan->SetAbsolute(false,false,true);
    StreetPlan->SetRelativeLocation(FVector(60.f,0.f,30.f));
    StreetPlan->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    StreetPlan->SetCastShadow(false);
    StreetPlan->SetVisibility(false);
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(TEXT("/Engine/EngineDebugMaterials/VertexColorMaterial.VertexColorMaterial"));
    PlanMaterial=Material.Object;
    for (int32 I=0;I<12;++I)
    {
        auto* Label=CreateDefaultSubobject<UTextRenderComponent>(*FString::Printf(TEXT("MailStop%d"),I));
        Label->SetupAttachment(StreetPlan);
        Label->SetWorldSize(5.f);
        Label->SetHorizontalAlignment(EHTA_Center);
        Label->SetVerticalAlignment(EVRTA_TextCenter);
        Label->SetTextRenderColor(FColor::White);
        Label->SetVisibility(false);
        StopLabels.Add(Label);
    }
}

void ADaedalusMailRouteBoard::BeginPlay()
{
    bEnding=false;
    Super::BeginPlay();
    if (!bEnding && !IsActorBeingDestroyed()) SetRouteSession(RouteSession);
}

void ADaedalusMailRouteBoard::UnbindSession()
{
    if (auto* Session=ObservedSession.Get()) Session->OnChanged.RemoveDynamic(this,&ADaedalusMailRouteBoard::SessionChanged);
    ObservedSession.Reset();
}

void ADaedalusMailRouteBoard::SetRouteSession(UDaedalusMailRouteSession* Session)
{
    if (bEnding) return;
    const uint64 Revision=++ConfigurationRevision;
    auto* Previous=ObservedSession.Get();
    UnbindSession(); RouteSession=Session;
    if (IsValid(Previous)) Previous->CancelStationRequest(this);
    if (bEnding || ConfigurationRevision!=Revision || RouteSession.Get()!=Session) return;
    if (IsValid(Session) && Session->GetWorld()==GetWorld())
    {
        ObservedSession=Session;
        Session->OnChanged.AddUniqueDynamic(this,&ADaedalusMailRouteBoard::SessionChanged);
    }
    RefreshBoard();
}

bool ADaedalusMailRouteBoard::SetPlotNumber(int32 Plot)
{
    if (bEnding) return false;
    daedalus::parcels::Stop Stop;
    if (Plot!=-1 && !daedalus::parcels::Mailbox(Plot,Stop)) return false;
    ++ConfigurationRevision; PlotNumber=Plot;
    if (auto* Session=ObservedSession.Get()) Session->CancelStationRequest(this);
    RefreshBoard();
    return true;
}

bool ADaedalusMailRouteBoard::ExpectedStationCube(FIntVector& Cube) const
{
    daedalus::parcels::Stop Stop;
    if (PlotNumber==-1) Stop=daedalus::parcels::Depot();
    else if (!daedalus::parcels::Mailbox(PlotNumber,Stop)) return false;
    const auto At=Stop.At(); Cube=FIntVector(At.X,At.Y,At.Z);
    return true;
}

FString ADaedalusMailRouteBoard::Prompt(const ADaedalusHero* Hero) const
{
    if (bEnding || !IsValid(RouteSession) || RouteSession->GetWorld()!=GetWorld()) return TEXT("Mail route inactive");
    return RouteSession->StationPrompt(Hero,PlotNumber);
}

bool ADaedalusMailRouteBoard::Use(ADaedalusHero* Hero)
{
    if (bEnding) return false;
    if (ObservedSession.Get()!=RouteSession.Get()) SetRouteSession(RouteSession);
    const bool Requested=IsValid(RouteSession) && RouteSession->RequestAction(Hero,this);
    RefreshBoard();
    return Requested;
}

void ADaedalusMailRouteBoard::SessionChanged(UDaedalusMailRouteSession* Session)
{
    if (!bEnding && Session==RouteSession.Get()) RefreshBoard();
}

void ADaedalusMailRouteBoard::RefreshBoard()
{
    if (bEnding) return;
    FIntVector Expected;
    if (!ExpectedStationCube(Expected))
    {
        Readout->SetText(FText::FromString(TEXT("Mailbox unavailable\nChoose a real plot outside the plaza.")));
        StreetPlan->SetVisibility(false);
        for (const auto& Label:StopLabels) if (IsValid(Label)) Label->SetVisibility(false);
        return;
    }
    Body->SetRelativeScale3D(PlotNumber==-1?FVector(0.2f,2.5f,6.f):FVector(0.45f,0.8f,1.f));
    const FString Text=IsValid(RouteSession) && RouteSession->GetWorld()==GetWorld()?
        RouteSession->StationText(PlotNumber):TEXT("Mail route inactive\nConnect a courier session and host adapter.");
    Readout->SetText(FText::FromString(Text));
    RefreshPlan();
}

void ADaedalusMailRouteBoard::RefreshPlan()
{
    StreetPlan->ClearAllMeshSections(); StreetPlan->SetVisibility(false);
    for (const auto& Label:StopLabels) if (IsValid(Label)) Label->SetVisibility(false);
    if (PlotNumber!=-1 || !IsValid(PlanMaterial) || !IsValid(RouteSession) || !RouteSession->HasHostBinding() ||
        !RouteSession->HasRoute() || StopLabels.Num()!=12) return;
    const auto& Route=RouteSession->ReadRoute();
    const auto& Day=Route.CurrentDay();
    if (Day.Letters.size()>11 || Day.ParOrder.size()!=Day.Letters.size()) return;
    DaedalusMailPlan::Drawing Map;
    for (int32 K=0;K<daedalus::parcels::Roads;++K)
    {
        const auto Top=daedalus::parcels::Stop{K,-146}.At(), Bottom=daedalus::parcels::Stop{K,-2}.At();
        Map.Line(DaedalusMailPlan::Point(Top),DaedalusMailPlan::Point(Bottom),0.45,FLinearColor(0.2f,0.3f,0.4f));
        const int32 Z=-146+36*K;
        Map.Line(DaedalusMailPlan::Point({-24,1,Z}),DaedalusMailPlan::Point({120,1,Z}),0.45,FLinearColor(0.2f,0.3f,0.4f));
    }
    auto At=daedalus::parcels::Depot();
    for (size_t Step=0;Step<=Day.ParOrder.size();++Step)
    {
        const auto Next=Step==Day.ParOrder.size()?daedalus::parcels::Depot():Day.Letters[static_cast<size_t>(Day.ParOrder[Step])].Mailbox;
        const auto Path=daedalus::parcels::Waypoints(At,Next);
        for (size_t I=1;I<Path.size();++I)
        {
            auto A=DaedalusMailPlan::Point(Path[I-1]), B=DaedalusMailPlan::Point(Path[I]); A.X=B.X=0.5;
            Map.Line(A,B,0.65,FLinearColor(1.f,0.65f,0.1f),true);
        }
        At=Next;
    }
    for (int32 I=0;I<=static_cast<int32>(Day.Letters.size());++I)
    {
        const bool Depot=I==0;
        const auto Location=Depot?daedalus::parcels::Depot().At():Day.Letters[static_cast<size_t>(I-1)].Mailbox.At();
        auto P=DaedalusMailPlan::Point(Location); P.X=1.f;
        const bool Done=!Depot && Route.IsDone(I-1);
        Map.Mark(P,Done?FLinearColor(0.3f,0.8f,0.4f):FLinearColor::White);
        auto* Label=StopLabels[I].Get();
        if (IsValid(Label))
        {
            Label->SetRelativeLocation(P+FVector(1.f,0.f,4.f));
            Label->SetText(FText::FromString(Depot?TEXT("H"):FString::FromInt(I)+(Done?TEXT("+"):TEXT(""))));
            Label->SetVisibility(true);
        }
    }
    StreetPlan->CreateMeshSection_LinearColor(0,Map.Vertices,Map.Triangles,TArray<FVector>(),TArray<FVector2D>(),Map.Colours,TArray<FProcMeshTangent>(),false);
    StreetPlan->SetMaterial(0,PlanMaterial); StreetPlan->SetVisibility(true);
}

void ADaedalusMailRouteBoard::EndPlay(const EEndPlayReason::Type Reason)
{
    bEnding=true; ++ConfigurationRevision;
    if (auto* Session=ObservedSession.Get()) Session->CancelStationRequest(this);
    UnbindSession();
    StreetPlan->SetVisibility(false);
    for (const auto& Label:StopLabels) if (IsValid(Label)) Label->SetVisibility(false);
    Super::EndPlay(Reason);
}
