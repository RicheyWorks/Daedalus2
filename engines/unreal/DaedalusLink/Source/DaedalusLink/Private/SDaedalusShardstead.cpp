// SPDX-License-Identifier: MIT
#include "SDaedalusShardstead.h"
#include "DaedalusInventoryCore.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"
namespace {
    const TCHAR* Names[]={TEXT("Food"),TEXT("Energy"),TEXT("Iron"),TEXT("Copper"),TEXT("Crystals"),TEXT("Stone")};
    const TCHAR* Groups[]={TEXT("SUSTENANCE"),TEXT("POWER"),TEXT("METAL"),TEXT("METAL"),TEXT("PRECIOUS"),TEXT("BUILDING")};
    FLinearColor Tint(uint32 V){return FLinearColor::FromSRGBColor(FColor((V>>16)&255,(V>>8)&255,V&255));}
    FSlateFontInfo Font(int32 Size,bool Bold=false){return FCoreStyle::GetDefaultFontStyle(Bold?"Bold":"Regular",Size);}
    const FSlateBrush* Brush(){return FCoreStyle::Get().GetBrush("GenericWhiteBox");}
}
void SDaedalusShardstead::Construct(const FArguments& Args){
    ThemeName=Args._ThemeName.IsEmpty()?TEXT("zero"):Args._ThemeName;
    ChildSlot[SNew(SScrollBox)+SScrollBox::Slot()[SAssignNew(Body,SVerticalBox)]];Rebuild();
}
void SDaedalusShardstead::Refresh(const FDaedalusIslandStats& In,const TArray<FDaedalusIslandClaimRow>& Rows){
    Stats=In;
    // A partial DTO is unknown, not a zero balance. Never present stale claims
    // beside an unavailable crew record after a disconnect or realm switch.
    Stats.Available=In.Available&&In.Cargo.Num()==6;
    for(int32 Quantity:In.Cargo)if(Quantity<0)Stats.Available=false;
    if(Stats.Available)Claims=Rows;else Claims.Reset();
    if(Stats.ProjectedNet.Num()!=6)Stats.ProjectedNet.Reset();
    Rebuild();
}
bool SDaedalusShardstead::RefreshFromHost(const UDaedalusShardsteadComponent* Source,const FString& CrewKey){
    if(!IsInGameThread())return false;
    FDaedalusIslandStats Record;
    TArray<FDaedalusIslandClaimRow> Rows;
    if(IsValid(Source)&&!CrewKey.IsEmpty()){
        Record=Source->GetCrewStats(CrewKey);
        if(Record.Available)Rows=Source->GetClaimRows(CrewKey);
    }
    Refresh(Record,Rows);
    return Stats.Available;
}
TSharedRef<SWidget> SDaedalusShardstead::Card(int32 Resource) const {
    const auto& Theme=daedalus::inv::ThemeNamed(TCHAR_TO_UTF8(*ThemeName));
    int32 Quantity=Stats.Cargo.IsValidIndex(Resource)?Stats.Cargo[Resource]:0;
    bool Forecast=Stats.Available&&Stats.ProjectedNet.IsValidIndex(Resource);int32 Net=Forecast?Stats.ProjectedNet[Resource]:0;
    bool Shortage=Stats.Available&&Resource<2&&Quantity==0;
    FString Rate=Forecast?FString::Printf(TEXT("%s%s next cycle"),Net>0?TEXT("+"):TEXT(""),*FText::AsNumber(Net).ToString()):TEXT("Forecast unavailable");
    return SNew(SBorder).BorderImage(Brush()).BorderBackgroundColor(Tint(Theme.Panel)).Padding(18)
    [SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(Groups[Resource])).Font(Font(11,true)).ColorAndOpacity(Tint(Theme.Dim))]
        +SVerticalBox::Slot().AutoHeight().Padding(0,6)[SNew(STextBlock).Text(FText::FromString(Names[Resource])).Font(Font(21,true)).ColorAndOpacity(Tint(Theme.Text))]
        +SVerticalBox::Slot().AutoHeight()[SNew(STextBlock).Text(Stats.Available?FText::AsNumber(Quantity):FText::FromString(TEXT("--"))).Font(Font(38,true)).ColorAndOpacity(Tint(Shortage?Theme.Hot:Theme.Focus))]
        +SVerticalBox::Slot().AutoHeight().Padding(0,6)[SNew(STextBlock).Text(FText::FromString(Shortage?TEXT("SHORTAGE — assign a producer"):Rate)).Font(Font(13)).ColorAndOpacity(Tint(Shortage?Theme.Hot:Theme.Dim))]
    ];
}
void SDaedalusShardstead::Rebuild(){
    if(!Body.IsValid())return;Body->ClearChildren();
    const auto& Theme=daedalus::inv::ThemeNamed(TCHAR_TO_UTF8(*ThemeName));
    Body->AddSlot().AutoHeight().Padding(12)[SNew(STextBlock).Text(FText::FromString(TEXT("SHARDSTEAD  /  PRODUCTION"))).Font(Font(27,true)).ColorAndOpacity(Tint(Theme.Text))];
    FString Summary=Stats.Available?FString::Printf(TEXT("Cycle %lld  •  %d claims  •  Friendship %d  •  Infamy %d"),static_cast<long long>(Stats.Cycle),Claims.Num(),Stats.Friendship,Stats.Infamy):TEXT("Waiting for the host's production record");
    Body->AddSlot().AutoHeight().Padding(12,0,12,12)[SNew(STextBlock).Text(FText::FromString(Summary)).Font(Font(15)).ColorAndOpacity(Tint(Theme.Dim))];
    for(int32 Row=0;Row<2;++Row){TSharedRef<SHorizontalBox> Cards=SNew(SHorizontalBox);
        for(int32 Col=0;Col<3;++Col)Cards->AddSlot().FillWidth(1).Padding(6)[Card(Row*3+Col)];
        Body->AddSlot().AutoHeight().Padding(6)[Cards];}
    Body->AddSlot().AutoHeight().Padding(12,18,12,8)[SNew(STextBlock).Text(FText::FromString(TEXT("ISLAND CLAIMS  —  Worker / task / deposit"))).Font(Font(19,true)).ColorAndOpacity(Tint(Theme.Text))];
    if(Claims.IsEmpty())Body->AddSlot().AutoHeight().Padding(12)[SNew(STextBlock).Text(FText::FromString(Stats.Available?TEXT("Talk to a Twaker, survey an island, then stake a permitted claim."):TEXT("Claim records unavailable — waiting for the host."))).Font(Font(15)).AutoWrapText(true).ColorAndOpacity(Tint(Theme.Dim))];
    for(const auto& Row:Claims){int32 K=static_cast<int32>(Row.Task);if(K<0||K>=6)continue;
        FString Deposit=K<2?TEXT("Renewable habitat"):FString::Printf(TEXT("%s left"),*FText::AsNumber(Row.Remaining).ToString());
        FString Worker=Row.Working?Row.WorkerId:TEXT("Unassigned");
        Body->AddSlot().AutoHeight().Padding(12,3)
        [SNew(SBorder).BorderImage(Brush()).BorderBackgroundColor(Tint(Theme.Panel)).Padding(12)
            [SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1)[SNew(STextBlock).Text(FText::FromString(FString::Printf(TEXT("Island %d"),Row.Island))).Font(Font(15,true)).ColorAndOpacity(Tint(Theme.Text))]
                +SHorizontalBox::Slot().FillWidth(2)[SNew(STextBlock).Text(FText::FromString(Worker)).AutoWrapText(true).Font(Font(14)).ColorAndOpacity(Tint(Row.Working?Theme.Focus:Theme.Hot))]
                +SHorizontalBox::Slot().FillWidth(1)[SNew(STextBlock).Text(FText::FromString(Names[K])).Font(Font(14)).ColorAndOpacity(Tint(Theme.Text))]
                +SHorizontalBox::Slot().FillWidth(2)[SNew(STextBlock).Text(FText::FromString(Deposit)).Font(Font(14)).ColorAndOpacity(Tint(Theme.Dim))]
            ]];
    }
    Body->AddSlot().AutoHeight().Padding(12)[SNew(STextBlock).Text(FText::FromString(TEXT("Quantities are carried units. Forecast is net of food and energy costs; conditions can change before the next cycle."))).Font(Font(12)).AutoWrapText(true).ColorAndOpacity(Tint(Theme.Dim))];
}
