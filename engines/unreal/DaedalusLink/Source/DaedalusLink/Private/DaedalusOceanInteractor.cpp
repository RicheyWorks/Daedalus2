#include "DaedalusOceanInteractor.h"
#include "DaedalusOceanDock.h"
#include "DaedalusHero.h"
#include "GameFramework/PlayerController.h"

UDaedalusOceanInteractor::UDaedalusOceanInteractor()
{
    SetIsReplicatedByDefault(true);
}
UDaedalusOceanInteractor* UDaedalusOceanInteractor::EnsureOnHero(ADaedalusHero* Hero)
{
    if (!IsValid(Hero) || !Hero->HasAuthority() || Hero->IsTemplate() || !Hero->GetWorld()) return nullptr;
    if (auto* Existing=Hero->FindComponentByClass<UDaedalusOceanInteractor>()) return Existing;
    auto* Component=NewObject<UDaedalusOceanInteractor>(Hero);
    Hero->AddInstanceComponent(Component);Component->RegisterComponent();
    return Component;
}
void UDaedalusOceanInteractor::RequestDockUse_Implementation(ADaedalusOceanDockControl* Dock)
{
    auto* Hero=Cast<ADaedalusHero>(GetOwner());
    if (!IsValid(Hero) || !Hero->HasAuthority() || !IsValid(Dock)
        || !Dock->HasAuthority() || Dock->GetWorld()!=GetWorld() || Hero->GetWorld()!=GetWorld()) return;
    auto* Player=Cast<APlayerController>(Hero->GetController());
    if (!IsValid(Player) || !Player->HasAuthority() || Player->GetPawn()!=Hero) return;
    Dock->Use(Hero);
}
