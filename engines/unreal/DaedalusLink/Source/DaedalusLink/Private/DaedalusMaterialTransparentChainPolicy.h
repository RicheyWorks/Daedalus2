// SPDX-License-Identifier: MIT
#pragma once
#if WITH_EDITOR
#include "CoreMinimal.h"

/** Pure cached-fact predicates. No object access, graph evaluation or default promotion. */
namespace DaedalusMaterialTransparentChainPolicy
{
enum class ELane { Scalar, Vector3, StaticBool };
enum class EStepFailure { None, InvalidIdentity, Cycle, StepLimit, VisitLimit };

struct FTraversal
{
	struct FVisit { FString FrameId, NodePath; int32 OutputIndex = -1; };
	TArray<FVisit> Visited;
	int32 Steps = 0;
	EStepFailure Failure = EStepFailure::None;

	/** Marks implicit named-declaration ancestry without emitting another step. */
	bool TryVisit(const FString& FrameId, const FString& NodePath, int32 OutputIndex)
	{
		if (FrameId.IsEmpty() || NodePath.IsEmpty() || OutputIndex < 0)
		{ Failure = EStepFailure::InvalidIdentity; return false; }
		for (const FVisit& Visit : Visited)
			if (Visit.FrameId == FrameId && Visit.NodePath == NodePath && Visit.OutputIndex == OutputIndex)
			{ Failure = EStepFailure::Cycle; return false; }
		if (Visited.Num() >= 64) { Failure = EStepFailure::VisitLimit; return false; }
		Visited.Add({FrameId, NodePath, OutputIndex});
		Failure = EStepFailure::None;
		return true;
	}

	bool TryStep(const FString& FrameId, const FString& NodePath, int32 OutputIndex)
	{
		if (Steps >= 32) { Failure = EStepFailure::StepLimit; return false; }
		if (!TryVisit(FrameId, NodePath, OutputIndex)) return false;
		++Steps;
		return true;
	}
};

struct FBinding
{
	int32 Index = -1;
	FGuid BindingGuid, NodeGuid;
	FString NodePath;
	bool bPointerValid = false, bOwnerExact = false, bClassExact = false;
};

inline bool ValidBindings(const TArray<FBinding>& Rows, int32 DeclaredCount, int32 Cap)
{
	if ((Cap != 128 && Cap != 16) || DeclaredCount < 0 || DeclaredCount > Cap || Rows.Num() != DeclaredCount) return false;
	TSet<FGuid> Guids;
	TSet<FString> Paths;
	for (int32 Index = 0; Index < Rows.Num(); ++Index)
	{
		const FBinding& Row = Rows[Index];
		if (Row.Index != Index || !Row.BindingGuid.IsValid() || Row.BindingGuid != Row.NodeGuid
			|| Row.NodePath.IsEmpty() || !Row.bPointerValid || !Row.bOwnerExact || !Row.bClassExact
			|| Guids.Contains(Row.NodeGuid) || Paths.Contains(Row.NodePath)) return false;
		Guids.Add(Row.NodeGuid); Paths.Add(Row.NodePath);
	}
	return true;
}

struct FFrame
{
	FString Id, Parent, FunctionPath, CallerPath, CallerOwner;
	int32 InputsCount = 0, OutputsCount = 0;
	bool bFunctionExact = false, bCallerExact = false, bCachedBindingsComplete = false;
	TArray<FBinding> Inputs, Outputs;
};

struct FFrames
{
	explicit FFrames(const FString& InRootFunctionPath) : RootFunctionPath(InRootFunctionPath) {}
	FString RootFunctionPath;
	TArray<FFrame> Items;

	const FFrame* Find(const FString& Id) const
	{
		for (const FFrame& Frame : Items) if (Frame.Id == Id) return &Frame;
		return nullptr;
	}

	/** -1 is unknown; root has depth0, and admitted nested frames have depth1..4. */
	int32 Depth(const FString& Id) const
	{
		if (RootFunctionPath.IsEmpty()) return -1;
		FString Current = Id;
		for (int32 Depth = 0; Depth <= 4; ++Depth)
		{
			if (Current == TEXT("root")) return Depth;
			const FFrame* Frame = Find(Current);
			if (!Frame) return -1;
			Current = Frame->Parent;
		}
		return -1;
	}

	bool TryAdd(const FFrame& Frame)
	{
		if (RootFunctionPath.IsEmpty() || Items.Num() >= 4 || Frame.Id.IsEmpty() || Frame.Id == TEXT("root")
			|| Frame.Id == TEXT("material") || Frame.Id != Frame.CallerPath || Find(Frame.Id)
			|| Frame.FunctionPath.IsEmpty() || !Frame.bFunctionExact || !Frame.bCallerExact
			|| !Frame.bCachedBindingsComplete || !ValidBindings(Frame.Inputs, Frame.InputsCount, 128)
			|| !ValidBindings(Frame.Outputs, Frame.OutputsCount, 16)) return false;
		const int32 ParentDepth = Depth(Frame.Parent);
		if (ParentDepth < 0 || ParentDepth >= 4) return false;
		FString Current = Frame.Parent;
		for (int32 Depth = ParentDepth; Depth >= 0; --Depth)
		{
			const FFrame* ParentFrame = Current == TEXT("root") ? nullptr : Find(Current);
			if (Current != TEXT("root") && !ParentFrame) return false;
			const FString& FunctionPath = ParentFrame ? ParentFrame->FunctionPath : RootFunctionPath;
			if ((Current == Frame.Parent && Frame.CallerOwner != FunctionPath) || Frame.FunctionPath == FunctionPath) return false;
			if (!ParentFrame) break;
			Current = ParentFrame->Parent;
		}
		Items.Add(Frame);
		return true;
	}
};

inline bool InputType(ELane Lane, int32 Type)
{
	return (Lane == ELane::Scalar && Type == 0) || (Lane == ELane::Vector3 && Type == 2)
		|| (Lane == ELane::StaticBool && Type == 8);
}

inline bool InputBinding(ELane Lane, int32 Type, bool bPointerExact, bool bUniqueBinding, bool bOwnerExact)
{
	return InputType(Lane, Type) && bPointerExact && bUniqueBinding && bOwnerExact;
}

enum class ERoute { Reroute, NamedDeclaration, NamedUsage, FunctionOutput, FunctionInput, Unsupported };

inline bool RouteAllowed(ERoute Route, bool bOutputZero, bool bPointerExact, bool bOwnerExact)
{
	if (!bPointerExact || !bOwnerExact) return false;
	switch (Route)
	{
	case ERoute::Reroute:
	case ERoute::NamedDeclaration:
	case ERoute::NamedUsage:
	case ERoute::FunctionInput: return bOutputZero;
	case ERoute::FunctionOutput: return true; // exact selected index is checked against its complete output manifest.
	default: return false;
	}
}

inline bool NamedLink(const FGuid& DeclarationGuid, const FGuid& VariableGuid,
	bool bCachedPointerExact, bool bDeclarationValid, bool bOwnerExact)
{
	return DeclarationGuid.IsValid() && DeclarationGuid == VariableGuid
		&& bCachedPointerExact && bDeclarationValid && bOwnerExact;
}

/** Every field is an explicitly normalized0/1 cached mask observation. */
struct FMask { int32 Mask = 0, R = 0, G = 0, B = 0, A = 0; };

inline bool ValidMask(const FMask& Mask)
{
	return (Mask.Mask == 0 || Mask.Mask == 1) && (Mask.R == 0 || Mask.R == 1)
		&& (Mask.G == 0 || Mask.G == 1) && (Mask.B == 0 || Mask.B == 1) && (Mask.A == 0 || Mask.A == 1);
}

inline bool SameMask(const FMask& A, const FMask& B)
{
	return A.Mask == B.Mask && A.R == B.R && A.G == B.G && A.B == B.B && A.A == B.A;
}

inline bool EffectiveMasks(const FMask& Raw, const FMask& Selected, bool bOutputValid, FMask& Effective)
{
	if (!bOutputValid || !ValidMask(Raw) || !ValidMask(Selected)) return false;
	Effective = Raw.Mask == 0 ? Selected : Raw;
	return true;
}

inline bool LaneMask(ELane Lane, const FMask& Mask)
{
	if (!ValidMask(Mask)) return false;
	const bool bZero = !Mask.Mask && !Mask.R && !Mask.G && !Mask.B && !Mask.A;
	const bool bRGB = Mask.Mask && Mask.R && Mask.G && Mask.B && !Mask.A;
	return bZero || (Lane == ELane::Vector3 && bRGB);
}
} // namespace DaedalusMaterialTransparentChainPolicy
#endif
