// SPDX-License-Identifier: MIT

#include "SDaedalusDialogue.h"

#include "Styling/CoreStyle.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SSpacer.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

using namespace daedalus::dlg;

namespace
{
	const FSlateBrush* White() { return FCoreStyle::Get().GetBrush("GenericWhiteBox"); }
	constexpr float BoxW = 980.f;
}

void SDaedalusDialogue::Construct(const FArguments& InArgs)
{
	OnOutcome = InArgs._OnOutcome;
	OnSfx = InArgs._OnSfx;
	Model.SetStyle(StyleNamed(TCHAR_TO_UTF8(*InArgs._Theme)));
	ChildSlot
	[
		SNew(SOverlay)
		+ SOverlay::Slot().HAlign(HAlign_Center).VAlign(VAlign_Bottom).Padding(0.f, 0.f, 0.f, 48.f)
		[
			SAssignNew(Body, SBox).WidthOverride(BoxW)
		]
	];
	Rebuild();
}

void SDaedalusDialogue::Say(const FString& Speaker, const FString& Text, const TArray<FString>& Choices)
{
	std::vector<std::string> C;
	for (const FString& S : Choices) C.push_back(TCHAR_TO_UTF8(*S));
	Model.Say(TCHAR_TO_UTF8(*Speaker), TCHAR_TO_UTF8(*Text), C);
	Rebuild();
}

FLinearColor SDaedalusDialogue::Col(uint32 Rgb, float Alpha) const
{
	return FLinearColor(FColor((Rgb >> 16) & 0xFF, (Rgb >> 8) & 0xFF, Rgb & 0xFF, static_cast<uint8>(Alpha * 255.f)));
}

FSlateFontInfo SDaedalusDialogue::Font(const char* Weight, int32 Size) const
{
	return FCoreStyle::GetDefaultFontStyle(Model.GetStyle().Font == "PIXEL" ? "Mono" : Weight, Size);
}

void SDaedalusDialogue::Rebuild()
{
	if (!Body.IsValid()) return;
	if (!Model.Open()) { Body->SetContent(SNew(SSpacer)); return; }
	const Style& St = Model.GetStyle();
	const double Bounce = Model.TagBounce();
	TSharedRef<SVerticalBox> Lines = SNew(SVerticalBox);
	for (const std::string& L : Model.Visible())
	{
		Lines->AddSlot().AutoHeight().Padding(0.f, 2.f)
		[
			SNew(STextBlock).Text(FText::FromString(UTF8_TO_TCHAR(L.c_str()))).Font(Font("Regular", St.E == Era::Retro ? 22 : 24)).ColorAndOpacity(Col(St.Text))
		];
	}
	TSharedRef<SVerticalBox> Choices = SNew(SVerticalBox);
	if (Model.Choosing())
	{
		const std::vector<std::string>& C = Model.Current().Choices;
		for (int32 i = 0; i < static_cast<int32>(C.size()); ++i)
		{
			const bool bHot = i == Model.Cursor();
			Choices->AddSlot().AutoHeight().Padding(0.f, 2.f)
			[
				SNew(SBorder).BorderImage(White()).BorderBackgroundColor(bHot ? Col(St.Ink) : Col(St.Ink, 0.f)).Padding(FMargin(14.f, 4.f))
				[
					SNew(STextBlock).Text(FText::FromString(FString(bHot ? TEXT("> ") : TEXT("   ")) + UTF8_TO_TCHAR(C[static_cast<size_t>(i)].c_str())))
					.Font(Font("Bold", 20)).ColorAndOpacity(bHot ? Col(St.Panel) : Col(St.Text))
				]
			];
		}
	}
	Body->SetContent(
		SNew(SVerticalBox)
		// the name tag, sitting on the box's top edge, bouncing in for the modern era
		+ SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Left).Padding(FMargin(28.f, 0.f, 0.f, static_cast<float>(-6.0 + Bounce * 10.0)))
		[
			SNew(SBorder).BorderImage(White()).BorderBackgroundColor(Col(St.Name)).Padding(FMargin(16.f, 6.f))
			[
				SNew(STextBlock).Text(FText::FromString(UTF8_TO_TCHAR(Model.Tag().c_str()))).Font(Font("Bold", 20)).ColorAndOpacity(Col(St.Panel))
			]
		]
		+ SVerticalBox::Slot().AutoHeight()
		[
			SNew(SBorder).BorderImage(White()).BorderBackgroundColor(Col(St.Ink)).Padding(St.E == Era::Retro ? 3.f : 2.f)   // the rule
			[
				SNew(SBorder).BorderImage(White()).BorderBackgroundColor(Col(St.Panel, 0.96f)).Padding(FMargin(28.f, 20.f))
				[
					SNew(SHorizontalBox)
					+ SHorizontalBox::Slot().FillWidth(1.f)
					[
						SNew(SVerticalBox)
						+ SVerticalBox::Slot().AutoHeight()[Lines]
						+ SVerticalBox::Slot().AutoHeight().Padding(0.f, 8.f, 0.f, 0.f)[Choices]
					]
					+ SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Bottom)
					[
						SNew(STextBlock).Text(FText::FromString(Model.MoreArrow() ? TEXT("▼") : TEXT(" "))).Font(Font("Bold", 18)).ColorAndOpacity(Col(St.Ink))
					]
				]
			]
		]);
}

void SDaedalusDialogue::Advance(double Dt)
{
	Model.Tick(Dt);
	for (const std::string& S : Model.TakeSfx()) OnSfx.ExecuteIfBound(UTF8_TO_TCHAR(S.c_str()));
	// Redraw only when what is seen changed: the typed text, the arrow's blink, the choice cursor.
	FString Now;
	for (const std::string& L : Model.Visible()) { Now += UTF8_TO_TCHAR(L.c_str()); Now += TEXT("\n"); }
	const bool bArrow = Model.MoreArrow();
	const int32 Cursor = Model.Choosing() ? Model.Cursor() : -1;
	if (Now != LastVisible || bArrow != bLastArrow || Cursor != LastCursor || Model.TagBounce() > 0.0)
	{
		LastVisible = Now; bLastArrow = bArrow; LastCursor = Cursor;
		Rebuild();
	}
}

void SDaedalusDialogue::Tick(const FGeometry& Geometry, const double CurrentTime, const float DeltaTime)
{
	SCompoundWidget::Tick(Geometry, CurrentTime, DeltaTime);
	Advance(DeltaTime);
}

void SDaedalusDialogue::Press(Button B)
{
	Outcome O;
	const bool bDone = Model.Press(B, O);
	for (const std::string& S : Model.TakeSfx()) OnSfx.ExecuteIfBound(UTF8_TO_TCHAR(S.c_str()));
	Rebuild();
	if (bDone) OnOutcome.ExecuteIfBound(O);
}

FString SDaedalusDialogue::Input(const FString& Command)
{
	FString Key, Rest;
	if (!Command.Split(TEXT(":"), &Key, &Rest)) Key = Command;
	if (Key == TEXT("a")) Press(Button::A);
	else if (Key == TEXT("b")) Press(Button::B);
	else if (Key == TEXT("up")) Press(Button::Up);
	else if (Key == TEXT("down")) Press(Button::Down);
	else if (Key == TEXT("tick")) Advance(FCString::Atod(*Rest));
	else if (Key != TEXT("state")) return FString::Printf(TEXT("unknown command %s"), *Command);
	return Describe();
}

FReply SDaedalusDialogue::OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
	const FKey K = Event.GetKey();
	if (K == EKeys::Enter || K == EKeys::SpaceBar || K == EKeys::E || K == EKeys::Gamepad_FaceButton_Bottom || K == EKeys::Gamepad_FaceButton_Left) { Press(Button::A); return FReply::Handled(); }
	if (K == EKeys::BackSpace || K == EKeys::Escape || K == EKeys::Gamepad_FaceButton_Right) { Press(Button::B); return FReply::Handled(); }
	if (K == EKeys::Up || K == EKeys::W || K == EKeys::Gamepad_DPad_Up) { Press(Button::Up); return FReply::Handled(); }
	if (K == EKeys::Down || K == EKeys::S || K == EKeys::Gamepad_DPad_Down) { Press(Button::Down); return FReply::Handled(); }
	return FReply::Unhandled();
}
