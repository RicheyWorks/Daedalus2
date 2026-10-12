// SPDX-License-Identifier: MIT

#include "SDaedalusSettingsMenu.h"

#include "DaedalusSettings.h"
#include "Framework/Application/SlateApplication.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SWidgetSwitcher.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

namespace DaedalusMenu
{
	// Halo Infinite's settings feel: deep blue-black glass, white type, a cool cyan accent on what's selected.
	const FLinearColor Ink(0.93f, 0.95f, 0.97f, 1.f);
	const FLinearColor Dim(0.58f, 0.64f, 0.71f, 1.f);
	const FLinearColor Accent(0.36f, 0.82f, 0.96f, 1.f);
	const FLinearColor Glass(0.015f, 0.03f, 0.055f, 0.90f);
	const FLinearColor RowIdle(1.f, 1.f, 1.f, 0.035f);
	const FLinearColor RowHot(1.f, 1.f, 1.f, 0.14f);
	const FLinearColor Track(1.f, 1.f, 1.f, 0.18f);
	const FLinearColor Clear(0.f, 0.f, 0.f, 0.f);

	const FSlateBrush* White() { return FCoreStyle::Get().GetBrush("GenericWhiteBox"); }
	FSlateFontInfo Font(const char* Weight, int32 Size) { return FCoreStyle::GetDefaultFontStyle(Weight, Size); }

	FDaedalusSetting& At(int32 Index) { return FDaedalusSettings::Get().All[Index]; }
}

using namespace DaedalusMenu;

void SDaedalusSettingsMenu::Construct(const FArguments& InArgs)
{
	OnClose = InArgs._OnClose;
	OnChanged = InArgs._OnChanged;
	OnRespawn = InArgs._OnRespawn;

	// The pause page: just the choices, like Halo Infinite's pause menu. Settings live one step in.
	static const TCHAR* PauseItems[] = {TEXT("RESUME"), TEXT("SETTINGS"), TEXT("RESPAWN")};
	TSharedRef<SVerticalBox> PauseList = SNew(SVerticalBox);
	for (int32 i = 0; i < 3; ++i)
	{
		PauseList->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
		[
			SNew(SBox).WidthOverride(460.f)
			[
				SNew(SBorder)
				.BorderImage(White())
				.BorderBackgroundColor_Lambda([this, i]() { return FSlateColor(i == PauseRow ? RowHot : RowIdle); })
				.Padding(0.f)
				.OnMouseButtonDown_Lambda([this, i](const FGeometry&, const FPointerEvent&) { PauseRow = i; PauseSelect(); return FReply::Handled(); })
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().AutoWidth()
					[
						SNew(SBox).WidthOverride(4.f)
						[
							SNew(SImage).Image(White()).ColorAndOpacity_Lambda([this, i]() { return FSlateColor(i == PauseRow ? Accent : Clear); })
						]
					]
					+ SHorizontalBox::Slot().FillWidth(1.f).Padding(22.f, 16.f)
					[
						SNew(STextBlock).Text(FText::FromString(PauseItems[i])).Font(Font("Bold", 22))
						.ColorAndOpacity_Lambda([this, i]() { return FSlateColor(i == PauseRow ? Ink : Dim); })
					]
				]
			]
		];
	}

	ChildSlot
	[
		SNew(SWidgetSwitcher)
		.WidgetIndex_Lambda([this]() { return bInSettings ? 1 : 0; })

		+ SWidgetSwitcher::Slot()
		[
			SNew(SBorder)
			.BorderImage(White())
			.BorderBackgroundColor(FLinearColor(0.015f, 0.03f, 0.055f, 0.72f))
			.Padding(FMargin(110.f, 90.f))
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 28.f)
				[
					SNew(STextBlock).Text(FText::FromString(TEXT("PAUSED"))).Font(Font("Bold", 34)).ColorAndOpacity(Ink)
				]
				+ SVerticalBox::Slot().AutoHeight()[PauseList]
				+ SVerticalBox::Slot().FillHeight(1.f)
				+ SVerticalBox::Slot().AutoHeight()
				[
					SNew(STextBlock).Font(Font("Bold", 15)).ColorAndOpacity(Dim)
					.Text(FText::FromString(TEXT("[A] Select      [B] Resume")))
				]
			]
		]

		+ SWidgetSwitcher::Slot()
		[
		SNew(SBorder)
		.BorderImage(White())
		.BorderBackgroundColor(Glass)
		.Padding(FMargin(90.f, 48.f))
		[
			SNew(SVerticalBox)

			// Title
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
				[
					SNew(STextBlock).Text(FText::FromString(TEXT("SETTINGS"))).Font(Font("Bold", 34)).ColorAndOpacity(Ink)
				]
				+ SHorizontalBox::Slot().FillWidth(1.f)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
				[
					SNew(STextBlock).Text(FText::FromString(TEXT("DAEDALUS"))).Font(Font("Bold", 16)).ColorAndOpacity(Dim)
				]
			]

			// Tab ribbon
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 22.f, 0.f, 0.f)
			[
				SAssignNew(TabBar, SHorizontalBox)
			]
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(SBox).HeightOverride(1.f)
				[
					SNew(SImage).Image(White()).ColorAndOpacity(FLinearColor(1.f, 1.f, 1.f, 0.15f))
				]
			]

			// Rows on the left, the selected row explained on the right
			+ SVerticalBox::Slot().FillHeight(1.f).Padding(0.f, 22.f, 0.f, 18.f)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().FillWidth(0.62f)
				[
					SAssignNew(Scroll, SScrollBox)
					+ SScrollBox::Slot()
					[
						SAssignNew(List, SVerticalBox)
					]
				]
				+ SHorizontalBox::Slot().FillWidth(0.38f).Padding(36.f, 0.f, 0.f, 0.f)
				[
					SNew(SBorder)
					.BorderImage(White())
					.BorderBackgroundColor(RowIdle)
					.Padding(FMargin(28.f, 24.f))
					[
						SNew(SVerticalBox)
						+ SVerticalBox::Slot().AutoHeight()
						[
							SNew(STextBlock)
							.Font(Font("Bold", 24)).ColorAndOpacity(Ink).AutoWrapText(true)
							.Text_Lambda([this]() { const int32 I = SettingIndex(); return FText::FromString(I >= 0 ? At(I).Label : FString()); })
						]
						+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 6.f, 0.f, 16.f)
						[
							SNew(SBox).HeightOverride(3.f).WidthOverride(48.f).HAlign(HAlign_Left)
							[
								SNew(SImage).Image(White()).ColorAndOpacity(Accent)
							]
						]
						+ SVerticalBox::Slot().AutoHeight()
						[
							SNew(STextBlock)
							.Font(Font("Regular", 17)).ColorAndOpacity(Dim).AutoWrapText(true)
							.Text_Lambda([this]() { const int32 I = SettingIndex(); return FText::FromString(I >= 0 ? At(I).Help : FString()); })
						]
						+ SVerticalBox::Slot().FillHeight(1.f)
						+ SVerticalBox::Slot().AutoHeight()
						[
							SNew(STextBlock)
							.Font(Font("Regular", 14)).ColorAndOpacity(Dim)
							.Text_Lambda([this]()
							{
								const int32 I = SettingIndex();
								if (I < 0) return FText::GetEmpty();
								FDaedalusSetting Def = At(I);
								Def.Value = Def.Default;
								return FText::FromString(FString::Printf(TEXT("DEFAULT  %s"), *Def.Format()));
							})
						]
					]
				]
			]

			// Button hints
			+ SVerticalBox::Slot().AutoHeight()
			[
				SNew(STextBlock)
				.Font(Font("Bold", 15)).ColorAndOpacity(Dim)
				.Text(FText::FromString(TEXT("[A] Select      [B] Back      [LB] [RB] Tabs      [D-Pad] Navigate      [Y] Reset Tab"
				                             "          Keyboard: Q E tabs, arrows, Enter, R reset, Backspace back, Tab closes")))
			]
		]
		]
	];

	RebuildTabs();
	RebuildRows();
}

int32 SDaedalusSettingsMenu::SettingIndex() const
{
	return Rows.IsValidIndex(Row) ? Rows[Row] : -1;
}

void SDaedalusSettingsMenu::RebuildTabs()
{
	TabBar->ClearChildren();
	auto Pill = [](const TCHAR* Label)
	{
		return SNew(SBorder)
			.BorderImage(White())
			.BorderBackgroundColor(FLinearColor(1.f, 1.f, 1.f, 0.10f))
			.Padding(FMargin(10.f, 4.f))
			[
				SNew(STextBlock).Text(FText::FromString(Label)).Font(Font("Bold", 13)).ColorAndOpacity(Dim)
			];
	};
	TabBar->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(0.f, 0.f, 26.f, 0.f)[Pill(TEXT("LB"))];
	const TArray<FString>& Tabs = FDaedalusSettings::Get().Tabs;
	for (int32 i = 0; i < Tabs.Num(); ++i)
	{
		TabBar->AddSlot().AutoWidth().Padding(0.f, 0.f, 34.f, 0.f)
		[
			SNew(SBorder)
			.BorderImage(White())
			.BorderBackgroundColor(Clear)
			.Padding(0.f)
			.OnMouseButtonDown_Lambda([this, i](const FGeometry&, const FPointerEvent&) { SelectTab(i); return FReply::Handled(); })
			[
				SNew(SVerticalBox)
				+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 10.f)
				[
					SNew(STextBlock)
					.Text(FText::FromString(Tabs[i]))
					.Font(Font("Bold", 19))
					.ColorAndOpacity_Lambda([this, i]() { return FSlateColor(i == Tab ? Ink : Dim); })
				]
				+ SVerticalBox::Slot().AutoHeight()
				[
					SNew(SBox).HeightOverride(3.f)
					[
						SNew(SImage).Image(White())
						.ColorAndOpacity_Lambda([this, i]() { return FSlateColor(i == Tab ? Accent : Clear); })
					]
				]
			]
		];
	}
	TabBar->AddSlot().AutoWidth().VAlign(VAlign_Center)[Pill(TEXT("RB"))];
}

void SDaedalusSettingsMenu::RebuildRows()
{
	FDaedalusSettings& S = FDaedalusSettings::Get();
	Rows = S.RowsOn(S.Tabs.IsValidIndex(Tab) ? S.Tabs[Tab] : FString());
	Row = FMath::Clamp(Row, 0, FMath::Max(0, Rows.Num() - 1));
	List->ClearChildren();
	RowWidgets.Reset();
	for (int32 r = 0; r < Rows.Num(); ++r)
	{
		const int32 Index = Rows[r];
		const bool bSlider = At(Index).Kind == EDaedalusSettingKind::Slider;
		auto Arrow = [this, r](const TCHAR* Glyph, int32 Dir)
		{
			return SNew(SBorder)
				.BorderImage(White())
				.BorderBackgroundColor(Clear)
				.Padding(FMargin(12.f, 6.f))
				.OnMouseButtonDown_Lambda([this, r, Dir](const FGeometry&, const FPointerEvent&) { Row = r; Adjust(Dir); return FReply::Handled(); })
				[
					SNew(STextBlock).Text(FText::FromString(Glyph)).Font(Font("Bold", 18))
					.ColorAndOpacity_Lambda([this, r]() { return FSlateColor(r == Row ? Ink : FLinearColor(1.f, 1.f, 1.f, 0.25f)); })
				];
		};
		TSharedRef<SWidget> Value = bSlider
			? StaticCastSharedRef<SWidget>(
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
				[
					SNew(SBox).WidthOverride(200.f).HeightOverride(6.f)
					[
						SNew(SOverlay)
						+ SOverlay::Slot()[SNew(SImage).Image(White()).ColorAndOpacity(Track)]
						+ SOverlay::Slot().HAlign(HAlign_Left)
						[
							SNew(SBox).WidthOverride_Lambda([Index]() { return FOptionalSize(200.f * At(Index).Fraction()); })
							[
								SNew(SImage).Image(White())
								.ColorAndOpacity_Lambda([this, r]() { return FSlateColor(r == Row ? Accent : Ink); })
							]
						]
					]
				]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(16.f, 0.f, 0.f, 0.f)
				[
					SNew(SBox).WidthOverride(64.f)
					[
						SNew(STextBlock).Font(Font("Bold", 18)).ColorAndOpacity(Ink)
						.Text_Lambda([Index]() { return FText::FromString(At(Index).Format()); })
					]
				])
			: StaticCastSharedRef<SWidget>(
				SNew(SBox).WidthOverride(280.f).HAlign(HAlign_Center)
				[
					SNew(STextBlock).Font(Font("Bold", 18))
					.Text_Lambda([Index]() { return FText::FromString(At(Index).Format()); })
					.ColorAndOpacity_Lambda([this, r]() { return FSlateColor(r == Row ? Accent : Ink); })
				]);

		TSharedRef<SWidget> RowWidget =
			SNew(SBorder)
			.BorderImage(White())
			.BorderBackgroundColor_Lambda([this, r]() { return FSlateColor(r == Row ? RowHot : RowIdle); })
			.Padding(0.f)
			.OnMouseButtonDown_Lambda([this, r](const FGeometry&, const FPointerEvent&) { Row = r; return FReply::Handled(); })
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().AutoWidth()
				[
					SNew(SBox).WidthOverride(4.f)
					[
						SNew(SImage).Image(White()).ColorAndOpacity_Lambda([this, r]() { return FSlateColor(r == Row ? Accent : Clear); })
					]
				]
				+ SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center).Padding(20.f, 16.f)
				[
					SNew(STextBlock).Text(FText::FromString(At(Index).Label)).Font(Font("Regular", 19)).ColorAndOpacity(Ink)
				]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Arrow(TEXT("<"), -1)]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Value]
				+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0.f, 0.f, 10.f, 0.f)[Arrow(TEXT(">"), +1)]
			];
		RowWidgets.Add(RowWidget);
		List->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, 6.f)[RowWidget];
	}
}

void SDaedalusSettingsMenu::SelectTab(int32 NewTab)
{
	const int32 N = FDaedalusSettings::Get().Tabs.Num();
	Tab = (NewTab % N + N) % N;
	Row = 0;
	RebuildRows();
	if (Scroll.IsValid())
	{
		Scroll->ScrollToStart();
	}
}

void SDaedalusSettingsMenu::MoveRow(int32 Dir)
{
	if (Rows.Num() == 0) return;
	Row = FMath::Clamp(Row + Dir, 0, Rows.Num() - 1);
	if (Scroll.IsValid() && RowWidgets.IsValidIndex(Row))
	{
		Scroll->ScrollDescendantIntoView(RowWidgets[Row], true, EDescendantScrollDestination::IntoView);
	}
}

void SDaedalusSettingsMenu::Changed()
{
	FDaedalusSettings::Get().PushCVars();
	FDaedalusSettings::Get().Save();
	OnChanged.ExecuteIfBound();
}

void SDaedalusSettingsMenu::Adjust(int32 Dir)
{
	const int32 I = SettingIndex();
	if (I >= 0 && At(I).Nudge(Dir))
	{
		Changed();
	}
}

void SDaedalusSettingsMenu::Accept()
{
	const int32 I = SettingIndex();
	if (I >= 0 && At(I).Activate())
	{
		Changed();
	}
}

void SDaedalusSettingsMenu::ResetTab()
{
	FDaedalusSettings& S = FDaedalusSettings::Get();
	if (S.Tabs.IsValidIndex(Tab))
	{
		S.ResetTab(S.Tabs[Tab]);
		Changed();
	}
}

void SDaedalusSettingsMenu::OpenSettings()
{
	bInSettings = true;
	SelectTab(Tab);
}

void SDaedalusSettingsMenu::Back()
{
	if (bInSettings)
	{
		bInSettings = false;   // B in settings returns to the pause list, like Halo Infinite
	}
	else
	{
		OnClose.ExecuteIfBound();
	}
}

void SDaedalusSettingsMenu::PauseSelect()
{
	switch (PauseRow)
	{
	case 0: OnClose.ExecuteIfBound(); break;
	case 1: OpenSettings(); break;
	case 2: OnRespawn.ExecuteIfBound(); OnClose.ExecuteIfBound(); break;
	default: break;
	}
}

FReply SDaedalusSettingsMenu::OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
	const FKey K = Event.GetKey();
	// Menu / Start / Tab / F10 always resume; B / Backspace step back one page.
	if (K == EKeys::Tab || K == EKeys::F10 || K == EKeys::Gamepad_Special_Right) { OnClose.ExecuteIfBound(); return FReply::Handled(); }
	if (K == EKeys::Gamepad_FaceButton_Right || K == EKeys::BackSpace) { Back(); return FReply::Handled(); }
	if (!bInSettings)
	{
		if (K == EKeys::Gamepad_FaceButton_Bottom || K == EKeys::Enter || K == EKeys::SpaceBar) { PauseSelect(); return FReply::Handled(); }
		if (K == EKeys::W) { PauseRow = FMath::Max(0, PauseRow - 1); return FReply::Handled(); }
		if (K == EKeys::S) { PauseRow = FMath::Min(2, PauseRow + 1); return FReply::Handled(); }
		return FReply::Unhandled();
	}
	if (K == EKeys::Gamepad_LeftShoulder || K == EKeys::Q) { SelectTab(Tab - 1); return FReply::Handled(); }
	if (K == EKeys::Gamepad_RightShoulder || K == EKeys::E) { SelectTab(Tab + 1); return FReply::Handled(); }
	if (K == EKeys::Gamepad_FaceButton_Bottom || K == EKeys::Enter || K == EKeys::SpaceBar) { Accept(); return FReply::Handled(); }
	if (K == EKeys::Gamepad_FaceButton_Top || K == EKeys::R) { ResetTab(); return FReply::Handled(); }
	if (K == EKeys::W) { MoveRow(-1); return FReply::Handled(); }
	if (K == EKeys::S) { MoveRow(+1); return FReply::Handled(); }
	if (K == EKeys::A) { Adjust(-1); return FReply::Handled(); }
	if (K == EKeys::D) { Adjust(+1); return FReply::Handled(); }
	return FReply::Unhandled();   // arrows, d-pad and the left stick arrive as navigation
}

FNavigationReply SDaedalusSettingsMenu::OnNavigation(const FGeometry& Geometry, const FNavigationEvent& Event)
{
	if (!bInSettings)
	{
		if (Event.GetNavigationType() == EUINavigation::Up) { PauseRow = FMath::Max(0, PauseRow - 1); return FNavigationReply::Stop(); }
		if (Event.GetNavigationType() == EUINavigation::Down) { PauseRow = FMath::Min(2, PauseRow + 1); return FNavigationReply::Stop(); }
		return FNavigationReply::Stop();
	}
	switch (Event.GetNavigationType())
	{
	case EUINavigation::Up: MoveRow(-1); break;
	case EUINavigation::Down: MoveRow(+1); break;
	case EUINavigation::Left: Adjust(-1); break;
	case EUINavigation::Right: Adjust(+1); break;
	default: return SCompoundWidget::OnNavigation(Geometry, Event);
	}
	return FNavigationReply::Stop();
}
