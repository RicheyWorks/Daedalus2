// SPDX-License-Identifier: MIT

#include "SDaedalusHud.h"

#include "DaedalusHero.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SConstraintCanvas.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

namespace DaedalusHud
{
	const FLinearColor Ink(0.93f, 0.95f, 0.97f, 0.95f);
	const FLinearColor Dim(0.70f, 0.76f, 0.82f, 0.85f);
	const FLinearColor Accent(0.36f, 0.82f, 0.96f, 1.f);
	const FLinearColor Hit(1.f, 0.30f, 0.25f, 1.f);
	const FLinearColor Hot(1.f, 0.55f, 0.15f, 1.f);
	const FSlateBrush* HudWhite() { return FCoreStyle::Get().GetBrush("GenericWhiteBox"); }
	FSlateFontInfo HudFont(const char* Weight, int32 Size) { return FCoreStyle::GetDefaultFontStyle(Weight, Size); }
}

using namespace DaedalusHud;

void SDaedalusHud::Construct(const FArguments& InArgs)
{
	Hero = InArgs._Hero;
	TWeakObjectPtr<ADaedalusHero> H = Hero;

	auto ReticleColor = [H]()
	{
		const ADaedalusHero* P = H.Get();
		return FSlateColor(P && P->HitMarkerTime() < 0.15f ? Hit : Ink);
	};
	// A dot and four ticks, 36 px across; the ticks spread while firing.
	TSharedRef<SConstraintCanvas> Reticle = SNew(SConstraintCanvas);
	Reticle->AddSlot().Offset(FMargin(16.f, 16.f, 4.f, 4.f))[SNew(SImage).Image(HudWhite()).ColorAndOpacity_Lambda(ReticleColor)];
	struct FTick { float DX, DY, W, Hh; };
	const FTick Ticks[] = {{0.f, -1.f, 2.f, 8.f}, {0.f, 1.f, 2.f, 8.f}, {-1.f, 0.f, 8.f, 2.f}, {1.f, 0.f, 8.f, 2.f}};
	for (const FTick& T : Ticks)
	{
		Reticle->AddSlot()
			.Offset(TAttribute<FMargin>::CreateLambda([H, T]()
			{
				const ADaedalusHero* P = H.Get();
				const float Spread = 9.f + (P ? P->Bloom() * 10.f : 0.f);
				return FMargin(18.f + T.DX * Spread - T.W * 0.5f, 18.f + T.DY * Spread - T.Hh * 0.5f, T.W, T.Hh);
			}))
			[
				SNew(SImage).Image(HudWhite()).ColorAndOpacity_Lambda(ReticleColor)
			];
	}

	ChildSlot
	[
		SNew(SOverlay)
		.Visibility(EVisibility::HitTestInvisible)

		// Hurt: the screen edge flushes red for a moment, deeper when the shield is down.
		+ SOverlay::Slot()
		[
			SNew(SImage).Image(HudWhite())
			.ColorAndOpacity_Lambda([H]()
			{
				const ADaedalusHero* P = H.Get();
				const float T = P ? FMath::Clamp(1.f - P->SinceHurt() / 0.4f, 0.f, 1.f) : 0.f;
				const float Deep = P && P->Shield <= 0.f ? 0.28f : 0.14f;
				return FSlateColor(FLinearColor(0.9f, 0.05f, 0.03f, T * Deep));
			})
		]

		// Top centre: the energy shield (Halo's bar) and health under it
		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Top).Padding(0.f, 40.f, 0.f, 0.f)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(SBox).WidthOverride(420.f).HeightOverride(12.f)
				[
					SNew(SOverlay)
					+ SOverlay::Slot()[SNew(SImage).Image(HudWhite()).ColorAndOpacity(FLinearColor(1.f, 1.f, 1.f, 0.15f))]
					+ SOverlay::Slot().HAlign(HAlign_Center)
					[
						SNew(SBox).WidthOverride_Lambda([H]() { const ADaedalusHero* P = H.Get(); return FOptionalSize(P && P->MaxShield > 0.f ? 420.f * P->Shield / P->MaxShield : 0.f); })
						[
							SNew(SImage).Image(HudWhite())
							.ColorAndOpacity_Lambda([H]()
							{
								const ADaedalusHero* P = H.Get();
								const bool bLow = P && P->Shield < P->MaxShield * 0.25f;
								return FSlateColor(bLow ? Hot : Accent);
							})
						]
					]
				]
			]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center).Padding(0.f, 5.f, 0.f, 0.f)
			[
				SNew(SBox).WidthOverride(300.f).HeightOverride(5.f)
				[
					SNew(SOverlay)
					+ SOverlay::Slot()[SNew(SImage).Image(HudWhite()).ColorAndOpacity(FLinearColor(1.f, 1.f, 1.f, 0.12f))]
					+ SOverlay::Slot().HAlign(HAlign_Left)
					[
						SNew(SBox).WidthOverride_Lambda([H]() { const ADaedalusHero* P = H.Get(); return FOptionalSize(P && P->MaxHealth > 0.f ? 300.f * P->Health / P->MaxHealth : 0.f); })
						[
							SNew(SImage).Image(HudWhite())
							.ColorAndOpacity_Lambda([H]() { const ADaedalusHero* P = H.Get(); return FSlateColor(P && P->Health < P->MaxHealth * 0.35f ? Hit : Ink); })
						]
					]
				]
			]
		]

		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
		[
			SNew(SBox).WidthOverride(36.f).HeightOverride(36.f)
			.Visibility_Lambda([H]() { const ADaedalusHero* P = H.Get(); return P && P->ShowsReticle() ? EVisibility::HitTestInvisible : EVisibility::Collapsed; })
			[
				Reticle
			]
		]

		// Bottom right: the weapon and its heat
		+ SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Bottom).Padding(0.f, 0.f, 70.f, 60.f)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right)
			[
				SNew(STextBlock).Font(HudFont("Bold", 22)).ColorAndOpacity(Ink)
				.Text_Lambda([H]() { const ADaedalusHero* P = H.Get(); return FText::FromString(P ? P->WeaponName() : FString()); })
			]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right).Padding(0.f, 8.f, 0.f, 0.f)
			[
				SNew(SBox).WidthOverride(220.f).HeightOverride(6.f)
				.Visibility_Lambda([H]() { const ADaedalusHero* P = H.Get(); return P && P->CurrentWeapon == 1 ? EVisibility::HitTestInvisible : EVisibility::Collapsed; })
				[
					SNew(SOverlay)
					+ SOverlay::Slot()[SNew(SImage).Image(HudWhite()).ColorAndOpacity(FLinearColor(1.f, 1.f, 1.f, 0.18f))]
					+ SOverlay::Slot().HAlign(HAlign_Left)
					[
						SNew(SBox).WidthOverride_Lambda([H]() { const ADaedalusHero* P = H.Get(); return FOptionalSize(220.f * (P ? P->Heat : 0.f)); })
						[
							SNew(SImage).Image(HudWhite())
							.ColorAndOpacity_Lambda([H]() { const ADaedalusHero* P = H.Get(); return FSlateColor(P && P->bOverheated ? Hot : Accent); })
						]
					]
				]
			]
			+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right).Padding(0.f, 6.f, 0.f, 0.f)
			[
				SNew(STextBlock).Font(HudFont("Bold", 13)).ColorAndOpacity(Hot)
				.Text(FText::FromString(TEXT("OVERHEATED")))
				.Visibility_Lambda([H]() { const ADaedalusHero* P = H.Get(); return P && P->bOverheated ? EVisibility::HitTestInvisible : EVisibility::Collapsed; })
			]
		]

		// Bottom left: the view and EXP
		+ SOverlay::Slot().HAlign(HAlign_Left).VAlign(VAlign_Bottom).Padding(70.f, 0.f, 0.f, 60.f)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(STextBlock).Font(HudFont("Bold", 15)).ColorAndOpacity(Dim)
				.Text_Lambda([H]() { const ADaedalusHero* P = H.Get(); return FText::FromString(P ? P->ViewName() : FString()); })
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 4.f, 0.f, 0.f)
			[
				SNew(STextBlock).Font(HudFont("Bold", 20)).ColorAndOpacity(Accent)
				.Text_Lambda([H]() { const ADaedalusHero* P = H.Get(); return FText::FromString(P ? FString::Printf(TEXT("EXP %d"), P->Exp) : FString()); })
			]
		]
	];
}
