// SPDX-License-Identifier: MIT

#include "SDaedalusRealm.h"

#include "DaedalusLinkModule.h"
#include "Containers/Ticker.h"
#include "Engine/Texture2D.h"
#include "RHITypes.h"
#include "HAL/IConsoleManager.h"
#include "HttpModule.h"
#include "ImageCore.h"
#include "ImageUtils.h"
#include "Interfaces/IHttpRequest.h"
#include "Styling/CoreStyle.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScaleBox.h"

namespace DR = daedalus::realm;

static TAutoConsoleVariable<FString> CVarJukebox(TEXT("daedalus.Jukebox"), TEXT(""),
	TEXT("Where the 8-bit realm sends its music cues and sound events (POST JSON {cue, sfx}); empty: log only."));

void SDaedalusRealm::Construct(const FArguments& InArgs)
{
	OnExit = InArgs._OnExit;
	Pixels.SetNumZeroed(DR::ScreenW * DR::ScreenH);
	UTexture2D* T = UTexture2D::CreateTransient(DR::ScreenW, DR::ScreenH, PF_B8G8R8A8);
	T->Filter = TF_Nearest;   // square pixels, no smearing
	T->SRGB = true;
	T->NeverStream = true;
	T->UpdateResource();
	Texture.Reset(T);
	Brush = MakeShared<FSlateBrush>();
	Brush->SetResourceObject(T);
	Brush->ImageSize = FVector2D(DR::ScreenW, DR::ScreenH);
	Brush->DrawAs = ESlateBrushDrawType::Image;

	ChildSlot
	[
		SNew(SBorder)
		.BorderImage(FCoreStyle::Get().GetBrush("GenericWhiteBox"))
		.BorderBackgroundColor(FLinearColor::Black)
		.Padding(0.f)
		[
			SNew(SScaleBox)
			.Stretch(EStretch::ScaleToFit)
			[
				SNew(SBox).WidthOverride(DR::ScreenW).HeightOverride(DR::ScreenH)
				[
					SNew(SImage).Image(Brush.Get())
				]
			]
		]
	];
	Refresh();
	// The game runs on the core ticker, not in Slate's Tick: Slate stops ticking a widget when the window is
	// minimized or hidden, and the realm (and the harness driving it) must keep going regardless.
	CoreTickHandle = FTSTicker::GetCoreTicker().AddTicker(FTickerDelegate::CreateSP(this, &SDaedalusRealm::CoreTick));
}

SDaedalusRealm::~SDaedalusRealm()
{
	FTSTicker::GetCoreTicker().RemoveTicker(CoreTickHandle);
	Brush.Reset();
	Texture.Reset();
}

bool SDaedalusRealm::LoadSpec(const FString& Spec, FString& Error)
{
	std::string Err;
	const bool Ok = Core.Load(TCHAR_TO_UTF8(*Spec), Err);
	Error = UTF8_TO_TCHAR(Err.c_str());
	bExitSent = false;
	Refresh();
	return Ok;
}

void SDaedalusRealm::RestoreSave(const FString& Save)
{
	if (!Save.IsEmpty()) Core.Restore(TCHAR_TO_UTF8(*Save));
}

FString SDaedalusRealm::SaveText() const
{
	return Core.IsLoaded() ? FString(UTF8_TO_TCHAR(Core.Save().c_str())) : FString();
}

void SDaedalusRealm::Refresh()
{
	const DR::Frame& F = Core.Render();
	for (int32 i = 0; i < DR::ScreenW * DR::ScreenH; ++i)
	{
		const uint32 C = F.Px[static_cast<size_t>(i)];
		Pixels[i] = FColor(static_cast<uint8>(C >> 16), static_cast<uint8>(C >> 8), static_cast<uint8>(C), 255);
	}
	if (!Texture.IsValid() || !Texture->GetResource()) return;
	// The render thread copies later; give it its own buffer and let it free that buffer when done.
	const int32 Bytes = DR::ScreenW * DR::ScreenH * 4;
	uint8* Copy = new uint8[Bytes];
	FMemory::Memcpy(Copy, Pixels.GetData(), Bytes);
	FUpdateTextureRegion2D* Region = new FUpdateTextureRegion2D(0, 0, 0, 0, DR::ScreenW, DR::ScreenH);
	Texture->UpdateTextureRegions(0, 1, Region, DR::ScreenW * 4, 4, Copy,
		[](uint8* Data, const FUpdateTextureRegion2D* R) { delete[] Data; delete R; });
}

bool SDaedalusRealm::CapturePng(const FString& Path, int32 Scale)
{
	Scale = FMath::Clamp(Scale, 1, 8);
	Refresh();
	const int32 W = DR::ScreenW * Scale, H = DR::ScreenH * Scale;
	TArray<FColor> Big;
	Big.SetNumUninitialized(W * H);
	for (int32 Y = 0; Y < H; ++Y)
		for (int32 X = 0; X < W; ++X) Big[Y * W + X] = Pixels[(Y / Scale) * DR::ScreenW + X / Scale];
	const FImageView View(Big.GetData(), W, H, EGammaSpace::sRGB);
	return FImageUtils::SaveImageByExtension(*Path, View);
}

void SDaedalusRealm::Jukebox()
{
	const FString Cue = UTF8_TO_TCHAR(Core.MusicCue().c_str());
	const std::vector<std::string> Sfx = Core.TakeSfx();
	const bool NewCue = Cue != LastCue;
	if (!NewCue && Sfx.empty()) return;
	if (NewCue) UE_LOG(LogDaedalus, Log, TEXT("Realm cue %s"), *Cue);
	LastCue = Cue;
	const FString Url = CVarJukebox.GetValueOnGameThread();
	if (Url.IsEmpty()) return;
	FString Body = FString::Printf(TEXT("{\"cue\":\"%s\",\"changed\":%s,\"sfx\":["), *Cue, NewCue ? TEXT("true") : TEXT("false"));
	for (size_t i = 0; i < Sfx.size(); ++i) Body += FString::Printf(TEXT("%s\"%s\""), i ? TEXT(",") : TEXT(""), UTF8_TO_TCHAR(Sfx[i].c_str()));
	Body += TEXT("]}");
	TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Req = FHttpModule::Get().CreateRequest();
	Req->SetURL(Url);
	Req->SetVerb(TEXT("POST"));
	Req->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
	Req->SetContentAsString(Body);
	Req->ProcessRequest();
}

bool SDaedalusRealm::CoreTick(float DeltaTime)
{
	Core.Tick(FMath::Min(DeltaTime, 0.1f));
	Jukebox();
	if (Core.WantsExit() && !bExitSent)
	{
		bExitSent = true;
		OnExit.ExecuteIfBound();
	}
	return true;
}

void SDaedalusRealm::Tick(const FGeometry& AllottedGeometry, const double InCurrentTime, const float InDeltaTime)
{
	SCompoundWidget::Tick(AllottedGeometry, InCurrentTime, InDeltaTime);
	Refresh();   // drawing only; the game itself runs in CoreTick
}

bool SDaedalusRealm::MapKey(const FKey& Key, DR::Button& Out)
{
	if (Key == EKeys::Up || Key == EKeys::W || Key == EKeys::Gamepad_DPad_Up) { Out = DR::Button::Up; return true; }
	if (Key == EKeys::Down || Key == EKeys::S || Key == EKeys::Gamepad_DPad_Down) { Out = DR::Button::Down; return true; }
	if (Key == EKeys::Left || Key == EKeys::A || Key == EKeys::Gamepad_DPad_Left) { Out = DR::Button::Left; return true; }
	if (Key == EKeys::Right || Key == EKeys::D || Key == EKeys::Gamepad_DPad_Right) { Out = DR::Button::Right; return true; }
	if (Key == EKeys::Enter || Key == EKeys::SpaceBar || Key == EKeys::Z || Key == EKeys::E || Key == EKeys::Gamepad_FaceButton_Bottom) { Out = DR::Button::A; return true; }
	if (Key == EKeys::BackSpace || Key == EKeys::X || Key == EKeys::Q || Key == EKeys::Gamepad_FaceButton_Right) { Out = DR::Button::B; return true; }
	if (Key == EKeys::Tab || Key == EKeys::Gamepad_Special_Right) { Out = DR::Button::Start; return true; }
	return false;
}

FReply SDaedalusRealm::OnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
	DR::Button B;
	if (!MapKey(Event.GetKey(), B)) return FReply::Unhandled();
	if (!Event.IsRepeat()) Core.Press(B);   // holding is the core's business: it keeps walking
	return FReply::Handled();
}

FReply SDaedalusRealm::OnKeyUp(const FGeometry& Geometry, const FKeyEvent& Event)
{
	DR::Button B;
	if (!MapKey(Event.GetKey(), B)) return FReply::Unhandled();
	Core.Release(B);
	return FReply::Handled();
}

FNavigationReply SDaedalusRealm::OnNavigation(const FGeometry& Geometry, const FNavigationEvent& Event)
{
	return FNavigationReply::Stop();   // focus never wanders off the realm
}

FReply SDaedalusRealm::OnAnalogValueChanged(const FGeometry& Geometry, const FAnalogInputEvent& Event)
{
	if (Event.GetKey() == EKeys::Gamepad_LeftX) StickX = Event.GetAnalogValue();
	else if (Event.GetKey() == EKeys::Gamepad_LeftY) StickY = Event.GetAnalogValue();
	else return FReply::Unhandled();
	int32 Dir = -1;
	if (FMath::Max(FMath::Abs(StickX), FMath::Abs(StickY)) > 0.55f)
		Dir = FMath::Abs(StickX) > FMath::Abs(StickY) ? (StickX > 0 ? 3 : 2) : (StickY > 0 ? 0 : 1);
	if (Dir != StickDir)
	{
		static const DR::Button Dirs[4] = {DR::Button::Up, DR::Button::Down, DR::Button::Left, DR::Button::Right};
		if (StickDir >= 0) Core.Release(Dirs[StickDir]);
		if (Dir >= 0) Core.Press(Dirs[Dir]);
		StickDir = Dir;
	}
	return FReply::Handled();
}
