// SPDX-License-Identifier: MIT

#include "SDaedalusInventory.h"

#include "Styling/CoreStyle.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SUniformGridPanel.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

using namespace daedalus::inv;

namespace
{
	const FSlateBrush* White() { return FCoreStyle::Get().GetBrush("GenericWhiteBox"); }
	const FLinearColor Clear(0.f, 0.f, 0.f, 0.f);
	constexpr float PanelW = 1180.f, PanelH = 700.f;
}

void SDaedalusInventory::Construct(const FArguments& InArgs)
{
	OnClose = InArgs._OnClose;
	OnIntent = InArgs._OnIntent;
	ChildSlot
	[
		SNew(SOverlay)
		+ SOverlay::Slot()[SNew(SImage).Image(White()).ColorAndOpacity(FLinearColor(0.f, 0.f, 0.f, 0.55f))]
		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Center)
		[
			SAssignNew(Body, SBox).WidthOverride(PanelW).HeightOverride(PanelH)
		]
	];
}

std::map<std::string, int> SDaedalusInventory::ToCounts(const TMap<FString, int32>& Bag)
{
	std::map<std::string, int> Out;
	for (const auto& P : Bag) Out[TCHAR_TO_UTF8(*P.Key)] = P.Value;
	return Out;
}

std::map<std::string, std::string> SDaedalusInventory::ToWorn(const TMap<FString, FString>& Worn)
{
	std::map<std::string, std::string> Out;
	for (const auto& P : Worn) Out[TCHAR_TO_UTF8(*P.Key)] = TCHAR_TO_UTF8(*P.Value);
	return Out;
}

void SDaedalusInventory::Open(const Catalog& Catalog, const TMap<FString, int32>& Bag, const TMap<FString, FString>& Worn)
{
	Model.Open(Catalog, ToCounts(Bag), ToWorn(Worn), ThemeNamed(Catalog.Theme).Cols);
	Rebuild();
}

void SDaedalusInventory::Refresh(const TMap<FString, int32>& Bag, const TMap<FString, FString>& Worn)
{
	Model.Refresh(ToCounts(Bag), ToWorn(Worn));
	Rebuild();
}

FLinearColor SDaedalusInventory::Col(uint32 Rgb, float Alpha) const
{
	return FLinearColor(FColor((Rgb >> 16) & 0xFF, (Rgb >> 8) & 0xFF, Rgb & 0xFF, static_cast<uint8>(Alpha * 255.f)));
}

FSlateFontInfo SDaedalusInventory::Font(const char* Weight, int32 Size) const
{
	// The retro theme (the 8-bit realm's kit) sets in the engine's monospace; every other realm in the default face.
	return FCoreStyle::GetDefaultFontStyle(Model.Look().Font == "PIXEL" ? "Mono" : Weight, Size);
}

void SDaedalusInventory::Rebuild()
{
	if (!Body.IsValid()) return;
	const Theme& T = Model.Look();
	const Catalog* C = Model.Current();
	const FString Realm = C ? UTF8_TO_TCHAR(C->Realm.c_str()) : TEXT("");
	// The decor word is what the realm hangs on the panel: a stripe in its ink for now; Sol's materials later.
	Body->SetContent(
		SNew(SBorder).BorderImage(White()).BorderBackgroundColor(Col(T.Panel, 0.94f)).Padding(FMargin(T.Corner + 18.f, 18.f))
		[
			SNew(SVerticalBox)
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 0.f, 0.f, 8.f)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().FillWidth(1.f)
				[
					SNew(STextBlock).Text(FText::FromString(Realm)).Font(Font("Bold", 26)).ColorAndOpacity(Col(T.Ink))
				]
				+ SHorizontalBox::Slot().AutoWidth()
				[
					SNew(STextBlock).Text(FText::FromString(UTF8_TO_TCHAR(T.Decor.c_str()))).Font(Font("Regular", 14)).ColorAndOpacity(Col(T.Dim))
				]
			]
			+ SVerticalBox::Slot().AutoHeight()[SNew(SBox).HeightOverride(3.f)[SNew(SImage).Image(White()).ColorAndOpacity(Col(T.Ink))]]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 10.f)[BuildTabs()]
			+ SVerticalBox::Slot().FillHeight(1.f)
			[
				SNew(SHorizontalBox)
				+ SHorizontalBox::Slot().FillWidth(0.62f).Padding(0.f, 0.f, 14.f, 0.f)[BuildGrid()]
				+ SHorizontalBox::Slot().FillWidth(0.38f)[BuildDetails()]
			]
			+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 10.f, 0.f, 0.f)
			[
				SNew(STextBlock).Font(Font("Bold", 14)).ColorAndOpacity(Col(T.Dim))
				.Text(FText::FromString(TEXT("[LB] [RB] Tabs     [A] Actions     [B] Back          Keyboard: Q E tabs, arrows, Enter, Backspace / I to close")))
			]
		]);
}

TSharedRef<SWidget> SDaedalusInventory::BuildTabs() const
{
	const Theme& T = Model.Look();
	TSharedRef<SHorizontalBox> Strip = SNew(SHorizontalBox);
	const Catalog* C = Model.Current();
	if (!C) return Strip;
	for (int32 i = 0; i < static_cast<int32>(C->Tabs.size()); ++i)
	{
		const bool bOn = i == Model.TabIndex();
		const FString Label = FString::Printf(TEXT("%s  %d"), UTF8_TO_TCHAR(C->Tabs[static_cast<size_t>(i)].c_str()), Model.CountIn(i));
		Strip->AddSlot().AutoWidth().Padding(0.f, 0.f, 6.f, 0.f)
		[
			SNew(SBorder).BorderImage(White()).BorderBackgroundColor(bOn ? Col(T.Ink) : Col(T.Ink, 0.12f)).Padding(FMargin(16.f, 7.f))
			[
				SNew(STextBlock).Text(FText::FromString(Label)).Font(Font("Bold", 17)).ColorAndOpacity(bOn ? Col(T.Panel) : Col(T.Text))
			]
		];
	}
	return Strip;
}

TSharedRef<SWidget> SDaedalusInventory::BuildGrid() const
{
	const Theme& T = Model.Look();
	TSharedRef<SUniformGridPanel> Grid = SNew(SUniformGridPanel).SlotPadding(FMargin(4.f));
	const std::vector<Entry>& Rows = Model.Rows();
	if (Rows.empty())
	{
		return SNew(SBorder).BorderImage(White()).BorderBackgroundColor(Col(T.Ink, 0.06f)).Padding(24.f).HAlign(HAlign_Center).VAlign(VAlign_Center)
		[
			SNew(STextBlock).Text(FText::FromString(TEXT("Nothing here yet."))).Font(Font("Regular", 20)).ColorAndOpacity(Col(T.Dim))
		];
	}
	const int32 Cols = Model.Cols();
	for (int32 i = 0; i < static_cast<int32>(Rows.size()); ++i)
	{
		const Entry& E = Rows[static_cast<size_t>(i)];
		const bool bSel = i == Model.Cursor();
		const FString Name = UTF8_TO_TCHAR(E.Def->Name.c_str());
		const FString Count = E.Count > 1 ? FString::Printf(TEXT("x%d"), E.Count) : FString();
		Grid->AddSlot(i % Cols, i / Cols)
		[
			SNew(SBorder).BorderImage(White()).BorderBackgroundColor(bSel ? Col(T.Focus, 0.9f) : Col(T.Ink, 0.10f)).Padding(2.f)
			[
				SNew(SBorder).BorderImage(White()).BorderBackgroundColor(Col(T.Panel, 0.9f)).Padding(FMargin(10.f, 8.f))
				[
					SNew(SVerticalBox)
					+ SVerticalBox::Slot().AutoHeight()
					[
						SNew(STextBlock).Text(FText::FromString(Name)).Font(Font("Bold", 15)).ColorAndOpacity(bSel ? Col(T.Hot) : Col(T.Text)).AutoWrapText(true)
					]
					+ SVerticalBox::Slot().AutoHeight()
					[
						SNew(SHorizontalBox)
						+ SHorizontalBox::Slot().FillWidth(1.f)[SNew(STextBlock).Text(FText::FromString(Count)).Font(Font("Regular", 13)).ColorAndOpacity(Col(T.Dim))]
						+ SHorizontalBox::Slot().AutoWidth()[SNew(STextBlock).Text(FText::FromString(E.Equipped ? TEXT("WORN") : TEXT(""))).Font(Font("Bold", 12)).ColorAndOpacity(Col(T.Hot))]
					]
				]
			]
		];
	}
	return Grid;
}

TSharedRef<SWidget> SDaedalusInventory::BuildDetails() const
{
	const Theme& T = Model.Look();
	const Entry* E = Model.Selected();
	TSharedRef<SVerticalBox> Box = SNew(SVerticalBox);
	if (!E)
	{
		Box->AddSlot().AutoHeight()[SNew(STextBlock).Text(FText::FromString(TEXT("Pick something."))).Font(Font("Regular", 18)).ColorAndOpacity(Col(T.Dim))];
	}
	else
	{
		Box->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, 6.f)
		[
			SNew(STextBlock).Text(FText::FromString(UTF8_TO_TCHAR(E->Def->Name.c_str()))).Font(Font("Bold", 24)).ColorAndOpacity(Col(T.Hot))
		];
		const FString Meta = FString::Printf(TEXT("%s%s%s"), UTF8_TO_TCHAR(E->Def->Tab.c_str()),
			E->Def->Slot.empty() ? TEXT("") : *FString::Printf(TEXT("   slot %s"), UTF8_TO_TCHAR(E->Def->Slot.c_str())),
			E->Count > 1 ? *FString::Printf(TEXT("   x%d"), E->Count) : TEXT(""));
		Box->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, 12.f)[SNew(STextBlock).Text(FText::FromString(Meta)).Font(Font("Regular", 14)).ColorAndOpacity(Col(T.Dim))];
		Box->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, 16.f)
		[
			SNew(STextBlock).Text(FText::FromString(UTF8_TO_TCHAR(E->Def->Detail.c_str()))).Font(Font("Regular", 17)).ColorAndOpacity(Col(T.Text)).AutoWrapText(true)
		];
		const std::vector<std::string> Labels = Model.ActionLabels();
		for (int32 i = 0; i < static_cast<int32>(Labels.size()); ++i)
		{
			const bool bHot = Model.ActionsShown() && i == Model.ActionIndex();
			Box->AddSlot().AutoHeight().Padding(0.f, 2.f)
			[
				SNew(SBorder).BorderImage(White()).BorderBackgroundColor(bHot ? Col(T.Focus) : Col(T.Ink, Model.ActionsShown() ? 0.10f : 0.05f)).Padding(FMargin(14.f, 8.f))
				[
					SNew(STextBlock).Text(FText::FromString(UTF8_TO_TCHAR(Labels[static_cast<size_t>(i)].c_str()))).Font(Font("Bold", 16))
					.ColorAndOpacity(bHot ? Col(T.Panel) : Model.ActionsShown() ? Col(T.Text) : Col(T.Dim))
				]
			];
		}
	}
	return SNew(SBorder).BorderImage(White()).BorderBackgroundColor(Col(T.Ink, 0.06f)).Padding(FMargin(18.f, 16.f))[Box];
}

FString SDaedalusInventory::Input(const FString& Command)
{
	Intent I;
	if (Command == TEXT("tab+")) Model.NextTab();
	else if (Command == TEXT("tab-")) Model.PrevTab();
	else if (Command == TEXT("up")) Model.Up();
	else if (Command == TEXT("down")) Model.Down();
	else if (Command == TEXT("left")) Model.Left();
	else if (Command == TEXT("right")) Model.Right();
	else if (Command == TEXT("accept")) { if (Model.Confirm(I)) OnIntent.ExecuteIfBound(I); }
	else if (Command == TEXT("back")) { if (Model.Back()) { OnClose.ExecuteIfBound(); return TEXT("closed"); } }
	else return FString::Printf(TEXT("unknown command %s"), *Command);
	Rebuild();
	return Describe();
}

FReply SDaedalusInventory::OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
	const FKey K = Event.GetKey();
	if (K == EKeys::Gamepad_LeftShoulder || K == EKeys::Q) { Input(TEXT("tab-")); return FReply::Handled(); }
	if (K == EKeys::Gamepad_RightShoulder || K == EKeys::E) { Input(TEXT("tab+")); return FReply::Handled(); }
	if (K == EKeys::Up || K == EKeys::Gamepad_DPad_Up) { Input(TEXT("up")); return FReply::Handled(); }
	if (K == EKeys::Down || K == EKeys::Gamepad_DPad_Down) { Input(TEXT("down")); return FReply::Handled(); }
	if (K == EKeys::Left || K == EKeys::Gamepad_DPad_Left) { Input(TEXT("left")); return FReply::Handled(); }
	if (K == EKeys::Right || K == EKeys::Gamepad_DPad_Right) { Input(TEXT("right")); return FReply::Handled(); }
	if (K == EKeys::Enter || K == EKeys::SpaceBar || K == EKeys::Gamepad_FaceButton_Bottom) { Input(TEXT("accept")); return FReply::Handled(); }
	if (K == EKeys::BackSpace || K == EKeys::Escape || K == EKeys::I || K == EKeys::Gamepad_FaceButton_Right) { Input(TEXT("back")); return FReply::Handled(); }
	return FReply::Unhandled();
}

FNavigationReply SDaedalusInventory::OnNavigation(const FGeometry& Geometry, const FNavigationEvent& Event)
{
	switch (Event.GetNavigationType())
	{
	case EUINavigation::Up: Input(TEXT("up")); break;
	case EUINavigation::Down: Input(TEXT("down")); break;
	case EUINavigation::Left: Input(TEXT("left")); break;
	case EUINavigation::Right: Input(TEXT("right")); break;
	default: break;
	}
	return FNavigationReply::Stop();
}
