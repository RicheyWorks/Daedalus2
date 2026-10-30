// SPDX-License-Identifier: MIT
// ======================================================================================================
//  STUB - NOT COMPILED, NOT WIRED IN. For later, when it is our turn in the Unreal editor.
//  Thin UE wrapper over the engine-free daedalus_sidecar library. Nothing here is imported by any module
//  today; no .Build.cs references it. Keep all logic in ../src (engine-free, unit tested) and only convert
//  types here.
// ======================================================================================================
#pragma once
#if 0  // enable when a UE module (e.g. DaedalusLink) adds daedalus_sidecar to its include/link paths

#include "CoreMinimal.h"
#include "daedalus/sidecar/sidecar.hpp"

namespace DaedalusSidecarUE
{
    inline FVector ToFVector(const daedalus::sidecar::Vec3& V) { return FVector(V[0], V[1], V[2]); }
    inline FRotator ToFRotator(const daedalus::sidecar::Rotator& R) { return FRotator(R.pitch, R.yaw, R.roll); }

    // Relative transform for a socket, sidecar-authoritative (use instead of the native socket rotation).
    inline bool GetSocketRelative(const daedalus::sidecar::SocketRegistry& Reg, const FString& Asset, const FString& Socket, FTransform& Out)
    {
        const auto* F = Reg.sockets(TCHAR_TO_UTF8(*Asset));
        if (!F) return false;
        const auto* S = F->socket(TCHAR_TO_UTF8(*Socket));
        if (!S) return false;
        Out = FTransform(ToFRotator(S->rotation), ToFVector(S->locationCm));
        return true;
    }

    // Placement yaw for Blender-built meshes (front = Blender -Y = UE +Y): apply on the actor/component.
    inline FRotator PlacementRotation() { return FRotator(0.0, daedalus::sidecar::kPlacementYawDeg, 0.0); }

    // Open pose for a hinged mover, relative to its closed pose.
    inline bool GetHingeOpen(const daedalus::sidecar::SocketRegistry& Reg, const FString& Asset, const FString& Mover, FRotator& Out)
    {
        const auto* F = Reg.sockets(TCHAR_TO_UTF8(*Asset));
        const auto* H = F ? F->hingeFor(TCHAR_TO_UTF8(*Mover)) : nullptr;
        if (!H) return false;
        Out = ToFRotator(H->openUe);
        return true;
    }
}

#endif  // stub
