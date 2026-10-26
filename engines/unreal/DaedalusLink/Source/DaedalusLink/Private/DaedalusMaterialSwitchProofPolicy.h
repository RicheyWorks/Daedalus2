// SPDX-License-Identifier: MIT
#pragma once
#if WITH_EDITOR
#include "CoreMinimal.h"

/** Pure admission predicates shared by the factual native switch producer/tests.
 * They consume explicit observations, never query objects or invent defaults.
 * Refusal leaves output values unchanged; callers must check the returned bool.
 */
namespace DaedalusMaterialSwitchProofPolicy
{
struct FParameterProof
{
	int32 InfoCount = 0, GuidCount = 0, Matches = 0;
	bool bEnumerationComplete = false, bContextExact = false, bNodeGuidValid = false;
	bool bReturnedGuidExact = false, bQuerySucceeded = false;
	bool bDynamicKnown = false, bDynamic = false, bValue = false;
};

inline bool ParameterValue(const FParameterProof& Proof, bool& Value)
{
	if (!Proof.bEnumerationComplete || Proof.InfoCount < 1 || Proof.InfoCount > 128
		|| Proof.InfoCount != Proof.GuidCount || Proof.Matches != 1
		|| !Proof.bContextExact || !Proof.bNodeGuidValid || !Proof.bReturnedGuidExact
		|| !Proof.bQuerySucceeded || !Proof.bDynamicKnown || Proof.bDynamic) return false;
	Value = Proof.bValue;
	return true;
}

struct FBoolProof
{
	bool bConnected = false, bDefaultKnown = false, bDefault = false;
	bool bUniqueBinding = false, bTypedStaticBool = false, bValueKnown = false, bValue = false;
	int32 FunctionInputType = -1; // -1: direct StaticBool; 8: uniquely bound StaticBool input.
};

inline bool StaticValue(const FBoolProof& Proof, bool& Value)
{
	if (!Proof.bConnected)
	{
		if (!Proof.bDefaultKnown) return false;
		Value = Proof.bDefault;
		return true;
	}
	const bool bDirect = !Proof.bUniqueBinding && Proof.FunctionInputType == -1;
	const bool bBoundStatic = Proof.bUniqueBinding && Proof.FunctionInputType == 8;
	if (!Proof.bTypedStaticBool || !Proof.bValueKnown || (!bDirect && !bBoundStatic)) return false;
	Value = Proof.bValue;
	return true;
}

struct FBranch
{
	bool bPresent = false, bTraceDirect = false, bReroute = false, bOwnerExact = false;
};

inline bool BothDirect(const FBranch& A, const FBranch& B)
{
	return A.bPresent && A.bTraceDirect && !A.bReroute && A.bOwnerExact
		&& B.bPresent && B.bTraceDirect && !B.bReroute && B.bOwnerExact;
}

enum class ELeaf { StaticBool, RGB, Scalar, Unsupported };

/** Eligibility only; actual typed values/masks/finite checks remain producer facts. */
inline bool ChosenLeaf(ELeaf Actual, ELeaf Expected, bool bPrimary, bool bOutputValid,
	bool bMaskContext, bool bOwnerExact)
{
	return Actual != ELeaf::Unsupported && Expected != ELeaf::Unsupported && Actual == Expected
		&& bPrimary && bOutputValid && bMaskContext && bOwnerExact;
}

struct FUsage
{
	int32 Roots = 0, Metadata = 0, Details = 0, Queries = 0, RootDetails = 0;
	bool TryRoot()
	{
		if (Roots >= 3) return false;
		++Roots; RootDetails = 0;
		return true;
	}
	bool TryMetadata()
	{
		if (Roots == 0 || Metadata >= 9) return false;
		++Metadata; return true;
	}
	bool TryDetail()
	{
		if (Roots == 0 || Details >= 15 || RootDetails >= 5) return false;
		++Details; ++RootDetails; return true;
	}
	bool TryQuery()
	{
		if (Roots == 0 || Queries >= 3) return false;
		++Queries; return true;
	}
	/** Caller supplies prospective count for its own lane (first edge1, second2). */
	bool TryEdge(int32 LaneEdges) const { return Roots > 0 && LaneEdges >= 1 && LaneEdges <= 2; }
};
} // namespace DaedalusMaterialSwitchProofPolicy
#endif
