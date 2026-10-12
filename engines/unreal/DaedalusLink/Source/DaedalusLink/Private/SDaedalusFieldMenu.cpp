// SPDX-License-Identifier: MIT

#include "SDaedalusFieldMenu.h"

#include "DaedalusHero.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SConstraintCanvas.h"
#include "Widgets/Layout/SWidgetSwitcher.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

namespace DaedalusField
{
	const FLinearColor Ink(0.93f, 0.95f, 0.97f, 1.f);
	const FLinearColor Dim(0.58f, 0.64f, 0.71f, 1.f);
	const FLinearColor Accent(0.36f, 0.82f, 0.96f, 1.f);
	const FLinearColor Glass(0.015f, 0.03f, 0.055f, 0.88f);
	const FLinearColor Panel(1.f, 1.f, 1.f, 0.035f);
	const FLinearColor Land(0.42f, 0.72f, 0.40f, 0.85f);
	const FLinearColor Clear(0.f, 0.f, 0.f, 0.f);
	const TCHAR* const TabNames[] = {TEXT("MAP"), TEXT("HERO"), TEXT("CONTROLS"), TEXT("SOCIAL")};
	constexpr int32 TabCount = 4;

	const FSlateBrush* FieldWhite() { return FCoreStyle::Get().GetBrush("GenericWhiteBox"); }
	FSlateFontInfo FieldFont(const char* Weight, int32 Size) { return FCoreStyle::GetDefaultFontStyle(Weight, Size); }

	TSharedRef<SWidget> Line(const FString& Left, const FString& Right, bool bHead = false)
	{
		return SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().FillWidth(0.45f).Padding(0.f, 7.f)
			[
				SNew(STextBlock).Text(FText::FromString(Left)).Font(FieldFont(bHead ? "Bold" : "Regular", bHead ? 15 : 19))
				.ColorAndOpacity(bHead ? Dim : Ink)
			]
			+ SHorizontalBox::Slot().FillWidth(0.55f).Padding(0.f, 7.f)
			[
				SNew(STextBlock).Text(FText::FromString(Right)).Font(FieldFont(bHead ? "Bold" : "Bold", bHead ? 15 : 19))
				.ColorAndOpacity(bHead ? Dim : Accent)
			];
	}
}

using namespace DaedalusField;

void SDaedalusFieldMenu::Construct(const FArguments& InArgs)
{
	OnClose = InArgs._OnClose;
	Hero = InArgs._Hero;

	// The map's land: every chunk of the Daedalus world, seen from above.
	Bounds = FBox2D(ForceInit);
	if (const ADaedalusHero* H = Hero.Get())
	{
		for (TActorIterator<AStaticMeshActor> It(H->GetWorld()); It; ++It)
		{
#if WITH_EDITOR
			const bool bChunk = It->GetActorLabel().StartsWith(TEXT("chunk_"));
#else
			const bool bChunk = It->GetName().Contains(TEXT("chunk_"));
#endif
			if (!bChunk) continue;
			const FBox B = It->GetComponentsBoundingBox();
			if (!B.IsValid) continue;
			Islands.Add(FBox2D(FVector2D(B.Min.X, B.Min.Y), FVector2D(B.Max.X, B.Max.Y)));
			Bounds += Islands.Last();
		}
		Bounds += FVector2D(H->GetActorLocation().X, H->GetActorLocation().Y);
		Bounds = Bounds.ExpandBy(Bounds.GetExtent().GetMax() * 0.08f);
	}

	TSharedRef<SHorizontalBox> Ribbon = SNew(SHorizontalBox);
	auto Pill = [](const TCHAR* Label)
	{
		return SNew(SBorder).BorderImage(FieldWhite()).BorderBackgroundColor(FLinearColor(1.f, 1.f, 1.f, 0.10f)).Padding(FMargin(10.f, 4.f))
			[SNew(STextBlock).Text(FText::FromString(Label)).Font(FieldFont("Bold", 13)).ColorAndOpacity(Dim)];
	};
	Ribbon->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(0.f, 0.f, 26.f, 0.f)[Pill(TEXT("LB"))];
	for (int32 i = 0; i < TabCount; ++i)
	{
		Ribbon->AddSlot().AutoWidth().Padding(0.f, 0.f, 34.f, 0.f)
		[
			SNew(SBorder).BorderImage(FieldWhite()).BorderBackgroundColor(Clear).Padding(0.f)
			.OnMouseButtonDown_Lambda([this, i](const FGeometry&, const FPointerEvent&) { SelectTab(i); return FReply::Handled(); })
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)
				[
					SNew(STextBlock).Text(FText::FromString(TabNames[i])).Font(FieldFont("Bold", 19))
					.ColorAndOpacity_Lambda([this, i]() { return FSlateColor(i == Tab ? Ink : Dim); })
				]
				+ SVerticalBox::Slot().AutoHeight()
				[
					SNew(SBox).HeightOverride(3.f)
					[
						SNew(SImage).Image(FieldWhite()).ColorAndOpacity_Lambda([this, i]() { return FSlateColor(i == Tab ? Accent : Clear); })
					]
				]
			]
		];
	}
	Ribbon->AddSlot().AutoWidth().VAlign(VAlign_Center)[Pill(TEXT("RB"))];

	ChildSlot
	[
		SNew(SBorder).BorderImage(FieldWhite()).BorderBackgroundColor(Glass).Padding(FMargin(90.f, 48.f))
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(STextBlock).Text(FText::FromString(TEXT("FIELD"))).Font(FieldFont("Bold", 34)).ColorAndOpacity(Ink)
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 22.f, 0.f, 0.f)[Ribbon]
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(SBox).HeightOverride(1.f)[SNew(SImage).Image(FieldWhite()).ColorAndOpacity(FLinearColor(1.f, 1.f, 1.f, 0.15f))]
			]
			+ SVerticalBox::Slot().FillHeight(1.f).Padding(0.f, 24.f, 0.f, 18.f)
			[
				SNew(SWidgetSwitcher).WidgetIndex_Lambda([this]() { return Tab; })
				+ SWidgetSwitcher::Slot()[BuildMap()]
				+ SWidgetSwitcher::Slot()[BuildHero()]
				+ SWidgetSwitcher::Slot()[BuildControls()]
				+ SWidgetSwitcher::Slot()[BuildSocial()]
			]
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(STextBlock).Font(FieldFont("Bold", 15)).ColorAndOpacity(Dim)
				.Text(FText::FromString(TEXT("[LB] [RB] Tabs      [B] Back          Keyboard: Q E tabs, Tab / M / Backspace to close")))
			]
		]
	];
}

FVector2D SDaedalusFieldMenu::ToMap(const FVector& World) const
{
	const FVector2D Size = Bounds.GetSize();
	const float Span = FMath::Max(Size.X, Size.Y);
	if (Span <= 0.f) return FVector2D(MapSize * 0.5f);
	// North (+X in Unreal) is up on the map; east (+Y) is right.
	return FVector2D((World.Y - Bounds.Min.Y) / Span * MapSize, (1.f - (World.X - Bounds.Min.X) / Span) * MapSize);
}

TSharedRef<SWidget> SDaedalusFieldMenu::BuildMap()
{
	TSharedRef<SConstraintCanvas> Canvas = SNew(SConstraintCanvas);
	for (const FBox2D& I : Islands)
	{
		const FVector2D A = ToMap(FVector(I.Max.X, I.Min.Y, 0.f));
		const FVector2D B = ToMap(FVector(I.Min.X, I.Max.Y, 0.f));
		Canvas->AddSlot().Offset(FMargin(A.X, A.Y, FMath::Max(2.f, B.X - A.X), FMath::Max(2.f, B.Y - A.Y)))
		[
			SNew(SImage).Image(FieldWhite()).ColorAndOpacity(Land)
		];
	}
	// The hero: a marker at his position that points the way he faces.
	Canvas->AddSlot()
		.Offset(TAttribute<FMargin>::CreateLambda([this]()
		{
			const ADaedalusHero* H = Hero.Get();
			const FVector2D P = H ? ToMap(H->GetActorLocation()) : FVector2D(MapSize * 0.5f);
			return FMargin(P.X - 14.f, P.Y - 14.f, 28.f, 28.f);
		}))
		[
			SNew(STextBlock).Text(FText::FromString(TEXT("▲"))).Font(FieldFont("Bold", 20)).ColorAndOpacity(Accent)
			.Justification(ETextJustify::Center)
			.RenderTransformPivot(FVector2D(0.5f, 0.5f))
			.RenderTransform_Lambda([this]()
			{
				const ADaedalusHero* H = Hero.Get();
				return TOptional<FSlateRenderTransform>(FSlateRenderTransform(FQuat2D(FMath::DegreesToRadians(H ? H->GetActorRotation().Yaw : 0.f))));
			})
		];

	return SNew(SHorizontalBox)
		+ SHorizontalBox::Slot().AutoWidth()
		[
			SNew(SBorder).BorderImage(FieldWhite()).BorderBackgroundColor(Panel).Padding(16.f)
			[
				SNew(SBox).WidthOverride(MapSize).HeightOverride(MapSize)[Canvas]
			]
		]
		+ SHorizontalBox::Slot().FillWidth(1.f).Padding(36.f, 0.f, 0.f, 0.f)
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()[Line(TEXT("TACMAP"), TEXT(""), true)]
			+ SVerticalBox::Slot().AutoHeight()[Line(TEXT("Islands"), FString::FromInt(Islands.Num()) + TEXT(" chunks"))]
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(STextBlock).Font(FieldFont("Regular", 17)).ColorAndOpacity(Dim).AutoWrapText(true)
				.Text(FText::FromString(TEXT("North is up. The marker is you, pointing the way you face. Land is every island of this world.")))
			]
		];
}

TSharedRef<SWidget> SDaedalusFieldMenu::BuildHero()
{
	auto Stat = [this](const TCHAR* Label, TFunction<FString(const ADaedalusHero&)> Get)
	{
		return SNew(SHorizontalBox)
			+ SHorizontalBox::Slot().FillWidth(0.45f).Padding(0.f, 8.f)
			[
				SNew(STextBlock).Text(FText::FromString(Label)).Font(FieldFont("Regular", 20)).ColorAndOpacity(Ink)
			]
			+ SHorizontalBox::Slot().FillWidth(0.55f).Padding(0.f, 8.f)
			[
				SNew(STextBlock).Font(FieldFont("Bold", 20)).ColorAndOpacity(Accent)
				.Text_Lambda([this, Get]() { const ADaedalusHero* H = Hero.Get(); return FText::FromString(H ? Get(*H) : FString(TEXT("-"))); })
			];
	};
	return SNew(SBorder).BorderImage(FieldWhite()).BorderBackgroundColor(Panel).Padding(FMargin(28.f, 22.f))
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()[Line(TEXT("RECORD"), TEXT(""), true)]
			+ SVerticalBox::Slot().AutoHeight()[Stat(TEXT("Sword swings"), [](const ADaedalusHero& H) { return FString::FromInt(H.Swings); })]
			+ SVerticalBox::Slot().AutoHeight()[Stat(TEXT("Down-thrust bounces"), [](const ADaedalusHero& H) { return FString::FromInt(H.Bounces); })]
			+ SVerticalBox::Slot().AutoHeight()[Stat(TEXT("Falls caught (respawns)"), [](const ADaedalusHero& H) { return FString::FromInt(H.Respawns); })]
			+ SVerticalBox::Slot().AutoHeight()[Stat(TEXT("Shield"), [](const ADaedalusHero& H) { return FString(H.bShielding ? TEXT("UP") : TEXT("DOWN")); })]
			+ SVerticalBox::Slot().AutoHeight()[Stat(TEXT("Last ground"), [](const ADaedalusHero& H)
			{
				return FString::Printf(TEXT("%.0f, %.0f, %.0f"), H.LastGround.X, H.LastGround.Y, H.LastGround.Z);
			})]
		];
}

TSharedRef<SWidget> SDaedalusFieldMenu::BuildControls()
{
	return SNew(SBorder).BorderImage(FieldWhite()).BorderBackgroundColor(Panel).Padding(FMargin(28.f, 22.f))
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()[Line(TEXT("ACTION"), TEXT("CONTROLLER  /  KEYBOARD & MOUSE"), true)]
			+ SVerticalBox::Slot().AutoHeight()[Line(TEXT("Move"), TEXT("Left stick, D-pad  /  WASD"))]
			+ SVerticalBox::Slot().AutoHeight()[Line(TEXT("Look"), TEXT("Right stick  /  Mouse"))]
			+ SVerticalBox::Slot().AutoHeight()[Line(TEXT("Jump"), TEXT("A  /  Space"))]
			+ SVerticalBox::Slot().AutoHeight()[Line(TEXT("Sword (down-thrust in the air)"), TEXT("X, RT  /  Left mouse, J"))]
			+ SVerticalBox::Slot().AutoHeight()[Line(TEXT("Dash"), TEXT("B, RB  /  Shift"))]
			+ SVerticalBox::Slot().AutoHeight()[Line(TEXT("Shield"), TEXT("LT, LB  /  Right mouse, K"))]
			+ SVerticalBox::Slot().AutoHeight()[Line(TEXT("Game Menu (pause, settings)"), TEXT("Menu  /  F1"))]
			+ SVerticalBox::Slot().AutoHeight()[Line(TEXT("Field Menu (map, hero)"), TEXT("View  /  Tab, M"))]
		];
}

TSharedRef<SWidget> SDaedalusFieldMenu::BuildSocial()
{
	return SNew(SBorder).BorderImage(FieldWhite()).BorderBackgroundColor(Panel).Padding(FMargin(28.f, 22.f))
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight()[Line(TEXT("FRIENDS & PARTY"), TEXT(""), true)]
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(STextBlock).Font(FieldFont("Regular", 18)).ColorAndOpacity(Dim).AutoWrapText(true)
				.Text(FText::FromString(TEXT("Friends, your party and team voice arrive with online play. This tab will list who's "
				                             "online, who's in your party, and their voice status.")))
			]
		];
}

void SDaedalusFieldMenu::SelectTab(int32 NewTab)
{
	Tab = (NewTab % TabCount + TabCount) % TabCount;
}

FReply SDaedalusFieldMenu::OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
	const FKey K = Event.GetKey();
	if (K == EKeys::Gamepad_LeftShoulder || K == EKeys::Q) { SelectTab(Tab - 1); return FReply::Handled(); }
	if (K == EKeys::Gamepad_RightShoulder || K == EKeys::E) { SelectTab(Tab + 1); return FReply::Handled(); }
	if (K == EKeys::Gamepad_FaceButton_Right || K == EKeys::Gamepad_Special_Left || K == EKeys::Tab || K == EKeys::M
		|| K == EKeys::BackSpace)
	{
		OnClose.ExecuteIfBound();
		return FReply::Handled();
	}
	return FReply::Unhandled();
}

FNavigationReply SDaedalusFieldMenu::OnNavigation(const FGeometry& Geometry, const FNavigationEvent& Event)
{
	if (Event.GetNavigationType() == EUINavigation::Left) { SelectTab(Tab - 1); return FNavigationReply::Stop(); }
	if (Event.GetNavigationType() == EUINavigation::Right) { SelectTab(Tab + 1); return FNavigationReply::Stop(); }
	return FNavigationReply::Stop();
}
